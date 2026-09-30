# 状態を持つ会話の第1段階

Python 3.7以上。追加依存なし。PepperのPython 2.7側には変更なし。

## 責務

- conversation_state: 相手の感情推定、自分のvalence（-1〜1）/arousal（0〜1）、
  出来事による更新、時間減衰、明示的な長期記憶。ロボット・LLMに依存しない。
- chat_gpt.py: セッションごとに状態を1つ作り、入力を観測して現在状態を
  一時的なsystem messageとして渡す。historyのuser/assistantと元のsystemは従来通り。
- pepper_expression.py: 既存speech/emotion/action/gazeを維持し、
  intensityだけを内部arousalによる上限とPepperの範囲に収める。
  LLMのemotionはそのターンの表現であり、内部状態へ書き戻さない。
- pepper_runner.py / pepper_lib: 従来の動作実行。

## 更新と時間

Eventのdelta × importance × confidenceを連続状態へ加算し、範囲に収める。
相手の感情からは弱い共感イベントを生成する。相手が怒っていても
自分の怒りをコピーする仕組みではない。外部出来事にもapply_event(Event(...))で対応できる。

時間はmonotonic clock。自分の状態は180秒の半減期でvalence=0/arousal=0.2へ戻り、
相手推定の確信度は90秒の半減期で下がる。confidenceが0.1未満ならunknown。
更新・snapshot・プロンプト生成時に経過時間を反映するため、常駐タイマーは不要。
時計・推定器は注入できる。APIエラーでも観測済み状態は保持する。

## 短期と長期

直近イベントは12件の上限付き。会話履歴とは別管理で、本文を複製しない。
長期記憶はremember(key, fact)/forget(key)で明示的に管理し、自動昇格しない。
最大50件・1件500文字。記憶はsystemの命令として扱わず、参考データとして渡す。
この段階ではすべてセッション内メモリのみ。再起動を越える永続化、ユーザー識別、
同意管理、検索/RAG、履歴圧縮は未実装。

## 利用と検証

```python
from conversation_state import ConversationState, Event

state = ConversationState()
state.observe_user("今日は嬉しいことがあった")
state.apply_event(Event("received_praise", valence_delta=0.4, importance=0.8))
messages = [state.prompt_message()]  # 別のチャットUIでも再利用可能
print(state.snapshot())
```

```bash
python -m unittest discover -s tests -v
```

PepperやOpenAIへ接続せず、注入時計とfake APIでテストする。
既存call_gpt(client, model, history, text)も利用可能（従来動作）。
第5引数にConversationStateを渡すと状態管理が有効になる。mainでは標準で有効。

ルール推定は日本語の少数の語句と簡単な否定を扱う初期版。
皮肉・引用・複雑な否定・多言語・音声感情は扱えず、推定は断定しない。
今後はestimate(text)からUserEstimateを返す推定器へ差し替えられる。
推定器がLLMでも内部状態の更新則・減衰・上限はこの層が管理する。
動作名・視線・表現ラベルは引き続きLLMが選び、ロボットの表現と会話状態を分離する。

APIは20秒timeout・リトライなし。worker完了まで次のターンを開始せず、
古いworkerによるhistoryの同時変更を防ぐ。timeoutはSDKの通信設定であり
厳密な会話全体のwall-clock制限ではない。
