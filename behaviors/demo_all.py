# -*- coding: utf-8 -*-
"""
behaviors/demo_all.py - ライブラリ全機能デモ

pepper_lib の全機能を順番にデモンストレーション。
動作確認・お披露目用。

使い方:
    python demo_all.py [IP]
"""
from __future__ import print_function
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP   = "192.168.0.46"
PEPPER_PORT = 9559


def demo_all(ip=PEPPER_IP, port=PEPPER_PORT):
    print("デモ開始。Ctrl+C で中断できます。")
    pp = Pepper(ip, port)

    # --- 1. 挨拶 ---
    print("[1/8] 挨拶")
    pp.set_led_color(0.0, 1.0, 0.8, 0.3)
    pp.wave("R", text="みなさん、こんにちは！Pepperです！")
    time.sleep(0.5)

    # --- 2. 感情: 嬉しい ---
    print("[2/8] 感情: happy")
    pp.emotion("happy", "今日もいい天気ですね！とても嬉しいです！")
    time.sleep(0.5)

    # --- 3. 感情: 考え中 ---
    print("[3/8] 感情: thinking")
    pp.emotion("thinking", "うーん、何かお手伝いできることはありますか？")
    time.sleep(0.5)

    # --- 4. 感情: 興奮 ---
    print("[4/8] 感情: excited")
    pp.emotion("excited", "わあ！すごいですね！")
    time.sleep(0.5)

    # --- 5. お辞儀 ---
    print("[5/8] お辞儀")
    pp.set_led_color(0.0, 0.8, 0.0, 0.3)
    pp.bow(text="よろしくお願いします！")
    time.sleep(0.5)

    # --- 6. LED レインボー ---
    print("[6/8] LED レインボー")
    pp.say("LEDのデモです。")
    pp.leds.rainbow(duration=3.0)
    time.sleep(0.3)

    # --- 7. 感情: 感謝 ---
    print("[7/8] 感情: grateful")
    pp.emotion("grateful", "見ていただいてありがとうございます！")
    time.sleep(0.5)

    # --- 8. さようなら ---
    print("[8/8] さようなら")
    pp.set_led_color(1.0, 0.5, 0.0, 0.3)
    pp.wave("R", text="それではまた！さようなら！")

    # 終了
    pp.reset_leds()
    pp.stand()
    print("デモ完了！")


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    demo_all(ip)
