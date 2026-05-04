# -*- coding: utf-8 -*-
"""
pepper_lib.speech - 発話・音声認識制御

ALTextToSpeech, ALAnimatedSpeech, ALSpeakingMovement,
ALSpeechRecognition をラップする。
"""
from __future__ import print_function
import sys
import time


def _s(text):
    """Python 2.7 NAOqi 用: unicode を UTF-8 bytes (str) に変換する。
    NAOqi C++ バインディングは unicode を受け付けないため必須。"""
    if sys.version_info[0] == 2:
        try:
            if isinstance(text, unicode):
                return text.encode('utf-8')
        except NameError:
            pass
    return text


class Speech(object):
    """
    発話・音声関連の操作をまとめたクラス。

    Example:
        speech = Speech(core)
        speech.say("こんにちは")
        speech.say_animated("こんにちは")
        speech.say_with_animation("こんにちは", "animations/Stand/Gestures/Hey_1")
    """

    def __init__(self, core):
        self._core = core
        self._language = "Japanese"
        self._body_language_mode = "contextual"

    def set_language(self, language):
        """
        発話言語を設定する。

        Args:
            language (str): "Japanese" / "English" / "French" など
        """
        self._language = _s(language)
        self._core.tts.setLanguage(_s(language))

    def set_voice(self, speed=100, volume=1.0, pitch=1.0):
        """
        声のパラメータを設定する。

        Args:
            speed (int): 速度 50〜400 (デフォルト 100)
            volume (float): 音量 0.0〜1.0
            pitch (float): ピッチ 0.5〜4.0 (1.0=標準)
        """
        tts = self._core.tts
        tts.setParameter("speed", speed)
        tts.setParameter("volume", volume)
        tts.setParameter("pitchShift", pitch)

    def set_body_language(self, mode="contextual"):
        """
        発話中の自動ジェスチャーモードを設定する。

        Args:
            mode (str): "contextual" / "disabled" / "random"
        """
        self._body_language_mode = _s(mode)
        self._core.speak_move.setMode(_s(mode))

    def say(self, text, wait=True):
        """
        テキストをシンプルに発話する（ジェスチャーなし）。

        Args:
            text (str): 発話テキスト
            wait (bool): 完了まで待機するか
        """
        tts = self._core.tts
        text = _s(text)
        if wait:
            tts.say(text)
        else:
            return tts.post.say(text)

    def say_animated(self, text, wait=True):
        """
        自動ジェスチャー付きで発話する（ALAnimatedSpeech）。

        Args:
            text (str): 発話テキスト
            wait (bool): 完了まで待機するか
        """
        animated = self._core.animated
        text = _s(text)
        if wait:
            animated.say(text)
        else:
            return animated.post.say(text)

    def say_with_animation(self, text, animation_path, wait=True):
        """
        指定したアニメーションを再生しながら発話する。

        まず ALBehaviorManager で直接ビヘイビアを実行し（確実）、
        ビヘイビアが見つからない場合は ALAnimatedSpeech の
        ^start/^wait 構文にフォールバックする。

        Args:
            text (str): 発話テキスト
            animation_path (str): アニメーションパス
                例: "animations/Stand/Gestures/Hey_1"
            wait (bool): 完了まで待機するか
        """
        text           = _s(text)
        animation_path = _s(animation_path)

        # --- 方法1: ALBehaviorManager + TTS を並列実行（確実） ---
        try:
            bm = self._core.proxy("ALBehaviorManager")
            if bm.isBehaviorInstalled(animation_path):
                bm_id  = bm.post.runBehavior(animation_path)
                say_id = self._core.tts.post.say(text)
                if wait:
                    bm.wait(bm_id, 15000)
                    self._core.tts.wait(say_id, 15000)
                return
        except Exception:
            pass

        # --- 方法2: ALAnimatedSpeech の ^start/^wait 構文（フォールバック） ---
        cmd = "^start({0}) {1}^wait({0})".format(animation_path, text)
        animated = self._core.animated
        if wait:
            animated.say(cmd)
        else:
            return animated.post.say(cmd)

    def say_async(self, text):
        """
        非同期で発話を開始し、タスクIDを返す。

        Returns:
            int: タスクID（wait_for() に渡せる）
        """
        return self._core.tts.post.say(_s(text))

    def wait_for(self, task_id, timeout_ms=15000):
        """
        非同期発話の完了を待つ。

        Args:
            task_id (int): say_async() の戻り値
            timeout_ms (int): タイムアウト（ミリ秒）
        """
        self._core.tts.wait(task_id, timeout_ms)

    def stop(self):
        """発話を停止する。"""
        self._core.tts.stopAll()

    def build_anim_cmd(self, text, animation_path):
        """
        ALAnimatedSpeech 用のコマンド文字列を構築して返す（発話しない）。

        Returns:
            str: "^start(path) text^wait(path)"
        """
        return "^start({0}) {1}^wait({0})".format(animation_path, text)

    def listen_once(self, vocabulary, language=None, timeout=10.0):
        """
        音声認識を一度だけ実行して認識した単語と信頼度を返す。

        Args:
            vocabulary (list): 認識する単語リスト
            language (str): 言語（省略時は現在の言語）
            timeout (float): 待機秒数

        Returns:
            tuple: (recognized_word: str, confidence: float)
                   タイムアウト時は ("", 0.0)
        """
        if language is None:
            language = self._language

        sr      = self._core.proxy("ALSpeechRecognition")
        memory  = self._core.memory

        sr.setLanguage(language)
        sr.setVocabulary(vocabulary, False)
        sr.subscribe("pepper_lib_asr")

        result = ("", 0.0)
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                data = memory.getData("WordRecognized")
                if data and len(data) >= 2 and data[0] in vocabulary and data[1] > 0.4:
                    result = (data[0], data[1])
                    break
                time.sleep(0.1)
        finally:
            sr.unsubscribe("pepper_lib_asr")

        return result
