# KVキャッシュ回避（prefix/prompt cache対策）ガイド

このドキュメントは、ベンチマーク時に **KVキャッシュが結果を“良く見せてしまう”**のを避けるための考え方と対策をまとめたものです。

## まず整理：どの「キャッシュ」を避けたい？

KVキャッシュには、混同されがちな2種類があります。

- **リクエスト内KV cache（通常のKV cache）**
  - 1つのリクエストの生成（デコード）中に使うキャッシュです。
  - これを無効化すると挙動や性能が別物になりやすく、**多くの推論サーバでは非推奨/不可**です。
- **リクエスト間 prefix/prompt cache（prefix cache）**
  - 複数リクエストで「同じプロンプト先頭（prefix）」が繰り返されると、先頭部分の計算を再利用できるタイプのキャッシュです。
  - ベンチマーク結果（特にTTFT）を歪めやすく、一般に「KVキャッシュ回避」と言うと **こちらを避けたいケース**が多いです。

このリポジトリで主に想定する「回避」は **prefix/prompt cacheを効かせない**ことです。

## prefix/prompt cacheが効いていそうな兆候

- **warmup後だけ** TTFT/スループットが不自然に良くなる
- リクエストを繰り返すと **TTFTがどんどん短くなる**
- 同じ入力（または同じ先頭prefix）を使った実験でのみ改善が出る

## 対策（優先度順）

### 1) サーバ側で prefix/prompt cache を無効化（最優先）

推論サーバ（OpenAI互換サーバ実装）によっては、prefix/prompt cache の無効化フラグや設定があります。

- **最も確実**で、ベンチの意図（“キャッシュ無しの素の性能”）を守りやすいです。
- 設定方法やパラメータ名は **サーバ実装ごとに異なる**ため、ここでは概念として覚えておくのが目的です。

このリポジトリでは `.env` の `EXTRA_INPUTS` を使って、AIPerf の `--extra-inputs key:val` を複数渡せます（サーバが対応していれば有効）。

```bash
# .env の例（キー名はサーバ依存）
EXTRA_INPUTS=disable_prompt_cache:true,enable_prefix_caching:false
```

### 2) 各リクエストの「先頭」を毎回変える（確実にキャッシュミスさせる）

prefix cache は「先頭の一致」に反応することが多いので、**リクエストごとに先頭へ nonce（乱数/UUID/時刻）**を付けると回避できます。

このリポジトリでは `INPUT_FILE` モード（JSONL）で実施するのが簡単です。

#### 手順

1. サンプルをコピーして入力ファイルを作る

```bash
cp prompts/trace.jsonl.example prompts/trace.jsonl
```

2. `prompts/trace.jsonl` の各行の先頭にnonceを入れる（例）

```jsonl
{"role":"user","text":"nonce:2026-02-05T10:12:01Z-0001\nWhat is the capital of Japan?"}
{"role":"user","text":"nonce:2026-02-05T10:12:01Z-0002\nExplain quantum computing in simple terms."}
```

3. `.env` で `INPUT_FILE` を指定して実行

```bash
# .env
INPUT_FILE=prompts/trace.jsonl
```

> ポイント: nonce は「末尾」ではなく **先頭（prefixに含まれる位置）**に入れるほうが確実です。

### 3) warmup と本番の間でキャッシュをクリア

warmup → 本番の流れだと、本番が「温まったキャッシュ込み」になってしまうことがあります。

- 可能なら **本番直前にサーバ再起動**（またはキャッシュクリア手段）を行う
- 実験目的が「実運用のホット状態」なら warmup を含めて良いが、その場合は **条件として明記**する

## このリポジトリでの実行メモ

- `INPUT_FILE` が未設定/存在しない場合は **Synthetic mode** になり、入力内容が固定/類似になりやすいです。
  - prefix cache が疑わしいときは、まず **`INPUT_FILE` + nonce** を試すのが分かりやすいです。
- サーバが追加パラメータでキャッシュ制御に対応しているなら、`.env` の `EXTRA_INPUTS` で渡せます。

## 注意（重要）

- **通常のKV cache（リクエスト内）を完全に無効化**すると、推論の前提が変わり、比較が難しくなることがあります。
- ここでの「KVキャッシュ回避」は、まず **リクエスト間のprefix/prompt cacheを避ける**方向で考えるのがおすすめです。

