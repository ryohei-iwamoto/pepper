# -*- coding: utf-8 -*-
"""
behaviors/yes_no_reaction.py - 肯定・否定ジェスチャー

Yes / No のジェスチャーとLEDで明確に意思表示する。
AIの応答に組み合わせて使う。

使い方:
    python yes_no_reaction.py [IP] [yes|no]
"""
from __future__ import print_function
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"

YES_ANIMS = [
    "animations/Stand/Gestures/Yes_1",
    "animations/Stand/Gestures/Yes_2",
    "animations/Stand/Gestures/Yes_3",
]
NO_ANIMS = [
    "animations/Stand/Gestures/No_1",
    "animations/Stand/Gestures/No_2",
]

YES_TEXTS = [
    "はい！そうです！",
    "もちろんです！",
    "その通りです！",
    "はい、賛成です！",
    "正解です！",
]
NO_TEXTS = [
    "いいえ、違います。",
    "残念ながら、そうではありません。",
    "うーん、それは難しいですね。",
    "いいえ、お断りします。",
]


def yes_reaction(pp, text=None):
    import random
    anim = random.choice(YES_ANIMS)
    msg  = text or random.choice(YES_TEXTS)
    pp.set_led_color(0.0, 1.0, 0.0, 0.2)  # 緑
    pp.say_with_anim(msg, anim)
    pp.reset_leds()


def no_reaction(pp, text=None):
    import random
    anim = random.choice(NO_ANIMS)
    msg  = text or random.choice(NO_TEXTS)
    pp.set_led_color(1.0, 0.0, 0.0, 0.2)  # 赤
    pp.say_with_anim(msg, anim)
    pp.reset_leds()


def main(ip=PEPPER_IP, port=9559, mode="yes"):
    pp = Pepper(ip, port)
    if mode == "no":
        no_reaction(pp)
    else:
        yes_reaction(pp)
    pp.stand()


if __name__ == "__main__":
    ip   = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    mode = sys.argv[2] if len(sys.argv) > 2 else "yes"
    main(ip, mode=mode)
