# -*- coding: utf-8 -*-
"""
behaviors/physical_ai.py - フィジカルAI メインループ

Pepper を Claude/GPT API と繋いでフィジカルAIを実現するテンプレート。

アーキテクチャ:
    [人間の声] → Whisper（音声認識）
        → Claude/GPT（思考・返答生成）
            → Pepper（感情表現・発話・動作）

Python 2.7 + NAOqi 制御部分のみここに記述。
AI API呼び出しは PC 側（Python 3）のプロセスで行い、
ソケット経由で受け取る想定。

プロトコル:
    受信: "@テキスト"  → 発話
          "$感情名"     → 感情表現
          "$感情名:テキスト" → 感情表現 + 発話
          "-"           → 終了

使い方:
    python physical_ai.py [IP] [SERVER_IP] [SERVER_PORT]
"""
from __future__ import print_function
import sys
import os
import socket
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pepper_lib import Pepper

PEPPER_IP    = "192.168.0.46"
PEPPER_PORT  = 9559
SERVER_HOST  = "127.0.0.1"
SERVER_PORT  = 12000
BUFF_SIZE    = 4096


def parse_command(raw):
    """
    コマンド文字列をパースして (type, payload) を返す。

    Returns:
        ("speech",  text)          → 発話
        ("emotion", (name, text))  → 感情表現 (text は None の場合あり)
        ("quit",    None)          → 終了
        ("unknown", raw)           → 不明
    """
    if not raw:
        return ("unknown", raw)

    if raw == "-":
        return ("quit", None)

    prefix = raw[0]
    rest   = raw[1:]

    if prefix == "@":
        return ("speech", rest)

    if prefix == "$":
        if ":" in rest:
            parts = rest.split(":", 1)
            return ("emotion", (parts[0].strip(), parts[1].strip()))
        else:
            return ("emotion", (rest.strip(), None))

    # プレフィックスなし → そのまま発話
    return ("speech", raw)


def run_physical_ai(ip=PEPPER_IP, port=PEPPER_PORT,
                    server_host=SERVER_HOST, server_port=SERVER_PORT):
    """フィジカルAI メインループ。"""

    print("=" * 50)
    print("  フィジカルAI 起動中...")
    print("=" * 50)

    # Pepper 初期化
    pp = Pepper(ip, port)
    pp.emotion("excited", "フィジカルAIモードを開始します！")

    # サーバー接続
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_host, server_port))
        sock.sendall(b"PepperPhysicalAI")
        print("AIサーバーに接続しました: {}:{}".format(server_host, server_port))
        pp.say("AIサーバーに接続しました。")
    except Exception as e:
        print("サーバー接続失敗: {}".format(e))
        pp.say("サーバーに接続できませんでした。スタンドアロンモードで起動します。")
        _standalone_mode(pp)
        return

    # メインループ
    try:
        while True:
            data = sock.recv(BUFF_SIZE)
            if not data:
                print("サーバー切断。")
                break

            text = data.decode("utf-8", "ignore").strip()
            print("受信: {!r}".format(text))

            cmd_type, payload = parse_command(text)

            if cmd_type == "quit":
                print("終了コマンド受信。")
                break

            elif cmd_type == "speech":
                pp.say(payload, animated=True)

            elif cmd_type == "emotion":
                emotion_name, emotion_text = payload
                pp.emotion(emotion_name, emotion_text)

            else:
                print("不明なコマンド: {!r}".format(text))

            # 完了通知
            sock.sendall(b"!")

    except KeyboardInterrupt:
        print("\n手動終了。")

    finally:
        sock.close()
        pp.emotion("grateful", "お疲れ様でした！またお話しましょう。")
        pp.wave("R")
        pp.stand()
        print("終了しました。")


def _standalone_mode(pp):
    """
    サーバーなしで動くデモモード。
    コンソールからテキスト入力して動作確認できる。
    """
    pp.say("スタンドアロンモードです。コマンドを入力してください。")
    print("\nコマンド形式:")
    print("  @テキスト          → 発話")
    print("  $感情名             → 感情表現")
    print("  $感情名:テキスト    → 感情表現+発話")
    print("  quit               → 終了\n")

    while True:
        try:
            try:
                raw = raw_input("コマンド> ").decode("utf-8")
            except NameError:
                raw = input("コマンド> ")

            raw = raw.strip()
            if not raw:
                continue

            if raw.lower() in ("quit", "exit", "q"):
                break

            cmd_type, payload = parse_command(raw)

            if cmd_type == "speech":
                pp.say(payload, animated=True)
            elif cmd_type == "emotion":
                name, text = payload
                pp.emotion(name, text)
            else:
                print("不明なコマンド")

        except KeyboardInterrupt:
            break

    pp.say("さようなら！")
    pp.stand()


if __name__ == "__main__":
    ip          = sys.argv[1] if len(sys.argv) > 1 else PEPPER_IP
    server_host = sys.argv[2] if len(sys.argv) > 2 else SERVER_HOST
    server_port = int(sys.argv[3]) if len(sys.argv) > 3 else SERVER_PORT

    run_physical_ai(ip, PEPPER_PORT, server_host, server_port)
