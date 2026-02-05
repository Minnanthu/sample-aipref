# Trace.jsonl ファイル形式（サンプル: trace.jsonl.example）

このディレクトリには、AIPerfで使用するカスタムプロンプト入力ファイル（`trace.jsonl`）を配置します。

このリポジトリでは、Gitで追跡できるサンプルとして `trace.jsonl.example` を同梱しています。
実際に使う場合は、まずコピーして `trace.jsonl` を作ってください（`trace.jsonl` は `.gitignore` で無視されます）。

```bash
cp prompts/trace.jsonl.example prompts/trace.jsonl
```

## ファイル形式

`trace.jsonl` は、1行1JSONの形式（JSONL）で、各行が1つのリクエスト（= 1 turn）を表します。

このリポジトリの `scripts/run_aiperf_profile.sh` は `--custom-dataset-type single_turn` を使用するため、
`trace.jsonl` は AIPerf の **SingleTurn** スキーマに従う必要があります。

### スキーマ（SingleTurn）

各行のJSONは、少なくとも1つのモダリティ（`text`/`texts`/`image`/`images`/`audio`/`audios` のいずれか）を含む必要があります。
テキストのみの最小例は以下です：

```json
{"text": "Your prompt here"}
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
{"role":"user","text":"Hello, how are you?"}
{"role":"user","text":"What is 2+2?"}
{"role":"user","text":"Tell me a joke."}
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
