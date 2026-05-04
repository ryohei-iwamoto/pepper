# -*- coding: utf-8 -*-
"""
behaviors/greet.py - 挨拶ビヘイビア

人を検出したときや起動時の挨拶。
手を振りながら日本語で挨拶する。

使い方:
    python greet.py [IP]
    python greet.py 192.168.0.46
"""
from __future__ import print_function
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP   = "192.168.0.46"
PEPPER_PORT = 9559


def greet(ip=PEPPER_IP, port=PEPPER_PORT):
    pp = Pepper(ip, port)

    # 顔LEDを明るく（歓迎色）
    pp.set_led_color(0.0, 1.0, 0.8, 0.3)

    # 手を振りながら挨拶
    pp.wave("R", text="こんにちは！私はPepperです。よろしくお願いします！")

    # お辞儀
    pp.bow(text="どうぞよろしくお願いします。")

    # LED白に戻す
    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    greet(ip)
