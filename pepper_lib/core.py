# -*- coding: utf-8 -*-
"""
pepper_lib.core - NAOqi 接続管理・プロキシキャッシュ

ALProxy のインスタンスを一元管理し、必要時に遅延生成する。
"""
from __future__ import print_function

import sys
import os

# SDK パスをこのファイル基準で解決
# 優先順位: 環境変数 PYNAOQI_SDK > リポジトリ直下の pynaoqi-sdk/ > 従来パス
_THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_SDK_PATH  = (
    os.environ.get("PYNAOQI_SDK")
    or os.path.join(_REPO_ROOT, "pynaoqi-sdk")
    or os.path.join(_REPO_ROOT,
                    "pynaoqi-python2.7-2.1.4.13-win32-vs2010 (1)",
                    "pynaoqi-python2.7-2.1.4.13-win32-vs2010")
)
if _SDK_PATH not in sys.path:
    sys.path.insert(0, _SDK_PATH)

from naoqi import ALProxy


class PepperCore(object):
    """
    NAOqi プロキシを遅延生成してキャッシュする基盤クラス。

    使い方:
        core = PepperCore("192.168.0.46", 9559)
        tts  = core.proxy("ALTextToSpeech")
        tts.say("hello")
    """

    def __init__(self, ip="192.168.0.46", port=9559):
        # NAOqi C++ バインディングは str (bytes) のみ受け付ける。
        # unicode_literals が有効な場合でも str に変換しておく。
        self.ip    = str(ip)
        self.port  = int(port)
        self._cache = {}

    def proxy(self, service_name):
        """
        指定サービスの ALProxy を返す（キャッシュあり）。

        Args:
            service_name (str): "ALTextToSpeech" など

        Returns:
            ALProxy instance
        """
        if service_name not in self._cache:
            try:
                # str() で bytes 型に統一（unicode_literals 対策）
                self._cache[service_name] = ALProxy(
                    str(service_name), self.ip, self.port
                )
            except Exception as e:
                try:
                    detail = str(e)
                except Exception:
                    detail = "(エラー詳細を取得できません)"
                raise RuntimeError(
                    "NAOqi 接続失敗: {0} @ {1}:{2}\n{3}".format(
                        service_name, self.ip, self.port, detail
                    )
                )
        return self._cache[service_name]

    # よく使うプロキシのショートカット
    @property
    def tts(self):
        return self.proxy("ALTextToSpeech")

    @property
    def animated(self):
        return self.proxy("ALAnimatedSpeech")

    @property
    def motion(self):
        return self.proxy("ALMotion")

    @property
    def posture(self):
        return self.proxy("ALRobotPosture")

    @property
    def leds_proxy(self):
        return self.proxy("ALLeds")

    @property
    def memory(self):
        return self.proxy("ALMemory")

    @property
    def awareness(self):
        return self.proxy("ALBasicAwareness")

    @property
    def speak_move(self):
        return self.proxy("ALSpeakingMovement")

    @property
    def listen_move(self):
        return self.proxy("ALListeningMovement")
