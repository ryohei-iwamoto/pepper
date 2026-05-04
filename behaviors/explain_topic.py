# -*- coding: utf-8 -*-
"""
behaviors/explain_topic.py - 説明・案内ビヘイビア

何かを説明するシーン。Explain ジェスチャーを使って
自然なプレゼンテーション風に話す。

使い方:
    python explain_topic.py [IP]
"""
from __future__ import print_function
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"

# 説明ジェスチャー一覧（Explain_1〜11 を使い回す）
EXPLAIN_ANIMS = [
    "animations/Stand/Gestures/Explain_1",
    "animations/Stand/Gestures/Explain_3",
    "animations/Stand/Gestures/Explain_5",
    "animations/Stand/Gestures/Explain_7",
    "animations/Stand/Gestures/Explain_9",
    "animations/Stand/Gestures/Explain_11",
]

SHOW_SKY_ANIMS = [
    "animations/Stand/Gestures/ShowSky_1",
    "animations/Stand/Gestures/ShowSky_4",
    "animations/Stand/Gestures/ShowSky_5",
    "animations/Stand/Gestures/ShowSky_6",
    "animations/Stand/Gestures/ShowSky_7",
    "animations/Stand/Gestures/ShowSky_8",
]


def explain(ip=PEPPER_IP, port=9559, sentences=None):
    """
    複数文を説明ジェスチャーで順番に話す。

    Args:
        sentences (list): 話す文のリスト（省略時はデモ文章）
    """
    pp = Pepper(ip, port)
    pp.set_led_color(0.0, 0.6, 1.0, 0.3)

    if sentences is None:
        sentences = [
            "まず、最初のポイントをご説明します。",
            "次に、重要なことをお伝えします。",
            "こちらがメインのポイントです。",
            "最後に、まとめをお伝えします。",
        ]

    for i, sentence in enumerate(sentences):
        anim = EXPLAIN_ANIMS[i % len(EXPLAIN_ANIMS)]
        pp.say_with_anim(sentence, anim)
        time.sleep(0.3)

    pp.reset_leds()
    pp.stand()


def show_big_picture(ip=PEPPER_IP, port=9559, text="大きなビジョンを描きましょう！"):
    """壮大なことを話す時のジェスチャー。"""
    pp = Pepper(ip, port)
    import random
    anim = random.choice(SHOW_SKY_ANIMS)
    pp.set_led_color(0.0, 0.5, 1.0, 0.3)
    pp.say_with_anim(text, anim)
    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    explain(ip)
