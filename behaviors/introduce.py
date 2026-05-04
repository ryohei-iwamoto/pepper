# -*- coding: utf-8 -*-
"""
behaviors/introduce.py - 自己紹介ビヘイビア

Pepperが自分のことを紹介する。
複数のジェスチャーと発話を組み合わせた長め のシーケンス。

使い方:
    python introduce.py [IP]
"""
from __future__ import print_function
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP   = "192.168.0.46"
PEPPER_PORT = 9559


def introduce(ip=PEPPER_IP, port=PEPPER_PORT):
    pp = Pepper(ip, port)

    # 1. 挨拶
    pp.set_led_color(0.0, 0.8, 1.0, 0.3)
    pp.say_with_anim(
        "みなさん、こんにちは！",
        "animations/Stand/Gestures/Hey_1"
    )
    time.sleep(0.3)

    # 2. 自己紹介
    pp.say_with_anim(
        "私の名前はPepperです。",
        "animations/Stand/Gestures/Me_1"
    )
    time.sleep(0.3)

    # 3. できること
    pp.set_led_color(1.0, 0.9, 0.0, 0.3)
    pp.say_with_anim(
        "私はお話したり、歌ったり、踊ったりすることができます！",
        "animations/Stand/Gestures/Enthusiastic_5"
    )
    time.sleep(0.3)

    # 4. 感情表現
    pp.emotion("happy", "みなさんとお話できて、とても嬉しいです！")
    time.sleep(0.3)

    # 5. お辞儀で締め
    pp.set_led_color(0.0, 1.0, 0.5, 0.3)
    pp.bow(text="どうぞよろしくお願いします！")

    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    introduce(ip)
