# -*- coding: utf-8 -*-
"""
behaviors/exercise.py - 運動・筋肉アピールビヘイビア

ALMotion.angleInterpolation() による直接関節制御で腕を動かす。
ALBehaviorManager のビルトインアニメーションには依存しない。

使い方:
    python exercise.py [IP]
"""
from __future__ import print_function
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"

# 制御する関節（左右腕+腰）
_JOINTS = [
    "LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
    "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
    "HipPitch",
]

# ニュートラル（直立・腕下げ）
_NEUTRAL = [1.4, 0.2, -0.5, -1.0,  1.4, -0.2, 0.5, 1.0,  0.0]

def _pose(motion, angles, duration=1.5):
    """指定ポーズへ移行する。"""
    motion.angleInterpolation(_JOINTS, angles, [duration] * len(_JOINTS), True)

def _neutral(motion, duration=0.8):
    _pose(motion, _NEUTRAL, duration)

def _say_and_move(pp, text, angles, duration=1.5):
    """発話と腕動作を並列実行する。"""
    motion = pp.core.motion
    tts    = pp.core.tts
    say_id = tts.post.say(text)           # 発話を非同期開始
    _pose(motion, angles, duration)       # 腕を動かす（同期）
    tts.wait(say_id, 15000)               # 発話完了を待つ
    time.sleep(0.2)


# ---- ポーズ定義: (テキスト, angles[9], 動作秒数) ----
ROUTINE = [
    (
        "私の筋肉を見てください！すごいでしょう？",
        # 両腕を横に上げてヒジを曲げる（力こぶ）
        [0.3,  0.7, -1.3, -0.5,   0.3, -0.7,  1.3,  0.5,  0.0],
        2.0,
    ),
    (
        "こんなに力持ちなんです！右も左も最強です！",
        # やや前に両腕を上げて強くヒジを曲げる
        [0.5,  0.4, -1.4, -0.3,   0.5, -0.4,  1.4,  0.3,  0.0],
        2.0,
    ),
    (
        "鍛えていますよ！毎日トレーニングです！",
        # 右腕を上に突き上げ、左腕は横に
        [0.8,  0.6, -0.5, -0.8,  -0.8, -0.3,  0.5,  1.0,  0.0],
        2.0,
    ),
    (
        "ロボットだって体力勝負です！両腕で受け止めます！",
        # 両腕を前に突き出す
        [-0.3, 0.1, -0.5, -1.0,  -0.3, -0.1,  0.5,  1.0,  0.2],
        2.0,
    ),
    (
        "フィットネスも得意ですよ！こんな感じです！",
        # 両腕を横に水平に広げる
        [0.0,  1.0, -0.2, -1.0,   0.0, -1.0,  0.2,  1.0,  0.0],
        2.0,
    ),
    (
        "伸びをしましょう！気持ちいいですよ！ぐーっと！",
        # 両腕を真上に高く挙げる
        [-1.4, 0.3, -0.4, -1.0,  -1.4, -0.3,  0.4,  1.0,  0.0],
        2.5,
    ),
    (
        "はい！完璧です！私の体は最高の状態です！",
        # 再び力こぶで締める
        [0.3,  0.7, -1.3, -0.5,   0.3, -0.7,  1.3,  0.5,  0.0],
        1.5,
    ),
]


def exercise(ip=PEPPER_IP, port=9559):
    pp = Pepper(ip, port)
    motion = pp.core.motion

    pp.set_led_color(1.0, 0.6, 0.0, 0.3)
    pp.core.tts.say("運動タイムです！私の体力を見せますよ！")
    time.sleep(0.3)

    for text, angles, dur in ROUTINE:
        _say_and_move(pp, text, angles, dur)
        _neutral(motion, 0.7)
        time.sleep(0.1)

    pp.emotion("confident", "毎日運動することが大切ですよ！運動は最高です！")
    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    exercise(ip)
