# -*- coding: utf-8 -*-
"""
behaviors/happy.py - 喜びの感情表現

LEDを黄色にして、喜びのアニメーションとともに喜ぶ。

使い方:
    python happy.py [IP] [発話テキスト]
    python happy.py 192.168.0.46 "やったー！"
"""
from __future__ import print_function
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP   = "192.168.0.46"
PEPPER_PORT = 9559


def happy(ip=PEPPER_IP, port=PEPPER_PORT, text=None):
    pp = Pepper(ip, port)
    pp.emotion("happy", text)
    pp.stand()


if __name__ == "__main__":
    ip   = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    text = sys.argv[2] if len(sys.argv) > 2 else None
    happy(ip, text=text)
