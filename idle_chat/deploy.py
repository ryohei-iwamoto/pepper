# -*- coding: utf-8 -*-
"""
deploy.py - idle_chat デーモンを Pepper にデプロイ

使い方:
    python deploy.py [PepperIP]

    例:
        python deploy.py 192.168.0.46

動作:
    1. idle_chat_daemon.py と idle_chat_jpj.top を SFTP で転送
    2. autoload.ini を作成（再起動時に自動起動）
    3. 既存デーモンを停止して新しいデーモンを起動

Pepper 側の変更:
    /home/nao/idle_chat_daemon.py    ← デーモン本体
    /home/nao/idle_chat_jpj.top      ← QiChat トピック
    /home/nao/naoqi/autoload.ini     ← 自動起動設定
"""
from __future__ import print_function
import sys
import os
import time

IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.46"

_HERE = os.path.dirname(os.path.abspath(__file__))

TRANSFERS = [
    (os.path.join(_HERE, "idle_chat_daemon.py"), "/home/nao/idle_chat_daemon.py"),
    (os.path.join(_HERE, "idle_chat_jpj.top"),   "/home/nao/idle_chat_jpj.top"),
]

AUTOLOAD_INI = "[python]\n/home/nao/idle_chat_daemon.py\n"


def _sftp_connect(ip):
    try:
        import paramiko
    except ImportError:
        print("エラー: paramiko がインストールされていません。")
        print("  pip install paramiko")
        sys.exit(1)

    transport = paramiko.Transport((ip, 22))
    transport.connect()
    transport.auth_interactive(
        "nao",
        lambda title, instructions, prompts: ["nao" for _ in prompts]
    )
    sftp = paramiko.SFTPClient.from_transport(transport)
    return sftp, transport


def _ssh_exec(ip, cmd):
    try:
        import paramiko
    except ImportError:
        return None, "paramiko not found"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="nao", password="nao",
                   look_for_keys=False, allow_agent=False)
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    client.close()
    return out, err


def main():
    print("=" * 50)
    print("  idle_chat デプロイ")
    print("  Pepper: {0}".format(IP))
    print("=" * 50)

    # ---- Step 1: ファイル転送 ----
    print("\n[1] ファイルを転送中...")
    sftp, transport = _sftp_connect(IP)
    try:
        for local, remote in TRANSFERS:
            sftp.put(local, remote)
            print("  転送: {0}".format(remote))

        # autoload.ini を作成
        try:
            sftp.mkdir("/home/nao/naoqi")
        except IOError:
            pass  # 既に存在する場合

        with sftp.open("/home/nao/naoqi/autoload.ini", "w") as f:
            f.write(AUTOLOAD_INI)
        print("  作成: /home/nao/naoqi/autoload.ini")
    finally:
        sftp.close()
        transport.close()

    # ---- Step 2: デーモン再起動 ----
    print("\n[2] デーモンを再起動中...")
    stop_cmd = "pkill -f idle_chat_daemon.py; sleep 1"
    _ssh_exec(IP, stop_cmd)
    print("  停止完了")

    start_cmd = (
        'bash -c "nohup python -u /home/nao/idle_chat_daemon.py'
        ' > /home/nao/idle_chat.log 2>&1 &"'
    )
    _ssh_exec(IP, start_cmd)
    print("  起動コマンド送信")

    # ---- Step 3: 起動確認 ----
    print("\n[3] 起動確認中（30秒待機）...")
    time.sleep(30)
    out, _ = _ssh_exec(IP, "tail -10 /home/nao/idle_chat.log")
    if out:
        print("  ログ (最新10行):")
        for line in out.strip().splitlines():
            print("    " + line)

    if "[init] デーモン初期化完了" in out or "idle_chat" in out:
        print("\nデプロイ成功！Pepper が自発発話を開始します。")
    else:
        print("\n起動確認中... ログを確認してください:")
        print("  ssh nao@{0}".format(IP))
        print("  tail -f /home/nao/idle_chat.log")


if __name__ == "__main__":
    main()
