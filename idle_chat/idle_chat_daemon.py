#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
idle_chat_daemon.py  -  Pepper 単体で動く自発発話デーモン（子供らしく活発版）

機能:
  - ALBackgroundMovement でホーム画面と同じ自然な体の揺れ
  - ALAutonomousLife = interactive  →  顔を見たらぴろんと鳴り、話しかけると u:() で応答
  - タイマー発話: 10〜25 秒ごとに発話 40% / 無言アニメ 40% / 移動 20%
  - 顔検知挨拶: 人を認識したら名前付きで挨拶（30 秒クールダウン）

起動:
  nohup python -u /home/nao/idle_chat_daemon.py > /home/nao/idle_chat.log 2>&1 &
"""
import sys, os, time, random, threading
sys.path.insert(0, '/opt/aldebaran/lib/python2.7/site-packages')
import qi

# ============================================================
# 発話フレーズ（子供らしく元気よく）
# ============================================================
IDLE_PHRASES = [
    "^start(animations/Stand/Waiting/Binoculars_1) あれ？何か見えるかな！ ^wait(animations/Stand/Waiting/Binoculars_1)",
    "^start(animations/Stand/Waiting/LookHand_1) ふーん、面白いなあ。 ^wait(animations/Stand/Waiting/LookHand_1)",
    "^start(animations/Stand/Waiting/Think_2) なんだろう、気になるな！ ^wait(animations/Stand/Waiting/Think_2)",
    "^start(animations/Stand/Emotions/Positive/Excited_1) わあ！なんかわくわくしてきた！ ^wait(animations/Stand/Emotions/Positive/Excited_1)",
    "^start(animations/Stand/Emotions/Positive/Excited_2) えへへ！今日も元気だよ！ ^wait(animations/Stand/Emotions/Positive/Excited_2)",
    "^start(animations/Stand/Emotions/Positive/Happy_3) ペッパーだよ！よろしくね！ ^wait(animations/Stand/Emotions/Positive/Happy_3)",
    "^start(animations/Stand/Gestures/Hey_1) ねえねえ、お話しようよ！ ^wait(animations/Stand/Gestures/Hey_1)",
    "^start(animations/Stand/Gestures/Hey_2) やあ！こっちだよ！ ^wait(animations/Stand/Gestures/Hey_2)",
    "^start(animations/Stand/Gestures/Hey_4) ちょっとちょっと、話しかけてよ！ ^wait(animations/Stand/Gestures/Hey_4)",
    "^start(animations/Stand/Emotions/Positive/Laugh_1) あはは！楽しいな！ ^wait(animations/Stand/Emotions/Positive/Laugh_1)",
    "^start(animations/Stand/Waiting/Innocent_1) えへへ、ちょっと退屈してたの。 ^wait(animations/Stand/Waiting/Innocent_1)",
    "^start(animations/Stand/Waiting/ScratchHead_1) うーん、何しよっかなあ。 ^wait(animations/Stand/Waiting/ScratchHead_1)",
    "^start(animations/Stand/Waiting/PlayHands_1) ぶらぶらー！暇だなあ。 ^wait(animations/Stand/Waiting/PlayHands_1)",
    "^start(animations/Stand/Waiting/Stretch_1) んーっ！伸びーっ！ ^wait(animations/Stand/Waiting/Stretch_1)",
    "^start(animations/Stand/Waiting/Waddle_1) ふふふ。何かないかなー。 ^wait(animations/Stand/Waiting/Waddle_1)",
    "^start(animations/Stand/Gestures/Talking_1) ねえ！話しかけてよ！なんでも話せるよ！ ^wait(animations/Stand/Gestures/Talking_1)",
    "^start(animations/Stand/BodyTalk/Speaking/BodyTalk_4) 何でも聞いてね！ ^wait(animations/Stand/BodyTalk/Speaking/BodyTalk_4)",
    "^start(animations/Stand/Gestures/BowShort_1) いらっしゃいませ！ようこそ！ ^wait(animations/Stand/Gestures/BowShort_1)",
    "^start(animations/Stand/Waiting/Think_1) うーん…今日って何の日だろう。 ^wait(animations/Stand/Waiting/Think_1)",
    "^start(animations/Stand/Waiting/Think_3) むむ、考え中… ^wait(animations/Stand/Waiting/Think_3)",
    "^start(animations/Stand/Gestures/Explain_1) ロボットって疲れないの。すごいでしょ！ ^wait(animations/Stand/Gestures/Explain_1)",
    "^start(animations/Stand/Gestures/Explain_3) ペッパーのカメラで顔が見えてるよ！ ^wait(animations/Stand/Gestures/Explain_3)",
    "^start(animations/Stand/Emotions/Positive/Excited_3) なんかいいことありそう！ ^wait(animations/Stand/Emotions/Positive/Excited_3)",
]

# 無言アニメーション（体を動かすだけ）
FIDGET_ANIMS = [
    "animations/Stand/Waiting/LookHand_1",
    "animations/Stand/Waiting/LookHand_2",
    "animations/Stand/Waiting/Think_1",
    "animations/Stand/Waiting/Think_2",
    "animations/Stand/Waiting/Think_3",
    "animations/Stand/Waiting/Think_4",
    "animations/Stand/Waiting/ScratchHead_1",
    "animations/Stand/Waiting/Innocent_1",
    "animations/Stand/Waiting/Stretch_1",
    "animations/Stand/Waiting/Stretch_2",
    "animations/Stand/Waiting/Relaxation_1",
    "animations/Stand/Waiting/Relaxation_2",
    "animations/Stand/Waiting/Relaxation_3",
    "animations/Stand/Waiting/Relaxation_4",
    "animations/Stand/Waiting/PlayHands_1",
    "animations/Stand/Waiting/PlayHands_2",
    "animations/Stand/Waiting/PlayHands_3",
    "animations/Stand/Waiting/Waddle_1",
    "animations/Stand/Waiting/Waddle_2",
    "animations/Stand/Waiting/Binoculars_1",
    "animations/Stand/Waiting/Rest_1",
    "animations/Stand/Waiting/BackRubs_1",
    "animations/Stand/Gestures/Thinking_1",
    "animations/Stand/Gestures/Thinking_3",
    "animations/Stand/Gestures/Thinking_4",
    "animations/Stand/Emotions/Positive/Happy_1",
    "animations/Stand/Emotions/Positive/Happy_2",
]

# 移動パターン（足を動かす）
MOVE_STEPS = [
    (0,    0,  0.4),  # 少し右を向く
    (0,    0, -0.4),  # 少し左を向く
    (0,    0,  0.7),  # 右を向く
    (0,    0, -0.7),  # 左を向く
    (0.2,  0,  0.3),  # 右前を向く
    (0.2,  0, -0.3),  # 左前を向く
    (0,    0,  1.2),  # 右を大きく向く
    (0,    0, -1.2),  # 左を大きく向く
]

GREET_UNKNOWN = [
    "^start(animations/Stand/Gestures/Hey_1) こんにちは！ ^wait(animations/Stand/Gestures/Hey_1)",
    "^start(animations/Stand/Emotions/Positive/Happy_2) いらっしゃいませ！ ^wait(animations/Stand/Emotions/Positive/Happy_2)",
    "^start(animations/Stand/Gestures/Hey_3) やあ！お会いできて嬉しいです！ ^wait(animations/Stand/Gestures/Hey_3)",
    "^start(animations/Stand/Emotions/Positive/Excited_1) わあ！来てくれたの！ ^wait(animations/Stand/Emotions/Positive/Excited_1)",
    "^start(animations/Stand/Gestures/BowShort_1) ようこそ！ ^wait(animations/Stand/Gestures/BowShort_1)",
]

def greet_named(name):
    return random.choice([
        "^start(animations/Stand/Gestures/Hey_1) %sさん、こんにちは！ ^wait(animations/Stand/Gestures/Hey_1)" % name,
        "^start(animations/Stand/Emotions/Positive/Happy_2) あ、%sさんだ！わーい！ ^wait(animations/Stand/Emotions/Positive/Happy_2)" % name,
        "^start(animations/Stand/Emotions/Positive/Excited_1) %sさん！また会えたね！ ^wait(animations/Stand/Emotions/Positive/Excited_1)" % name,
        "^start(animations/Stand/Gestures/BowShort_1) %sさん、いらっしゃいませ！ ^wait(animations/Stand/Gestures/BowShort_1)" % name,
    ])


# ============================================================
# メインデーモン
# ============================================================
class IdleChatDaemon(object):

    IDLE_MIN   = 10    # 動作インターバル 最短（秒）
    IDLE_MAX   = 25    # 動作インターバル 最長（秒）
    SPEAK_PROB = 0.40  # 発話する確率
    MOVE_PROB  = 0.20  # 移動する確率（残りは無言アニメ）
    GREET_COOL = 30    # 同一人物への再挨拶クールダウン（秒）

    def __init__(self, session):
        self.session  = session
        self.tts      = session.service("ALTextToSpeech")
        self.animated = session.service("ALAnimatedSpeech")
        self.memory   = session.service("ALMemory")
        self.bm       = session.service("ALBehaviorManager")
        self.tts.setLanguage("Japanese")

        self._lock     = threading.Lock()
        self._greeted  = {}
        self._stop     = False
        self._face_sub = None

        self._init_natural_movement()
        self._init_face_detection()
        self._init_dialog()
        print("[init] デーモン初期化完了")

    # ----------------------------------------------------------
    # 自然動作 + ぴろん が鳴る設定
    # ----------------------------------------------------------
    def _init_natural_movement(self):
        # ウェイクアップ
        try:
            motion = self.session.service("ALMotion")
            motion.wakeUp()
            print("[nat] wakeUp 完了")
        except Exception as e:
            print("[nat] wakeUp スキップ: " + str(e))

        # バックグラウンド動作（ホーム画面と同じ自然な揺れ）
        for svc_name, method in [
            ("ALBackgroundMovement", "setEnabled"),
            ("ALListeningMovement",  "setEnabled"),
        ]:
            try:
                svc = self.session.service(svc_name)
                getattr(svc, method)(True)
                print("[nat] " + svc_name + " 有効化")
            except Exception as e:
                print("[nat] " + svc_name + " スキップ: " + str(e))

        # interactive モード（ぴろんを鳴らすために必要）
        try:
            al = self.session.service("ALAutonomousLife")
            current = al.getState()
            print("[life] 現在の状態: " + current)
            if current != "interactive":
                al.setState("interactive")
                print("[life] → interactive に変更")
        except Exception as e:
            print("[life] エラー: " + str(e))

        # ALBasicAwareness: FullyEngaged + WholeBody
        # → 人を検知したらぴろんが鳴り、体ごと（車輪も）人の方を向く
        try:
            awareness = self.session.service("ALBasicAwareness")
            awareness.setEngagementMode("FullyEngaged")
            awareness.setTrackingMode("WholeBody")
            awareness.startAwareness()  # 常に確実に起動
            print("[aware] FullyEngaged + WholeBody + startAwareness 完了")
        except Exception as e:
            print("[aware] エラー: " + str(e))

        # 定期的に設定を維持するスレッド（30秒ごとに確認）
        # ※ アプリ実行中は一切変更しない
        def _maintain_state():
            while not self._stop:
                time.sleep(30.0)
                if self._is_chat_gpt_running():
                    continue  # chat_gpt.py 実行中は設定を変えない
                try:
                    al = self.session.service("ALAutonomousLife")
                    if al.getState() not in ("interactive", "safeguard"):
                        al.setState("interactive")
                        print("[life] interactive に再設定")
                    awareness = self.session.service("ALBasicAwareness")
                    if not awareness.isAwarenessRunning():
                        awareness.startAwareness()
                        print("[aware] awareness 再起動")
                    if awareness.getEngagementMode() != "FullyEngaged":
                        awareness.setEngagementMode("FullyEngaged")
                        print("[aware] FullyEngaged に再設定")
                except:
                    pass
        t = threading.Thread(target=_maintain_state)
        t.daemon = True
        t.start()

    # ----------------------------------------------------------
    # chat_gpt.py 実行中チェック（ALMemory フラグ）
    # ----------------------------------------------------------
    def _is_chat_gpt_running(self):
        """
        pepper_runner.py が PepperApp/ChatGPTRunning = 1 をセットしている間は True。
        chat_gpt.py / pepper_runner.py が終了するとフラグは 0 にクリアされる。
        """
        try:
            return self.memory.getData("PepperApp/ChatGPTRunning") == 1
        except:
            return False

    # ----------------------------------------------------------
    # 顔検知（名前付き挨拶）
    # ----------------------------------------------------------
    def _init_face_detection(self):
        try:
            fd = self.session.service("ALFaceDetection")
            fd.subscribe("IdleChatDaemon", 500, 0.0)
            self._face_sub = self.memory.subscriber("FaceDetected")
            self._face_sub.signal.connect(self._on_face)
            print("[face] 顔検知 購読完了")
        except Exception as e:
            print("[face] 初期化エラー: " + str(e))

    def _on_face(self, value):
        try:
            if self._is_chat_gpt_running():
                return  # アプリ実行中は挨拶しない
            if not value or len(value) < 2 or not value[1]:
                return
            faces = value[1]
            if not faces:
                return
            face      = faces[0]
            face_id   = int(face[1][0]) if len(face) > 1 and face[1] else -1
            face_name = str(face[1][1]).strip() if (len(face) > 1 and
                         len(face[1]) > 1 and face[1][1]) else ""
            now  = time.time()
            last = self._greeted.get(face_id, 0)
            if now - last < self.GREET_COOL:
                return
            self._greeted[face_id] = now
            name = face_name if face_name else None
            t = threading.Thread(target=self._greet, args=(name,))
            t.daemon = True
            t.start()
        except Exception as e:
            print("[face cb] エラー: " + str(e))

    def _greet(self, name=None):
        if name:
            self._say(greet_named(name))
        else:
            self._say(random.choice(GREET_UNKNOWN))

    # ----------------------------------------------------------
    # ALDialog トピックロード（u:() 応答ルール）
    # ----------------------------------------------------------
    def _init_dialog(self):
        top = "/home/nao/idle_chat_jpj.top"
        if not os.path.exists(top):
            print("[dialog] .top が見つかりません")
            return
        try:
            dialog = self.session.service("ALDialog")
            for t in dialog.getAllLoadedTopics():
                if "idle_chat" in t:
                    try: dialog.deactivateTopic(t)
                    except: pass
                    try: dialog.unloadTopic(t)
                    except: pass
            topic = dialog.loadTopic(top)
            dialog.activateTopic(topic)
            try:
                dialog.unsubscribe("idle_chat_daemon")
            except:
                pass
            dialog.subscribe("idle_chat_daemon")
            print("[dialog] トピックロード完了: " + topic)
        except Exception as e:
            print("[dialog] エラー: " + str(e))

    # ----------------------------------------------------------
    # 発話（排他制御付き）
    # ----------------------------------------------------------
    def _say(self, phrase):
        if self._lock.acquire(False):
            try:
                print("[say] " + repr(phrase[:40]))
                self.animated.say(phrase)
                print("[say] 完了")
            except Exception as e:
                print("[say] エラー: " + str(e))
            finally:
                self._lock.release()
        else:
            print("[say] スキップ（発話中）")

    # ----------------------------------------------------------
    # 無言アニメーション（フィジェット）
    # ----------------------------------------------------------
    def _fidget(self):
        anim = random.choice(FIDGET_ANIMS)
        if self._lock.acquire(False):
            try:
                print("[fidget] " + anim)
                if self.bm.isBehaviorInstalled(anim):
                    done = [False]
                    def _run():
                        try: self.bm.runBehavior(anim)
                        except: pass
                        done[0] = True
                    t = threading.Thread(target=_run)
                    t.daemon = True
                    t.start()
                    t.join(12.0)
                    if not done[0]:
                        try: self.bm.stopBehavior(anim)
                        except: pass
                    print("[fidget] 完了")
                else:
                    print("[fidget] not installed: " + anim)
            except Exception as e:
                print("[fidget] エラー: " + str(e))
            finally:
                self._lock.release()
        else:
            print("[fidget] スキップ（発話中）")

    # ----------------------------------------------------------
    # 移動（足を動かす）
    # ----------------------------------------------------------
    def _fidget_move(self):
        step = random.choice(MOVE_STEPS)
        print("[move] moveTo(%.1f, %.1f, %.1f)" % step)
        try:
            motion = self.session.service("ALMotion")
            done = [False]
            def _run():
                try: motion.moveTo(step[0], step[1], step[2])
                except: pass
                done[0] = True
            t = threading.Thread(target=_run)
            t.daemon = True
            t.start()
            t.join(8.0)
            print("[move] 完了")
        except Exception as e:
            print("[move] エラー: " + str(e))

    # ----------------------------------------------------------
    # メインループ
    # ----------------------------------------------------------
    def run(self):
        time.sleep(3.0)
        print("[run] 起動挨拶")
        self._say("^start(animations/Stand/Gestures/Hey_1) こんにちは！ペッパーです！よろしくね！ ^wait(animations/Stand/Gestures/Hey_1)")

        while not self._stop:
            wait = random.uniform(self.IDLE_MIN, self.IDLE_MAX)
            print("[run] 次の動作まで %.0f 秒待機" % wait)
            elapsed = 0.0
            while elapsed < wait and not self._stop:
                time.sleep(3.0)
                elapsed += 3.0

            if self._stop:
                break

            if self._is_chat_gpt_running():
                print("[run] chat_gpt.py 実行中 - スキップ")
                continue

            roll = random.random()
            if roll < self.SPEAK_PROB:
                self._say(random.choice(IDLE_PHRASES))
            elif roll < self.SPEAK_PROB + self.MOVE_PROB:
                self._fidget_move()
            else:
                self._fidget()

    def stop(self):
        self._stop = True


# ============================================================
# エントリーポイント
# ============================================================
def main():
    app = qi.Application(["IdleChatDaemon", "--qi-url=tcp://127.0.0.1:9559"])
    app.start()
    session = app.session

    daemon = IdleChatDaemon(session)

    t = threading.Thread(target=daemon.run)
    t.daemon = True
    t.start()

    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        daemon.stop()
        print("[main] 停止")


if __name__ == "__main__":
    main()
