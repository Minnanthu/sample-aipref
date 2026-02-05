# Trace.jsonl ファイル形式（サンプル: trace.jsonl.example / trace_multi_turn.jsonl.example）

このディレクトリには、AIPerfで使用するカスタムプロンプト入力ファイル（`trace.jsonl`）を配置します。

このリポジトリでは、Gitで追跡できるサンプルとして以下を同梱しています。

- `trace.jsonl.example`（SingleTurn）
- `trace_multi_turn.jsonl.example`（MultiTurn）

実際に使う場合は、まずコピーしてローカル用の `.jsonl` を作ってください（`.gitignore` により `trace.jsonl` などは無視されます）。

```bash
cp prompts/trace.jsonl.example prompts/trace.jsonl
cp prompts/trace_multi_turn.jsonl.example prompts/trace_multi_turn.jsonl
```

## ファイル形式

JSONL は、**1行＝1JSON** の形式です。  
ただし、1行が「1 turn」なのか「1セッション（複数turn）」なのかは `CUSTOM_DATASET_TYPE` によって変わります。  
**同じファイルに SingleTurn と MultiTurn を混在させるとバリデーションエラーになります。**

### スキーマ（SingleTurn: `CUSTOM_DATASET_TYPE=single_turn`）

各行のJSONは、少なくとも1つのモダリティ（`text`/`texts`/`image`/`images`/`audio`/`audios` のいずれか）を含む必要があります。  
なお、OpenAI API では `messages[*].name` が **空文字だと 400** になるため、このリポジトリのサンプルでは `texts`（`name` 付き）を推奨します。

テキストのみの最小例は以下です：

```json
{"text": "Your prompt here"}
```

OpenAI API向けの推奨例（`name` 付き）：

```json
{"role":"user","texts":[{"name":"prompt","contents":["Your prompt here"]}]}
```

`role`（任意）を付けることもできます（通常は `"user"`）：

```json
{"role": "user", "text": "Your prompt here"}
```

### フィールド説明（主要）

- `text`: 単一のテキスト入力（最も簡単）
- `texts`: 複数のテキスト入力（クライアント側バッチ）
- `role`: 任意。turnのrole（例: `"user"`）

### 使用例

```jsonl
{"role":"user","texts":[{"name":"prompt","contents":["Hello, how are you?"]}]}
{"role":"user","texts":[{"name":"prompt","contents":["What is 2+2?"]}]}
{"role":"user","texts":[{"name":"prompt","contents":["Tell me a joke."]}]}
```

### 使用方法

1. カスタムプロンプトファイルを作成（例: `my_prompts.jsonl`）
2. `.env` ファイルで `INPUT_FILE` を設定：
   ```
   INPUT_FILE=prompts/my_prompts.jsonl
   ```
   `CUSTOM_DATASET_TYPE` もファイルに合わせて設定します：
   ```
   # SingleTurn（1行=1turn）
   CUSTOM_DATASET_TYPE=single_turn
   # MultiTurn（1行=1セッション）
   # CUSTOM_DATASET_TYPE=multi_turn
   ```
3. `make profile` を実行

### スキーマ（MultiTurn: `CUSTOM_DATASET_TYPE=multi_turn`）

MultiTurn は **1行＝1セッション（会話）**で、`turns` に複数の turn（SingleTurn）を入れます。  
最小例は以下です：

```json
{"session_id":"s1","turns":[{"role":"user","texts":[{"name":"prompt","contents":["Hello"]}]},{"role":"assistant","texts":[{"name":"prompt","contents":["Hi!"]}]}]}
```

### 注意事項

- AIPerfの `--custom-dataset-type`（このリポジトリでは `.env` の `CUSTOM_DATASET_TYPE`）と組み合わせて使用します
- ファイルはUTF-8エンコーディングで保存してください
- 各行は有効なJSONである必要があります（末尾のカンマは不可）
- `INPUT_FILE` が設定されている場合、synthetic mode（`--synthetic-input-tokens-mean` など）は無視されます

### 参考

AIPerfの公式ドキュメントやソースコードを参照して、より詳細なスキーマ要件を確認してください。
実際のAIPerfのバージョンによって、スキーマが異なる可能性があります。
