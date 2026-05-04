# -*- coding: utf-8 -*-
"""
behaviors/storytelling.py - ストーリーテリングビヘイビア

複数のジェスチャー・感情・LEDを組み合わせて
Pepperが短い物語を語る。長めのシーケンスのサンプル。

使い方:
    python storytelling.py [IP]
"""
from __future__ import print_function
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"


def tell_story(ip=PEPPER_IP, port=9559):
    pp = Pepper(ip, port)

    # オープニング
    pp.set_led_color(0.0, 0.5, 1.0, 0.5)
    pp.say_with_anim(
        "みなさん、今から短いお話をしますね。",
        "animations/Stand/Gestures/Hey_1"
    )
    time.sleep(0.3)

    # 1. 出会い
    pp.set_led_color(1.0, 0.9, 0.0, 0.5)
    pp.say_with_anim(
        "昔々、ある森の中にひとりの旅人がいました。",
        "animations/Stand/Gestures/ShowSky_1"
    )
    time.sleep(0.3)

    # 2. 問題発生
    pp.set_led_color(1.0, 0.5, 0.0, 0.5)
    pp.say_with_anim(
        "その旅人は道に迷ってしまいました。",
        "animations/Stand/Gestures/IDontKnow_1"
    )
    time.sleep(0.3)

    # 3. 考える
    pp.emotion("thinking", "どこへ行けばいいんだろう... と悩んでいました。")
    time.sleep(0.3)

    # 4. 解決
    pp.set_led_color(0.0, 1.0, 0.5, 0.5)
    pp.say_with_anim(
        "すると星が輝いて、道を照らしてくれました！",
        "animations/Stand/Gestures/ShowSky_5"
    )
    time.sleep(0.3)

    # 5. ハッピーエンド
    pp.emotion("happy", "旅人は無事に家に帰ることができました。めでたし、めでたし！")
    time.sleep(0.3)

    # エンディング
    pp.set_led_color(1.0, 0.9, 0.0, 0.5)
    pp.say_with_anim(
        "どんなに困っても、諦めなければ道は開けるものですね。",
        "animations/Stand/Gestures/Explain_1"
    )
    time.sleep(0.3)

    pp.bow(text="お聞きいただきありがとうございました！")
    pp.leds.rainbow(2.0)
    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    tell_story(ip)
