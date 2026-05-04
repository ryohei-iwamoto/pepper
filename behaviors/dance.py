# -*- coding: utf-8 -*-
"""
behaviors/dance.py - ダンス・音楽系ビヘイビア

エアギター・回転・ウィング・ハッピーバースデーなどの
音楽・ダンス系アニメーション集。

使い方:
    python dance.py [IP] [air_guitar|birthday|robot|wings]
"""
from __future__ import print_function
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"

DANCE_MOVES = {
    "air_guitar": (
        "animations/Stand/Waiting/AirGuitar_1",
        "ロックンロール！エアギターをお楽しみください！"
    ),
    "birthday": (
        "animations/Stand/Waiting/HappyBirthday_1",
        "ハッピーバースデー！お誕生日おめでとうございます！"
    ),
    "robot": (
        "animations/Stand/Waiting/Robot_1",
        "ロボットダンスを披露します！"
    ),
    "wings": (
        "animations/Stand/Waiting/Wings_1",
        "翼を広げます！"
    ),
    "wings2": (
        "animations/Stand/Waiting/Wings_2",
        "大きく羽ばたきます！"
    ),
    "play_hands": (
        "animations/Stand/Waiting/PlayHands_1",
        "手遊びをしましょう！"
    ),
    "binoculars": (
        "animations/Stand/Waiting/Binoculars_1",
        "遠くを見てみましょう！"
    ),
    "scratch_head": (
        "animations/Stand/Waiting/ScratchHead_1",
        "うーん、面白いですね。"
    ),
}


def dance(ip=PEPPER_IP, port=9559, move=None):
    pp = Pepper(ip, port)

    if move and move in DANCE_MOVES:
        anim, text = DANCE_MOVES[move]
        pp.set_led_color(1.0, 0.5, 0.0, 0.3)
        pp.say_with_anim(text, anim)
    else:
        # ランダムで3回ダンス
        moves = list(DANCE_MOVES.items())
        random.shuffle(moves)
        pp.set_led_color(1.0, 0.5, 0.0, 0.3)
        pp.say("ダンスタイムです！色々やってみますよ！")
        for name, (anim, text) in moves[:3]:
            pp.say_with_anim(text, anim)
            time.sleep(0.3)

    pp.emotion("happy", "楽しんでいただけましたか？")
    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip   = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    move = sys.argv[2] if len(sys.argv) > 2 else None
    dance(ip, move=move)
