# -*- coding: utf-8 -*-
"""
behaviors/celebrate.py - お祝い・勝利ビヘイビア

勝ったとき、良いことがあったときなどに使う。
LEDを派手に点滅させて勝利アニメーションを再生。

使い方:
    python celebrate.py [IP] [発話テキスト]
"""
from __future__ import print_function
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"


def celebrate(ip=PEPPER_IP, port=9559, text=None):
    pp = Pepper(ip, port)

    message = text or "やったー！おめでとうございます！最高です！"

    # LED 点滅（オレンジ→黄→白）
    pp.leds.set_color(1.0, 0.5, 0.0, 0.1)
    time.sleep(0.2)
    pp.leds.set_color(1.0, 1.0, 0.0, 0.1)
    time.sleep(0.2)

    # 勝利アニメーション
    pp.say_with_anim(message, "animations/Stand/Emotions/Positive/Victory_1")
    time.sleep(0.3)

    # 興奮アニメーション
    pp.say_with_anim(
        "最高の結果ですね！",
        "animations/Stand/Emotions/Positive/Excited_1"
    )
    time.sleep(0.3)

    # 手を振る
    pp.wave("R", text="素晴らしい！")

    # レインボーLED
    pp.leds.rainbow(2.0)
    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip   = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    text = sys.argv[2] if len(sys.argv) > 2 else None
    celebrate(ip, text=text)
