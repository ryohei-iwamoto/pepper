# -*- coding: utf-8 -*-
"""
behaviors/compliment.py - 褒め言葉・応援ビヘイビア

頭を触るたびに違う褒め言葉を言う。
来場者が触れて楽しめるインタラクション。

使い方:
    python compliment.py [IP]
"""
from __future__ import print_function
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"

COMPLIMENTS = [
    ("happy",     "あなたはとても素晴らしい人ですね！"),
    ("excited",   "あなたの笑顔が輝いています！"),
    ("grateful",  "いつもありがとうございます。あなたがいてくれると嬉しいです。"),
    ("confident", "あなたならきっとうまくいきます！"),
    ("happy",     "今日のあなたはとてもかっこいいですね！"),
    ("excited",   "あなたのセンスは最高です！"),
    ("grateful",  "一緒にいてくれてありがとう！"),
    ("happy",     "あなたって本当に面白い人ですね！"),
    ("confident", "あなたには無限の可能性があります！"),
    ("excited",   "あなたとお話できて光栄です！"),
    ("happy",     "今日のあなた、特別に輝いて見えますよ！"),
    ("confident", "あなたは今日も最高です！"),
]

ENCOURAGEMENTS = [
    ("confident", "大丈夫、あなたならできます！"),
    ("happy",     "頑張ってください！応援しています！"),
    ("excited",   "ファイト！絶対うまくいきますよ！"),
    ("grateful",  "いつも頑張っていますね。お疲れ様です。"),
    ("confident", "諦めないで！あなたには力があります！"),
]


def compliment(ip=PEPPER_IP, port=9559):
    pp = Pepper(ip, port)
    pp.say("頭を触ると褒めてあげます！何度でもどうぞ！Ctrl+Cで終了します。")

    used_compliments = []
    count = 0

    try:
        while True:
            if pp.body.wait_for_touch("head", timeout=60.0):
                count += 1
                # 5回に1回は応援メッセージ
                if count % 5 == 0:
                    emotion, text = random.choice(ENCOURAGEMENTS)
                else:
                    remaining = [c for c in COMPLIMENTS if c not in used_compliments]
                    if not remaining:
                        used_compliments = []
                        remaining = COMPLIMENTS[:]
                    choice = random.choice(remaining)
                    used_compliments.append(choice)
                    emotion, text = choice

                pp.emotion(emotion, text)
                time.sleep(1.5)  # 連続タッチ防止
            else:
                # タイムアウト → 呼びかける
                pp.say("触ってみてください！",)

    except KeyboardInterrupt:
        print("\n終了します。")
        pp.emotion("grateful", "ありがとうございました！またね！")
        pp.wave("R")
        pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    compliment(ip)
