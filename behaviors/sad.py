# -*- coding: utf-8 -*-
"""
behaviors/sad.py - 悲しみの感情表現

LEDを青にして、がっかりしたアニメーションとともに悲しむ。

使い方:
    python sad.py [IP] [発話テキスト]
"""
from __future__ import print_function
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP   = "192.168.0.46"
PEPPER_PORT = 9559


def sad(ip=PEPPER_IP, port=PEPPER_PORT, text=None):
    pp = Pepper(ip, port)
    pp.emotion("sad", text)
    pp.stand()


if __name__ == "__main__":
    ip   = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    text = sys.argv[2] if len(sys.argv) > 2 else None
    sad(ip, text=text)
