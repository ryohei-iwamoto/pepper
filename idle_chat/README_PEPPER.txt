================================================================
  Pepper カスタマイズ ドキュメント
  作成: 2026-05-04
  対象ロボット: pepper (192.168.0.46)
  OS: NAOqi / Linux 4.0.4 (Intel Atom E3845)
================================================================

----------------------------------------------------------------
1. このドキュメントについて
----------------------------------------------------------------

このファイルは /home/nao/ に追加されたファイルと設定変更の
記録です。元の状態に戻したい場合の手順も記載しています。

----------------------------------------------------------------
2. 追加・変更したファイル一覧
----------------------------------------------------------------

【追加したファイル】

  /home/nao/idle_chat_daemon.py
    - 自発発話デーモン（メインプログラム）
    - NAOqi 起動時に autoload.ini 経由で自動起動される
    - Python 2.7 / qi フレームワーク使用

  /home/nao/idle_chat_jpj.top
    - ALDialog 用 QiChat トピックファイル（日本語）
    - u:() ルール: 話しかけたときの応答 40種類以上
    - daemon 起動時に ALDialog にロードされる

  /home/nao/idle_chat.log
    - daemon の動作ログ（起動のたびに上書きまたは追記）

  /home/nao/idle_chat_autostart.py
    - 旧版のセットアップスクリプト（現在は未使用）

  /home/nao/hello_world.py
    - テスト用スクリプト（削除可）

【変更したファイル】

  /home/nao/naoqi/autoload.ini  ← 新規作成（元はファイルなし）
    変更前: ファイルが存在しなかった
    変更後:
      [python]
      /home/nao/idle_chat_daemon.py

【インストールしたアプリ（PackageManager）】

  face-reg-pepper
    - 顔登録アプリ（タブレット UI）
    - ランチャーから「顔登録」で起動
    - ALFaceCharacteristics.learnFace() で顔データを登録
    - 登録した顔はデーモンが「○○さん！」と名前で呼ぶ

【変更していないもの】

  - /opt/aldebaran/ 以下のシステムファイル（一切変更なし）
  - animations/Stand/ などのビルトインビヘイビア（変更なし）
  - SoftBank デフォルトアプリ（全て残存）:
      dance-pepper, janken-pepper, jikoshoukai-pepper,
      momotaro-pepper, ohayou-pepper, ouen-pepper,
      oyasumi-pepper, quiz-pepper, taisou-pepper,
      tenki-pepper, uranai-pepper, youtube-pepper 等

----------------------------------------------------------------
3. idle_chat_daemon.py の動作概要
----------------------------------------------------------------

  起動シーケンス:
    1. ALMotion.wakeUp()
    2. ALBackgroundMovement 有効化（ホーム画面と同じ自然な揺れ）
    3. ALListeningMovement 有効化
    4. ALAutonomousLife を "interactive" に設定
    5. ALBasicAwareness を "FullyEngaged" + "WholeBody" に設定
       → 人が近づくと「ぴろん」と鳴り、話しかけると応答
       → WholeBody: 車輪で体ごと人の方向を向く
    6. ALFaceDetection 購読（顔認識で名前付き挨拶）
    7. ALDialog トピックロード（u:() 応答ルール）
    8. メインループ開始

  メインループ（10〜25秒ごとに実行）:
    - 確率40%: IDLE_PHRASES からランダムに発話
    - 確率20%: 車輪で小さく回転・移動
    - 確率40%: 無言アニメーション（Waiting/ 系）
    ※ ユーザーアプリ実行中はすべてスキップ

  30秒ごとの設定維持:
    - ALAutonomousLife が interactive から外れたら再設定
    - ALBasicAwareness が停止したら再起動
    ※ ユーザーアプリ実行中はスキップ

  顔認識挨拶:
    - 未登録: 「こんにちは！」等からランダム
    - 登録済み: 「○○さん！また会えたね！」等
    - クールダウン: 同一人物へは30秒間隔

  ぴろん（会話応答）の仕組み:
    ALBasicAwareness FullyEngaged →
    人を検知 → ALDialog が「ぴろん」を鳴らす →
    ユーザーが話す → idle_chat_jpj.top の u:() にマッチ →
    Pepper が返答

----------------------------------------------------------------
4. 手動操作コマンド
----------------------------------------------------------------

  【daemon の手動起動】
    nohup python -u /home/nao/idle_chat_daemon.py > /home/nao/idle_chat.log 2>&1 &

  【daemon の停止】
    pkill -f idle_chat_daemon.py

  【ログ確認】
    tail -f /home/nao/idle_chat.log

  【dialog トピックの確認】
    python -c "
    import sys; sys.path.insert(0, '/opt/aldebaran/lib/python2.7/site-packages')
    import qi
    app = qi.Application(['test', '--qi-url=tcp://127.0.0.1:9559'])
    app.start()
    d = app.session.service('ALDialog')
    print(d.getAllLoadedTopics())
    "

  【顔登録一覧確認】
    python -c "
    import sys; sys.path.insert(0, '/opt/aldebaran/lib/python2.7/site-packages')
    import qi
    app = qi.Application(['test', '--qi-url=tcp://127.0.0.1:9559'])
    app.start()
    fc = app.session.service('ALFaceCharacteristics')
    print(fc.getPeopleList())
    "

----------------------------------------------------------------
5. 元の状態に戻す手順
----------------------------------------------------------------

  ステップ1: daemon の自動起動を無効化
    rm /home/nao/naoqi/autoload.ini
    # または中身を空にする

  ステップ2: 追加ファイルを削除
    rm /home/nao/idle_chat_daemon.py
    rm /home/nao/idle_chat_jpj.top
    rm /home/nao/idle_chat.log
    rm /home/nao/idle_chat_autostart.py
    rm /home/nao/hello_world.py

  ステップ3: 顔登録アプリを削除（PC から実行）
    python -c "
    import sys
    sys.path.insert(0, r'D:\...\pynaoqi-python2.7-...')
    from naoqi import ALProxy
    pm = ALProxy('PackageManager', '192.168.0.46', 9559)
    pm.removePkg('face-reg-pepper')
    "

  ステップ4: ALAutonomousLife を元の状態に戻す
    python -c "
    import sys; sys.path.insert(0, '/opt/aldebaran/lib/python2.7/site-packages')
    import qi
    app = qi.Application(['test', '--qi-url=tcp://127.0.0.1:9559'])
    app.start()
    al = app.session.service('ALAutonomousLife')
    al.setState('solitary')
    "

  ステップ5: 再起動
    (Pepper の電源ボタンを長押しして再起動)

  以上で完全に元の状態に戻ります。

----------------------------------------------------------------
6. トラブルシューティング
----------------------------------------------------------------

  【daemon が起動しない】
    - autoload.ini のパスが正しいか確認
    - python -m py_compile /home/nao/idle_chat_daemon.py で構文確認
    - tail /home/nao/idle_chat.log でエラー確認

  【ぴろんが鳴らない】
    - ALBasicAwareness が動いているか確認:
      python -c "import sys; sys.path.insert(0, '/opt/aldebaran/lib/python2.7/site-packages')
      import qi; app=qi.Application(['t','--qi-url=tcp://127.0.0.1:9559']); app.start()
      aw=app.session.service('ALBasicAwareness')
      print(aw.isAwarenessRunning(), aw.getEngagementMode())"
    - daemon を再起動すると自動で FullyEngaged + startAwareness される

  【話しかけても応答しない】
    - ALAutonomousLife が interactive か確認
    - idle_chat_jpj.top が /home/nao/ にあるか確認
    - ALDialog に idle_chat トピックがロードされているか確認

  【アプリ実行中に daemon が喋る】
    - _is_user_app_running() が正しくアプリを検出できていない可能性
    - getRunningBehaviors() の出力を確認する

----------------------------------------------------------------
7. PC 側の開発ファイル
----------------------------------------------------------------

  d:\D_Playprograming\pepper\idle_chat\
    idle_chat_daemon.py     (このファイルのソース)
    idle_chat_jpj.top       (dialog トピックのソース)
    install_and_run.py      (dialog トピックを手動でロードするスクリプト)
    autostart_setup.py      (旧版セットアップスクリプト)
    learn_face.py           (コマンドラインで顔登録するスクリプト)

  d:\D_Playprograming\pepper\apps\face_reg\
    html\index.html         (顔登録タブレット UI)
    manifest.xml            (アプリのメタ情報)
    behavior.xar            (アプリ起動ビヘイビア)
    build_and_install.py    (ビルド & インストールスクリプト)

  d:\D_Playprograming\pepper\KNOWHOW.md
    開発で得た知見・ハマりポイントまとめ

================================================================
