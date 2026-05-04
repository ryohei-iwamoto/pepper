# -*- coding: utf-8 -*-
"""
pepper_lib - Pepper ロボット開発ライブラリ
Python 2.7 + NAOqi SDK 2.1.4.13

使い方:
    import sys
    sys.path.insert(0, r"D:\D_Playprograming\pepper")
    from pepper_lib import Pepper

    pp = Pepper("192.168.0.46")
    pp.say("こんにちは！")
    pp.emotion("happy")
    pp.bow()
"""


import sys
import os

# SDK パスを自動追加
# 優先順位: 環境変数 PYNAOQI_SDK > リポジトリ直下の pynaoqi-sdk/ > 従来パス
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SDK_PATH = (
    os.environ.get("PYNAOQI_SDK")
    or os.path.join(_REPO_ROOT, "pynaoqi-sdk")
    or os.path.join(_REPO_ROOT,
                    r"pynaoqi-python2.7-2.1.4.13-win32-vs2010 (1)",
                    "pynaoqi-python2.7-2.1.4.13-win32-vs2010")
)
if _SDK_PATH not in sys.path:
    sys.path.insert(0, _SDK_PATH)

from pepper_lib.core import PepperCore
from pepper_lib.speech import Speech
from pepper_lib.body import Body
from pepper_lib.leds import Leds
from pepper_lib.emotions import Emotions
from pepper_lib.navigation import Navigation
from pepper_lib.primitives import Primitives


class Pepper(object):
    """
    Pepper ロボットのメインファサードクラス。

    全機能に統一されたインタフェースでアクセスできる。

    Example:
        pp = Pepper("192.168.0.46")
        pp.say("こんにちは！")
        pp.emotion("happy")
        pp.bow()
        pp.move_forward(0.5)
    """

    def __init__(self, ip="192.168.0.46", port=9559, language="Japanese", auto_stand=True):
        """
        Args:
            ip (str): Pepper の IP アドレス
            port (int): NAOqi ポート（通常 9559）
            language (str): TTS 言語 ("Japanese" / "English" など)
            auto_stand (bool): 初期化時に自動で立ち上がるか
        """
        self.ip   = ip
        self.port = port

        self.core       = PepperCore(ip, port)
        self.speech     = Speech(self.core)
        self.body       = Body(self.core)
        self.leds       = Leds(self.core)
        self.emotions   = Emotions(self.core, self.speech, self.body, self.leds)
        self.navigation = Navigation(self.core)
        self.primitives = Primitives(self.core)

        self.speech.set_language(language)

        if auto_stand:
            # ALAutonomousLife を無効化（NAOqi 2.1 でも動作している場合がある）。
            # これが running だとモーション制御が完全に上書きされる。
            try:
                autonomous = self.core.proxy("ALAutonomousLife")
                if autonomous.getState() != "disabled":
                    autonomous.setState("disabled")
            except Exception:
                pass

            self.body.wake_up()

            # ALBasicAwareness を停止する。
            # これが動いているとアニメーション付き発話が干渉されて動かなくなる。
            try:
                self.core.awareness.stopAwareness()
            except Exception:
                pass

            self.body.stand()

            # ALSpeakingMovement: 発話中に体を自然に揺らす
            try:
                self.core.speak_move.setMode("contextual")
                self.core.speak_move.setEnabled(True)
            except Exception:
                pass

            # ALAnimatedSpeech: 自動ジェスチャーモード
            try:
                self.core.animated.setBodyLanguageMode("contextual")
            except Exception:
                pass

    # ---- ショートカットメソッド ----

    def say(self, text, animated=True):
        """発話する。animated=True で自動ジェスチャー付き。"""
        if animated:
            self.speech.say_animated(text)
        else:
            self.speech.say(text)

    def say_with_anim(self, text, animation_path):
        """指定アニメーションと同時に発話する。"""
        self.speech.say_with_animation(text, animation_path)

    def emotion(self, name, text=None):
        """
        感情を表現する。

        Args:
            name (str): "happy" / "sad" / "angry" / "surprised" /
                        "thinking" / "shy" / "excited" / "bored"
            text (str): 発話テキスト（省略時はデフォルト発話）
        """
        self.emotions.express(name, text)

    def bow(self, text=None):
        """お辞儀をする。"""
        self.body.bow(text=text, speech=self.speech)

    def wave(self, text=None):
        """手を振る。"""
        self.body.wave(text=text, speech=self.speech)

    def nod(self):
        """頷く（うなずく）。"""
        self.body.nod()

    def shake_head(self):
        """首を横に振る。"""
        self.body.shake_head()

    def look_at(self, yaw, pitch, speed=0.15):
        """指定した方向に顔を向ける（ラジアン）。"""
        self.body.look_at(yaw, pitch, speed)

    def set_led_color(self, r, g, b, duration=0.2, group="FaceLeds"):
        """顔LEDの色を設定する（0.0〜1.0）。"""
        self.leds.set_color(r, g, b, duration, group)

    def reset_leds(self):
        """LEDを標準の白に戻す。"""
        self.leds.reset()

    def move_to(self, x, y=0.0, theta=0.0):
        """指定位置まで移動する（x=前後m, y=左右m, theta=回転rad）。"""
        self.navigation.move_to(x, y, theta)

    def turn(self, theta):
        """回転する（rad, 正=左回り）。"""
        self.navigation.turn(theta)

    def stand(self):
        """立ち姿勢に戻る。"""
        self.body.stand()

    def rest(self):
        """モーターを休止する（省エネ）。"""
        self.body.rest()

    def neutral(self, text=None):
        """ニュートラルな会話ジェスチャーで発話する（BodyTalk使用）。"""
        self.emotions.express("neutral", text)

    def explain(self, text=None):
        """説明・プレゼン風ジェスチャーで発話する。"""
        self.emotions.express("explain", text)

    def do(self, action, intensity=1.0, **kwargs):
        """
        プリミティブ動作を実行する。

        Args:
            action (str): プリミティブ名（primitives.CATALOG 参照）
            intensity (float): 動作強度 0.1〜1.5 (デフォルト 1.0)
        """
        self.primitives.execute(action, intensity=intensity, **kwargs)

    def do_speak(self, action, text, intensity=1.0):
        """
        プリミティブ動作と発話を並列実行する。

        Args:
            action (str): プリミティブ名
            text (str): 発話テキスト
            intensity (float): 動作強度 0.1〜1.5
        """
        self.primitives.execute_with_speech(action, text, intensity=intensity)

    def close(self):
        """セッションを安全に終了する。"""
        self.body.stand()
        self.leds.reset()
