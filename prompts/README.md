# Trace.jsonl ファイル形式（サンプル: trace.jsonl.example）

このディレクトリには、AIPerfで使用するカスタムプロンプト入力ファイル（`trace.jsonl`）を配置します。

このリポジトリでは、Gitで追跡できるサンプルとして `trace.jsonl.example` を同梱しています。
実際に使う場合は、まずコピーして `trace.jsonl` を作ってください（`trace.jsonl` は `.gitignore` で無視されます）。

```bash
cp prompts/trace.jsonl.example prompts/trace.jsonl
```

## ファイル形式

`trace.jsonl` は、1行1JSONの形式（JSONL）で、各行が1つのリクエストを表します。

### スキーマ

各JSONオブジェクトは、OpenAI互換のchat completionsリクエストの `messages` フィールドを含む必要があります：

```json
{
  "messages": [
    {"role": "user", "content": "Your prompt here"}
  ]
}
```

### フィールド説明

- `messages`: 必須。メッセージの配列
  - `role`: メッセージの役割（`"user"`, `"assistant"`, `"system"` など）
  - `content`: メッセージの内容（文字列）

### 使用例

```jsonl
{"messages": [{"role": "user", "content": "Hello, how are you?"}]}
{"messages": [{"role": "user", "content": "What is 2+2?"}]}
{"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Tell me a joke."}]}
```

### 使用方法

1. カスタムプロンプトファイルを作成（例: `my_prompts.jsonl`）
2. `.env` ファイルで `INPUT_FILE` を設定：
   ```
   INPUT_FILE=prompts/my_prompts.jsonl
   ```
3. `make profile` を実行

### 注意事項

- AIPerfの `--custom-dataset-type single_turn` オプションと組み合わせて使用します
- ファイルはUTF-8エンコーディングで保存してください
- 各行は有効なJSONである必要があります（末尾のカンマは不可）
- `INPUT_FILE` が設定されている場合、synthetic mode（`--synthetic-input-tokens-mean` など）は無視されます

### 参考

AIPerfの公式ドキュメントやソースコードを参照して、より詳細なスキーマ要件を確認してください。
実際のAIPerfのバージョンによって、スキーマが異なる可能性があります。
