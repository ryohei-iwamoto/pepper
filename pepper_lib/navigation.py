# -*- coding: utf-8 -*-
"""
pepper_lib.navigation - 移動制御

ALMotion の車輪制御・歩行をラップする。
Pepperは3輪車輪型（前左・前右・後中）なので
実際に「歩く」のではなく車輪で移動する。
"""
from __future__ import print_function
import math
import time


class Navigation(object):
    """
    Pepper の移動を制御するクラス。

    Example:
        nav = Navigation(core)
        nav.move_to(1.0)          # 1m前進
        nav.move_to(-0.5)         # 0.5m後退
        nav.turn(math.pi / 2)     # 左に90度回転
        nav.turn(-math.pi / 2)    # 右に90度回転
        nav.move_to(0.5, 0.3)     # 斜め移動
    """

    def __init__(self, core):
        self._core = core

    def move_to(self, x, y=0.0, theta=0.0, speed=0.5):
        """
        指定した位置まで移動する（ブロッキング）。

        Args:
            x (float): 前後方向（メートル）: 正=前進, 負=後退
            y (float): 左右方向（メートル）: 正=左, 負=右
            theta (float): 回転（ラジアン）: 正=左回り, 負=右回り
            speed (float): 最大速度倍率 0.0〜1.0（ALNavigation使用時）
        """
        self._core.motion.moveTo(x, y, theta)

    def turn(self, theta, speed=0.5):
        """
        その場で回転する。

        Args:
            theta (float): 回転量（ラジアン）: 正=左回り, 負=右回り
        """
        self._core.motion.moveTo(0.0, 0.0, theta)

    def turn_degrees(self, degrees):
        """
        その場で指定角度（度数法）回転する。

        Args:
            degrees (float): 角度: 正=左回り, 負=右回り
        """
        self.turn(math.radians(degrees))

    def move_velocity(self, vx, vy=0.0, vtheta=0.0):
        """
        速度制御モードで移動する（stopまで続く）。

        Args:
            vx (float): 前後速度 m/s
            vy (float): 左右速度 m/s
            vtheta (float): 回転速度 rad/s
        """
        self._core.motion.move(vx, vy, vtheta)

    def stop(self):
        """移動を停止する。"""
        self._core.motion.stopMove()

    def is_moving(self):
        """移動中かどうかを返す。"""
        return self._core.motion.moveIsActive()

    def move_forward(self, distance, speed=0.5):
        """前進する。distance: メートル"""
        self.move_to(distance)

    def move_backward(self, distance):
        """後退する。distance: メートル"""
        self.move_to(-abs(distance))

    def strafe_left(self, distance):
        """左に横移動する。distance: メートル"""
        self.move_to(0.0, abs(distance))

    def strafe_right(self, distance):
        """右に横移動する。distance: メートル"""
        self.move_to(0.0, -abs(distance))

    def face_direction(self, target_yaw):
        """
        指定した方向（ラジアン, ロボット正面=0）に正面を向ける。
        現在の向きを基準とした相対回転。

        Args:
            target_yaw (float): 目標方向（rad）
        """
        self.turn(target_yaw)

    def patrol(self, waypoints, loop=False):
        """
        複数のウェイポイントを順番に移動する。

        Args:
            waypoints (list): [(x, y, theta), ...] のリスト
            loop (bool): True にするとループ
        """
        def _run():
            for wp in waypoints:
                x     = wp[0] if len(wp) > 0 else 0.0
                y     = wp[1] if len(wp) > 1 else 0.0
                theta = wp[2] if len(wp) > 2 else 0.0
                self.move_to(x, y, theta)

        if loop:
            while True:
                _run()
        else:
            _run()
