# Pepper Kit

Pepper ロボット用の GPT 会話システム + 自発発話デーモン。

## 構成

```
pepper-kit/
├── chat_gpt.py          # GPT × Pepper 会話（Python 3、エントリーポイント）
├── pepper_runner.py     # NAOqi ソケットサーバー（Python 2.7）
├── pepper_lib/          # Pepper 制御ライブラリ（Python 2.7）
└── idle_chat/
    ├── idle_chat_daemon.py   # 自発発話デーモン（Pepper 上で常駐）
    ├── idle_chat_jpj.top     # QiChat 応答ルール
    └── deploy.py             # 新しい Pepper にデプロイするスクリプト
```

## セットアップ

### 1. pynaoqi SDK の配置

SoftBank Robotics から入手した `pynaoqi-python2.7-...` フォルダを
リポジトリ直下に `pynaoqi-sdk/` という名前でリネームして配置する。

```
pepper-kit/
└── pynaoqi-sdk/          ← ここに配置
    ├── naoqi.py
    ├── qi.dll
    └── ...
```

または環境変数で指定することも可能：
```
PYNAOQI_SDK=C:\path\to\pynaoqi-python2.7-2.1.4.13-win32-vs2010
```

### 2. Python 3 依存パッケージのインストール

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. OpenAI API キーの設定

`.env.example` をコピーして `.env` を作成し、API キーを設定する。

```bash
copy .env.example .env
# .env を編集して OPENAI_API_KEY を入力
```

---

## GPT 会話モード

```bash
# Pepper マイクで音声入力
python chat_gpt.py 192.168.0.46

# テキスト入力（マイクなし）
python chat_gpt.py 192.168.0.46 --text

# GPT-4o を使用
python chat_gpt.py --model gpt-4o --text
```

---

## 自発発話デーモンのデプロイ

新しい Pepper に一括デプロイ：

```bash
python idle_chat/deploy.py 192.168.0.46
```

このスクリプトは以下を自動で実行する：
- `idle_chat_daemon.py` と `idle_chat_jpj.top` を SFTP 転送
- `/home/nao/naoqi/autoload.ini` を作成（再起動後も自動起動）
- デーモンを起動

デプロイ後は Pepper が以下を行うようになる：
- 10〜25 秒ごとに自発発話またはアニメーション
- 人が近づくと「ぴろん」と鳴って会話に応答
- 顔を登録した人には名前で挨拶
- `chat_gpt.py` 実行中は自発発話を自動停止

---

## 接続情報デフォルト

| 項目 | 値 |
|------|-----|
| Pepper IP | `192.168.0.46` |
| NAOqi ポート | `9559` |
| SSH ユーザー | `nao` |
| SSH パスワード | `nao` |
