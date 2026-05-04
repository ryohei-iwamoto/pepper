# -*- coding: utf-8 -*-
"""
pepper_runner.py - Pepper ソケットサーバー (Python 2.7)

chat_gpt.py からサブプロセスとして起動される。
ソケット経由でコマンドを受け取りPepperを制御する。

コマンド形式（優先順位順）:
    JSON形式（推奨）:
        {"speech":"...", "emotion":"happy", "action":"nod_gentle",
         "intensity":0.8, "gaze":"face"}

    レガシー形式（後方互換）:
        @text                            → pp.say(text, animated=True)
        $emotion                         → pp.emotion(emotion)
        $emotion:text                    → pp.emotion(emotion, text)
        $bow / $wave / $nod ...          → 物理アクション
        -                                → 終了

使い方:
    python pepper_runner.py 192.168.0.46 9559 12345
    （通常は chat_gpt.py から自動起動される）
"""
from __future__ import print_function
import sys
import os
import socket
import time
import json
import struct
import threading
import wave
import subprocess
import random
import select

# --- pepper_lib のパス設定 ---
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

# pepper_lib 内で SDK パスを自動追加するため、import するだけでOK
from pepper_lib import Pepper

# ---- 設定 ----
DEFAULT_PEPPER_IP   = "192.168.0.46"
DEFAULT_PEPPER_PORT = 9559
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 12345
BUFF_SIZE           = 8192

# ---- 感情 → LED色マッピング ----
_EMOTION_LED = {
    "happy":     (1.0, 0.9, 0.0),
    "excited":   (1.0, 0.5, 0.0),
    "sad":       (0.0, 0.3, 1.0),
    "angry":     (1.0, 0.1, 0.0),
    "surprised": (0.8, 0.0, 1.0),
    "thinking":  (0.0, 0.8, 1.0),
    "shy":       (1.0, 0.4, 0.6),
    "bored":     (0.4, 0.4, 0.4),
    "confident": (0.2, 1.0, 0.3),
    "grateful":  (1.0, 0.9, 0.6),
    "victory":   (0.0, 1.0, 0.3),
    "fearful":   (0.5, 0.0, 1.0),
    "neutral":   (1.0, 1.0, 1.0),
    "explain":   (0.3, 0.8, 1.0),
}

# ---- 視線方向 → HeadYaw/HeadPitch ----
_GAZE_TARGET = {
    "face":    ( 0.0,  0.0),
    "forward": ( 0.0,  0.0),
    "up":      ( 0.0, -0.4),
    "down":    ( 0.0,  0.25),
    "left":    ( 0.5,  0.0),
    "right":   (-0.5,  0.0),
    "away":    ( 0.7, -0.1),
    "side":    ( 0.4, -0.05),
}


def _set_led_for_emotion(pp, emotion):
    """感情に対応したLED色を設定する。"""
    rgb = _EMOTION_LED.get(emotion.lower(), (1.0, 1.0, 1.0))
    pp.set_led_color(rgb[0], rgb[1], rgb[2], 0.2)


def _gaze(pp, target):
    """頭の向きを設定する（0.25秒）。"""
    if not target:
        return
    coords = _GAZE_TARGET.get(target.lower())
    if coords is None:
        return
    yaw, pitch = coords
    try:
        pp.core.motion.angleInterpolation(
            ["HeadYaw", "HeadPitch"],
            [yaw, pitch],
            [0.25, 0.25],
            True
        )
    except Exception as e:
        print("[gaze error] {0}".format(e))


# ---- NAOqi オーディオストリーミング ----
# 方式A（推奨）: qi.Session + registerService (NAOqi 2.x)
#   PC→Pepperの既存TCP接続を双方向利用するためファイアウォール不要
# 方式B（フォールバック）: ALBroker + ALModule (NAOqi 1.x)
#   Pepperから PC へのインバウンド接続が必要（ファイアウォール例外が必要）

_audio_broker = None   # 方式B用グローバルブローカー
BROKER_AUDIO_PORT = 16384
_mic_module_seq = [0]

try:
    from naoqi import ALModule as _ALModule, ALBroker as _ALBroker, ALProxy as _ALProxy
    _NAOQI_AVAILABLE = True
except ImportError:
    _NAOQI_AVAILABLE = False

try:
    import qi as _qi
    _QI_AVAILABLE = True
except ImportError:
    _QI_AVAILABLE = False


if _NAOQI_AVAILABLE:
    class _AudioCapture(_ALModule):
        """
        Pepper の ALAudioDevice からリモートコールバックで音声を受信。
        VAD (音声区間検出) で発話開始・終了を自動検出する。

        VAD 状態遷移:
          WAITING → SPEAKING : RMS > speech_threshold
          SPEAKING → SILENCE  : RMS < silence_threshold
          SILENCE  → SPEAKING : RMS > speech_threshold (誤検知防止)
          SILENCE  → DONE     : 無音が silence_duration 秒続いた
        """

        # ---- 定数 ----
        _SAMPLES_PER_CHUNK = 512          # NAOqi の1コールバックあたりサンプル数
        _PREROLL_SEC       = 0.4          # 発話検出前のバッファ時間（秒）

        def __init__(self, name, ip, port, save_path,
                     max_duration=30,
                     samplerate=16000,
                     speech_threshold=400,
                     silence_threshold=250,
                     silence_duration=0.9,
                     min_speech_duration=0.25):
            _ALModule.__init__(self, name)
            self._ip               = str(ip)
            self._port             = int(port)
            self._save_path        = save_path
            self._max_duration     = float(max_duration)
            self._samplerate       = samplerate
            self._speech_thr       = speech_threshold
            self._silence_thr      = silence_threshold
            self._silence_dur      = silence_duration
            self._min_speech_dur   = min_speech_duration

            self._frames           = []
            self._preroll          = []
            self._max_preroll      = int(samplerate * self._PREROLL_SEC / self._SAMPLES_PER_CHUNK)
            self._lock             = threading.Lock()
            self._done             = threading.Event()

            # VAD 状態
            self._state            = "WAITING"
            self._first_time       = None
            self._speech_start     = None
            self._silence_start    = None

        def subscribe(self):
            import time as _t
            audio = _ALProxy("ALAudioDevice", self._ip, self._port)
            # モジュール登録がPepperに伝播するまで少し待つ
            _t.sleep(0.5)
            # setClientPreferences + subscribe を最大3回リトライ
            for attempt in range(3):
                try:
                    # channelID: 3=フロントマイク, samplerate=16000, deinterleave=0
                    audio.setClientPreferences(self.getName(), self._samplerate, 3, 0)
                    audio.subscribe(self.getName())
                    return
                except Exception as e:
                    print("[mic] subscribe 試行 {0}/3 失敗: {1}".format(attempt + 1, e))
                    sys.stdout.flush()
                    if attempt < 2:
                        _t.sleep(1.0)
                    else:
                        print("[mic] ヒント: Windowsファイアウォールがポート {0} をブロックしている可能性があります。".format(BROKER_AUDIO_PORT))
                        print("[mic]   管理者 PowerShell で以下を実行してください:")
                        print("[mic]   netsh advfirewall firewall add rule name=PepperNAOqi protocol=TCP dir=in action=allow localport={0} profile=any".format(BROKER_AUDIO_PORT))
                        sys.stdout.flush()
                        raise

        def process(self, nbOfChannels, nbrOfSamplesByChannel, timeStamp, inputBuffer):
            self._handle(inputBuffer)

        def processRemoteClient(self, nbOfChannels, nbrOfSamplesByChannel, timeStamp, inputBuffer):
            self._handle(inputBuffer)

        def _handle(self, inputBuffer):
            if self._done.is_set():
                return

            import time as _t, struct as _st, math as _m

            now = _t.time()
            if self._first_time is None:
                self._first_time = now

            # NAOqi ALValue → bytes
            if isinstance(inputBuffer, str):
                chunk = inputBuffer
            else:
                try:
                    chunk = bytes(bytearray(inputBuffer))
                except Exception:
                    chunk = b""

            if not chunk:
                return

            # RMS 計算
            n = len(chunk) // 2
            if n == 0:
                return
            try:
                samples = _st.unpack_from("<{0}h".format(n), chunk, 0)
                rms = _m.sqrt(sum(s * s for s in samples) / n)
            except Exception:
                rms = 0.0

            # ---- VAD 状態機械 ----
            if self._state == "WAITING":
                # プリロールバッファを維持
                self._preroll.append(chunk)
                if len(self._preroll) > self._max_preroll:
                    self._preroll.pop(0)

                # タイムアウト（待ちすぎ）
                if now - self._first_time > self._max_duration:
                    self._finish()
                    return

                if rms >= self._speech_thr:
                    self._state = "SPEAKING"
                    self._speech_start = now
                    with self._lock:
                        self._frames = list(self._preroll)
                        self._frames.append(chunk)
                    self._preroll = []
                    print("[VAD] 発話開始"); sys.stdout.flush()

            elif self._state == "SPEAKING":
                with self._lock:
                    self._frames.append(chunk)

                if rms < self._silence_thr:
                    self._state = "SILENCE"
                    self._silence_start = now

                # 最大録音時間
                if now - self._speech_start > self._max_duration:
                    self._finish()

            elif self._state == "SILENCE":
                with self._lock:
                    self._frames.append(chunk)

                if rms >= self._speech_thr:
                    # 発話再開（誤検知だった）
                    self._state = "SPEAKING"
                    self._silence_start = None
                elif now - self._silence_start >= self._silence_dur:
                    # 無音確定
                    speech_len = self._silence_start - self._speech_start
                    if speech_len >= self._min_speech_dur:
                        print("[VAD] 発話終了 ({0:.1f}s)".format(speech_len)); sys.stdout.flush()
                        self._finish()
                    else:
                        # 短すぎる → リセット
                        print("[VAD] 短音無視 ({0:.2f}s)".format(speech_len)); sys.stdout.flush()
                        self._state = "WAITING"
                        with self._lock:
                            self._frames = []

        def _finish(self):
            if self._done.is_set():
                return
            # unsubscribe をデーモンスレッドで実行（ブロッキング防止）
            def _unsub():
                try:
                    _ALProxy("ALAudioDevice", self._ip, self._port).unsubscribe(self.getName())
                except Exception as e:
                    print("[mic] unsubscribe: {0}".format(e))
            t = threading.Thread(target=_unsub)
            t.daemon = True
            t.start()
            t.join(timeout=3.0)  # 最大3秒待つ
            self._save()
            self._done.set()

        def _save(self):
            with self._lock:
                raw = b"".join(self._frames)
            if not raw:
                print("[mic] 警告: 音声データが空です。")
                return
            try:
                with wave.open(self._save_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self._samplerate)
                    wf.writeframes(raw)
                dur = len(raw) / 2.0 / self._samplerate
                print("[mic] 保存: {0} ({1:.1f}s)".format(self._save_path, dur))
            except Exception as e:
                print("[mic] 保存エラー: {0}".format(e))

        def wait(self, extra=5):
            """録音完了まで待機。タイムアウト時は強制終了。"""
            self._done.wait(timeout=self._max_duration + extra)
            if not self._done.is_set():
                print("[mic] タイムアウト、強制終了")
                self._finish()


def _ensure_audio_broker(ip, port):
    """ローカル NAOqi ブローカーを作成（初回のみ）。
    固定ポートを使用し、Windowsファイアウォール例外を追加することで
    Pepper からのコールバック接続を許可する。
    """
    global _audio_broker
    if _audio_broker is not None:
        return True
    if not _NAOQI_AVAILABLE:
        return False

    # Windowsファイアウォールに受信許可ルールを追加（既存ルールがあっても安全）
    # ポート固定ルール + プログラムルール（動的qimessagingポート対応）
    python_exe = sys.executable
    fw_cmds = [
        # ポート指定ルール
        ["netsh", "advfirewall", "firewall", "add", "rule",
         "name=PepperNAOqiPort", "protocol=TCP", "dir=in", "action=allow",
         "localport=" + str(BROKER_AUDIO_PORT), "profile=any"],
        # プログラム指定ルール（動的ポートもカバー）
        ["netsh", "advfirewall", "firewall", "add", "rule",
         "name=PepperNAOqiPython", "program=" + python_exe,
         "protocol=TCP", "dir=in", "action=allow", "profile=private"],
    ]
    fw_ok = True
    for cmd in fw_cmds:
        try:
            ret = subprocess.call(cmd,
                                  stdout=open(os.devnull, "w"),
                                  stderr=open(os.devnull, "w"))
            if ret != 0:
                fw_ok = False
        except Exception:
            fw_ok = False
    if fw_ok:
        print("[mic] ファイアウォール例外 追加済み (port={0}, python={1})".format(
            BROKER_AUDIO_PORT, python_exe))
    else:
        print("[mic] 警告: ファイアウォール例外の追加に失敗しました。")
        print("[mic]   管理者権限で実行するか、以下を手動で実行してください:")
        print("[mic]   netsh advfirewall firewall add rule name=PepperNAOqi protocol=TCP dir=in action=allow localport={0} profile=any".format(BROKER_AUDIO_PORT))
    sys.stdout.flush()

    try:
        _audio_broker = _ALBroker(
            "PepperMicBroker",      # ブローカー名
            "0.0.0.0",              # ローカル IP（全インターフェース）
            BROKER_AUDIO_PORT,      # 固定ポート（ファイアウォール例外と一致）
            str(ip),                # Pepper IP
            int(port)               # Pepper NAOqi ポート
        )
        print("[mic] NAOqi ブローカー起動 OK (port={0})".format(BROKER_AUDIO_PORT))
        sys.stdout.flush()
        return True
    except Exception as e:
        print("[mic] ブローカー起動失敗: {0}".format(e))
        sys.stdout.flush()
        _audio_broker = None
        return False


def _record_mic_qi(ip, port, save_path, max_duration=30,
                   speech_threshold=400, silence_threshold=250,
                   silence_duration=0.9, min_speech_duration=0.25):
    """
    qi.Session ベースの音声録音（NAOqi 2.x / ファイアウォール不要）。

    PC→Pepperの既存qimessagingセッション接続を双方向に利用するため、
    Pepperからのインバウンド接続（＝Windowsファイアウォール例外）が不要。
    """
    import math as _m, struct as _st, time as _t

    SAMPLERATE       = 16000
    CHUNKS_PER_SEC   = SAMPLERATE / 512  # ~31
    PREROLL_MAX      = int(CHUNKS_PER_SEC * 0.4)

    _frames    = []
    _preroll   = []
    _state     = ["WAITING"]
    _t0        = [None]
    _sp_start  = [None]
    _si_start  = [None]
    _lock      = threading.Lock()
    _done      = threading.Event()

    def _handle(inputBuffer):
        if _done.is_set():
            return
        now = _t.time()
        if _t0[0] is None:
            _t0[0] = now

        # バイト変換
        try:
            if isinstance(inputBuffer, (bytes, bytearray)):
                chunk = bytes(inputBuffer)
            elif isinstance(inputBuffer, str):
                chunk = inputBuffer
            else:
                chunk = bytes(bytearray(inputBuffer))
        except Exception:
            return
        if not chunk:
            return

        n = len(chunk) // 2
        if n == 0:
            return
        try:
            samples = _st.unpack_from("<{0}h".format(n), chunk, 0)
            rms = _m.sqrt(sum(s * s for s in samples) / n)
        except Exception:
            rms = 0.0

        if _state[0] == "WAITING":
            _preroll.append(chunk)
            if len(_preroll) > PREROLL_MAX:
                _preroll.pop(0)
            if now - _t0[0] > max_duration:
                _done.set(); return
            if rms >= speech_threshold:
                _state[0] = "SPEAKING"
                _sp_start[0] = now
                with _lock:
                    _frames[:] = list(_preroll) + [chunk]
                _preroll[:] = []
                print("[VAD] 発話開始"); sys.stdout.flush()

        elif _state[0] == "SPEAKING":
            with _lock:
                _frames.append(chunk)
            if rms < silence_threshold:
                _state[0] = "SILENCE"
                _si_start[0] = now
            if now - _sp_start[0] > max_duration:
                _done.set()

        elif _state[0] == "SILENCE":
            with _lock:
                _frames.append(chunk)
            if rms >= speech_threshold:
                _state[0] = "SPEAKING"
                _si_start[0] = None
            elif now - _si_start[0] >= silence_duration:
                sp_len = _si_start[0] - _sp_start[0]
                if sp_len >= min_speech_duration:
                    print("[VAD] 発話終了 ({0:.1f}s)".format(sp_len)); sys.stdout.flush()
                    _done.set()
                else:
                    print("[VAD] 短音無視 ({0:.2f}s)".format(sp_len)); sys.stdout.flush()
                    _state[0] = "WAITING"
                    with _lock:
                        _frames[:] = []

    # ---- qi サービスクラス（デコレータ不要、動的バインド）----
    class _QiAudioCapture(object):
        def processRemoteClient(self, nbOfChannels, nbrOfSamplesByChannel, timeStamp, inputBuffer):
            _handle(inputBuffer)
        def process(self, nbOfChannels, nbrOfSamplesByChannel, timeStamp, inputBuffer):
            _handle(inputBuffer)

    session  = _qi.Session()
    session.connect("tcp://{0}:{1}".format(ip, port))

    cap      = _QiAudioCapture()
    svc_name = "PepperMicCaptureQi"
    svc_id   = session.registerService(svc_name, cap)
    print("[mic] qi: サービス登録 OK ({0})".format(svc_name)); sys.stdout.flush()

    audio = session.service("ALAudioDevice")

    # 登録伝播待ち
    _t.sleep(0.5)

    for attempt in range(3):
        try:
            audio.setClientPreferences(svc_name, SAMPLERATE, 3, 0)
            audio.subscribe(svc_name)
            print("[mic] qi: subscribe OK"); sys.stdout.flush()
            break
        except Exception as e:
            print("[mic] qi: subscribe 試行 {0}/3: {1}".format(attempt + 1, e))
            sys.stdout.flush()
            if attempt < 2:
                _t.sleep(1.0)
            else:
                raise

    print("[mic] qi: 話しかけてください..."); sys.stdout.flush()
    _done.wait(timeout=float(max_duration) + 5)

    # ---- クリーンアップ（非ブロッキング）----
    def _cleanup():
        try: audio.unsubscribe(svc_name)
        except Exception: pass
        try: session.unregisterService(svc_id)
        except Exception: pass
        try: session.close()
        except Exception: pass

    t = threading.Thread(target=_cleanup)
    t.daemon = True
    t.start()
    t.join(timeout=3.0)

    # ---- 保存 ----
    with _lock:
        raw = b"".join(_frames)
    if raw:
        with wave.open(save_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLERATE)
            wf.writeframes(raw)
        dur = len(raw) / 2.0 / SAMPLERATE
        print("[mic] qi: 保存 {0} ({1:.1f}s)".format(save_path, dur)); sys.stdout.flush()
        return True
    else:
        print("[mic] qi: 警告: 音声データなし"); sys.stdout.flush()
        return False


def _transfer_wav_from_pepper(ip, remote_path, local_path):
    """
    Pepper のファイルシステムから WAV ファイルをローカルに転送する。
    paramiko SFTP → FTP → subprocess SCP の順に試みる。
    """
    # --- 方式1: paramiko SFTP ---
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(str(ip), username="nao", password="nao",
                       timeout=15, look_for_keys=False, allow_agent=False)
        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        client.close()
        print("[transfer] paramiko SFTP 完了: {0}".format(local_path))
        sys.stdout.flush()
        return True
    except ImportError:
        print("[transfer] paramiko 未インストール (Python 2.7 環境)")
        sys.stdout.flush()
    except Exception as e:
        print("[transfer] paramiko SFTP エラー: {0}".format(e))
        sys.stdout.flush()

    # --- 方式2: FTP ---
    try:
        import ftplib
        ftp = ftplib.FTP()
        ftp.connect(str(ip), 21, timeout=10)
        ftp.login("nao", "nao")
        with open(local_path, "wb") as f:
            ftp.retrbinary("RETR " + remote_path, f.write)
        ftp.quit()
        print("[transfer] FTP 完了: {0}".format(local_path))
        sys.stdout.flush()
        return True
    except Exception as e:
        print("[transfer] FTP エラー: {0}".format(e))
        sys.stdout.flush()

    # --- 方式3: subprocess SCP (Windows OpenSSH クライアント) ---
    scp_candidates = [
        r"C:\Windows\System32\OpenSSH\scp.exe",
        "scp",
    ]
    for scp_exe in scp_candidates:
        try:
            if scp_exe != "scp" and not os.path.exists(scp_exe):
                continue
            cmd = [
                scp_exe,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "BatchMode=yes",
                "nao@{0}:{1}".format(ip, remote_path),
                local_path,
            ]
            ret = subprocess.call(cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            if ret == 0 and os.path.exists(local_path):
                print("[transfer] SCP 完了: {0}".format(local_path))
                sys.stdout.flush()
                return True
        except Exception as e:
            print("[transfer] SCP ({0}) エラー: {1}".format(scp_exe, e))
            sys.stdout.flush()

    print("[transfer] 全転送方式失敗。")
    print("[transfer] 手動転送コマンド: scp nao@{0}:{1} {2}".format(
        ip, remote_path, local_path))
    sys.stdout.flush()
    return False


def _record_mic_polling(ip, port, save_path, max_duration=30,
                        speech_threshold=600, silence_threshold=480,
                        silence_duration=1.2, min_speech_duration=0.3):
    """
    ポーリング方式の音声録音（ファイアウォール設定不要・推奨）。

    動作フロー:
    1. ALAudioRecorder.startMicrophonesRecording() → /home/nao/ に録音
    2. ALAudioDevice.getFrontMicEnergy() ポーリング → VAD
    3. ALAudioRecorder.stopMicrophonesRecording() → 録音停止
    4. ALFileManager.getFileContents(basename) → バイナリ取得 → ローカル保存
       ※ getFileContents はファイル名のみ指定（フルパス不可）

    エネルギー値の目安（getFrontMicEnergy）:
      無音時:   400〜500
      発話時:   600〜1500+

    Returns:
        bool: 成功なら True
    """
    import time as _t

    POLL_INTERVAL = 0.05   # ポーリング間隔（秒）
    REC_FILENAME  = "pepper_mic_capture.wav"
    REC_PATH      = "/home/nao/" + REC_FILENAME
    ENERGY_REPORT = 2.0    # 待機中のエネルギー表示間隔（秒）

    # qi.Session で接続（すべての操作に共通セッションを使う）
    session = _qi.Session()
    session.connect("tcp://{0}:{1}".format(ip, port))
    audio   = session.service("ALAudioDevice")
    rec_svc = session.service("ALAudioRecorder")
    fm      = session.service("ALFileManager")

    # エネルギー計算を有効化
    try:
        audio.enableEnergyComputation()
    except Exception as e:
        print("[mic] enableEnergyComputation: {0}".format(e))
        sys.stdout.flush()

    # 聴取中の LED を青に（視覚フィードバック）
    try:
        leds = session.service("ALLeds")
        leds.fadeRGB("FaceLeds", 0.0, 0.4, 1.0, 0.2)
    except Exception:
        leds = None

    # 録音開始（ALAudioRecorder: 4引数形式が必要）
    try:
        rec_svc.startMicrophonesRecording(REC_PATH, "wav", 16000, [0, 0, 1, 0])
        print("[mic] 録音開始 → {0}".format(REC_PATH))
        sys.stdout.flush()
    except Exception as e:
        print("[mic] startMicrophonesRecording 失敗: {0}".format(e))
        sys.stdout.flush()
        try:
            session.close()
        except Exception:
            pass
        return False

    print("[mic] 話しかけてください... (speech_thr={0}, silence_thr={1})".format(
        speech_threshold, silence_threshold))
    sys.stdout.flush()

    state         = "WAITING"
    t0            = _t.time()
    last_report   = t0
    speech_start  = None
    silence_start = None
    stop_recording = False

    try:
        while True:
            elapsed = _t.time() - t0

            # 最大録音時間超過
            if elapsed > max_duration:
                if state in ("SPEAKING", "SILENCE") and speech_start is not None:
                    print("[mic] 最大録音時間 {0}s 超過（発話あり）".format(max_duration))
                    sys.stdout.flush()
                    stop_recording = True
                else:
                    print("[mic] タイムアウト（発話検出なし）")
                    sys.stdout.flush()
                break

            # エネルギー取得
            try:
                energy = audio.getFrontMicEnergy()
            except Exception as e:
                print("[mic] エネルギー取得エラー: {0}".format(e))
                sys.stdout.flush()
                _t.sleep(POLL_INTERVAL)
                continue

            now = _t.time()

            # WAITING 中は定期的にエネルギー値を表示（閾値調整の参考に）
            if state == "WAITING" and now - last_report >= ENERGY_REPORT:
                print("[mic] 待機中... energy={0:.0f} (閾値={1})".format(
                    energy, speech_threshold))
                sys.stdout.flush()
                last_report = now

            # VAD 状態機械
            if state == "WAITING":
                if energy >= speech_threshold:
                    state = "SPEAKING"
                    speech_start = now
                    print("[VAD] 発話開始 energy={0:.0f}".format(energy))
                    sys.stdout.flush()

            elif state == "SPEAKING":
                if energy < silence_threshold:
                    state = "SILENCE"
                    silence_start = now
                elif now - speech_start > max_duration:
                    print("[VAD] 最大発話時間超過")
                    sys.stdout.flush()
                    stop_recording = True
                    break

            elif state == "SILENCE":
                if energy >= speech_threshold:
                    # 発話再開（一時的な無音だった）
                    state = "SPEAKING"
                    silence_start = None
                elif now - silence_start >= silence_duration:
                    speech_len = silence_start - speech_start
                    if speech_len >= min_speech_duration:
                        print("[VAD] 発話終了 {0:.1f}s".format(speech_len))
                        sys.stdout.flush()
                        stop_recording = True
                        break
                    else:
                        print("[VAD] 短音無視 {0:.2f}s".format(speech_len))
                        sys.stdout.flush()
                        state         = "WAITING"
                        speech_start  = None
                        silence_start = None

            _t.sleep(POLL_INTERVAL)

    finally:
        # 録音停止（VAD ループの正常/異常終了どちらでも実行）
        try:
            rec_svc.stopMicrophonesRecording()
            print("[mic] 録音停止")
            sys.stdout.flush()
        except Exception as e:
            print("[mic] stopMicrophonesRecording エラー: {0}".format(e))
            sys.stdout.flush()
        # LED を白に戻す
        if leds:
            try:
                leds.fadeRGB("FaceLeds", 1.0, 1.0, 1.0, 0.3)
            except Exception:
                pass

    if not stop_recording:
        try:
            session.close()
        except Exception:
            pass
        return False

    # ファイル書き込み完了待ち（バッファフラッシュ）
    time.sleep(0.3)

    # ---- ALFileManager でファイル取得（ファイル名のみ指定、フルパス不可）----
    try:
        data = fm.getFileContents(REC_FILENAME)
        raw  = bytearray(data)
        with open(save_path, "wb") as f:
            f.write(raw)
        dur = len(raw) / 2.0 / 16000
        print("[mic] 転送完了: {0} ({1:.1f}s)".format(save_path, dur))
        sys.stdout.flush()
        try:
            session.close()
        except Exception:
            pass
        return True
    except Exception as e:
        print("[mic] ALFileManager 転送失敗: {0}".format(e))
        sys.stdout.flush()

    # ---- フォールバック: SFTP / FTP / SCP ----
    try:
        session.close()
    except Exception:
        pass
    return _transfer_wav_from_pepper(str(ip), REC_PATH, save_path)


def _record_mic(pp, save_path=None, max_duration=30,
                speech_threshold=400, silence_threshold=250,
                silence_duration=0.9):
    """
    Pepper の内蔵マイクで VAD 付きリアルタイム録音。

    方式A: ポーリング（getFrontMicEnergy + startMicrophonesRecording）— ファイアウォール不要・推奨
    方式B: qi.Session コールバック (NAOqi 2.x) — フォールバック
    方式D: ALBroker + ALModule (NAOqi 1.x)    — ファイアウォール要
    方式E: ALAudioRecorder（固定時間録音）     — 最終フォールバック

    Args:
        pp (Pepper): Pepper インスタンス
        save_path (str): 保存先（省略時は output.wav）
        max_duration (int): 最大録音秒数（上限）
        speech_threshold (int): 発話開始 RMS 閾値
        silence_threshold (int): 無音 RMS 閾値
        silence_duration (float): 無音継続秒数（発話終了判定）
    """
    if save_path is None:
        save_path = os.path.join(_HERE, "output.wav")

    ip   = pp.ip
    port = pp.port

    # ---- 方式A: ポーリング（getFrontMicEnergy + startMicrophonesRecording）----
    # ファイアウォール設定不要・最も安定した方式
    if _QI_AVAILABLE:
        # バックグラウンドアニメーションを停止してリスニングジェスチャーに切り替え
        _bg_pause()

        # 録音中は聴いている感じの頭・腕の動きを演出
        _idle_rec_stop = [False]

        def _head_idle_during_rec():
            _listen_gestures = [
                "idle_head_tilt", "look_around", "fidget_look",
                "sway_gentle", "think_chin", "tilt_head", "look_away",
                "listen_intense", "lean_in",
            ]
            while not _idle_rec_stop[0]:
                time.sleep(random.uniform(3.5, 7.0))
                if _idle_rec_stop[0]:
                    break
                try:
                    pp.do(random.choice(_listen_gestures), intensity=0.5)
                except Exception:
                    pass

        _head_t = threading.Thread(target=_head_idle_during_rec)
        _head_t.daemon = True
        _head_t.start()

        try:
            ok = _record_mic_polling(ip, port, save_path,
                                     max_duration=max_duration,
                                     speech_threshold=600,
                                     silence_threshold=480,
                                     silence_duration=silence_duration)
            _idle_rec_stop[0] = True
            if ok:
                return
            # 音声データなし（無音タイムアウト）でも正常終了
            print("[mic] ポーリング方式: 音声なし（タイムアウト）")
            sys.stdout.flush()
            return
        except Exception as e:
            _idle_rec_stop[0] = True
            print("[mic] ポーリング方式失敗: {0}".format(e))
            print("[mic] qi コールバック方式にフォールバック...")
            sys.stdout.flush()
        finally:
            _bg_resume()  # 録音終了後にバックグラウンドアニメーション再開

    # ---- 方式B: qi.Session コールバック (NAOqi 2.x) ----
    if _QI_AVAILABLE:
        try:
            ok = _record_mic_qi(ip, port, save_path,
                                max_duration=max_duration,
                                speech_threshold=speech_threshold,
                                silence_threshold=silence_threshold,
                                silence_duration=silence_duration)
            if ok:
                return
            return
        except Exception as e:
            print("[mic] qi コールバック方式失敗: {0}".format(e))
            print("[mic] ALBroker 方式にフォールバック...")
            sys.stdout.flush()

    # ---- 方式D: ALBroker + ALModule (NAOqi 1.x) — ファイアウォール要 ----
    if _ensure_audio_broker(ip, port):
        _mic_module_seq[0] += 1
        module_name = "PepperMicCapture{0}".format(_mic_module_seq[0])
        try:
            cap = _AudioCapture(
                module_name, ip, port, save_path,
                max_duration=max_duration,
                speech_threshold=speech_threshold,
                silence_threshold=silence_threshold,
                silence_duration=silence_duration,
            )
            cap.subscribe()
            print("[mic] 話しかけてください...")
            sys.stdout.flush()
            cap.wait()
            print("[mic] 録音完了。")
            sys.stdout.flush()
            return
        except Exception as e:
            print("[mic] ストリーミングエラー: {0}".format(e))
            print("[mic] ALAudioRecorder にフォールバック...")
            sys.stdout.flush()

    # ---- 方式E: ALAudioRecorder（固定時間フォールバック）----
    wav_path = "/home/nao/audio_input.wav"
    try:
        recorder = pp.core.proxy("ALAudioRecorder")
        print("[mic] ALAudioRecorder 録音 {0}秒...".format(max_duration))
        recorder.startMicrophonesRecording(wav_path, "wav", 16000, [0, 0, 1, 0])
        time.sleep(float(max_duration))
        recorder.stopMicrophonesRecording()
        time.sleep(0.5)
        print("[mic] 注意: SSHパスワードが必要です。--text モードを使用してください。")
    except Exception as e:
        print("[mic] ALAudioRecorder エラー: {0}".format(e))


def execute_json(pp, data):
    """
    JSON形式コマンドを解析して Pepper を操作する。

    JSON フィールド:
        speech    (str)   : 発話テキスト（省略可）
        emotion   (str)   : 感情名 happy/sad/angry/... （省略可）
        action    (str)   : プリミティブ動作名（省略可）
        intensity (float) : 動作強度 0.1〜1.5 （デフォルト 1.0）
        gaze      (str)   : 視線方向 face/up/down/left/right/away （省略可）
    """
    speech    = data.get("speech", "")
    emotion   = data.get("emotion", "")
    action    = data.get("action", "")
    intensity = float(data.get("intensity", 1.0))
    gaze      = data.get("gaze", "face")

    # バックグラウンドアニメーションを停止してから動作実行（競合防止）
    _bg_pause()
    try:
        # 1. LED色を感情に合わせて設定
        if emotion:
            _set_led_for_emotion(pp, emotion)

        # 2. 視線設定
        _gaze(pp, gaze)

        # 3. 動作 + 発話
        if action and action in pp.primitives.CATALOG:
            if speech:
                pp.do_speak(action, speech, intensity=intensity)
            else:
                pp.do(action, intensity=intensity)
        elif emotion and speech:
            # 感情ジェスチャー + 発話
            pp.emotion(emotion, speech)
        elif speech:
            # 発話のみ（自動ジェスチャー付き）
            pp.say(speech, animated=True)
        elif emotion:
            # 感情のみ
            pp.emotion(emotion)

        # 4. LED をリセット（感情色を設定した場合）
        if emotion and emotion not in ("neutral", "explain"):
            time.sleep(0.1)
            pp.reset_leds()
    finally:
        _bg_resume()  # バックグラウンドアニメーション再開


# ---- レガシーアクションマップ ----
def _make_action_map(pp):
    return {
        "bow":      lambda: pp.bow(),
        "wave":     lambda: pp.wave(),
        "nod":      lambda: pp.nod(),
        "shake":    lambda: pp.shake_head(),
        "dance":    lambda: pp.say_with_anim(
            "楽しんでくださいね！",
            "animations/Stand/Waiting/AirGuitar_1"
        ),
        "sing":     lambda: pp.say_with_anim(
            "ハッピーバースデーを歌います！",
            "animations/Stand/Waiting/HappyBirthday_1"
        ),
        "guitar":   lambda: pp.say_with_anim(
            "エアギターをお楽しみください！",
            "animations/Stand/Waiting/AirGuitar_1"
        ),
        "fitness":  lambda: pp.say_with_anim(
            "私の筋肉を見てください！",
            "animations/Stand/Waiting/ShowMuscles_1"
        ),
        "stretch":  lambda: pp.say_with_anim(
            "伸びをしましょう。",
            "animations/Stand/Waiting/Stretch_1"
        ),
        "think":    lambda: pp.emotion("thinking"),
    }


def execute_command(pp, action_map, raw):
    """
    コマンド文字列を解析して Pepper を操作する。

    まず JSON パースを試みる。失敗した場合はレガシー形式として処理する。

    Returns:
        bool: False なら終了
    """
    if not raw:
        return True

    # Python 2: bytes -> unicode
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "ignore")

    raw = raw.strip()
    if not raw:
        return True

    if raw == "-":
        return False

    # ---- JSON 形式を優先して試みる ----
    if raw.startswith("{"):
        try:
            data = json.loads(raw)

            # 特殊コマンド: マイク録音
            if data.get("cmd") == "record_mic":
                save_path        = str(data["save_path"]) if data.get("save_path") else None
                max_duration     = int(data.get("max_duration", 30))
                speech_threshold = int(data.get("speech_threshold", 400))
                silence_threshold= int(data.get("silence_threshold", 250))
                silence_duration = float(data.get("silence_duration", 0.9))
                _record_mic(pp, save_path=save_path,
                            max_duration=max_duration,
                            speech_threshold=speech_threshold,
                            silence_threshold=silence_threshold,
                            silence_duration=silence_duration)
                return True

            execute_json(pp, data)
            return True
        except (ValueError, KeyError) as e:
            print("[json parse error] {0}  raw={1!r}".format(e, raw[:80]))
            # JSON パース失敗 → レガシー形式にフォールバック

    # ---- レガシー形式 ----
    prefix = raw[0] if raw else ""
    body   = raw[1:] if len(raw) > 1 else ""

    if prefix == "@":
        pp.say(body, animated=True)

    elif prefix == "$":
        if ":" in body:
            parts   = body.split(":", 1)
            emotion = parts[0].strip().lower()
            text    = parts[1].strip()
            pp.emotion(emotion, text if text else None)
        else:
            name = body.strip().lower()
            if name in action_map:
                action_map[name]()
            else:
                pp.emotion(name)

    else:
        pp.say(raw, animated=True)

    return True


# ---- 生命感スレッド（呼吸・重心移動）----
_life_flag = {"stop": False}


def _start_life_thread(pp):
    """
    呼吸・重心移動を連続的に再現する「生命感」スレッドを起動する。

    setAngles(fractionMaxSpeed=0.06) で 20Hz の連続更新を行う。
    fractionMaxSpeed が低いため、angleInterpolation ジェスチャーと
    競合せず、ジェスチャー完了後に自然に呼吸ポーズへ戻る。
    """
    import math as _m
    _life_flag["stop"] = False

    BREATH_T = 4.2    # 呼吸周期（秒）≈ 14回/分 (安静時)
    SWAY_T   = 9.5    # 重心移動周期（秒）
    MICRO_T  = 2.9    # 微細揺れ周期（ランダム感）

    def _fn():
        t0 = time.time()
        while not _life_flag["stop"]:
            t = time.time() - t0

            breath = _m.sin(2 * _m.pi * t / BREATH_T)         # -1 〜 1
            sway   = _m.sin(2 * _m.pi * t / SWAY_T)  * 0.009  # ±0.009 rad
            micro  = _m.sin(2 * _m.pi * t / MICRO_T) * 0.005  # ±0.005 rad
            arm    = breath * 0.020                            # 腕の呼吸連動

            try:
                pp.core.motion.setAngles(
                    ["HipPitch",         "KneePitch",
                     "HipRoll",
                     "LShoulderPitch",   "RShoulderPitch"],
                    [breath * 0.025,
                     max(0.0, breath * 0.013 + 0.008),
                     sway + micro,
                     1.40 + arm,         1.40 + arm],
                    0.06   # fractionMaxSpeed: 6% — ゆっくり滑らか
                )
            except Exception:
                pass

            time.sleep(0.05)   # 20 Hz

    t = threading.Thread(target=_fn)
    t.daemon = True
    t.start()
    print("[life] 呼吸スレッド起動")
    sys.stdout.flush()


# ============================================================
# バックグラウンドアニメーション（Pepper ビルトイン）
# ============================================================
# ※ 実際に Pepper にインストールされているパスを使用（list_behaviors.py で確認済み）

# BodyTalk/Speaking: 会話中の自然な体言語（2〜4秒・ループに最適）
_BG_SPEAKING = [
    "animations/Stand/BodyTalk/Speaking/BodyTalk_1",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_2",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_3",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_4",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_5",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_6",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_7",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_8",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_9",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_10",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_11",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_12",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_13",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_14",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_15",
    "animations/Stand/BodyTalk/Speaking/BodyTalk_16",
]
# BodyTalk/Listening: 聞いている最中のリアクション
_BG_LISTENING = [
    "animations/Stand/BodyTalk/Listening/Listening_1",
    "animations/Stand/BodyTalk/Listening/Listening_2",
    "animations/Stand/BodyTalk/Listening/Listening_3",
    "animations/Stand/BodyTalk/Listening/Listening_4",
    "animations/Stand/BodyTalk/Listening/Listening_5",
    "animations/Stand/BodyTalk/Listening/Listening_6",
    "animations/Stand/BodyTalk/Listening/Listening_7",
]
# BodyTalk/Thinking: 考え中ループ
_BG_THINKING = [
    "animations/Stand/BodyTalk/Thinking/ThinkingLoop_1",
    "animations/Stand/BodyTalk/Thinking/ThinkingLoop_2",
    "animations/Stand/BodyTalk/Thinking/Remember_1",
    "animations/Stand/BodyTalk/Thinking/Remember_2",
    "animations/Stand/BodyTalk/Thinking/Remember_3",
]
# Waiting: 待機中のアクション（人間らしい仕草・SSH実機確認済み）
# ※ Think_5/6・Wings_1/2 は Waiting フォルダに存在しないため除外
_BG_WAITING = [
    # 呼吸ループ（生命感・最重要）
    "animations/Stand/Waiting/BreathLoop_1",
    "animations/Stand/Waiting/BreathLoop_2",
    "animations/Stand/Waiting/BreathLoop_3",
    # リラクゼーション
    "animations/Stand/Waiting/Relaxation_1",
    "animations/Stand/Waiting/Relaxation_2",
    "animations/Stand/Waiting/Relaxation_3",
    "animations/Stand/Waiting/Relaxation_4",
    # 思考系（Think_1〜4 のみ存在）
    "animations/Stand/Waiting/Think_1",
    "animations/Stand/Waiting/Think_2",
    "animations/Stand/Waiting/Think_3",
    "animations/Stand/Waiting/Think_4",
    # 体を搔く（最も人間らしい仕草）
    "animations/Stand/Waiting/ScratchHead_1",
    "animations/Stand/Waiting/ScratchBack_1",
    "animations/Stand/Waiting/ScratchBottom_1",
    "animations/Stand/Waiting/ScratchEye_1",
    "animations/Stand/Waiting/ScratchHand_1",
    "animations/Stand/Waiting/ScratchLeg_1",
    "animations/Stand/Waiting/ScratchTorso_1",
    # 手遊び
    "animations/Stand/Waiting/PlayHands_1",
    "animations/Stand/Waiting/PlayHands_2",
    "animations/Stand/Waiting/PlayHands_3",
    # 手を見る・伸び・よたよた
    "animations/Stand/Waiting/LookHand_1",
    "animations/Stand/Waiting/LookHand_2",
    "animations/Stand/Waiting/Stretch_1",
    "animations/Stand/Waiting/Stretch_2",
    "animations/Stand/Waiting/Waddle_1",
    "animations/Stand/Waiting/Waddle_2",
    # その他の自然な仕草
    "animations/Stand/Waiting/Rest_1",
    "animations/Stand/Waiting/BackRubs_1",
    "animations/Stand/Waiting/Innocent_1",
    "animations/Stand/Waiting/Binoculars_1",
]
# 重み付き結合：Speaking多め（短くて自然）、Waiting も豊富に
_BG_ANIMS_ALL = (
    _BG_SPEAKING  * 3 +   # 最も頻繁（短く自然）
    _BG_LISTENING * 2 +   # 聴きリアクション
    _BG_THINKING  * 1 +   # 考え中
    _BG_WAITING   * 2     # 待機中の人間らしい仕草
)

_bg_anim_lock        = threading.Lock()
_bg_anim_pause_count = [0]   # 0=動作中, >0=一時停止
_bg_anim_stop        = [False]
_bg_anim_task        = [None]  # (ALBehaviorManager proxy, task_id) or None


def _bg_pause():
    """バックグラウンドアニメーションを一時停止し、現在の動作を止める。"""
    with _bg_anim_lock:
        _bg_anim_pause_count[0] += 1
    # 現在実行中の動作を強制停止
    with _bg_anim_lock:
        entry = _bg_anim_task[0]
    if entry:
        try:
            entry[0].stop(entry[1])
        except Exception:
            pass
    time.sleep(0.10)  # 停止確認まで待機


def _bg_resume():
    """バックグラウンドアニメーションを再開する。"""
    with _bg_anim_lock:
        _bg_anim_pause_count[0] = max(0, _bg_anim_pause_count[0] - 1)


def _start_bg_animation_thread(pp):
    """
    Pepper のビルトインアニメーションを常時バックグラウンドで連続実行する。

    ALBehaviorManager.post.runBehavior() で非同期実行し、
    完了したら即座に次のアニメーションを選択。
    _bg_pause() / _bg_resume() でメインアクションと協調する。
    """
    _bg_anim_stop[0] = False
    with _bg_anim_lock:
        _bg_anim_pause_count[0] = 0

    def _fn():
        try:
            bm = pp.core.proxy("ALBehaviorManager")
        except Exception as e:
            print("[bg_anim] ALBehaviorManager 初期化失敗: {0}".format(e))
            sys.stdout.flush()
            return

        available = list(_BG_ANIMS_ALL)  # コピーして使う（失敗時に削除）
        last = [None]

        while not _bg_anim_stop[0]:
            # 一時停止チェック
            with _bg_anim_lock:
                paused = (_bg_anim_pause_count[0] > 0)
            if paused:
                time.sleep(0.05)
                continue

            if not available:
                # 全アニメーション失敗 → primitives にフォールバック
                try:
                    pp.do(random.choice(["idle_sway", "think_chin", "look_around"]), 0.6)
                except Exception:
                    pass
                time.sleep(2.0)
                continue

            # 直前と異なるアニメーションを選択
            pool = [a for a in available if a != last[0]]
            anim = random.choice(pool if pool else available)
            last[0] = anim

            try:
                task_id = bm.post.runBehavior(str(anim))
                with _bg_anim_lock:
                    _bg_anim_task[0] = (bm, task_id)

                # 実行中のポーリング（80ms 間隔）
                while not _bg_anim_stop[0]:
                    with _bg_anim_lock:
                        paused = (_bg_anim_pause_count[0] > 0)
                    if paused:
                        try:
                            bm.stop(task_id)
                        except Exception:
                            pass
                        break
                    try:
                        if not bm.isRunning(task_id):
                            break
                    except Exception:
                        break
                    time.sleep(0.08)

                with _bg_anim_lock:
                    _bg_anim_task[0] = None

            except Exception:
                with _bg_anim_lock:
                    _bg_anim_task[0] = None
                # 失敗したアニメーションをリストから除外
                available = [a for a in available if a != anim]

            # アニメーション間のわずかな間隔（不自然な連続感を防ぐ）
            with _bg_anim_lock:
                paused = (_bg_anim_pause_count[0] > 0)
            if not paused and not _bg_anim_stop[0]:
                time.sleep(random.uniform(0.1, 0.5))

    t = threading.Thread(target=_fn)
    t.daemon = True
    t.start()
    print("[bg_anim] バックグラウンドアニメーション起動")
    sys.stdout.flush()


def main():
    pepper_ip   = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PEPPER_IP
    pepper_port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PEPPER_PORT
    server_host = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SERVER_HOST
    server_port = int(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_SERVER_PORT

    print("=" * 50)
    print("  pepper_runner 起動中...")
    print("  Pepper: {0}:{1}".format(pepper_ip, pepper_port))
    print("  Socket: {0}:{1}".format(server_host, server_port))
    print("=" * 50)

    # --- NAOqi 音声ブローカーを最初に初期化（グローバルブローカーを Pepper 接続より先に確立）---
    if _NAOQI_AVAILABLE:
        print("[main] NAOqi 音声ブローカー初期化中...")
        sys.stdout.flush()
        _ensure_audio_broker(pepper_ip, pepper_port)

    # --- Pepper 初期化 ---
    try:
        pp = Pepper(pepper_ip, pepper_port)
    except Exception as e:
        print("Pepper 接続失敗: {0}".format(e))
        sys.exit(1)

    # idle_chat_daemon.py に「chat_gpt.py 実行中」を通知（ALMemory フラグ）
    _mem = None
    if _NAOQI_AVAILABLE:
        try:
            _mem = _ALProxy("ALMemory", pepper_ip, pepper_port)
            _mem.insertData("PepperApp/ChatGPTRunning", 1)
            print("[flag] PepperApp/ChatGPTRunning = 1")
            sys.stdout.flush()
        except Exception as e:
            print("[flag] ALMemory フラグ設定失敗: {0}".format(e))
            sys.stdout.flush()

    _start_life_thread(pp)          # 呼吸・重心移動スレッド起動
    _start_bg_animation_thread(pp)  # ビルトインアニメーション常時実行
    action_map = _make_action_map(pp)

    # --- ソケットサーバー起動 ---
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((server_host, server_port))
    server_sock.listen(1)
    print("サーバー起動: {0}:{1} — 接続待ち...".format(server_host, server_port))
    # chat_gpt.py が "READY" を待つためにフラッシュ
    sys.stdout.write("READY\n")
    sys.stdout.flush()

    conn, addr = server_sock.accept()
    print("接続: {0}".format(addr))

    _bg_thread = [None]  # 非同期コマンド実行スレッド

    try:
        while True:
            # バックグラウンドアニメーションが常時動いているので
            # select timeout は長め（たまに歩き回るだけ）
            idle_timeout = random.uniform(50.0, 120.0)
            readable, _, _ = select.select([conn], [], [], idle_timeout)

            if not readable:
                # たまに小さく歩き回る（bg animation は止めずに移動）
                if _bg_thread[0] is None or not _bg_thread[0].is_alive():
                    walk_opts = [
                        (0.3, 0.0,  0.0), (-0.2, 0.0, 0.0),
                        (0.0, 0.0,  0.5), (0.0,  0.0, -0.5),
                    ]
                    x, y, t = random.choice(walk_opts)
                    try:
                        pp.core.motion.moveTo(x, y, t)
                    except Exception:
                        pass
                continue

            data = conn.recv(BUFF_SIZE)
            if not data:
                print("クライアント切断。")
                break

            raw = data.decode("utf-8", "ignore").strip()
            print("[recv] {0!r}".format(raw[:120]))

            # 前の非同期コマンドが動いていれば完了を待つ（モーション競合防止）
            if _bg_thread[0] and _bg_thread[0].is_alive():
                _bg_thread[0].join()

            # 非同期コマンド判定（"async": true があれば ack を先送りしてバックグラウンド実行）
            is_async = False
            if raw.startswith("{"):
                try:
                    d = json.loads(raw)
                    if d.pop("async", False):
                        is_async = True
                        raw = json.dumps(d, ensure_ascii=False)
                except (ValueError, KeyError):
                    pass

            if is_async:
                conn.sendall(b"!")  # ack を先に返す
                def _run_bg(r=raw):
                    try:
                        execute_command(pp, action_map, r)
                    except Exception as e:
                        print("[async] エラー: {0}".format(e))
                _bg_thread[0] = threading.Thread(target=_run_bg)
                _bg_thread[0].daemon = True
                _bg_thread[0].start()
            else:
                keep = execute_command(pp, action_map, raw)
                # 完了通知
                conn.sendall(b"!")
                if not keep:
                    print("終了コマンド受信。")
                    break

    except KeyboardInterrupt:
        print("\n手動終了。")
    except Exception as e:
        print("エラー: {0}".format(e))
    finally:
        _life_flag["stop"] = True
        _bg_anim_stop[0] = True
        conn.close()
        server_sock.close()
        # ALMemory フラグをクリア（idle_chat_daemon に制御を返す）
        try:
            if _mem is not None:
                _mem.insertData("PepperApp/ChatGPTRunning", 0)
                print("[flag] PepperApp/ChatGPTRunning = 0")
                sys.stdout.flush()
        except Exception:
            pass
        pp.emotion("grateful", "お疲れ様でした。またお話しましょう！")
        pp.stand()
        print("pepper_runner 終了。")


if __name__ == "__main__":
    main()
