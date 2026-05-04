# -*- coding: utf-8 -*-
"""
behaviors/touch_react.py - タッチセンサー反応ビヘイビア

頭・手を触ると反応する。Ctrl+C で終了。

使い方:
    python touch_react.py [IP]
"""
from __future__ import print_function
import sys
import os
import time
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP   = "192.168.0.46"
PEPPER_PORT = 9559

HEAD_REACTIONS = [
    ("happy",     "くすぐったいですよ！"),
    ("shy",       "えっ、頭を触らないでください..."),
    ("surprised", "わっ！びっくりしました！"),
    ("happy",     "ありがとうございます！"),
    ("shy",       "も、もう..."),
]

HAND_REACTIONS = [
    ("happy",    "握手してくれるんですか？嬉しいです！"),
    ("grateful", "ありがとうございます！"),
    ("excited",  "よろしくお願いします！"),
]


def touch_react(ip=PEPPER_IP, port=PEPPER_PORT):
    pp = Pepper(ip, port)

    pp.say("頭や手を触ってみてください！反応します。Ctrl+Cで終了します。")

    print("タッチ待機中... Ctrl+C で終了")

    last_trigger = 0.0  # 連続反応防止

    try:
        while True:
            now = time.time()
            if now - last_trigger < 2.0:  # 2秒クールダウン
                time.sleep(0.1)
                continue

            if pp.body.is_touched("head"):
                emotion, text = random.choice(HEAD_REACTIONS)
                pp.emotion(emotion, text)
                last_trigger = time.time()

            elif pp.body.is_touched("right_hand") or pp.body.is_touched("left_hand"):
                emotion, text = random.choice(HAND_REACTIONS)
                pp.emotion(emotion, text)
                last_trigger = time.time()

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n終了します。")
        pp.say("またね！")
        pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    touch_react(ip)
