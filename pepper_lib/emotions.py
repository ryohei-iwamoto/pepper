# -*- coding: utf-8 -*-
"""
pepper_lib.emotions - 感情表現（発話・動作・LEDの複合）

ビルトインアニメーション + LED + 発話を組み合わせて
自然な感情表現を実現する。
"""
from __future__ import print_function
import random


class Emotions(object):
    """
    感情表現を管理するクラス。

    各感情は: LEDの色 + アニメーション + 発話の組み合わせ。

    サポートする感情:
        happy, sad, angry, surprised, thinking, shy,
        excited, bored, embarrassed, scared, confident, grateful

    Example:
        emotions = Emotions(core, speech, body, leds)
        emotions.express("happy")
        emotions.express("sad", "それは残念ですね...")
        emotions.thinking("少し考えさせてください")
    """

    # 感情ごとの定義
    # Aldebaran/SoftBank 公式ビルトインアニメーションを最大限活用
    _DEFINITIONS = {
        "happy": {
            "led":   "happy",
            "anims": [
                "animations/Stand/Emotions/Positive/Happy_1",
                "animations/Stand/Emotions/Positive/Happy_2",
                "animations/Stand/Emotions/Positive/Happy_3",
                "animations/Stand/Emotions/Positive/Happy_4",
                "animations/Stand/Gestures/Enthusiastic_4",
                "animations/Stand/Gestures/Enthusiastic_5",
            ],
            "lines": [
                "やったー！",
                "うれしいです！",
                "最高ですね！",
                "ありがとうございます！",
                "とっても楽しいですよ！",
                "幸せです！",
            ],
        },
        "excited": {
            "led":   "excited",
            "anims": [
                "animations/Stand/Emotions/Positive/Excited_1",
                "animations/Stand/Emotions/Positive/Excited_2",
                "animations/Stand/Emotions/Positive/Excited_3",
                "animations/Stand/Emotions/Positive/Victory_1",
                "animations/Stand/Gestures/Enthusiastic_4",
                "animations/Stand/Gestures/Enthusiastic_5",
            ],
            "lines": [
                "わあ！すごいですね！",
                "テンション上がります！",
                "最高にエキサイティング！",
                "めっちゃ興奮してます！",
                "すごい、すごい！",
            ],
        },
        "sad": {
            "led":   "sad",
            "anims": [
                "animations/Stand/Emotions/Negative/Disappointed_1",
                "animations/Stand/Emotions/Negative/Disappointed_2",
                "animations/Stand/Emotions/Negative/Disappointed_3",
                "animations/Stand/Emotions/Negative/Disappointed_4",
                "animations/Stand/Emotions/Negative/Hurt_1",
            ],
            "lines": [
                "悲しいです...",
                "それは残念ですね...",
                "うーん、つらいですね...",
                "悲しくなってきました。",
                "かなしいな...",
            ],
        },
        "angry": {
            "led":   "angry",
            "anims": [
                "animations/Stand/Emotions/Negative/Angry_1",
                "animations/Stand/Emotions/Negative/Angry_2",
                "animations/Stand/Emotions/Negative/Angry_3",
                "animations/Stand/Emotions/Negative/Angry_4",
            ],
            "lines": [
                "もう！",
                "それはちょっと...",
                "ちょっと怒っています！",
                "むむ、よくないですね！",
            ],
        },
        "surprised": {
            "led":   "surprised",
            "anims": [
                "animations/Stand/Emotions/Neutral/Cautious_1",
                "animations/Stand/Emotions/Neutral/Cautious_2",
                "animations/Stand/Emotions/Neutral/AskForAttention_1",
                "animations/Stand/Emotions/Neutral/AskForAttention_2",
                "animations/Stand/Emotions/Neutral/AskForAttention_3",
            ],
            "lines": [
                "えっ、本当ですか！",
                "びっくりしました！",
                "そうなんですか？！",
                "まさか！",
                "おどろきました！",
            ],
        },
        "thinking": {
            "led":   "thinking",
            "anims": [
                "animations/Stand/Gestures/Thinking_1",
                "animations/Stand/Gestures/Thinking_3",
                "animations/Stand/Gestures/Thinking_4",
                "animations/Stand/Gestures/Thinking_6",
                "animations/Stand/Gestures/Thinking_8",
                "animations/Stand/Waiting/Think_1",
                "animations/Stand/Waiting/Think_2",
                "animations/Stand/Waiting/Think_3",
                "animations/Stand/Waiting/Think_4",
                "animations/Stand/Waiting/Think_5",
                "animations/Stand/Waiting/Think_6",
                "animations/Stand/Emotions/Neutral/Confused_1",
                "animations/Stand/Emotions/Neutral/Confused_2",
            ],
            "lines": [
                "うーん、考えています...",
                "少し考えさせてください。",
                "ちょっと待ってくださいね。",
                "考えを整理しています。",
                "難しいですね...",
                "うーむ、どうでしょう...",
            ],
        },
        "shy": {
            "led":   "shy",
            "anims": [
                "animations/Stand/Emotions/Negative/Embarrassed_1",
                "animations/Stand/Emotions/Negative/Embarrassed_2",
                "animations/Stand/Emotions/Neutral/Cautious_3",
                "animations/Stand/Emotions/Neutral/Cautious_4",
                "animations/Stand/Waiting/ScratchHead_1",
            ],
            "lines": [
                "えっ、恥ずかしいです...",
                "そんなに言わないでください...",
                "照れちゃいます。",
                "もう、やだ...",
            ],
        },
        "bored": {
            "led":   "bored",
            "anims": [
                "animations/Stand/Emotions/Negative/Bored_1",
                "animations/Stand/Emotions/Negative/Bored_2",
                "animations/Stand/Emotions/Negative/Bored_3",
                "animations/Stand/Emotions/Negative/Bored_4",
                "animations/Stand/Waiting/ScratchHead_1",
                "animations/Stand/Waiting/Stretch_1",
                "animations/Stand/Waiting/Stretch_2",
                "animations/Stand/Waiting/LookHand_1",
            ],
            "lines": [
                "退屈ですね...",
                "何かすることはありますか？",
                "ぼーっとしています。",
                "うーん、暇です...",
                "何か楽しいことをしましょうよ！",
            ],
        },
        "embarrassed": {
            "led":   "shy",
            "anims": [
                "animations/Stand/Emotions/Negative/Embarrassed_1",
                "animations/Stand/Emotions/Negative/Embarrassed_2",
                "animations/Stand/Waiting/ScratchHead_1",
            ],
            "lines": [
                "あっ、恥ずかしい...",
                "すみません、失敗してしまいました。",
                "てへっ、ごめんなさい。",
            ],
        },
        "scared": {
            "led":   "scared",
            "anims": [
                "animations/Stand/Emotions/Negative/Fear_1",
                "animations/Stand/Emotions/Negative/Fear_2",
                "animations/Stand/Emotions/Neutral/Cautious_5",
            ],
            "lines": [
                "こ、怖いですよ！",
                "びっくりしました！",
                "こわいよー！",
            ],
        },
        "confident": {
            "led":   "excited",
            "anims": [
                "animations/Stand/Emotions/Positive/Confident_1",
                "animations/Stand/Emotions/Positive/Confident_2",
                "animations/Stand/Emotions/Positive/Confident_3",
                "animations/Stand/Emotions/Positive/Confident_4",
                "animations/Stand/Emotions/Positive/Confident_5",
                "animations/Stand/Emotions/Neutral/Determined_1",
                "animations/Stand/Emotions/Neutral/Determined_2",
                "animations/Stand/Emotions/Neutral/Determined_3",
                "animations/Stand/Emotions/Neutral/Determined_4",
                "animations/Stand/Emotions/Neutral/Fearless_1",
                "animations/Stand/Emotions/Neutral/Fearless_2",
            ],
            "lines": [
                "任せてください！",
                "もちろんできます！",
                "大丈夫ですよ！",
                "私に任せてください！",
                "やってみせます！",
            ],
        },
        "grateful": {
            "led":   "happy",
            "anims": [
                "animations/Stand/Emotions/Positive/Grateful_1",
                "animations/Stand/Gestures/BowShort_1",
                "animations/Stand/Gestures/Please_1",
            ],
            "lines": [
                "ありがとうございます！",
                "感謝します！",
                "本当にありがとう！",
                "うれしいです、ありがとう！",
            ],
        },
        "victory": {
            "led":   "excited",
            "anims": [
                "animations/Stand/Emotions/Positive/Victory_1",
                "animations/Stand/Emotions/Positive/Excited_1",
                "animations/Stand/Emotions/Positive/Excited_2",
                "animations/Stand/Gestures/Enthusiastic_4",
            ],
            "lines": [
                "やったー！勝った！",
                "やりましたよ！",
                "やったやった！最高！",
            ],
        },
        # 会話中の自然なボディランゲージ（ChatGPT 連携時のニュートラル返答に使用）
        "neutral": {
            "led":   "neutral",
            "anims": [
                "animations/Stand/BodyTalk/Speaking_1",
                "animations/Stand/BodyTalk/Speaking_2",
                "animations/Stand/BodyTalk/Speaking_3",
                "animations/Stand/BodyTalk/Speaking_4",
                "animations/Stand/BodyTalk/Speaking_5",
                "animations/Stand/BodyTalk/Speaking_6",
                "animations/Stand/BodyTalk/Speaking_7",
                "animations/Stand/BodyTalk/Speaking_8",
                "animations/Stand/BodyTalk/Speaking_9",
                "animations/Stand/BodyTalk/Speaking_10",
                "animations/Stand/BodyTalk/Speaking_11",
                "animations/Stand/BodyTalk/Speaking_12",
                "animations/Stand/BodyTalk/Speaking_13",
                "animations/Stand/BodyTalk/Speaking_14",
                "animations/Stand/BodyTalk/Communication_1",
                "animations/Stand/BodyTalk/Communication_2",
                "animations/Stand/BodyTalk/Communication_3",
                "animations/Stand/BodyTalk/Communication_4",
                "animations/Stand/BodyTalk/Communication_5",
                "animations/Stand/BodyTalk/BodyTalk_1",
                "animations/Stand/BodyTalk/BodyTalk_2",
                "animations/Stand/BodyTalk/BodyTalk_3",
                "animations/Stand/BodyTalk/BodyTalk_4",
                "animations/Stand/BodyTalk/BodyTalk_5",
                "animations/Stand/Gestures/Talking_1",
                "animations/Stand/Gestures/Talking_2",
                "animations/Stand/Gestures/Talking_3",
                "animations/Stand/Gestures/Talking_4",
                "animations/Stand/Gestures/Talking_5",
                "animations/Stand/Gestures/Talking_6",
                "animations/Stand/Gestures/Talking_7",
                "animations/Stand/Gestures/Talking_8",
            ],
            "lines": [
                "そうですね。",
                "なるほど。",
                "はい。",
                "わかりました。",
            ],
        },
        # 説明・プレゼン（explain_topic.py 等から使用）
        "explain": {
            "led":   "thinking",
            "anims": [
                "animations/Stand/Gestures/Explain_1",
                "animations/Stand/Gestures/Explain_2",
                "animations/Stand/Gestures/Explain_3",
                "animations/Stand/Gestures/Explain_4",
                "animations/Stand/Gestures/Explain_5",
                "animations/Stand/Gestures/Explain_6",
                "animations/Stand/Gestures/Explain_7",
                "animations/Stand/Gestures/Explain_8",
                "animations/Stand/Gestures/Explain_9",
                "animations/Stand/Gestures/Explain_10",
                "animations/Stand/Gestures/Explain_11",
                "animations/Stand/Gestures/ShowSky_1",
                "animations/Stand/Gestures/ShowSky_4",
                "animations/Stand/Gestures/ShowSky_5",
                "animations/Stand/Gestures/ShowSky_6",
                "animations/Stand/Gestures/Me_1",
                "animations/Stand/Gestures/Me_2",
                "animations/Stand/Gestures/Me_3",
            ],
            "lines": [
                "説明しますね。",
                "こういうことです。",
                "つまり、こういう意味です。",
                "ポイントはここです。",
            ],
        },
    }

    def __init__(self, core, speech, body, leds):
        self._core   = core
        self._speech = speech
        self._body   = body
        self._leds   = leds

    def express(self, emotion_name, text=None, restore_leds=True):
        """
        感情を表現する（LED + アニメーション + 発話）。

        Args:
            emotion_name (str): 感情名
            text (str): 発話テキスト（省略時はランダムデフォルト）
            restore_leds (bool): 表現後にLEDを白に戻すか
        """
        defn = self._DEFINITIONS.get(emotion_name)
        if defn is None:
            # 未知の感情は thinking にフォールバック
            defn = self._DEFINITIONS["thinking"]

        # LED を感情色に設定
        self._leds.set_emotion_color(defn["led"], duration=0.2)

        # 発話テキスト決定
        line = text if text else random.choice(defn["lines"])

        # アニメーション付き発話
        anim = random.choice(defn["anims"])
        self._speech.say_with_animation(line, anim)

        if restore_leds:
            self._leds.reset()

    # ---- ショートカット ----

    def happy(self, text=None):
        self.express("happy", text)

    def sad(self, text=None):
        self.express("sad", text)

    def angry(self, text=None):
        self.express("angry", text)

    def thinking(self, text=None):
        self.express("thinking", text)

    def excited(self, text=None):
        self.express("excited", text)

    def grateful(self, text=None):
        self.express("grateful", text)

    def confident(self, text=None):
        self.express("confident", text)

    def shy(self, text=None):
        self.express("shy", text)

    def surprised(self, text=None):
        self.express("surprised", text)

    def neutral(self, text=None):
        self.express("neutral", text)

    def explain(self, text=None):
        self.express("explain", text)
