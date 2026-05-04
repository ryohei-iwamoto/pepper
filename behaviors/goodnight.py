# -*- coding: utf-8 -*-
"""
behaviors/goodnight.py - おやすみ・スリープシーケンス

段々おとなしくなっていく眠りのシーケンス。
LEDをゆっくり暗くして、最後に省エネモードへ。

使い方:
    python goodnight.py [IP]
"""
from __future__ import print_function
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"


def goodnight(ip=PEPPER_IP, port=9559):
    pp = Pepper(ip, port)

    # 1. あくびポーズ（ScratchHead で代用）
    pp.set_led_color(0.5, 0.0, 0.8, 0.5)
    pp.say_with_anim(
        "うーん、少し眠くなってきました。",
        "animations/Stand/Waiting/ScratchHead_1"
    )
    time.sleep(0.5)

    # 2. 退屈・眠いポーズ
    pp.set_led_color(0.2, 0.0, 0.5, 0.5)
    pp.say_with_anim(
        "今日もお疲れ様でした。",
        "animations/Stand/Emotions/Negative/Bored_1"
    )
    time.sleep(0.5)

    # 3. おやすみの挨拶
    pp.set_led_color(0.1, 0.0, 0.3, 1.0)
    pp.say_with_anim(
        "おやすみなさい。また明日お話しましょう！",
        "animations/Stand/Gestures/BowShort_1"
    )
    time.sleep(0.5)

    # 4. LEDをゆっくり消す
    for intensity in [0.8, 0.6, 0.4, 0.2, 0.0]:
        pp.leds.set_color(intensity * 0.1, 0.0, intensity * 0.3, 0.3)
        time.sleep(0.4)

    # 5. 省エネモード
    pp.body.rest()
    print("スリープモードに入りました。")


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    goodnight(ip)
