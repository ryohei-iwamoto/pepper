# -*- coding: utf-8 -*-
"""
build_and_install.py  -  顔登録アプリを .pkg にしてPepperにインストール

使い方:
    py -2.7 apps/face_reg/build_and_install.py [PepperIP]

動作:
    1. face_reg/ を ZIP -> face_reg.pkg に圧縮
    2. SFTP で Pepper の /home/nao/ に転送
    3. PackageManager.install() でインストール
"""
from __future__ import print_function
import sys, os, zipfile, io, time

if sys.platform == 'win32':
    sys.stdout = io.open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

IP   = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.46"
PORT = 9559

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SDK_PATH = (
    os.environ.get("PYNAOQI_SDK")
    or os.path.join(_REPO_ROOT, "pynaoqi-sdk")
    or r"D:\D_Playprograming\pepper\pynaoqi-python2.7-2.1.4.13-win32-vs2010 (1)\pynaoqi-python2.7-2.1.4.13-win32-vs2010"
)
sys.path.insert(0, SDK_PATH)

_HERE      = os.path.dirname(os.path.abspath(__file__))
PKG_LOCAL  = os.path.join(_HERE, "face_reg.pkg")
PKG_REMOTE = "/home/nao/face_reg.pkg"


def build_pkg():
    u"""face_reg/ ディレクトリを ZIP (.pkg) に固める"""
    with zipfile.ZipFile(PKG_LOCAL, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root_dir, dirs, files in os.walk(_HERE):
            for fname in files:
                if fname == "build_and_install.py" or fname.endswith(".pkg"):
                    continue
                fpath = os.path.join(root_dir, fname)
                arcname = os.path.relpath(fpath, _HERE)
                arcname = arcname.replace("\\", "/")
                zf.write(fpath, arcname)
                print(u"  追加: " + arcname.decode('utf-8') if isinstance(arcname, bytes) else u"  追加: " + arcname)
    print(u"[build] 完了: " + PKG_LOCAL.decode('utf-8') if isinstance(PKG_LOCAL, bytes) else u"[build] 完了: " + PKG_LOCAL)


def transfer_pkg():
    u"""SFTP で Pepper に転送"""
    import paramiko

    transport = paramiko.Transport((IP, 22))
    transport.connect()

    def handler(title, instructions, prompts):
        return ['nao' for _ in prompts]

    transport.auth_interactive('nao', handler)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.put(PKG_LOCAL, PKG_REMOTE)
    sftp.close()
    transport.close()
    print(u"[transfer] OK: " + PKG_REMOTE)


def install_pkg():
    u"""PackageManager.install() でインストール"""
    from naoqi import ALProxy
    pm = ALProxy("PackageManager", IP, PORT)
    result = pm.install(PKG_REMOTE)
    if result:
        print(u"[install] 成功！")
        print(u"")
        print(u"ランチャーに「顔登録」アプリが追加されました。")
        print(u"タブレットのホームボタンから起動できます。")
    else:
        print(u"[install] 失敗。ログを確認してください。")
    return result


def main():
    print(u"=== 顔登録アプリ ビルド & インストール ===")
    print(u"Pepper: {0}:{1}".format(IP, PORT))
    print(u"")

    print(u"[1] パッケージをビルド中...")
    build_pkg()
    print(u"")

    print(u"[2] Pepper に転送中...")
    try:
        transfer_pkg()
    except Exception as e:
        print(u"[transfer] エラー: {0}".format(e))
        print(u"paramiko がインストールされているか確認: pip install paramiko")
        sys.exit(1)
    print(u"")

    print(u"[3] インストール中...")
    try:
        install_pkg()
    except Exception as e:
        print(u"[install] エラー: {0}".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
