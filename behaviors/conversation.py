# -*- coding: utf-8 -*-
"""
behaviors/conversation.py - シンプルな会話ビヘイビア

OpenAI GPT / Claude API とPepperを繋ぐ基本テンプレート。
AI の返答を受け取り、感情解析してLED+アニメーション付きで発話する。

使い方:
    OPENAI_API_KEY=xxx python conversation.py [IP]
    または
    ANTHROPIC_API_KEY=xxx python conversation.py [IP] --claude

NOTE: このスクリプトは Python 3 で動作する AI API 呼び出し部分と
      Python 2.7 で動作する Pepper 制御部分を分離した設計になっています。
      実際の運用では blackbox (Python 3) と pepper_controller (Python 2.7) を
      別プロセスで動かしてソケット通信するアーキテクチャを推奨します。
"""
from __future__ import print_function
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP   = "192.168.0.46"
PEPPER_PORT = 9559

# 感情キーワード → emotions.express() の感情名へのマッピング
EMOTION_KEYWORDS = {
    "happy":      ["嬉しい", "うれしい", "やった", "最高", "素晴らしい", "ありがとう"],
    "sad":        ["悲しい", "かなしい", "残念", "つらい", "寂しい"],
    "angry":      ["怒", "ダメ", "許せない", "もう"],
    "thinking":   ["考え", "うーん", "ちょっと待", "難しい"],
    "excited":    ["すごい", "わあ", "驚", "びっくり", "信じられない"],
    "grateful":   ["感謝", "ありがとう", "感動"],
    "shy":        ["恥ずかしい", "照れ"],
    "confident":  ["任せて", "大丈夫", "もちろん", "できます"],
}


def detect_emotion(text):
    """
    テキストからキーワードで感情を推定する（シンプルなルールベース）。

    Returns:
        str: 感情名 or "neutral"
    """
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return emotion
    return "neutral"


def speak_with_emotion(pp, text):
    """
    感情を検出して LED + アニメーション付きで発話する。

    Args:
        pp (Pepper): Pepper インスタンス
        text (str): 発話テキスト
    """
    emotion = detect_emotion(text)
    if emotion == "neutral":
        pp.say(text, animated=True)
    else:
        pp.emotion(emotion, text)


def run_conversation(ip=PEPPER_IP, port=PEPPER_PORT):
    """
    コンソールからテキストを入力して Pepper に発話させるデモ。
    実際のAI統合時はこの関数の入力部分をAPIに置き換える。
    """
    pp = Pepper(ip, port)
    pp.say("会話モードを開始します。テキストを入力してください。")

    print("=" * 50)
    print("Pepper 会話デモ")
    print("終了するには 'quit' と入力してください")
    print("=" * 50)

    while True:
        try:
            # Python 2/3 両対応
            try:
                user_input = raw_input("\nあなた: ").decode("utf-8")
            except NameError:
                user_input = input("\nあなた: ")

            if user_input.lower() in ("quit", "exit", "終了", "q"):
                pp.say("またお話しましょう！バイバイ！")
                pp.wave("R")
                break

            # ここでAI APIを呼ぶ（今はそのまま発話）
            # response = call_ai_api(user_input)
            response = user_input  # デモ用: 入力をそのまま発話

            print("Pepper: {}".format(response))
            speak_with_emotion(pp, response)

        except KeyboardInterrupt:
            print("\n終了します。")
            pp.say("さようなら！")
            break

    pp.stand()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    run_conversation(ip)
