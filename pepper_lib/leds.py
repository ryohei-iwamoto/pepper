# -*- coding: utf-8 -*-
"""
pepper_lib.leds - LED 制御

ALLeds をラップして色・パターン制御を簡単にする。
"""
from __future__ import print_function
import time


class Leds(object):
    """
    Pepper の LED を制御するクラス。

    LEDグループ名:
        FaceLeds         - 顔全体
        FaceLedsTop      - 顔上部
        FaceLedsBottom   - 顔下部
        FaceLedsExternal - 顔外側
        FaceLedsInternal - 顔内側
        EarLeds          - 両耳
        LeftEarLeds      - 左耳
        RightEarLeds     - 右耳
        ChestLeds        - 胸
        HeadLeds         - 頭頂部
        AllLeds          - 全LED

    Example:
        leds = Leds(core)
        leds.set_color(1.0, 0.0, 0.0)   # 赤
        leds.emotion_happy()
        leds.emotion_sad()
        leds.reset()
    """

    # 感情に対応する色 (R, G, B)
    EMOTION_COLORS = {
        "happy":     (1.0, 0.9, 0.0),   # 黄
        "excited":   (1.0, 0.5, 0.0),   # オレンジ
        "sad":       (0.0, 0.2, 1.0),   # 青
        "angry":     (1.0, 0.0, 0.0),   # 赤
        "scared":    (0.5, 0.0, 0.5),   # 紫
        "thinking":  (0.0, 0.6, 1.0),   # シアン
        "surprised": (1.0, 1.0, 0.0),   # 黄（明るい）
        "shy":       (1.0, 0.4, 0.4),   # ピンク
        "bored":     (0.3, 0.3, 0.3),   # グレー
        "neutral":   (1.0, 1.0, 1.0),   # 白
    }

    def __init__(self, core):
        self._core = core

    def set_color(self, r, g, b, duration=0.2, group="FaceLeds"):
        """
        LEDグループの色を設定する。

        Args:
            r, g, b (float): 各色成分 0.0〜1.0
            duration (float): 遷移時間（秒）
            group (str): LEDグループ名
        """
        self._core.leds_proxy.fadeRGB(group, r, g, b, duration)

    def set_emotion_color(self, emotion, duration=0.3, group="FaceLeds"):
        """
        感情に対応する色に設定する。

        Args:
            emotion (str): 感情名（EMOTION_COLORS のキー）
            duration (float): 遷移時間（秒）
            group (str): LEDグループ名
        """
        r, g, b = self.EMOTION_COLORS.get(emotion, (1.0, 1.0, 1.0))
        self.set_color(r, g, b, duration, group)

    def reset(self, group="FaceLeds", duration=0.5):
        """LEDを標準の白に戻す。"""
        self.set_color(1.0, 1.0, 1.0, duration, group)

    def off(self, group="FaceLeds"):
        """LEDを消灯する。"""
        self._core.leds_proxy.off(group)

    def on(self, group="FaceLeds"):
        """LEDを点灯（白）する。"""
        self._core.leds_proxy.on(group)

    def blink(self, r, g, b, interval=0.3, times=5, group="FaceLeds"):
        """
        LEDを点滅させる。

        Args:
            r, g, b (float): 色 0.0〜1.0
            interval (float): 点滅間隔（秒）
            times (int): 点滅回数
            group (str): LEDグループ名
        """
        leds = self._core.leds_proxy
        for _ in range(times):
            leds.fadeRGB(group, r, g, b, interval * 0.3)
            time.sleep(interval * 0.5)
            leds.fadeRGB(group, 0.0, 0.0, 0.0, interval * 0.3)
            time.sleep(interval * 0.5)
        leds.fadeRGB(group, 1.0, 1.0, 1.0, 0.3)

    def rainbow(self, duration=3.0, group="FaceLeds"):
        """
        虹色にゆっくり変化する。
        """
        colors = [
            (1.0, 0.0, 0.0),   # 赤
            (1.0, 0.5, 0.0),   # オレンジ
            (1.0, 1.0, 0.0),   # 黄
            (0.0, 1.0, 0.0),   # 緑
            (0.0, 0.0, 1.0),   # 青
            (0.5, 0.0, 1.0),   # 紫
        ]
        step = duration / len(colors)
        leds = self._core.leds_proxy
        for r, g, b in colors:
            leds.fadeRGB(group, r, g, b, step * 0.9)
            time.sleep(step)
        self.reset(group)

    def pulse(self, r, g, b, times=3, period=1.0, group="FaceLeds"):
        """
        指定色でゆっくりパルス（息をするような明滅）。

        Args:
            r, g, b (float): 色
            times (int): 繰り返し回数
            period (float): 1周期の秒数
            group (str): LEDグループ名
        """
        leds = self._core.leds_proxy
        half = period / 2.0
        for _ in range(times):
            leds.fadeRGB(group, r, g, b, half)
            time.sleep(half)
            leds.fadeRGB(group, r * 0.1, g * 0.1, b * 0.1, half)
            time.sleep(half)
        self.reset(group)

    # ---- 感情ショートカット ----

    def emotion_happy(self):
        """喜び: 黄色"""
        self.set_emotion_color("happy")

    def emotion_sad(self):
        """悲しみ: 青"""
        self.set_emotion_color("sad")

    def emotion_angry(self):
        """怒り: 赤"""
        self.set_emotion_color("angry")

    def emotion_thinking(self):
        """思考中: シアン"""
        self.set_emotion_color("thinking")

    def emotion_surprised(self):
        """驚き: 明るい黄"""
        self.set_emotion_color("surprised")

    def emotion_shy(self):
        """恥ずかしい: ピンク"""
        self.set_emotion_color("shy")

    def emotion_excited(self):
        """興奮: オレンジ"""
        self.set_emotion_color("excited")

    # ---- 耳・胸 ----

    def ear_rotate(self, period=2.0):
        """耳LEDをくるくる回す（開始するだけ、同期しない）。"""
        leds = self._core.leds_proxy
        try:
            leds.rotateEars(period, True)
        except Exception:
            # 古いファームウェアでは未対応の場合あり
            self.set_color(0.0, 0.5, 1.0, 0.2, "EarLeds")

    def chest_color(self, r, g, b, duration=0.3):
        """胸のLEDの色を設定する。"""
        self.set_color(r, g, b, duration, "ChestLeds")
