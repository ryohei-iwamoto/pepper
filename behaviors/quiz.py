# -*- coding: utf-8 -*-
"""
behaviors/quiz.py - クイズ・質問インタラクション

頭タッチで「はい」、手タッチで「いいえ」を入力できる
インタラクティブなクイズビヘイビア。

使い方:
    python quiz.py [IP]
"""
from __future__ import print_function
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pepper_lib import Pepper

PEPPER_IP = "192.168.0.46"

QUESTIONS = [
    {
        "question": "Pepperは何色ですか？白ですか？",
        "answer_yes": True,
        "correct_msg": "正解です！私はホワイトカラーです！",
        "wrong_msg":   "残念！私は白色ですよ！",
    },
    {
        "question": "私は料理ができますか？",
        "answer_yes": False,
        "correct_msg": "大正解！残念ながら料理はできません。",
        "wrong_msg":   "惜しい！私は料理ができないんです。",
    },
    {
        "question": "私には両手があります。そうですか？",
        "answer_yes": True,
        "correct_msg": "正解！左右両方の手があります！",
        "wrong_msg":   "不正解！ちゃんと両手ありますよ！",
    },
]


def ask_yes_no(pp, question, timeout=15.0):
    """
    質問してタッチで回答を受け取る。
    頭=はい、手=いいえ。

    Returns:
        bool or None: True=はい, False=いいえ, None=タイムアウト
    """
    pp.say_with_anim(
        question + "　頭を触ったら「はい」、手を触ったら「いいえ」です。",
        "animations/Stand/Gestures/You_1"
    )

    deadline = time.time() + timeout
    while time.time() < deadline:
        if pp.body.is_touched("head"):
            time.sleep(0.3)
            return True
        if pp.body.is_touched("right_hand") or pp.body.is_touched("left_hand"):
            time.sleep(0.3)
            return False
        time.sleep(0.1)
    return None


def quiz(ip=PEPPER_IP, port=9559):
    pp = Pepper(ip, port)
    score = 0

    pp.emotion("excited", "クイズを始めましょう！全問正解できるかな？")
    time.sleep(0.5)

    for i, q in enumerate(QUESTIONS):
        pp.say("第{}問！".format(i + 1))
        answer = ask_yes_no(pp, q["question"])

        if answer is None:
            pp.emotion("sad", "時間切れです！次に行きましょう。")
            continue

        if answer == q["answer_yes"]:
            score += 1
            pp.emotion("happy", q["correct_msg"])
        else:
            pp.emotion("sad", q["wrong_msg"])
        time.sleep(0.5)

    # 結果発表
    total = len(QUESTIONS)
    msg = "{}問中{}問正解です！".format(total, score)
    if score == total:
        pp.emotion("excited", msg + "パーフェクト！すごい！")
        pp.leds.rainbow(2.0)
    elif score >= total // 2:
        pp.emotion("happy", msg + "よくできました！")
    else:
        pp.emotion("sad", msg + "次は頑張りましょう！")

    pp.reset_leds()
    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    quiz(ip)
