# -*- coding: utf-8 -*-
"""
pepper_lib.primitives - コミュニケーション動作プリミティブ集

ALMotion.angleInterpolation() による直接関節制御。
ALBehaviorManager / ビルトインアニメーションに一切依存しない。

カテゴリ (94 プリミティブ):
    社会的挨拶  (12): greet_bow, greet_wave, farewell, welcome,
                       thank_bow, apologize_bow, clap,
                       bow_deep, bow_slight, wave_both, nod_hello,
                       handshake_gesture
    傾聴・反応  (11): nod_strong, nod_gentle, nod_triple,
                       shake_no, tilt_head, lean_in,
                       agree_enthusiastic, disagree_arms, listen_intense,
                       impressed_nod, confirm_nod
    指示・方向  (11): point_forward, point_up, point_left, point_right,
                       beckon, show_palm, present_both,
                       point_self, point_past, point_future, come_here
    思考・処理   (9): think_chin, think_scratch, look_away,
                       confused_tilt, focused,
                       recall_gesture, doubt_head, wonder_look, pause_think
    感情表現    (15): joy_arms_up, surprise_recoil, sad_droop,
                       proud_chest, shy_hide, fear_back, excited_bounce,
                       laugh_shake, victory_arms, determined_fist,
                       angry_cross, relief_slump, embarrassed_chin,
                       amazed_open, satisfied_nod
    強調・説明  (13): raise_one_hand, spread_explain,
                       count_one, count_two, count_three, count_four,
                       open_arms, shrug_dunno,
                       show_size_small, show_size_big, thumbs_up,
                       present_item, emphasize_down
    ダンス・エンタメ(8): dance_sway, dance_wave_arms, robot_move, celebrate,
                       air_drum, conductor_wave, clap_rhythm, shimmy
    態度・スタンス(8): arms_forward, hands_on_hips, attention_stand,
                       open_stance, lean_back_relax, arms_behind,
                       ready_pose, thinking_stance
    待機・アイドル(7): look_around, stretch_up, idle_sway,
                       fidget_look, idle_head_tilt,
                       check_surroundings, sway_gentle

使い方:
    prim = Primitives(core)
    prim.execute("nod_gentle", intensity=0.8)
    prim.execute_with_speech("greet_bow", "こんにちは！")
"""
from __future__ import print_function
import sys
import time


def _s(text):
    """Python 2.7 NAOqi 用: unicode を UTF-8 bytes に変換。"""
    if sys.version_info[0] == 2:
        try:
            if isinstance(text, unicode):
                return text.encode("utf-8")
        except NameError:
            pass
    return text


class Primitives(object):
    """
    Pepper コミュニケーション動作プリミティブ集。

    全プリミティブは ALMotion.angleInterpolation() による直接関節制御。
    intensity パラメータで動作の強さを 0.1〜1.5 でスケールできる。
    """

    CATALOG = [
        # 社会的挨拶 (12)
        "greet_bow", "greet_wave", "farewell", "welcome",
        "thank_bow", "apologize_bow", "clap",
        "bow_deep", "bow_slight", "wave_both", "nod_hello", "handshake_gesture",
        # 傾聴・反応 (11)
        "nod_strong", "nod_gentle", "nod_triple",
        "shake_no", "tilt_head", "lean_in",
        "agree_enthusiastic", "disagree_arms", "listen_intense",
        "impressed_nod", "confirm_nod",
        # 指示・方向 (11)
        "point_forward", "point_up", "point_left", "point_right",
        "beckon", "show_palm", "present_both",
        "point_self", "point_past", "point_future", "come_here",
        # 思考・処理 (9)
        "think_chin", "think_scratch", "look_away",
        "confused_tilt", "focused",
        "recall_gesture", "doubt_head", "wonder_look", "pause_think",
        # 感情表現 (15)
        "joy_arms_up", "surprise_recoil", "sad_droop",
        "proud_chest", "shy_hide", "fear_back", "excited_bounce",
        "laugh_shake", "victory_arms", "determined_fist",
        "angry_cross", "relief_slump", "embarrassed_chin",
        "amazed_open", "satisfied_nod",
        # 強調・説明 (13)
        "raise_one_hand", "spread_explain",
        "count_one", "count_two", "count_three", "count_four",
        "open_arms", "shrug_dunno",
        "show_size_small", "show_size_big", "thumbs_up",
        "present_item", "emphasize_down",
        # ダンス・エンタメ (8)
        "dance_sway", "dance_wave_arms", "robot_move", "celebrate",
        "air_drum", "conductor_wave", "clap_rhythm", "shimmy",
        # 態度・スタンス (8)
        "arms_forward", "hands_on_hips", "attention_stand",
        "open_stance", "lean_back_relax", "arms_behind",
        "ready_pose", "thinking_stance",
        # 待機・アイドル (7)
        "look_around", "stretch_up", "idle_sway",
        "fidget_look", "idle_head_tilt", "check_surroundings", "sway_gentle",
    ]

    def __init__(self, core):
        self._core = core

    # ──────────────────────────────────────────────────────────────
    # 内部ヘルパー
    # ──────────────────────────────────────────────────────────────

    @property
    def _m(self):
        return self._core.motion

    def _go(self, joints, angles, duration):
        """指定時間で各関節を目標角度へ移行（同期）。"""
        self._m.angleInterpolation(
            joints, angles, [duration] * len(joints), True
        )

    def _tl(self, joints, angle_seqs, time_seqs):
        """タイムライン形式のアニメーション（複数キーフレーム、同期）。"""
        self._m.angleInterpolation(joints, angle_seqs, time_seqs, True)

    def _neutral(self, duration=1.1):
        """全関節をニュートラル直立姿勢に戻す。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadYaw", "HeadPitch", "HipPitch", "HipRoll"]
        a = [1.4, 0.2, -0.5, -1.0,
             1.4, -0.2, 0.5, 1.0,
             0.0, 0.0, 0.0, 0.0]
        self._go(j, a, duration)

    def _neutral_head(self, duration=0.8):
        """頭だけニュートラルに戻す。"""
        self._go(["HeadYaw", "HeadPitch"], [0.0, 0.0], duration)

    def _neutral_arms(self, duration=1.1):
        """両腕だけニュートラルに戻す。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        a = [1.4, 0.2, -0.5, -1.0, 1.4, -0.2, 0.5, 1.0]
        self._go(j, a, duration)

    # ──────────────────────────────────────────────────────────────
    # 公開 API
    # ──────────────────────────────────────────────────────────────

    def execute(self, name, intensity=1.0, **kwargs):
        """
        プリミティブを名前で実行する。

        Args:
            name (str)       : CATALOG 内のプリミティブ名
            intensity (float): 動作強度 0.1〜1.5
            **kwargs         : プリミティブ固有オプション
        """
        name = str(name)
        fn = getattr(self, name, None)
        if fn is None or not callable(fn) or name.startswith("_"):
            self.nod_gentle(intensity=0.5)
            return
        fn(intensity=float(intensity), **kwargs)

    def execute_with_speech(self, name, text, intensity=1.0, **kwargs):
        """
        発話と動作プリミティブを並列実行する。

        TTS を非同期で開始 → 動作（同期）→ TTS 完了待ち。
        """
        tts    = self._core.tts
        say_id = tts.post.say(_s(text))
        self.execute(name, intensity=intensity, **kwargs)
        tts.wait(say_id, 20000)

    # ================================================================
    # 社会的挨拶 (Social Greetings)  12 primitives
    # ================================================================

    def greet_bow(self, intensity=1.0):
        """丁寧にお辞儀して挨拶する。"""
        ang = min(0.9, 0.45 * max(0.1, intensity))
        j   = ["HipPitch", "HeadPitch"]
        self._tl(j,
                 [[0.0, ang,        ang,        0.0],
                  [0.0, ang * 0.55, ang * 0.55, 0.0]],
                 [[0.2, 1.0, 2.2, 3.2],
                  [0.2, 1.0, 2.2, 3.2]])

    def greet_wave(self, intensity=1.0, hand="R"):
        """手を振って挨拶する。"""
        spd = max(0.15, 0.45 / max(0.1, intensity))
        if hand == "R":
            j   = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
            up  = [-0.4, -0.3,  1.0, 1.0]
            w1  = [-0.4, -0.3,  0.4, 1.0]
            w2  = [-0.4, -0.3,  1.4, 1.0]
            ret = [ 1.4, -0.2,  0.5, 1.0]
        else:
            j   = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw"]
            up  = [-0.4,  0.3, -1.0, -1.0]
            w1  = [-0.4,  0.3, -0.4, -1.0]
            w2  = [-0.4,  0.3, -1.4, -1.0]
            ret = [ 1.4,  0.2, -0.5, -1.0]
        t = [0.5, 0.5 + spd, 0.5 + spd * 2,
             0.5 + spd * 3,  0.5 + spd * 4, 2.0 + spd * 4]
        self._tl(j,
                 [[a0, a1, a2, a1, a2, a3]
                  for a0, a1, a2, a3 in zip(up, w1, w2, ret)],
                 [t] * 4)

    def farewell(self, intensity=1.0):
        """手を振ってさようならを言う（波+小さなお辞儀）。"""
        self.greet_wave(intensity=intensity, hand="R")
        self._go(["HeadPitch"], [0.2], 0.4)
        time.sleep(0.3)
        self._go(["HeadPitch"], [0.0], 0.4)

    def welcome(self, intensity=1.0):
        """両腕を広げて歓迎する（どうぞ）。"""
        ang = min(1.1, 0.9 * max(0.1, intensity))
        j   = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
               "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
               "HeadPitch"]
        self._go(j, [0.3,  ang, -0.15,
                     0.3, -ang,  0.15,
                     0.0], 0.9)
        time.sleep(1.5)
        self._neutral(0.8)

    def thank_bow(self, intensity=1.0):
        """感謝してお辞儀する（腕を体の前で合わせながら）。"""
        ang = min(0.9, 0.55 * max(0.1, intensity))
        j   = ["HipPitch", "HeadPitch",
               "LShoulderPitch", "LElbowRoll",
               "RShoulderPitch", "RElbowRoll"]
        self._tl(j,
                 [[0.0, ang,      ang,      0.0],
                  [0.0, ang*0.6,  ang*0.6,  0.0],
                  [1.4, 0.7,      0.7,      1.4],
                  [-0.5, -0.8,   -0.8,     -0.5],
                  [1.4, 0.7,      0.7,      1.4],
                  [0.5,  0.8,     0.8,      0.5]],
                 [[0.2, 1.0, 2.5, 3.5]] * 6)

    def apologize_bow(self, intensity=1.0):
        """深くお辞儀して謝る（2回繰り返し）。"""
        ang = min(0.9, 0.7 * max(0.1, intensity))
        j   = ["HipPitch", "HeadPitch"]
        for _ in range(2):
            self._tl(j,
                     [[0.0, ang,       ang,       0.0],
                      [0.0, ang * 0.6, ang * 0.6, 0.0]],
                     [[0.2, 0.9, 2.0, 3.0],
                      [0.2, 0.9, 2.0, 3.0]])
            time.sleep(0.2)

    def clap(self, intensity=1.0):
        """拍手する（両腕を前に出して交互に動かす）。"""
        j = ["LShoulderPitch", "LElbowRoll",
             "RShoulderPitch", "RElbowRoll"]
        self._go(j, [0.2, -0.4, 0.2, 0.4], 0.6)
        reps = max(2, int(4 * max(0.3, intensity)))
        for _ in range(reps):
            self._go(["LElbowRoll", "RElbowRoll"], [-0.15, 0.15], 0.12)
            self._go(["LElbowRoll", "RElbowRoll"], [-0.6,  0.6],  0.12)
        self._neutral(0.6)

    def bow_deep(self, intensity=1.0):
        """深くお辞儀する（最大前傾・礼）。"""
        ang = min(0.95, 0.85 * max(0.1, intensity))
        j = ["HipPitch", "HeadPitch", "LShoulderPitch", "RShoulderPitch"]
        self._tl(j,
                 [[0.0, ang,      ang,      0.0],
                  [0.0, ang*0.5,  ang*0.5,  0.0],
                  [1.4, 1.0,      1.0,      1.4],
                  [1.4, 1.0,      1.0,      1.4]],
                 [[0.3, 1.2, 2.8, 4.0]] * 4)

    def bow_slight(self, intensity=1.0):
        """軽く会釈する（通り過ぎる時など）。"""
        ang = min(0.30, 0.22 * max(0.1, intensity))
        j = ["HipPitch", "HeadPitch"]
        self._tl(j,
                 [[0.0, ang,      ang,      0.0],
                  [0.0, ang*0.5,  ang*0.5,  0.0]],
                 [[0.15, 0.5, 1.2, 1.8]] * 2)

    def wave_both(self, intensity=1.0):
        """両手を挙げて振る（大きな挨拶）。"""
        spd = max(0.14, 0.28 / max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [-0.4, 0.4, -1.0, -0.4, -0.4, 1.0], 0.6)
        reps = max(2, int(3 * max(0.3, intensity)))
        for _ in range(reps):
            self._go(["LElbowRoll", "RElbowRoll"], [-0.35, 0.35], spd)
            self._go(["LElbowRoll", "RElbowRoll"], [-1.2,  1.2],  spd)
        self._neutral_arms(0.8)

    def nod_hello(self, intensity=1.0):
        """軽く頷いて挨拶する（目礼・会釈）。"""
        amp = min(0.18, 0.13 * max(0.1, intensity))
        self._go(["HeadPitch"], [amp], 0.28)
        self._go(["HeadPitch"], [0.0], 0.28)

    def handshake_gesture(self, intensity=1.0):
        """右手を前に差し出す（握手の仕草）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [0.3, -0.1, 0.8, 0.8], 0.7)
        for _ in range(2):
            self._go(["RShoulderPitch"], [0.0], 0.25)
            self._go(["RShoulderPitch"], [0.3], 0.25)
        self._go(j, [1.4, -0.2, 0.5, 1.0], 0.7)

    # ================================================================
    # 傾聴・反応 (Listening / Reactions)  11 primitives
    # ================================================================

    def nod_strong(self, intensity=1.0):
        """大きく深くうなずく（強い同意）。"""
        amp = min(0.42, 0.35 * max(0.1, intensity))
        spd = max(0.15, 0.28 / max(0.1, intensity))
        for _ in range(2):
            self._go(["HeadPitch"], [amp], spd)
            self._go(["HeadPitch"], [0.0], spd)

    def nod_gentle(self, intensity=1.0):
        """小さく静かにうなずく（聞いている・相槌）。"""
        amp = min(0.25, 0.18 * max(0.1, intensity))
        self._go(["HeadPitch"], [amp], 0.35)
        self._go(["HeadPitch"], [0.0], 0.35)

    def nod_triple(self, intensity=1.0):
        """3回連続でうなずく（強調した同意）。"""
        amp = min(0.25, 0.2 * max(0.1, intensity))
        for _ in range(3):
            self._go(["HeadPitch"], [amp], 0.22)
            self._go(["HeadPitch"], [0.0], 0.22)

    def shake_no(self, intensity=1.0):
        """首を横に振る（否定・断り）。"""
        amp = min(0.5, 0.38 * max(0.1, intensity))
        for _ in range(2):
            self._go(["HeadYaw"], [ amp], 0.22)
            self._go(["HeadYaw"], [-amp], 0.22)
        self._go(["HeadYaw"], [0.0], 0.2)

    def tilt_head(self, intensity=1.0, direction="R"):
        """首をかしげる（疑問・関心）。"""
        sign  = -1.0 if direction == "L" else 1.0
        yaw   = min(0.45, 0.3 * max(0.1, intensity)) * sign
        pitch = min(0.2,  0.1 * max(0.1, intensity))
        self._go(["HeadYaw", "HeadPitch"], [yaw, pitch], 0.7)
        time.sleep(1.2)
        self._neutral_head(0.5)

    def lean_in(self, intensity=1.0):
        """前傾みで話を傾聴する（関心・集中）。"""
        ang = min(0.25, 0.18 * max(0.1, intensity))
        self._go(["HipPitch", "HeadPitch"], [ang, -0.05], 0.9)
        time.sleep(1.8)
        self._go(["HipPitch", "HeadPitch"], [0.0, 0.0], 0.7)

    def agree_enthusiastic(self, intensity=1.0):
        """力強く同意する（大きなうなずき＋腕の動き）。"""
        amp = min(0.38, 0.30 * max(0.1, intensity))
        spd = max(0.16, 0.22 / max(0.1, intensity))
        j = ["HeadPitch", "LShoulderPitch", "RShoulderPitch"]
        for _ in range(2):
            self._go(j, [amp, 1.2, 1.2], spd)
            self._go(j, [0.0, 1.4, 1.4], spd)

    def disagree_arms(self, intensity=1.0):
        """腕を広げながら否定する（それは違います）。"""
        amp = min(0.42, 0.35 * max(0.1, intensity))
        j = ["HeadYaw", "LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll"]
        self._go(j, [0.0, 0.5, 0.6, 0.5, -0.6], 0.5)
        for _ in range(2):
            self._go(["HeadYaw"], [ amp], 0.2)
            self._go(["HeadYaw"], [-amp], 0.2)
        self._go(["HeadYaw"], [0.0], 0.2)
        self._neutral_arms(0.7)

    def listen_intense(self, intensity=1.0):
        """前傾みで真剣に聞く（集中して傾聴）。"""
        ang = min(0.35, 0.28 * max(0.1, intensity))
        j = ["HipPitch", "HeadPitch", "LShoulderPitch", "RShoulderPitch"]
        self._go(j, [ang, 0.0, 1.1, 1.1], 1.0)
        time.sleep(2.5)
        self._neutral(0.8)

    def impressed_nod(self, intensity=1.0):
        """感心してゆっくりうなずく（なるほど）。"""
        amp = min(0.35, 0.28 * max(0.1, intensity))
        for _ in range(2):
            self._go(["HeadPitch", "HipPitch"], [amp, amp * 0.3], 0.55)
            self._go(["HeadPitch", "HipPitch"], [0.0, 0.0], 0.55)

    def confirm_nod(self, intensity=1.0):
        """確信を持って一度うなずく（決定・了解）。"""
        amp = min(0.32, 0.25 * max(0.1, intensity))
        spd = max(0.18, 0.22 / max(0.1, intensity))
        self._go(["HeadPitch"], [amp], spd)
        self._go(["HeadPitch"], [0.0], spd)

    # ================================================================
    # 指示・方向 (Pointing / Directing)  11 primitives
    # ================================================================

    def point_forward(self, intensity=1.0, hand="R"):
        """前方を指差す（強調・方向指示）。"""
        if hand == "R":
            j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
            a = [-0.3, -0.1, 0.3, 1.0]
            n = [ 1.4, -0.2, 0.5, 1.0]
        else:
            j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw"]
            a = [-0.3,  0.1, -0.3, -1.0]
            n = [ 1.4,  0.2, -0.5, -1.0]
        self._go(j, a, 0.7)
        time.sleep(1.5)
        self._go(j, n, 0.6)

    def point_up(self, intensity=1.0):
        """上方を指す（重要・強調・未来を示す）。"""
        self._go(["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "HeadPitch"],
                 [-0.9, -0.1, 0.2, -0.2], 0.8)
        time.sleep(1.5)
        self._neutral(0.7)

    def point_left(self, intensity=1.0):
        """左方向を示す。"""
        self._go(["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "HeadYaw"],
                 [0.0, 0.9, -0.2, 0.5], 0.7)
        time.sleep(1.5)
        self._go(["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "HeadYaw"],
                 [1.4, 0.2, -0.5, 0.0], 0.6)

    def point_right(self, intensity=1.0):
        """右方向を示す。"""
        self._go(["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "HeadYaw"],
                 [0.0, -0.9, 0.2, -0.5], 0.7)
        time.sleep(1.5)
        self._go(["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "HeadYaw"],
                 [1.4, -0.2, 0.5, 0.0], 0.6)

    def beckon(self, intensity=1.0):
        """手招きする（こっちに来て）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.0, -0.3, 0.9], 0.6)
        reps = max(2, int(3 * max(0.3, intensity)))
        for _ in range(reps):
            self._go(["RElbowRoll"], [0.5], 0.25)
            self._go(["RElbowRoll"], [1.1], 0.25)
        self._neutral_arms(0.7)

    def show_palm(self, intensity=1.0):
        """手のひらを見せる（止まれ・待って）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [-0.1, -0.25, 0.6, 0.8], 0.7)
        time.sleep(1.8)
        self._go(j, [1.4, -0.2, 0.5, 1.0], 0.6)

    def present_both(self, intensity=1.0):
        """両手を前に差し出す（どうぞ・提示）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.7, 0.25, -0.3, 0.7, -0.25, 0.3], 0.8)
        time.sleep(2.0)
        self._neutral_arms(0.7)

    def point_self(self, intensity=1.0):
        """自分自身を指す（私が・私は）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HeadPitch"]
        self._go(j, [0.7, 0.1, -1.1, 0.7, -0.1, 1.1, 0.05], 0.8)
        time.sleep(1.5)
        self._neutral(0.7)

    def point_past(self, intensity=1.0):
        """過去・後ろを肩越しに示す。"""
        j = ["HeadYaw", "LShoulderPitch", "LShoulderRoll", "LElbowRoll"]
        self._go(j, [-0.6, 1.55, 0.3, -0.3], 0.7)
        time.sleep(1.5)
        self._neutral(0.7)

    def point_future(self, intensity=1.0):
        """未来・前方を力強く示す。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "HeadPitch"]
        self._go(j, [-0.6, -0.05, 0.15, -0.08], 0.7)
        time.sleep(1.5)
        self._go(j, [1.4, -0.2, 0.5, 0.0], 0.6)

    def come_here(self, intensity=1.0):
        """両手で招く（こちらへ来て）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.0, 0.3, -0.8, 0.0, -0.3, 0.8], 0.6)
        reps = max(2, int(3 * max(0.3, intensity)))
        for _ in range(reps):
            self._go(["LElbowRoll", "RElbowRoll"], [-0.4, 0.4], 0.25)
            self._go(["LElbowRoll", "RElbowRoll"], [-1.1, 1.1], 0.25)
        self._neutral_arms(0.7)

    # ================================================================
    # 思考・処理 (Thinking / Processing)  9 primitives
    # ================================================================

    def think_chin(self, intensity=1.0):
        """あごに手を当てて熟考する。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadPitch", "HeadYaw"]
        self._go(j, [0.5, -0.3, 1.0, 0.5, 0.1, 0.25], 1.0)
        time.sleep(2.0)
        self._neutral(0.8)

    def think_scratch(self, intensity=1.0):
        """頭を掻きながら悩む（ちょっと困った）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadYaw", "HeadPitch"]
        self._go(j, [-0.3, -0.7, 1.4, 0.4, 0.3, 0.15], 0.9)
        for _ in range(3):
            self._go(["RElbowYaw"], [0.2], 0.18)
            self._go(["RElbowYaw"], [0.6], 0.18)
        self._neutral(0.8)

    def look_away(self, intensity=1.0):
        """横を向く（躊躇・照れ・考え中）。"""
        yaw = min(0.6, 0.5 * max(0.1, intensity))
        self._go(["HeadYaw", "HeadPitch"], [yaw, 0.1], 0.6)
        time.sleep(1.5)
        self._neutral_head(0.5)

    def confused_tilt(self, intensity=1.0):
        """首をかしげて困惑する。"""
        yaw = min(0.55, 0.45 * max(0.1, intensity))
        j = ["HeadYaw", "HeadPitch",
             "LShoulderPitch", "LShoulderRoll"]
        self._go(j, [yaw, 0.2, 0.9, 0.4], 0.8)
        time.sleep(1.5)
        self._neutral(0.7)

    def focused(self, intensity=1.0):
        """集中ポーズ（前傾み＋腕を体前で構える）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HipPitch", "HeadPitch"]
        self._go(j, [0.8, 0.1, -0.7, 0.8, -0.1, 0.7, 0.15, -0.05], 1.0)
        time.sleep(2.0)
        self._neutral(0.8)

    def recall_gesture(self, intensity=1.0):
        """記憶を辿る（上を見ながら手を額に当てる）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadPitch", "HeadYaw"]
        self._go(j, [-0.1, -0.5, 1.3, 0.4, -0.25, 0.3], 1.0)
        time.sleep(2.0)
        self._neutral(0.8)

    def doubt_head(self, intensity=1.0):
        """疑念・不確かさで頭をゆっくり振る。"""
        amp = min(0.4, 0.3 * max(0.1, intensity))
        self._go(["HeadYaw", "HeadPitch"], [ amp, 0.08], 0.5)
        self._go(["HeadYaw", "HeadPitch"], [-amp, 0.08], 0.9)
        self._go(["HeadYaw", "HeadPitch"], [ amp, 0.05], 0.9)
        self._neutral_head(0.6)

    def wonder_look(self, intensity=1.0):
        """不思議そうに上を見る（何かを想像する）。"""
        yaw = min(0.45, 0.35 * max(0.1, intensity))
        self._go(["HeadYaw", "HeadPitch"], [yaw, -0.25], 0.7)
        time.sleep(2.0)
        self._neutral_head(0.5)

    def pause_think(self, intensity=1.0):
        """発話を止めて静かに考える間を作る。"""
        self._go(["HeadPitch"], [0.08], 0.5)
        time.sleep(1.0)
        self._go(["HeadPitch"], [0.0], 0.4)

    # ================================================================
    # 感情表現 (Emotional Expressions)  15 primitives
    # ================================================================

    def joy_arms_up(self, intensity=1.0):
        """喜んで両腕を上に挙げる。"""
        ang = min(2.0, 1.5 * max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HeadPitch"]
        self._go(j, [-ang, 0.3, -0.4, -ang, -0.3, 0.4, -0.1], 0.9)
        time.sleep(1.5)
        self._neutral(0.8)

    def surprise_recoil(self, intensity=1.0):
        """驚いて後ろに傾く（のけぞる）。"""
        ang = min(0.25, 0.2 * max(0.1, intensity))
        j = ["HipPitch", "HeadPitch",
             "LShoulderPitch", "RShoulderPitch"]
        self._go(j, [-ang, -0.1, 0.6, 0.6], 0.35)
        time.sleep(0.8)
        self._neutral(0.8)

    def sad_droop(self, intensity=1.0):
        """肩を落として悲しむ。"""
        ang = min(0.2, 0.15 * max(0.1, intensity))
        j = ["HipPitch", "HeadPitch",
             "LShoulderPitch", "RShoulderPitch",
             "HeadYaw"]
        self._go(j, [ang, 0.3, 1.7, 1.7, 0.15], 1.2)
        time.sleep(2.0)
        self._neutral(1.0)

    def proud_chest(self, intensity=1.0):
        """胸を張って誇らしそうにする。"""
        ang = min(0.12, 0.1 * max(0.1, intensity))
        j = ["HipPitch", "HeadPitch",
             "LShoulderRoll", "RShoulderRoll"]
        self._go(j, [-ang, -0.1, 0.3, -0.3], 0.8)
        time.sleep(2.0)
        self._neutral(0.8)

    def shy_hide(self, intensity=1.0):
        """照れて俯く・腕を交差させる。"""
        j = ["HeadPitch", "HeadYaw",
             "LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.25, 0.3,
                     0.5,  0.15, -1.0,
                     0.5, -0.15,  1.0], 1.0)
        time.sleep(1.5)
        self._neutral(0.8)

    def fear_back(self, intensity=1.0):
        """怖くて後ずさりするような防御ポーズ。"""
        ang = min(0.22, 0.18 * max(0.1, intensity))
        j = ["HipPitch", "HeadPitch",
             "LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll"]
        self._go(j, [-ang, -0.1, 0.4, 0.4, 0.4, -0.4], 0.4)
        time.sleep(1.2)
        self._neutral(0.8)

    def excited_bounce(self, intensity=1.0):
        """興奮してその場で弾むような動き。"""
        j = ["KneePitch",
             "LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll"]
        amp  = min(0.15, 0.1 * max(0.1, intensity))
        reps = max(2, int(3 * max(0.3, intensity)))
        for _ in range(reps):
            self._go(j, [amp, 0.7,  0.4, 0.7, -0.4], 0.18)
            self._go(j, [0.0, 0.5,  0.2, 0.5, -0.2], 0.18)
        self._neutral(0.7)

    def laugh_shake(self, intensity=1.0):
        """笑いで肩と頭が揺れる。"""
        reps = max(3, int(5 * max(0.3, intensity)))
        j    = ["HeadPitch", "LShoulderPitch", "RShoulderPitch"]
        H = []; L = []; R = []; times = []
        for i in range(reps):
            times.append(0.2 * (i + 1))
            if i % 2 == 0:
                H.append(0.12); L.append(1.3); R.append(1.3)
            else:
                H.append(0.0);  L.append(1.5); R.append(1.5)
        times.append(times[-1] + 0.7)
        H.append(0.0); L.append(1.4); R.append(1.4)
        self._tl(j, [H, L, R], [times, times, times])

    def victory_arms(self, intensity=1.0):
        """勝利！両腕を高く突き上げる。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HeadPitch"]
        self._go(j, [-1.9, 0.4, -0.3, -1.9, -0.4, 0.3, -0.12], 0.8)
        time.sleep(1.5)
        self._neutral(0.8)

    def determined_fist(self, intensity=1.0):
        """決意の拳（気合を入れる）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HipPitch", "HeadPitch"]
        self._go(j, [0.8, -0.15, 1.3, 0.1, 0.0], 0.7)
        time.sleep(1.2)
        self._neutral(0.8)

    def angry_cross(self, intensity=1.0):
        """怒って腕を組む（不機嫌・拒絶）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HipPitch", "HeadPitch"]
        self._go(j, [0.5, 0.0, -1.0, 0.5, 0.0, 1.0, 0.1, 0.1], 0.8)
        time.sleep(2.0)
        self._neutral(0.8)

    def relief_slump(self, intensity=1.0):
        """安堵して肩の力が抜ける（ほっとした）。"""
        j = ["HeadPitch", "HipPitch", "LShoulderPitch", "RShoulderPitch"]
        self._go(j, [0.2, 0.08, 1.6, 1.6], 1.2)
        time.sleep(0.5)
        self._go(j, [0.0, 0.0, 1.4, 1.4], 1.0)

    def embarrassed_chin(self, intensity=1.0):
        """恥ずかしくて俯く（あごを引く）。"""
        j = ["HeadPitch", "HeadYaw",
             "LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll"]
        self._go(j, [0.35, 0.18, 0.9, 0.1, 0.9, -0.1], 1.0)
        time.sleep(2.0)
        self._neutral(0.8)

    def amazed_open(self, intensity=1.0):
        """驚嘆して両腕を広げ、頭を仰け反らせる。"""
        ang = min(1.1, 0.9 * max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HeadPitch"]
        self._go(j, [-0.2, ang, -0.15, -0.2, -ang, 0.15, -0.18], 0.7)
        time.sleep(1.5)
        self._neutral(0.8)

    def satisfied_nod(self, intensity=1.0):
        """満足そうにゆっくりうなずく（うまくいった）。"""
        j = ["HeadPitch", "HipPitch", "LShoulderRoll", "RShoulderRoll"]
        self._go(j, [0.28, 0.0, 0.18, -0.18], 0.7)
        self._go(j, [0.0, -0.05, 0.2, -0.2], 0.7)
        time.sleep(0.5)
        self._neutral(0.6)

    # ================================================================
    # 強調・説明 (Emphasis / Explanation)  13 primitives
    # ================================================================

    def raise_one_hand(self, intensity=1.0, hand="R"):
        """片手を挙げて注目を引く（それと・ところで）。"""
        if hand == "R":
            j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
            a = [-0.5, -0.1, 0.4]
            n = [ 1.4, -0.2, 0.5]
        else:
            j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll"]
            a = [-0.5,  0.1, -0.4]
            n = [ 1.4,  0.2, -0.5]
        self._go(j, a, 0.6)
        time.sleep(1.5)
        self._go(j, n, 0.6)

    def spread_explain(self, intensity=1.0):
        """両腕を広げながら説明する（大きな概念・全体像）。"""
        ang = min(1.0, 0.75 * max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HeadPitch"]
        self._go(j, [0.3, ang, -0.25, 0.3, -ang, 0.25, 0.0], 0.8)
        time.sleep(2.0)
        self._neutral(0.8)

    def count_one(self, intensity=1.0):
        """1つ目を示す。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [-0.2, -0.1, 0.5, 0.8], 0.7)
        time.sleep(1.0)
        self._neutral_arms(0.6)

    def count_two(self, intensity=1.0):
        """2つ目を示す（左腕も追加）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.2, 0.5, -0.4, -0.2, -0.5, 0.4], 0.7)
        time.sleep(1.0)
        self._neutral_arms(0.6)

    def count_three(self, intensity=1.0):
        """3つ目を示す（両腕前に）。"""
        j = ["LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll"]
        self._go(j, [0.4, 0.3, 0.4, -0.3], 0.7)
        time.sleep(1.0)
        self._neutral_arms(0.6)

    def count_four(self, intensity=1.0):
        """4つ目を示す（両腕を異なる高さで）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.2, 0.5, -0.4, -0.1, -0.2, 0.5], 0.7)
        time.sleep(1.0)
        self._neutral_arms(0.6)

    def open_arms(self, intensity=1.0):
        """腕を大きく広げる（受け入れ・大きさ強調）。"""
        ang = min(1.15, 0.9 * max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.1, ang, -0.1, 0.1, -ang, 0.1], 0.8)
        time.sleep(2.0)
        self._neutral_arms(0.8)

    def shrug_dunno(self, intensity=1.0):
        """肩をすくめる（わからない・どうしようもない）。"""
        ang = min(0.65, 0.5 * max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll",
             "RShoulderPitch", "RShoulderRoll",
             "HeadPitch", "HeadYaw"]
        self._go(j, [0.8, ang, 0.8, -ang, 0.1, 0.2], 0.55)
        time.sleep(1.2)
        self._neutral(0.7)

    def show_size_small(self, intensity=1.0):
        """両手を近づけて「小さい」を示す。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [0.6,  0.2, -1.2,  0.3,
                     0.6, -0.2,  1.2, -0.3], 0.8)
        time.sleep(2.0)
        self._neutral_arms(0.7)

    def show_size_big(self, intensity=1.0):
        """両腕を大きく広げて「大きい」を示す。"""
        ang = min(1.25, 1.05 * max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HeadPitch"]
        self._go(j, [0.1, ang, -0.12, 0.1, -ang, 0.12, -0.05], 0.9)
        time.sleep(2.0)
        self._neutral(0.8)

    def thumbs_up(self, intensity=1.0):
        """親指を立てる（グッド！いいね！）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [0.4, -0.2, 1.0, 1.6], 0.7)
        time.sleep(1.5)
        self._go(j, [1.4, -0.2, 0.5, 1.0], 0.6)

    def present_item(self, intensity=1.0):
        """手のひらで何かを差し出す（どうぞ・提示）。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadPitch"]
        self._go(j, [0.5, -0.2, 0.6, 0.8, 0.05], 0.8)
        time.sleep(2.0)
        self._neutral(0.7)

    def emphasize_down(self, intensity=1.0):
        """両手を下に押さえるように強調する（落ち着いて・重要）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.5, 0.1, -0.3, 0.5, -0.1, 0.3], 0.6)
        for _ in range(2):
            self._go(["LShoulderPitch", "RShoulderPitch"], [0.7, 0.7], 0.22)
            self._go(["LShoulderPitch", "RShoulderPitch"], [0.4, 0.4], 0.22)
        self._neutral_arms(0.7)

    # ================================================================
    # ダンス・エンタメ (Dance / Entertainment)  8 primitives
    # ================================================================

    def dance_sway(self, intensity=1.0):
        """音楽に合わせて左右にスウェーする。"""
        amp = min(0.14, 0.10 * max(0.1, intensity))
        j   = ["HipRoll", "LShoulderPitch", "RShoulderPitch", "HeadYaw"]
        a_seqs = [
            [-amp,  0.0,  amp, 0.0, -amp,  0.0],
            [ 1.3,  1.4,  1.5, 1.4,  1.3,  1.4],
            [ 1.5,  1.4,  1.3, 1.4,  1.5,  1.4],
            [-0.15, 0.0,  0.15, 0.0, -0.1, 0.0],
        ]
        times = [0.5, 1.0, 1.5, 2.0, 2.5, 3.2]
        self._tl(j, a_seqs, [times] * 4)
        self._neutral(0.6)

    def dance_wave_arms(self, intensity=1.0):
        """波のように両腕を流れるように動かすダンス。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        a_seqs = [
            [-0.5,  0.3,  1.0,  1.4, -0.3],
            [ 0.6,  0.8,  0.5,  0.2,  0.6],
            [-0.4, -0.8, -0.4, -0.3, -0.4],
            [ 1.4,  0.3, -0.5,  0.5,  1.4],
            [-0.2, -0.4, -0.8, -0.3, -0.2],
            [ 0.4,  0.8,  0.4,  0.3,  0.4],
        ]
        times = [0.5, 1.1, 1.7, 2.3, 3.0]
        self._tl(j, a_seqs, [times] * 6)
        self._neutral(0.7)

    def robot_move(self, intensity=1.0):
        """ロボットらしいぎこちない機械的な動き。"""
        spd = max(0.12, 0.16 / max(0.1, intensity))
        j = ["LShoulderPitch", "RShoulderPitch", "LElbowRoll", "RElbowRoll",
             "HeadYaw"]
        self._go(j, [0.3,  1.0, -1.0, 0.5,  0.4], spd)
        time.sleep(0.15)
        self._go(j, [1.0,  0.3, -0.5, 1.0, -0.4], spd)
        time.sleep(0.15)
        self._go(j, [0.0,  0.0, -0.6, 0.6,  0.0], spd)
        time.sleep(0.15)
        self._go(j, [-0.5, -0.5, -0.8, 0.8,  0.2], spd)
        time.sleep(0.15)
        self._neutral(0.5)

    def celebrate(self, intensity=1.0):
        """大きく喜びを表現する（万歳＋ウェーブ）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HeadPitch", "HipPitch"]
        self._go(j, [-1.8, 0.4, -0.3, -1.8, -0.4, 0.3, -0.1, 0.0], 0.6)
        reps = max(2, int(3 * max(0.3, intensity)))
        for _ in range(reps):
            self._go(["LElbowRoll", "RElbowRoll"], [-1.1, 1.1], 0.2)
            self._go(["LElbowRoll", "RElbowRoll"], [-0.2, 0.2], 0.2)
        self._neutral(0.9)

    def air_drum(self, intensity=1.0):
        """エアドラムをたたく（両腕交互）。"""
        reps = max(3, int(5 * max(0.3, intensity)))
        L = []; R = []; times = []
        for i in range(reps * 2):
            times.append(0.19 * (i + 1))
            if i % 2 == 0:
                L.append(0.3); R.append(1.0)
            else:
                L.append(1.0); R.append(0.3)
        times.append(times[-1] + 0.7)
        L.append(1.4); R.append(1.4)
        self._tl(["LShoulderPitch", "RShoulderPitch"],
                 [L, R], [times, times])

    def conductor_wave(self, intensity=1.0):
        """指揮者のように腕を振る。"""
        j = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "LShoulderPitch", "LShoulderRoll"]
        a_seqs = [
            [-0.1,  0.4,  0.0, -0.3,  0.5, 1.4],
            [-0.1, -0.5, -0.2, -0.1, -0.2, -0.2],
            [ 0.5,  1.1,  0.5,  0.3,  0.6,  0.5],
            [ 0.4,  0.7,  0.4,  0.7,  0.4,  1.4],
            [ 0.3,  0.5,  0.3,  0.5,  0.3,  0.2],
        ]
        times = [0.4, 0.9, 1.4, 1.9, 2.4, 3.2]
        self._tl(j, a_seqs, [times] * 5)

    def clap_rhythm(self, intensity=1.0):
        """リズミカルに拍手する（速め・繰り返し）。"""
        j = ["LShoulderPitch", "LElbowRoll",
             "RShoulderPitch", "RElbowRoll"]
        self._go(j, [0.2, -0.4, 0.2, 0.4], 0.5)
        reps = max(4, int(6 * max(0.3, intensity)))
        spd  = max(0.08, 0.10 / max(0.1, intensity))
        for _ in range(reps):
            self._go(["LElbowRoll", "RElbowRoll"], [-0.12, 0.12], spd)
            self._go(["LElbowRoll", "RElbowRoll"], [-0.7,  0.7],  spd)
        self._neutral(0.6)

    def shimmy(self, intensity=1.0):
        """肩を交互に揺らすシミー（ダンス・軽快）。"""
        amp  = min(0.25, 0.18 * max(0.1, intensity))
        reps = max(4, int(6 * max(0.3, intensity)))
        L = []; R = []; times = []
        for i in range(reps * 2):
            times.append(0.14 * (i + 1))
            if i % 2 == 0:
                L.append(1.4 - amp); R.append(1.4 + amp)
            else:
                L.append(1.4 + amp); R.append(1.4 - amp)
        times.append(times[-1] + 0.5)
        L.append(1.4); R.append(1.4)
        self._tl(["LShoulderPitch", "RShoulderPitch"],
                 [L, R], [times, times])

    # ================================================================
    # 態度・スタンス (Posture / Stance)  8 primitives
    # ================================================================

    def arms_forward(self, intensity=1.0):
        """腕を体の前で構える（考え・待機・中立）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [0.6,  0.1, -0.7,
                     0.6, -0.1,  0.7], 0.8)
        time.sleep(2.0)
        self._neutral_arms(0.7)

    def hands_on_hips(self, intensity=1.0):
        """腰に手を当てる（自信・問いかけ・堂々）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [1.1,  0.7, -0.8, -0.4,
                     1.1, -0.7,  0.8,  0.4], 0.8)
        time.sleep(2.0)
        self._neutral_arms(0.8)

    def attention_stand(self, intensity=1.0):
        """気をつけ（腕を体側に密着・整列）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
             "HeadYaw", "HeadPitch", "HipPitch", "HipRoll"]
        self._go(j, [1.5,  0.1, -0.1, -1.0,
                     1.5, -0.1,  0.1,  1.0,
                     0.0,  0.0,  0.0,  0.0], 0.8)
        time.sleep(1.5)
        self._neutral(0.7)

    def open_stance(self, intensity=1.0):
        """オープンで友好的な姿勢（腕を軽く広げる）。"""
        ang = min(0.55, 0.40 * max(0.1, intensity))
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll"]
        self._go(j, [1.1, ang, -0.3, 1.1, -ang, 0.3], 0.8)
        time.sleep(2.0)
        self._neutral_arms(0.8)

    def lean_back_relax(self, intensity=1.0):
        """少し後ろに寄りかかるようなリラックスした姿勢。"""
        j = ["HipPitch", "HeadPitch",
             "LShoulderPitch", "RShoulderPitch"]
        self._go(j, [-0.1, -0.05, 1.6, 1.6], 1.0)
        time.sleep(2.0)
        self._neutral(0.9)

    def arms_behind(self, intensity=1.0):
        """腕を後ろに組む（フォーマル・at ease・思索）。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [1.9,  0.1, -0.3, -0.5,
                     1.9, -0.1,  0.3,  0.5], 0.8)
        time.sleep(2.0)
        self._neutral_arms(0.8)

    def ready_pose(self, intensity=1.0):
        """やる気を示す準備姿勢（前傾み＋腕前構え）。"""
        j = ["HipPitch", "HeadPitch",
             "LShoulderPitch", "LElbowRoll",
             "RShoulderPitch", "RElbowRoll"]
        self._go(j, [0.12, -0.02, 0.9, -0.6, 0.9, 0.6], 0.8)
        time.sleep(1.5)
        self._neutral(0.7)

    def thinking_stance(self, intensity=1.0):
        """長考ポーズ（体を少し傾けながら手をあごに当てる）。"""
        j = ["HipRoll", "HeadYaw", "HeadPitch",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw"]
        self._go(j, [0.08, 0.25, 0.1, 0.5, -0.3, 1.0, 0.4], 1.1)
        time.sleep(2.5)
        self._neutral(0.9)

    # ================================================================
    # 待機・アイドル (Waiting / Idle)  7 primitives
    # ================================================================

    def look_around(self, intensity=1.0):
        """左右をゆっくり見回す（待機中・何かを探している）。"""
        spd = max(0.5, 0.8 / max(0.1, intensity))
        yaw = min(0.7, 0.6 * max(0.1, intensity))
        self._go(["HeadYaw"], [ yaw], spd)
        self._go(["HeadYaw"], [-yaw], spd * 2)
        self._go(["HeadYaw"], [ 0.0], spd)

    def stretch_up(self, intensity=1.0):
        """両腕を上に伸ばしてストレッチする。"""
        j = ["LShoulderPitch", "LShoulderRoll", "LElbowRoll",
             "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
             "HipPitch"]
        self._go(j, [-1.4, 0.3, -0.3, -1.4, -0.3, 0.3, -0.05], 1.5)
        time.sleep(1.5)
        self._neutral(1.0)

    def idle_sway(self, intensity=1.0):
        """ゆっくり左右に揺れる（待機中の自然な動き）。"""
        amp = min(0.11, 0.08 * max(0.1, intensity))
        arm = amp * 0.55
        j   = ["HipRoll", "HeadYaw",
               "LShoulderPitch", "RShoulderPitch"]
        for _ in range(2):
            self._go(j, [ amp,  amp * 2.2, 1.40 + arm, 1.40 - arm], 1.0)
            self._go(j, [-amp, -amp * 2.2, 1.40 - arm, 1.40 + arm], 1.0)
        self._go(j, [0.0, 0.0, 1.40, 1.40], 0.8)

    def fidget_look(self, intensity=1.0):
        """落ち着かなく視線を動かし、腕を少し動かす。"""
        j = ["HeadYaw", "HeadPitch", "LShoulderPitch"]
        self._tl(j,
                 [[ 0.3, -0.2,  0.4, -0.3,  0.0],
                  [ 0.05, 0.1,  0.0,  0.08, 0.0],
                  [ 1.3,  1.5,  1.3,  1.5,  1.4]],
                 [[0.5, 1.1, 1.7, 2.3, 3.0]] * 3)

    def idle_head_tilt(self, intensity=1.0):
        """ゆっくり頭を傾けて戻す（アイドル中の自然な動き）。"""
        yaw   = min(0.30, 0.22 * max(0.1, intensity))
        pitch = min(0.10, 0.08 * max(0.1, intensity))
        self._go(["HeadYaw", "HeadPitch"], [yaw, pitch], 1.5)
        time.sleep(1.0)
        self._neutral_head(1.2)

    def check_surroundings(self, intensity=1.0):
        """周囲を確認するように上下左右を見る。"""
        self._go(["HeadYaw", "HeadPitch"], [ 0.5,  0.0], 0.7)
        self._go(["HeadYaw", "HeadPitch"], [-0.5,  0.0], 1.3)
        self._go(["HeadYaw", "HeadPitch"], [ 0.0, -0.3], 0.7)
        self._go(["HeadYaw", "HeadPitch"], [ 0.0,  0.2], 0.7)
        self._neutral_head(0.6)

    def sway_gentle(self, intensity=1.0):
        """ごく穏やかに揺れる（静かな待機）。"""
        amp = min(0.055, 0.042 * max(0.1, intensity))
        arm = amp * 0.50
        j   = ["HipRoll", "LShoulderPitch", "RShoulderPitch"]
        for _ in range(3):
            self._go(j, [ amp, 1.40 + arm, 1.40 - arm], 1.4)
            self._go(j, [-amp, 1.40 - arm, 1.40 + arm], 1.4)
        self._go(j, [0.0, 1.40, 1.40], 1.0)
