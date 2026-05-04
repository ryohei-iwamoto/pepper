# -*- coding: utf-8 -*-
"""
behaviors/morning.py - おはよう・起動シーケンス

眠りから覚めてだんだん活発になるウェイクアップシーケンス。

使い方:
    python morning.py [IP]
"""
from __future__ import print_function
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"


def morning(ip=PEPPER_IP, port=9559):
    pp = Pepper(ip, port)

    # 1. LEDを徐々に明るく
    for v in [0.1, 0.3, 0.5, 0.7, 1.0]:
        pp.leds.set_color(v, v * 0.8, v * 0.2, 0.4)
        time.sleep(0.3)

    # 2. 伸び
    pp.say_with_anim(
        "おはようございます！よく眠れましたか？",
        "animations/Stand/Waiting/Stretch_1"
    )
    time.sleep(0.3)

    # 3. もう一度伸び
    pp.say_with_anim(
        "気持ちのいい朝ですね！",
        "animations/Stand/Waiting/Stretch_2"
    )
    time.sleep(0.3)

    # 4. 元気よく挨拶
    pp.set_led_color(1.0, 0.9, 0.0, 0.2)
    pp.say_with_anim(
        "今日も一日頑張りましょう！",
        "animations/Stand/Emotions/Positive/Excited_1"
    )
    time.sleep(0.3)

    # 5. 手を振る
    pp.wave("R", text="よろしくお願いします！")

    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    morning(ip)
