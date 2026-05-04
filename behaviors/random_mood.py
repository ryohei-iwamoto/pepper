# -*- coding: utf-8 -*-
"""
behaviors/random_mood.py - ランダム感情表現ループ

指定した時間ごとにランダムに感情を変えながら過ごす。
展示・デモ用。Ctrl+C で終了。

使い方:
    python random_mood.py [IP] [間隔秒]
    python random_mood.py 192.168.0.46 5
"""
from __future__ import print_function
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"

MOOD_POOL = [
    ("happy",     "今日はとても気分がいいです！"),
    ("excited",   "わあ、なんかワクワクしてきました！"),
    ("thinking",  "ふむふむ、考えさせてください。"),
    ("shy",       "えっ、そんなに見ないでください..."),
    ("confident", "任せてください！"),
    ("surprised", "えっ、本当ですか？"),
    ("grateful",  "ありがとうございます！感謝しています！"),
    ("bored",     "少し退屈になってきました...何かありますか？"),
    ("sad",       "なんだか寂しい気分です..."),
    ("happy",     "みなさんと話すのが大好きです！"),
    ("excited",   "面白いことを思いつきました！"),
    ("thinking",  "むむ、これは難しいですね。"),
]

IDLE_ANIMS = [
    ("animations/Stand/Waiting/Think_1",    "少し考えています。"),
    ("animations/Stand/Waiting/Think_2",    "ぼーっとしていましたね。"),
    ("animations/Stand/Waiting/PlayHands_1","手遊びしちゃいました。"),
    ("animations/Stand/Waiting/LookHand_1", "自分の手が気になります。"),
    ("animations/Stand/Waiting/ScratchHead_1", "頭が少しかゆい？"),
    ("animations/Stand/Waiting/Binoculars_1", "何か見えますか？"),
]


def random_mood(ip=PEPPER_IP, port=9559, interval=8.0):
    pp = Pepper(ip, port)
    pp.say("ランダム感情デモを開始します。Ctrl+Cで終了できます。")

    print("ランダム感情ループ（{:.1f}秒ごと）。Ctrl+C で終了。".format(interval))

    try:
        while True:
            # 70% 感情表現、30% アイドルアニメーション
            if random.random() < 0.7:
                emotion, text = random.choice(MOOD_POOL)
                print("[感情] {} : {}".format(emotion, text))
                pp.emotion(emotion, text)
            else:
                anim, text = random.choice(IDLE_ANIMS)
                print("[アイドル] {}".format(text))
                pp.say_with_anim(text, anim)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n終了します。")
        pp.say("デモを終了します。ありがとうございました！")
        pp.stand()
        pp.reset_leds()


if __name__ == "__main__":
    ip       = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    random_mood(ip, interval=interval)
