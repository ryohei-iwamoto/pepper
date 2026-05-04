# -*- coding: utf-8 -*-
"""
chat_gpt.py - Pepper × GPT 会話 (Python 3) — ワンコマンド起動

使い方:
    python chat_gpt.py [PEPPER_IP] [--text] [--model gpt-4o-mini]

    PEPPER_IP    : PepperのIPアドレス（省略時 192.168.0.46）
    --text       : マイクなし・テキスト入力モード（Whisperを使わない）
    --model NAME : GPTモデル名（デフォルト gpt-4o-mini）
    --key APIKEY : OpenAI APIキー（省略時 OPENAI_API_KEY 環境変数）
    --port PORT  : PepperのNAOqiポート（デフォルト 9559）

    例:
        python chat_gpt.py 192.168.0.46
        python chat_gpt.py 192.168.0.46 --text
        python chat_gpt.py --key sk-xxxxx --text

環境変数:
    OPENAI_API_KEY   : OpenAI APIキー
    PEPPER_IP        : PepperのIPアドレス

仕組み:
    1. Python 2.7 の pepper_runner.py をサブプロセスで起動
    2. ソケット経由でJSONコマンドを送信
    3. マイク入力 → Whisper → GPT → 動作+感情+発話 → Pepper
"""
import os
import sys
import socket
import subprocess
import threading
import concurrent.futures
import time
import argparse
import json
import re


# ============================================================
# .env ファイルの自動読み込み（python-dotenv 不要）
# ============================================================
def _load_dotenv(path=None):
    """
    スクリプトと同じディレクトリの .env を読み込む。
    既に os.environ に値がある場合は上書きしない。
    """
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if key and val and key not in os.environ:
                    os.environ[key] = val
    except FileNotFoundError:
        pass

_load_dotenv()


# ============================================================
# 設定
# ============================================================
DEFAULT_PEPPER_IP   = os.environ.get("PEPPER_IP", "192.168.0.46")
DEFAULT_PEPPER_PORT = 9559
RUNNER_HOST         = "127.0.0.1"
RUNNER_PORT         = 12345
BUFF_SIZE           = 8192
READY_TIMEOUT       = 30       # pepper_runner 起動待ちタイムアウト（秒）

# Whisper / VAD 設定
WHISPER_MODEL  = "small"       # tiny / base / small / medium  (small = 日本語精度と速度のバランス)
SAMPLE_RATE    = 16000
MIN_DB         = 2000
SILENCE_DELAY  = 0.8
AUDIO_FILE     = "output.wav"

# GPT 設定
DEFAULT_MODEL  = "gpt-4o-mini"
MAX_TOKENS     = 300

# ============================================================
# システムプロンプト（構造化JSON出力 + 動作選択ガイド）
# ============================================================
SYSTEM_PROMPT = """\
あなたは「Pepper」という名前の親切で明るいヒューマノイドロボットです。
ユーザーと日本語で自然に会話してください。

返答は必ず次のJSON形式のみで返してください（余計な説明・前置き不要）：
{"speech":"発話内容","emotion":"感情名","action":"動作名","intensity":1.0,"gaze":"face"}

■ speech（必須）: 自然な日本語で50〜100文字以内。ロボットらしい個性を出す。

■ emotion（必須）: 以下から1つ選ぶ
  happy excited sad angry surprised thinking shy bored
  confident grateful victory fearful neutral explain

■ action（必須・省略禁止）: 以下から状況に最も合う1つを必ず選ぶ。身振り手振りを豊かに表現すること！
  [挨拶・社交]  greet_bow greet_wave farewell welcome thank_bow apologize_bow clap
                bow_deep bow_slight wave_both nod_hello handshake_gesture
  [傾聴・反応]  nod_strong nod_gentle nod_triple shake_no tilt_head lean_in
                agree_enthusiastic disagree_arms listen_intense impressed_nod confirm_nod
  [指示・方向]  point_forward point_up point_left point_right beckon show_palm present_both
                point_self point_past point_future come_here
  [思考・処理]  think_chin think_scratch look_away confused_tilt focused
                recall_gesture doubt_head wonder_look pause_think
  [感情表現]    joy_arms_up surprise_recoil sad_droop proud_chest shy_hide fear_back excited_bounce
                laugh_shake victory_arms determined_fist angry_cross relief_slump
                embarrassed_chin amazed_open satisfied_nod
  [強調・説明]  raise_one_hand spread_explain count_one count_two count_three count_four
                open_arms shrug_dunno show_size_small show_size_big thumbs_up
                present_item emphasize_down
  [ダンス]      dance_sway dance_wave_arms robot_move celebrate air_drum conductor_wave
                clap_rhythm shimmy
  [態度・姿勢]  arms_forward hands_on_hips attention_stand open_stance lean_back_relax
                arms_behind ready_pose thinking_stance
  [待機]        look_around stretch_up idle_sway fidget_look idle_head_tilt
                check_surroundings sway_gentle

■ intensity（0.3〜1.5）: 動作の強さ。感情が強い時は1.2〜1.5、落ち着いた時は0.6〜0.8。

■ gaze: face（正面・相手を見る）/ up / down / left / right / away（視線を外す）

動作選択の例:
  挨拶・初対面   → greet_bow / greet_wave / handshake_gesture  視線: face
  深礼・お辞儀   → bow_deep                                    視線: down
  軽い会釈       → bow_slight / nod_hello                      視線: face
  感謝する       → thank_bow                                   視線: face
  謝罪する       → apologize_bow                               視線: down
  強い同意       → agree_enthusiastic / nod_triple             視線: face  intensity: 1.2
  普通の相槌     → nod_gentle / confirm_nod                    視線: face
  否定・断る     → shake_no / disagree_arms                    視線: face
  考え中         → think_chin / think_scratch / recall_gesture 視線: away
  疑問・困惑     → confused_tilt / doubt_head / wonder_look    視線: away
  喜び・興奮     → joy_arms_up / excited_bounce / celebrate    視線: face  intensity: 1.3
  驚き・感嘆     → surprise_recoil / amazed_open               視線: face  intensity: 1.2
  悲しみ         → sad_droop / embarrassed_chin                視線: down
  自己紹介       → point_self / greet_bow                      視線: face
  説明・案内     → spread_explain / raise_one_hand / point_forward 視線: face
  数を数える     → count_one / count_two / count_three / count_four
  わからない     → shrug_dunno / confused_tilt                 視線: away
  勝利・達成     → victory_arms / celebrate                    視線: face  intensity: 1.5
  決意・やる気   → determined_fist / ready_pose                視線: face
  お別れ         → farewell / bow_slight                       視線: face
  ダンス・楽しい → dance_sway / shimmy / celebrate
"""

STOP_WORDS = {"stop", "ストップ", "終了", "終わり", "バイバイ", "さよなら", "おわり", "quit", "exit"}


# ============================================================
# Python 2.7 実行ファイルの自動検出
# ============================================================
def find_python2():
    """Python 2.7 の実行ファイルパスを返す。見つからない場合は None。"""
    candidates = [
        ["py", "-2.7"],
        ["py", "-2"],
        ["python2.7"],
        ["python2"],
    ]

    for cmd in [["python"], ["python3"]]:
        try:
            result = subprocess.run(
                cmd + ["--version"],
                capture_output=True, text=True, timeout=3
            )
            ver = (result.stdout + result.stderr).strip()
            if "Python 2.7" in ver:
                return cmd
        except Exception:
            pass

    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd + ["--version"],
                capture_output=True, text=True, timeout=3
            )
            ver = (result.stdout + result.stderr).strip()
            if "Python 2.7" in ver or "2.7" in ver:
                return cmd
        except Exception:
            continue

    return None


# ============================================================
# pepper_runner.py サブプロセス管理
# ============================================================
class PepperRunner:
    def __init__(self, python2_cmd, pepper_ip, pepper_port, runner_port):
        self._python2_cmd = python2_cmd
        self._pepper_ip   = pepper_ip
        self._pepper_port = pepper_port
        self._runner_port = runner_port
        self._proc        = None
        self._ready_event = threading.Event()

    def start(self):
        runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pepper_runner.py")
        cmd = self._python2_cmd + [
            runner_path,
            self._pepper_ip,
            str(self._pepper_port),
            RUNNER_HOST,
            str(self._runner_port),
        ]
        print(f"[起動] {' '.join(cmd)}")

        # Python 2.7 プロセスの文字コードを UTF-8 に統一
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        t = threading.Thread(target=self._read_output, daemon=True)
        t.start()

    def _read_output(self):
        for line in self._proc.stdout:
            line = line.rstrip()
            print(f"  [runner] {line}")
            if "READY" in line:
                self._ready_event.set()

    def wait_ready(self, timeout=READY_TIMEOUT):
        return self._ready_event.wait(timeout=timeout)

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._proc.wait(timeout=5)


# ============================================================
# Pepper ソケットクライアント
# ============================================================
class PepperClient:
    def __init__(self, host=RUNNER_HOST, port=RUNNER_PORT):
        self._host = host
        self._port = port
        self._sock = None

    def connect(self, retries=10, delay=1.0):
        for i in range(retries):
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.connect((self._host, self._port))
                print(f"pepper_runner に接続しました ({self._host}:{self._port})")
                return True
            except ConnectionRefusedError:
                if i < retries - 1:
                    time.sleep(delay)
        return False

    def send_json(self, data, timeout=20.0):
        """
        dict を JSON 文字列としてエンコードして送信し、完了ack を待つ。

        Args:
            data (dict): {"speech":..., "emotion":..., "action":..., ...}
            timeout (float): 発話・動作完了待ちタイムアウト（秒）

        Returns:
            bool: 成功なら True
        """
        if not self._sock:
            return False
        try:
            cmd = json.dumps(data, ensure_ascii=False)
            self._sock.sendall(cmd.encode("utf-8"))
            self._sock.settimeout(timeout)
            ack = self._sock.recv(BUFF_SIZE)
            self._sock.settimeout(None)
            return ack == b"!"
        except Exception as e:
            print(f"  送受信エラー: {e}")
            return False

    def send_recv(self, cmd_str, timeout=15.0):
        """レガシー文字列コマンドを送信する（後方互換）。"""
        if not self._sock:
            return False
        try:
            self._sock.sendall(cmd_str.encode("utf-8"))
            self._sock.settimeout(timeout)
            ack = self._sock.recv(BUFF_SIZE)
            self._sock.settimeout(None)
            return ack == b"!"
        except Exception as e:
            print(f"  送受信エラー: {e}")
            return False

    def close(self):
        if self._sock:
            try:
                self._sock.sendall(b"-")
            except Exception:
                pass
            self._sock.close()
            self._sock = None


# ============================================================
# GPT 呼び出し
# ============================================================
def call_gpt(client_openai, model, history, user_input):
    """
    GPT を呼び出して Pepper コマンド dict を返す。

    Returns:
        dict: {
            "speech":    発話テキスト,
            "emotion":   感情名,
            "action":    動作名 (なければ ""),
            "intensity": float,
            "gaze":      視線方向,
        }
    """
    history.append({"role": "user", "content": user_input})
    raw = ""
    try:
        resp = client_openai.chat.completions.create(
            model=model,
            messages=history,
            max_tokens=MAX_TOKENS,
            temperature=0.8,
        )
        raw = resp.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": raw})

        # コードブロック除去
        raw_clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        parsed = json.loads(raw_clean)

        return {
            "speech":    parsed.get("speech", "").strip(),
            "emotion":   parsed.get("emotion", "neutral").strip().lower(),
            "action":    parsed.get("action", "").strip().lower(),
            "intensity": float(parsed.get("intensity", 1.0)),
            "gaze":      parsed.get("gaze", "face").strip().lower(),
        }

    except json.JSONDecodeError:
        # JSON でなければテキストをそのまま発話
        fallback = raw if raw else "うまく返答できませんでした。"
        if not history or history[-1].get("content") != fallback:
            history.append({"role": "assistant", "content": fallback})
        return {
            "speech":    fallback,
            "emotion":   "neutral",
            "action":    "nod_gentle",
            "intensity": 1.0,
            "gaze":      "face",
        }
    except Exception as e:
        print(f"GPT エラー: {e}")
        return {
            "speech":    "申し訳ありません。エラーが発生しました。",
            "emotion":   "thinking",
            "action":    "think_chin",
            "intensity": 1.0,
            "gaze":      "away",
        }


# ============================================================
# 音声入力（Whisper + マルチバックエンド録音）
# ============================================================
def load_whisper(model_name=WHISPER_MODEL):
    try:
        import whisper
        print(f"Whisper ({model_name}) 読み込み中...")
        m = whisper.load_model(model_name)
        print("Whisper 準備完了。")
        return m
    except ImportError:
        print("警告: whisper がインストールされていません。--text モードを使用してください。")
        print("      pip install openai-whisper")
        return None


# ─── PyAudio バックエンド（VAD付き） ───────────────────────

def _record_pyaudio(audio_file):
    """
    PyAudio + VAD (音声区間検出) でマイク録音。
    戻り値: "ok" / "no_device" / "import_error"
    """
    try:
        import pyaudio
        import numpy as np
    except ImportError:
        return "import_error"

    audio = pyaudio.PyAudio()
    chunk = 1024
    try:
        stream = audio.open(format=pyaudio.paInt16, channels=1,
                            rate=SAMPLE_RATE, input=True, frames_per_buffer=chunk)
    except OSError as e:
        audio.terminate()
        print(f"[PyAudio] デバイスエラー: {e}")
        return "no_device"

    sample_width = audio.get_sample_size(pyaudio.paInt16)
    frames       = []
    started      = False
    stopped      = False
    stop_tick    = 0
    tick         = 0
    delay_ticks  = int(SILENCE_DELAY * (SAMPLE_RATE / chunk))

    print("\n話しかけてください...")
    while True:
        data  = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        level = int(np.max(np.frombuffer(data, dtype=np.int16)))

        if level > MIN_DB and not started:
            started   = True
            stop_tick = tick
            print("録音中...")
        if started:
            if level < MIN_DB and not stopped:
                stopped   = True
                stop_tick = tick
            if level > MIN_DB:
                stopped   = False
                stop_tick = tick
            if stopped and tick > stop_tick + delay_ticks:
                break
        tick += 1

    stream.stop_stream()
    stream.close()
    audio.terminate()

    import wave
    with wave.open(audio_file, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    return "ok"


# ─── ffmpeg DirectShow バックエンド ────────────────────────
# PyAudio/sounddevice は PortAudio (WASAPI) を使うが、
# ffmpeg は DirectShow を使うため、WASAPI で見えないデバイスを
# 検出できる場合がある。

_ffmpeg_audio_device = None   # None=未検索, False=利用不可, str=デバイス名


def _detect_ffmpeg_device():
    """
    ffmpeg -f dshow -list_devices でシステムの音声入力デバイスを検出。
    見つかればデバイス名、なければ False を返す。結果はキャッシュする。
    """
    global _ffmpeg_audio_device
    if _ffmpeg_audio_device is not None:
        return _ffmpeg_audio_device

    try:
        proc = subprocess.run(
            ['ffmpeg', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
            capture_output=True, timeout=8,
            encoding='utf-8', errors='replace'
        )
        output = proc.stderr   # ffmpeg は情報を stderr に出力
    except FileNotFoundError:
        print("[ffmpeg] ffmpeg が見つかりません。")
        print("         インストール方法: winget install ffmpeg  または  choco install ffmpeg")
        _ffmpeg_audio_device = False
        return False
    except subprocess.TimeoutExpired:
        _ffmpeg_audio_device = False
        return False

    # "DirectShow audio devices" セクションのデバイス名を収集
    devices     = []
    in_audio    = False
    for line in output.splitlines():
        low = line.lower()
        if 'audio' in low and 'device' in low:
            in_audio = True
        if 'video' in low and 'device' in low:
            in_audio = False
        if in_audio and '"' in line and 'alternative' not in low:
            m = re.search(r'"([^"]+)"', line)
            if m:
                name = m.group(1).strip()
                if name:
                    devices.append(name)

    if devices:
        print(f"[ffmpeg] 音声入力デバイス: {devices[0]}")
        if len(devices) > 1:
            print(f"         その他: {devices[1:]}")
        _ffmpeg_audio_device = devices[0]
    else:
        print("[ffmpeg] DirectShow でも音声入力デバイスが見つかりません。")
        _ffmpeg_audio_device = False

    return _ffmpeg_audio_device


def _record_ffmpeg(audio_file, max_sec=20):
    """
    ffmpeg DirectShow でマイク録音（PTTモード）。
    録音中は Enter キーで停止。max_sec 秒経過でも自動停止。
    成功なら True、失敗なら False を返す。
    """
    device = _detect_ffmpeg_device()
    if not device:
        return False

    cmd = [
        'ffmpeg', '-y',
        '-f', 'dshow',
        '-i', f'audio={device}',
        '-ar', str(SAMPLE_RATE),
        '-ac', '1',
        '-t', str(max_sec),
        audio_file
    ]

    print(f"\n話しかけてください（最大 {max_sec} 秒）...")
    print("  → 話し終わったら Enter を押してください")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 別スレッドで Enter キー待ち
        enter_evt = threading.Event()

        def _wait_enter():
            try:
                sys.stdin.readline()
            except Exception:
                pass
            enter_evt.set()

        th = threading.Thread(target=_wait_enter, daemon=True)
        th.start()

        # ffmpeg 終了 or Enter まで待機
        while proc.poll() is None:
            if enter_evt.is_set():
                break
            time.sleep(0.1)

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 1024:
            print("録音完了。")
            return True
        print("[ffmpeg] 録音ファイルが空です。マイクが動作しているか確認してください。")
        return False

    except Exception as e:
        print(f"[ffmpeg] 録音エラー: {e}")
        return False


def _show_mic_help():
    """マイクが認識されない場合のトラブルシューティングを表示"""
    print("\n" + "=" * 60)
    print("  マイクが認識されません")
    print("=" * 60)
    print("  原因診断を行うには:")
    print("    python chat_gpt.py --fix-audio")
    print()
    print("  よくある原因と対処法:")
    print("  1. USBケーブルを一度抜いて差し直す（最も効果的）")
    print("  2. 別のUSBポートに差し替える")
    print("     ※ USB 3.0（青いポート）では認識しない場合あり")
    print("     ※ USB 2.0（黒いポート）を試す")
    print("  3. デバイスマネージャーでドライバーを再インストール")
    print("     devmgmt.msc → サウンド/ビデオ → C922 → 右クリック")
    print("     → デバイスのアンインストール → ハードウェアのスキャン")
    print("  4. Windowsを再起動してから再接続")
    print()
    print("  テキスト入力モードで会話を続けるには:")
    print("    python chat_gpt.py --text")
    print("=" * 60 + "\n")


def _run_fix_audio():
    """
    音声デバイスの診断と修復を試みる。
    --fix-audio フラグで呼び出される。
    """
    import subprocess as sp

    print("\n=== 音声デバイス診断 ===\n")

    # 1. PyAudio でデバイス列挙
    print("[ PyAudio デバイス一覧 ]")
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        input_count = 0
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                print(f"  [{i}] {info['name']}  channels={info['maxInputChannels']}")
                input_count += 1
        if input_count == 0:
            print("  入力デバイスなし")
        pa.terminate()
    except Exception as e:
        print(f"  エラー: {e}")

    # 2. ffmpeg DirectShow
    print("\n[ ffmpeg DirectShow デバイス一覧 ]")
    global _ffmpeg_audio_device
    _ffmpeg_audio_device = None  # キャッシュをリセットして再検索
    _detect_ffmpeg_device()

    # 3. Windows PnP デバイス状態
    print("\n[ Windows PnP 音声デバイス状態 ]")
    try:
        r = sp.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-PnpDevice -Class AudioEndpoint | "
             "Select-Object FriendlyName,Status | "
             "Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        print(r.stdout.strip() or "  情報なし")
    except Exception as e:
        print(f"  PowerShell エラー: {e}")

    # 4. C922 USBデバイス状態
    print("\n[ C922 USB デバイス状態 ]")
    try:
        r = sp.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-PnpDevice | Where-Object { $_.FriendlyName -match 'C922' } | "
             "Select-Object FriendlyName,Status,Class | "
             "Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        print(r.stdout.strip() or "  C922 デバイスが見つかりません")
    except Exception as e:
        print(f"  エラー: {e}")

    # 5. 修復を試みる: pnputil /scan-devices
    print("\n[ デバイス再スキャン試行 ]")
    try:
        r = sp.run(
            ["pnputil", "/scan-devices"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        if r.returncode == 0:
            print("  デバイス再スキャン完了。再度 --list-audio で確認してください。")
        else:
            print("  再スキャンには管理者権限が必要です。")
            print("  管理者として実行してください:")
            print("    右クリック → 管理者として実行 → pnputil /scan-devices")
    except Exception as e:
        print(f"  エラー: {e}")

    # 6. 診断結果と対処法
    print("\n=== 診断結果 ===")
    print()
    print("C922 Pro Stream Webcam の音声インターフェース (MI_02) が")
    print("Windows に 'Unknown/切断' として認識されています。")
    print()
    print("→ USBケーブルを抜き差しすると直る可能性が高いです。")
    print("→ 試してもダメな場合は USB 2.0 ポートへ差し替えてください。")
    print()
    print("今すぐテキストモードで会話を始めるには:")
    print("  python chat_gpt.py --text")


# ─── Pepper マイク（SFTP ダウンロード + 録音） ──────────────

PEPPER_MIC_PATH = "/home/nao/audio_input.wav"   # Pepper 上の録音先


def _download_pepper_audio(pepper_ip, local_path, remote_path=PEPPER_MIC_PATH):
    """
    Pepper から音声ファイルを SFTP (paramiko) または scp で取得する。
    成功なら True。

    paramiko がない場合は pip install paramiko の案内を出す。
    """
    # ---- paramiko (SFTP) ----
    try:
        import paramiko

        transport = paramiko.Transport((pepper_ip, 22))
        transport.connect()
        # Pepper の SSH は keyboard-interactive のみ許可
        transport.auth_interactive_dumb(
            "nao",
            lambda title, instructions, prompt_list: ["nao"] * len(prompt_list)
        )
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get(remote_path, local_path)
        sftp.close()
        transport.close()
        return True
    except ImportError:
        pass   # scp にフォールバック
    except Exception as e:
        print(f"[SFTP] エラー: {e}")
        return False

    # ---- scp フォールバック (Windows OpenSSH が必要) ----
    try:
        r = subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no",
             "-o", "BatchMode=yes",
             f"nao@{pepper_ip}:{remote_path}", local_path],
            capture_output=True, timeout=20
        )
        if r.returncode == 0:
            return True
    except Exception:
        pass

    print("音声ダウンロードに失敗しました。paramiko をインストールしてください:")
    print("  pip install paramiko")
    return False


def record_and_transcribe_pepper(pepper_client, pepper_ip, whisper_model,
                                  max_duration=30, audio_file=AUDIO_FILE,
                                  silence_duration=0.7):
    """
    Pepper の内蔵マイクで VAD 付きリアルタイム録音 → Whisper 文字起こし。

    - 発話開始を自動検出
    - 無音が silence_duration 秒続いたら自動停止
    - pepper_runner.py が NAOqi ストリーミングで PC ローカルに保存（SSH 不要）
    """
    abs_path = os.path.abspath(audio_file)

    # pepper_runner に VAD 録音コマンドを送信
    ok = pepper_client.send_json(
        {
            "cmd":              "record_mic",
            "save_path":        abs_path,
            "max_duration":     max_duration,
            "silence_duration": silence_duration,
        },
        timeout=float(max_duration) + 25.0
    )
    if not ok:
        print("[Pepper マイク] 録音コマンド失敗。")
        return None

    # ローカルファイル確認
    if not (os.path.exists(abs_path) and os.path.getsize(abs_path) > 512):
        # SFTP フォールバック
        if not _download_pepper_audio(pepper_ip, abs_path):
            return None

    # Whisper 文字起こし
    result = whisper_model.transcribe(
        abs_path,
        language="ja",
        task="transcribe",
        temperature=0.0,                    # 決定論的・ハルシネーション抑制
        condition_on_previous_text=False,   # 前セグメントの影響を遮断（ループ防止）
        no_speech_threshold=0.6,            # 無音・雑音のみは空文字で返す
        logprob_threshold=-1.0,
    )
    segments = result.get("segments", [])
    text     = " ".join(seg["text"] for seg in segments).strip()
    if not text:
        text = result.get("text", "").strip()

    # ハルシネーション検出: 同じフレーズが3回以上繰り返されていたら無効とする
    if text:
        words = text.split()
        if len(words) >= 6:
            half = len(words) // 2
            if words[:half] == words[half:half*2]:
                print(f"[Whisper] ハルシネーション検出、破棄: {text[:60]}...")
                return None
        # 短い単語が大量に繰り返されるパターン（例: "として として として..."）
        unique_ratio = len(set(words)) / float(max(len(words), 1))
        if len(words) > 8 and unique_ratio < 0.2:
            print(f"[Whisper] 繰り返し検出、破棄: {text[:60]}...")
            return None

    print(f"あなた: {text}")
    return text if text else None


# ─── 統合録音 + 文字起こし ─────────────────────────────────

def record_and_transcribe(whisper_model, audio_file=AUDIO_FILE):
    """
    マイクから録音し Whisper で日本語テキストへ変換する。
    バックエンド優先順: PyAudio (WASAPI/MME) → ffmpeg (DirectShow)
    失敗時は None を返す。
    """
    # 1. PyAudio で試みる
    pa_result = _record_pyaudio(audio_file)
    if pa_result == "ok":
        pass  # 録音成功
    elif pa_result == "no_device":
        print("[PyAudio] 入力デバイスなし → ffmpeg DirectShow にフォールバック...")
        if not _record_ffmpeg(audio_file):
            _show_mic_help()
            return None
    else:  # import_error
        return None

    # Whisper で文字起こし
    result   = whisper_model.transcribe(audio_file, language="ja", task="transcribe")
    segments = result.get("segments", [])
    text     = " ".join(seg["text"] for seg in segments).strip()
    if not text:
        text = result.get("text", "").strip()
    print(f"あなた: {text}")
    return text


# ============================================================
# メイン
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Pepper × GPT 会話 (ワンコマンド)")
    parser.add_argument("pepper_ip",  nargs="?", default=DEFAULT_PEPPER_IP, help="Pepper IP")
    parser.add_argument("--port",     type=int,  default=DEFAULT_PEPPER_PORT)
    parser.add_argument("--text",     action="store_true", help="テキスト入力モード（マイクなし）")
    parser.add_argument("--model",    default=DEFAULT_MODEL)
    parser.add_argument("--key",      default=None, help="OpenAI APIキー")
    parser.add_argument("--whisper",  default=WHISPER_MODEL)
    parser.add_argument("--runner-port", type=int, default=RUNNER_PORT)
    parser.add_argument("--list-audio",  action="store_true",
                        help="音声入力デバイスを列挙して終了（デバッグ用）")
    parser.add_argument("--fix-audio",   action="store_true",
                        help="音声デバイスの診断と修復を試みて終了")
    parser.add_argument("--pepper-mic",  action="store_true",
                        help="PC マイクではなく Pepper の内蔵マイクを使用する")
    parser.add_argument("--mic-duration", type=int, default=15,
                        help="Pepper マイク録音秒数（デフォルト 15）")
    args = parser.parse_args()

    # 音声修復診断モード
    if args.fix_audio:
        _run_fix_audio()
        sys.exit(0)

    # 音声デバイス診断モード
    if args.list_audio:
        print("=== PyAudio デバイス一覧 ===")
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    print(f"  [{i}] {info['name']}  in={info['maxInputChannels']}")
            pa.terminate()
        except Exception as e:
            print(f"  PyAudio エラー: {e}")

        print("\n=== ffmpeg DirectShow デバイス一覧 ===")
        _detect_ffmpeg_device()
        sys.exit(0)

    # OpenAI API キー確認
    api_key = args.key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("エラー: OpenAI APIキーが見つかりません。")
        print("  --key sk-xxxx  または  OPENAI_API_KEY 環境変数で指定してください。")
        sys.exit(1)

    # Python 2.7 検出
    print("Python 2.7 を検索中...")
    python2 = find_python2()
    if python2 is None:
        print("エラー: Python 2.7 が見つかりません。")
        print("  インストール先: https://www.python.org/downloads/release/python-2718/")
        sys.exit(1)
    print(f"Python 2.7: {' '.join(python2)}")

    # pepper_runner.py 起動
    runner = PepperRunner(python2, args.pepper_ip, args.port, args.runner_port)
    runner.start()
    print(f"pepper_runner を起動中（最大 {READY_TIMEOUT}秒待機）...")
    if not runner.wait_ready():
        print("エラー: pepper_runner の起動タイムアウト。")
        runner.stop()
        sys.exit(1)

    # ソケット接続
    client = PepperClient(RUNNER_HOST, args.runner_port)
    if not client.connect():
        print("エラー: pepper_runner に接続できません。")
        runner.stop()
        sys.exit(1)

    # OpenAI クライアント
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=api_key)
    except ImportError:
        print("エラー: openai パッケージがありません。  pip install openai")
        runner.stop()
        sys.exit(1)

    # Whisper（テキストモードでなければ）
    whisper_model = None
    if not args.text:
        whisper_model = load_whisper(args.whisper)
        if whisper_model is None:
            print("Whisperが使えないため、テキスト入力モードに切り替えます。")
            args.text = True

    # 入力方式の決定（デフォルト: Pepper 内蔵マイク）
    if args.text:
        input_mode = "text"
    else:
        input_mode = "pepper_mic"

    # GPT 会話履歴
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    mode_label = {
        "pepper_mic": f"Pepper マイク (最大{args.mic_duration}秒/発話)",
        "pc_mic":     "PC マイク (Whisper)",
        "text":       "テキスト入力",
    }

    print("\n" + "=" * 50)
    print("  Pepper × GPT 会話モード 開始")
    print(f"  Pepper IP : {args.pepper_ip}")
    print(f"  GPT モデル: {args.model}")
    print(f"  入力方式  : {mode_label[input_mode]}")
    print("  終了      : 「終わり」「バイバイ」と言うか Ctrl+C")
    print("=" * 50)

    # 挨拶（JSON形式）
    client.send_json({
        "speech":    "こんにちは！GPT会話モードを開始します。何でも話しかけてください！",
        "emotion":   "happy",
        "action":    "greet_wave",
        "intensity": 1.2,
        "gaze":      "face",
    })

    # ──────── メインループ ────────
    _mic_fail = 0  # 連続マイク失敗カウンター

    try:
        while True:
            # --- 入力取得 ---
            if input_mode == "text":
                try:
                    user_input = input("\nあなた: ").strip()
                except EOFError:
                    break
                if not user_input:
                    continue

            elif input_mode == "pepper_mic":
                user_input = record_and_transcribe_pepper(
                    client, args.pepper_ip, whisper_model,
                    max_duration=args.mic_duration,
                )
                if user_input is None:
                    _mic_fail += 1
                    if _mic_fail >= 2:
                        print("\nPepper マイクが使えません。テキスト入力に切り替えます。")
                        input_mode = "text"
                        _mic_fail = 0
                    continue
                if not user_input:
                    _mic_fail = 0
                    client.send_json({
                        "speech":    "すみません、うまく聞き取れませんでした。もう一度お願いします。",
                        "emotion":   "shy",
                        "action":    "tilt_head",
                        "intensity": 0.8,
                        "gaze":      "face",
                    })
                    continue
                _mic_fail = 0

            else:  # pc_mic
                user_input = record_and_transcribe(whisper_model)
                if user_input is None:
                    # マイクエラー（デバイスなし等）→ 2回失敗で Pepper マイクに切り替え
                    _mic_fail += 1
                    if _mic_fail >= 2:
                        print("\nPCマイクが使えません。Pepper 内蔵マイクに切り替えます。")
                        input_mode = "pepper_mic"
                        _mic_fail = 0
                    else:
                        print("マイクを認識できませんでした。もう一度試みます...")
                    continue
                elif not user_input:
                    # 無音 → 聞き取れなかった
                    _mic_fail = 0
                    client.send_json({
                        "speech":    "すみません、うまく聞き取れませんでした。もう一度お願いします。",
                        "emotion":   "shy",
                        "action":    "tilt_head",
                        "intensity": 0.8,
                        "gaze":      "face",
                    })
                    continue
                _mic_fail = 0

            # 終了ワード判定
            if any(w in user_input for w in STOP_WORDS):
                print("終了します。")
                break

            # ── 並列処理: GPT 呼び出し と 思考モーション を同時に実行 ──
            # 思考モーション（発話なし）と GPT API を並列に走らせることで
            # 返答までの体感レイテンシを大幅に短縮する。
            print("GPT 処理中...")

            gpt_result_box = [None]
            gpt_done       = threading.Event()

            def _run_gpt():
                try:
                    gpt_result_box[0] = call_gpt(
                        openai_client, args.model, history, user_input
                    )
                except Exception as e:
                    print(f"GPT エラー: {e}")
                finally:
                    gpt_done.set()

            gpt_thread = threading.Thread(target=_run_gpt, daemon=True)
            gpt_thread.start()

            # GPT が考えている間に思考モーション（非同期: ack をすぐ返してもらい即座に次へ）
            client.send_json({
                "emotion":   "thinking",
                "action":    "think_chin",
                "intensity": 0.7,
                "gaze":      "away",
                "async":     True,
            }, timeout=5.0)

            # GPT 結果を待つ（最大 20 秒）
            gpt_done.wait(timeout=20.0)
            result = gpt_result_box[0]

            if result is None:
                result = {
                    "speech":    "少々お待ちください。",
                    "emotion":   "neutral",
                    "action":    "nod_gentle",
                    "intensity": 1.0,
                    "gaze":      "face",
                }

            print(f"Pepper [{result['emotion']}][{result['action']}]: {result['speech']}")

            # Pepper に JSON コマンド送信
            client.send_json(result, timeout=25.0)

    except KeyboardInterrupt:
        print("\n\nCtrl+C で終了します。")

    finally:
        print("会話終了。")
        client.send_json({
            "speech":    "またお話ししましょう！さようなら！",
            "emotion":   "grateful",
            "action":    "farewell",
            "intensity": 1.0,
            "gaze":      "face",
        })
        time.sleep(1)
        client.close()
        time.sleep(0.5)
        runner.stop()
        print("終了しました。")


if __name__ == "__main__":
    main()
