# -*- coding: utf-8 -*-
"""
pepper_lib.body - 身体動作・ポーズ制御

ALMotion, ALRobotPosture をラップする。
関節名・角度範囲は CLAUDE.md のテーブルを参照。
"""
from __future__ import print_function
import time
import math


class Body(object):
    """
    Pepperの身体動作全般を管理するクラス。

    Example:
        body = Body(core)
        body.wake_up()
        body.stand()
        body.bow()
        body.wave()
        body.look_at(0.3, -0.2)
    """

    def __init__(self, core):
        self._core = core

    # ---- 電源・スタミナ ----

    def wake_up(self):
        """モーターを起動する（必ず動作前に呼ぶ）。"""
        self._core.motion.wakeUp()

    def rest(self):
        """モーターを休止する（省エネ・安全）。"""
        self._core.motion.rest()

    def set_stiffness(self, value=1.0, body_part="Body"):
        """
        関節の剛性を設定する。

        Args:
            value (float): 0.0（脱力）〜 1.0（固い）
            body_part (str): "Body" / "Head" / "LArm" / "RArm" / "Legs"
        """
        self._core.motion.setStiffnesses(body_part, value)

    # ---- ポーズ ----

    def stand(self, speed=0.5):
        """直立姿勢に移行する。"""
        self._core.posture.goToPosture("Stand", speed)

    def stand_init(self, speed=0.5):
        """両手を下ろした標準直立姿勢。"""
        self._core.posture.goToPosture("StandInit", speed)

    def crouch(self, speed=0.5):
        """しゃがむ。"""
        self._core.posture.goToPosture("Crouch", speed)

    def sit(self, speed=0.5):
        """座る。"""
        self._core.posture.goToPosture("Sit", speed)

    def get_posture(self):
        """現在のポーズ名を返す。"""
        return self._core.posture.getCurrentPostureName()

    # ---- 頭の動き ----

    def look_at(self, yaw, pitch, speed=0.15):
        """
        顔を指定方向に向ける。

        Args:
            yaw (float): 左右 (rad): 正=左, 負=右。範囲 -2.09〜2.09
            pitch (float): 上下 (rad): 負=上, 正=下。範囲 -0.71〜0.45
            speed (float): 速度 0.0〜1.0
        """
        motion = self._core.motion
        motion.setAngles(["HeadYaw", "HeadPitch"], [yaw, pitch], speed)

    def look_forward(self, speed=0.15):
        """正面を向く。"""
        self.look_at(0.0, 0.0, speed)

    def nod(self, times=2, amplitude=0.2, interval=0.4):
        """
        縦に首を振る（うなずく）。

        Args:
            times (int): 回数
            amplitude (float): 振り幅（rad）
            interval (float): 1回の周期（秒）
        """
        motion = self._core.motion
        t = interval / 2.0
        joints = ["HeadPitch"]
        for _ in range(times):
            motion.angleInterpolation(joints, [amplitude], [t], True)
            motion.angleInterpolation(joints, [0.0], [t], True)

    def shake_head(self, times=2, amplitude=0.3, interval=0.5):
        """
        横に首を振る（否定）。

        Args:
            times (int): 回数
            amplitude (float): 振り幅（rad）
            interval (float): 1回の周期（秒）
        """
        motion = self._core.motion
        t = interval / 2.0
        for _ in range(times):
            motion.angleInterpolation(["HeadYaw"], [amplitude], [t], True)
            motion.angleInterpolation(["HeadYaw"], [-amplitude], [t], True)
        motion.angleInterpolation(["HeadYaw"], [0.0], [t], True)

    # ---- お辞儀・挨拶 ----

    def bow(self, angle=0.5, duration=1.0, hold=0.5, text=None, speech=None):
        """
        お辞儀をする。

        Args:
            angle (float): 前傾角度（HipPitch, rad）
            duration (float): 前傾にかかる秒数
            hold (float): 前傾を保持する秒数
            text (str): お辞儀中に発話するテキスト（省略可）
            speech (Speech): Speech インスタンス（text指定時に必要）
        """
        motion = self._core.motion
        bow_joints = ["HipPitch", "HeadPitch"]
        bow_angles  = [
            [0.0, angle, angle, 0.0],
            [0.0, angle * 0.5, angle * 0.5, 0.0],
        ]
        t_down = duration
        t_hold = duration + hold
        t_up   = duration + hold + duration
        bow_times = [
            [0.1, t_down, t_hold, t_up],
            [0.1, t_down, t_hold, t_up],
        ]

        if text and speech:
            say_id = speech.say_async(text)
            motion.angleInterpolation(bow_joints, bow_angles, bow_times, True)
            speech.wait_for(say_id)
        else:
            motion.angleInterpolation(bow_joints, bow_angles, bow_times, True)

    # ---- 手を振る ----

    def wave(self, hand="R", text=None, speech=None):
        """
        手を振る。

        Args:
            hand (str): "R" or "L"
            text (str): 同時に発話するテキスト
            speech (Speech): Speech インスタンス
        """
        motion = self._core.motion

        if hand == "R":
            joints = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
            # 上げる → 振る → 振る → 振る → 戻す
            angles = [
                [-0.5, -0.5, -0.5, -0.5, 1.4],   # Pitch
                [-0.3, -0.3, -0.3, -0.3, -0.2],   # Roll
                [1.0,  1.0,  0.5,  1.0,  0.9],    # ElbowRoll
                [1.0,  1.0,  1.0,  1.0,  1.2],    # ElbowYaw
            ]
        else:
            joints = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw"]
            angles = [
                [-0.5, -0.5, -0.5, -0.5, 1.4],
                [0.3,  0.3,  0.3,  0.3,  0.2],
                [-1.0, -1.0, -0.5, -1.0, -0.9],
                [-1.0, -1.0, -1.0, -1.0, -1.2],
            ]

        times = [[0.5, 1.0, 1.5, 2.0, 3.0]] * 4

        if text and speech:
            say_id = speech.say_async(text)
            motion.angleInterpolation(joints, angles, times, True)
            speech.wait_for(say_id)
        else:
            motion.angleInterpolation(joints, angles, times, True)

    # ---- 汎用ポーズ ----

    def set_joint_angles(self, joints, angles, times, absolute=True, async_=False):
        """
        任意の関節をタイムラインで動かす低レベルAPI。

        Args:
            joints (list or str): 関節名リスト
            angles (list): 各関節の角度タイムライン（ネストリスト）
            times (list): 各関節の時刻タイムライン（ネストリスト）
            absolute (bool): True=絶対角度, False=相対角度
            async_ (bool): True=非同期

        Returns:
            task_id or None
        """
        motion = self._core.motion
        if async_:
            return motion.post.angleInterpolation(joints, angles, times, absolute)
        else:
            motion.angleInterpolation(joints, angles, times, absolute)
            return None

    def open_hand(self, hand="both"):
        """
        手を開く。

        Args:
            hand (str): "R" / "L" / "both"
        """
        motion = self._core.motion
        if hand in ("R", "both"):
            motion.openHand("RHand")
        if hand in ("L", "both"):
            motion.openHand("LHand")

    def close_hand(self, hand="both"):
        """
        手を閉じる。

        Args:
            hand (str): "R" / "L" / "both"
        """
        motion = self._core.motion
        if hand in ("R", "both"):
            motion.closeHand("RHand")
        if hand in ("L", "both"):
            motion.closeHand("LHand")

    def raise_arm(self, hand="R", speed=0.3):
        """
        腕を前に挙げる（指差しポーズ）。

        Args:
            hand (str): "R" or "L"
            speed (float): 動作速度 0.0〜1.0
        """
        motion = self._core.motion
        if hand == "R":
            motion.setAngles(
                ["RShoulderPitch", "RShoulderRoll", "RElbowRoll"],
                [-0.5, -0.1, 0.5], speed
            )
        else:
            motion.setAngles(
                ["LShoulderPitch", "LShoulderRoll", "LElbowRoll"],
                [-0.5, 0.1, -0.5], speed
            )

    def neutral_arms(self, speed=0.2):
        """両腕をニュートラル（自然な垂れ下がり）ポジションに戻す。"""
        motion = self._core.motion
        motion.setAngles(
            ["LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll"],
            [1.4, 0.2, 1.4, -0.2],
            speed
        )

    # ---- タッチセンサー ----

    def is_touched(self, sensor="head"):
        """
        タッチセンサーの状態を返す。

        Args:
            sensor (str): "head" / "head_front" / "head_mid" / "head_rear" /
                          "right_hand" / "left_hand" / "bumper_right" / "bumper_left"

        Returns:
            bool: タッチされていれば True
        """
        _sensor_keys = {
            "head_front":   "Device/SubDeviceList/Head/Touch/Front/Sensor/Value",
            "head_mid":     "Device/SubDeviceList/Head/Touch/Middle/Sensor/Value",
            "head_rear":    "Device/SubDeviceList/Head/Touch/Rear/Sensor/Value",
            "right_hand":   "Device/SubDeviceList/RHand/Touch/Back/Sensor/Value",
            "left_hand":    "Device/SubDeviceList/LHand/Touch/Back/Sensor/Value",
            "bumper_right": "Device/SubDeviceList/RFoot/Bumper/Right/Sensor/Value",
            "bumper_left":  "Device/SubDeviceList/LFoot/Bumper/Left/Sensor/Value",
        }
        memory = self._core.memory

        if sensor == "head":
            return any(
                memory.getData(k) > 0.5
                for k in [_sensor_keys["head_front"],
                          _sensor_keys["head_mid"],
                          _sensor_keys["head_rear"]]
            )
        key = _sensor_keys.get(sensor)
        if key:
            return memory.getData(key) > 0.5
        return False

    def wait_for_touch(self, sensor="head", timeout=30.0):
        """
        タッチされるまでブロックする。

        Args:
            sensor (str): センサー名（is_touched() と同じ）
            timeout (float): タイムアウト秒数

        Returns:
            bool: タッチされた場合 True、タイムアウトで False
        """
        import time as _time
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            if self.is_touched(sensor):
                return True
            _time.sleep(0.1)
        return False

    # ---- ジェスチャー（直接関節制御） ----

    def point(self, direction="forward", hand="R", speed=0.2):
        """
        指を差す。

        Args:
            direction (str): "forward" / "up" / "left" / "right"
            hand (str): "R" or "L"
            speed (float): 動作速度
        """
        motion = self._core.motion
        dir_angles = {
            "forward": (-0.5,  0.0),   # (ShoulderPitch, ShoulderRoll)
            "up":      (-1.2,  0.0),
            "left":    (-0.3,  0.5) if hand == "L" else (-0.3, -0.5),
            "right":   (-0.3, -0.5) if hand == "L" else (-0.3,  0.5),
        }
        sp, sr = dir_angles.get(direction, (-0.5, 0.0))
        if hand == "R":
            motion.setAngles(
                ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"],
                [sp, sr, 0.2, 1.2], speed
            )
        else:
            motion.setAngles(
                ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw"],
                [sp, -sr, -0.2, -1.2], speed
            )

    def spread_arms(self, speed=0.2):
        """両腕を水平に広げる（歓迎・大きさを示す）。"""
        motion = self._core.motion
        motion.angleInterpolation(
            ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"],
            [0.1, 1.0, -0.2,
             0.1, -1.0, 0.2],
            [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            True
        )

    def hug_pose(self, speed=0.2):
        """ハグのポーズ（両腕を前に伸ばして内向き）。"""
        motion = self._core.motion
        motion.angleInterpolation(
            ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"],
            [-0.2, 0.3, -0.8,
             -0.2, -0.3, 0.8],
            [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            True
        )

    def shrug(self, speed=0.2):
        """肩をすくめる（わからない・困惑）。"""
        motion = self._core.motion
        # 肩を上げる
        motion.angleInterpolation(
            ["LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll",
             "HeadPitch"],
            [0.8, 0.6, 0.8, -0.6, 0.3],
            [0.5, 0.5, 0.5, 0.5, 0.5],
            True
        )
        time.sleep(0.8)
        # 戻す
        motion.angleInterpolation(
            ["LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll",
             "HeadPitch"],
            [1.4, 0.2, 1.4, -0.2, 0.0],
            [0.5, 0.5, 0.5, 0.5, 0.5],
            True
        )

    def cross_arms(self, speed=0.2):
        """腕を組む（拒否・考え中・自信）。"""
        motion = self._core.motion
        motion.angleInterpolation(
            ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"],
            [0.5,  0.1, -1.2, -0.5,
             0.5, -0.1,  1.2,  0.5],
            [1.0] * 8,
            True
        )

    def scratch_head(self, speed=0.2):
        """頭を掻く（困惑・照れ）。"""
        motion = self._core.motion
        motion.angleInterpolation(
            ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadYaw"],
            # 右手を頭の上へ
            [-0.3, -0.8, 1.4, 0.5,
             0.3],
            [0.8, 0.8, 0.8, 0.8, 0.5],
            True
        )
        time.sleep(0.5)
        # 小さく前後に動かす（掻く動き）
        for _ in range(3):
            motion.angleInterpolation(["RElbowYaw"], [0.3], [0.2], True)
            motion.angleInterpolation(["RElbowYaw"], [0.7], [0.2], True)
        # 戻す
        motion.angleInterpolation(
            ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadYaw"],
            [1.4, -0.2, 0.9, 1.2, 0.0],
            [0.8] * 5,
            True
        )

    def think_pose(self, speed=0.15):
        """考えるポーズ（片手をあごに）。"""
        motion = self._core.motion
        motion.angleInterpolation(
            ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadPitch", "HeadYaw"],
            [0.3, -0.3, 1.0, 1.0,
             0.1,  0.2],
            [1.0, 1.0, 1.0, 1.0, 0.5, 0.5],
            True
        )

    def lean_forward(self, angle=0.3, speed=0.15):
        """前傾みになる（関心を示す）。"""
        motion = self._core.motion
        motion.angleInterpolation(
            ["HipPitch", "HeadPitch"],
            [angle, -angle * 0.5],
            [1.0, 1.0],
            True
        )

    def lean_back(self, angle=0.2, speed=0.15):
        """後傾みになる（驚き・拒否）。"""
        motion = self._core.motion
        motion.angleInterpolation(
            ["HipPitch", "HeadPitch"],
            [-angle, angle * 0.5],
            [1.0, 1.0],
            True
        )
