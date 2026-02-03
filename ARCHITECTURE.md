# リポジトリ構成・設定・スクリプト解説

## 目次

1. [概要](#概要)
2. [リポジトリ構造](#リポジトリ構造)
3. [環境設定](#環境設定)
4. [ビルドシステム（Makefile）](#ビルドシステムmakefile)
5. [スクリプト詳細](#スクリプト詳細)
6. [Docker構成](#docker構成)
7. [データフローと処理パイプライン](#データフローと処理パイプライン)
8. [実装の重要ポイント](#実装の重要ポイント)
9. [トラブルシューティング](#トラブルシューティング)

---

## 概要

このリポジトリは、NVIDIA AIPerfを使用したOpenAI互換Chat Completions APIのベンチマークプロトタイプです。macOS上でのローカル開発とLinuxサーバでの本番実行の両方をサポートしています。

### 主な特徴

- **OpenAI APIとカスタムサーバの両対応**: 環境変数で簡単に切り替え可能
- **ストリーミング対応**: Chat Completionsのストリーミングレスポンスを測定
- **詳細なメトリクス**: TTFT、Request Latency、Inter-Token Latencyのp50/p95/p99を計算
- **柔軟な入力モード**: Synthetic modeとカスタムプロンプト（trace.jsonl）の両対応
- **Docker対応**: Linux環境への移行が容易

---

## リポジトリ構造

```
sample-aipref/
├── README.md                    # ユーザー向けドキュメント
├── ARCHITECTURE.md             # このファイル（技術ドキュメント）
├── Makefile                    # タスク自動化
├── requirements.txt            # Python依存関係
├── .gitignore                  # Git除外設定
│
├── scripts/                    # 実行スクリプト群
│   ├── run_aiperf_profile.sh  # AIPerfラッパースクリプト（メイン）
│   ├── smoke_stream.py        # 疎通確認スクリプト
│   └── summarize_export.py    # サマリ生成スクリプト
│
├── tests/                      # ユニットテスト
│   ├── __init__.py
│   ├── test_smoke_stream.py   # smoke_stream.pyのテスト
│   └── test_summarize_export.py # summarize_export.pyのテスト
│
├── prompts/                    # カスタムプロンプト
│   ├── trace.jsonl            # サンプルプロンプトファイル
│   └── README.md              # trace.jsonlスキーマドキュメント
│
├── docker/                     # Docker構成
│   ├── Dockerfile             # コンテナイメージ定義
│   ├── docker-compose.yml     # Docker Compose設定
│   └── entrypoint.sh         # コンテナエントリーポイント
│
├── artifacts/                  # ベンチマーク結果（gitignore）
│   └── ISL{INPUT}_OSL{OUTPUT}_CON{CONCURRENCY}/
│       ├── profile_export.jsonl    # メトリクスデータ（JSONL形式）
│       ├── profile_export.json     # メトリクスデータ（JSON形式）
│       ├── benchmark_results.jsonl # ベンチマーク結果
│       └── logs/                   # 実行ログ
│
├── venv/                       # Python仮想環境（gitignore）
├── summary.tsv                 # 生成されたサマリ（gitignore）
└── summary.md                  # 生成されたサマリ（gitignore）
```

### ファイルの役割

| ファイル | 役割 |
|---------|------|
| `README.md` | ユーザー向け使用方法ドキュメント |
| `ARCHITECTURE.md` | 技術ドキュメント（このファイル） |
| `Makefile` | タスク自動化（setup, smoke, warmup, profile, summary） |
| `requirements.txt` | Python依存関係（aiperf, openai, python-dotenv） |
| `.env` | 環境変数設定（ユーザーが作成） |
| `.gitignore` | Git除外設定 |

---

## 環境設定

### 環境変数（.env）

ベンチマーク実行に必要な環境変数を`.env`ファイルで管理します。

#### 必須設定

```bash
# モデル名（必須）
MODEL=gpt-3.5-turbo

# OpenAI APIを使用する場合
OPENAI_API_KEY=sk-your-api-key-here
AIPERF_URL=  # 空またはhttps://api.openai.com/v1

# カスタムOpenAI互換サーバを使用する場合
AIPERF_URL=http://192.168.1.100:8000
OPENAI_API_KEY=  # 認証が必要な場合のみ
```

#### ベンチマークパラメータ

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `CONCURRENCY` | 並行リクエスト数 | `10` |
| `REQUEST_COUNT` | リクエスト総数 | `CONCURRENCY * 3` |
| `INPUT_TOKENS_MEAN` | 入力トークン数の平均 | `100` |
| `INPUT_TOKENS_STDDEV` | 入力トークン数の標準偏差 | `20` |
| `OUTPUT_TOKENS_MEAN` | 出力トークン数の平均 | `200` |
| `REQUEST_TIMEOUT_SECONDS` | リクエストタイムアウト（秒） | `300` |

#### カスタムプロンプト設定

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `INPUT_FILE` | カスタムプロンプトファイル（trace.jsonl形式） | 未設定（synthetic mode） |
| `CUSTOM_DATASET_TYPE` | カスタムデータセットタイプ | `single_turn` |
| `EXTRA_INPUTS` | 追加パラメータ（カンマ区切り） | 未設定 |

**使用例**:
```bash
INPUT_FILE=prompts/trace.jsonl
EXTRA_INPUTS=min_tokens:50,ignore_eos:true
```

#### Tokenizer設定

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `TOKENIZER` | Tokenizer名（HuggingFaceモデル名） | OpenAI API使用時: `gpt2`（自動設定） |

#### macOS固有設定

macOSでのAIPerfサービス登録タイムアウト問題を回避するための設定です。

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `AIPERF_SERVICE_REGISTRATION_TIMEOUT` | サービス登録タイムアウト（秒） | `120.0` |
| `AIPERF_SERVICE_REGISTRATION_INTERVAL` | サービス登録試行間隔（秒） | `2.0` |
| `AIPERF_SERVICE_REGISTRATION_MAX_ATTEMPTS` | サービス登録最大試行回数 | `20` |
| `AIPERF_SERVICE_START_TIMEOUT` | サービス起動タイムアウト（秒） | `60.0` |

**注意**: これらの変数は`AIPERF_SERVICE__REGISTRATION_TIMEOUT`（ダブルアンダースコア）の形式で環境変数にエクスポートされます（pydantic-settingsのネスト設定形式）。

---

## ビルドシステム（Makefile）

### 概要

`Makefile`は、ベンチマーク実行の各ステップを自動化します。`.env`ファイルを条件付きで読み込み、適切なスクリプトを実行します。

### ターゲット一覧

| ターゲット | 説明 | 実行内容 |
|-----------|------|----------|
| `make help` | ヘルプ表示 | 利用可能なターゲット一覧を表示 |
| `make setup` | 環境セットアップ | Python仮想環境の作成と依存関係のインストール |
| `make test` | ユニットテスト | スクリプトの単体テストを実行（27テスト） |
| `make smoke` | 疎通確認 | 1リクエストでストリーミング接続をテスト |
| `make warmup` | Warmup実行 | 軽い負荷（CONCURRENCY=3, REQUEST_COUNT=9）でベンチマーク |
| `make profile` | 本番ベンチマーク | `.env`の設定に基づいてフルベンチマーク |
| `make sweep` | Concurrency Sweep | 複数の並行度（1, 5, 10, 20, 50）でベンチマーク |
| `make summary` | サマリ生成 | 最新のartifactからp50/p95/p99を計算してTSV/MD生成 |

### 環境変数の読み込み

```makefile
ifneq (,$(wildcard .env))
    include .env
    export
endif
```

`.env`ファイルが存在する場合のみ読み込み、すべての変数を自動的にエクスポートします。

### 詳細な実装

#### `make setup`

Python 3.12の仮想環境を優先的に作成します。

**処理内容**:
1. 仮想環境がアクティブでない場合:
   - `venv`ディレクトリが存在する場合は再利用
   - Python 3.12を検出（`python3.12`コマンドまたは`$HOME/.pyenv/versions/3.12.7/bin/python3`）
   - Python 3.12が見つかれば`venv`を作成、見つからない場合はエラー終了
2. 依存関係のインストール:
   - `venv/bin/pip install --upgrade pip`
   - `venv/bin/pip install -r requirements.txt`（aiperf, openai, python-dotenv）

**ポイント**:
- Python 3.12が必須（AIPerf 0.4.0はPython 3.14と非互換）
- `pyenv`でインストールされたPython 3.12.7を自動検出
- 既存の仮想環境がある場合は再利用
- Python 3.12が見つからない場合はエラー終了

#### `make smoke`

疎通確認を実行します。`.env`の存在をチェックし、`scripts/smoke_stream.py`を実行して1リクエストの疎通確認を行います。

#### `make warmup`

軽い負荷でwarmupを実行します。`CONCURRENCY=3`, `REQUEST_COUNT=9`で実行し、Artifactは`artifacts/warmup_ISL{INPUT}_OSL{OUTPUT}_CON{CONCURRENCY}`に保存されます。

#### `make profile`

本番レベルのベンチマークを実行します。`.env`の設定に基づいてフルベンチマークを実行し、Artifactは`artifacts/ISL{INPUT}_OSL{OUTPUT}_CON{CONCURRENCY}`に保存されます。

#### `make sweep`

複数の並行度（1, 5, 10, 20, 50）でベンチマークを順次実行します。各実行のArtifactディレクトリは`artifacts/sweep_{concurrency}_ISL{INPUT}_OSL{OUTPUT}_CON{CONCURRENCY}`に保存されます。

#### `make summary`

最新のartifactディレクトリを自動検出し、`scripts/summarize_export.py`を実行して`summary.tsv`（Slack貼り付け用）と`summary.md`（人間読み用）を生成します。

---

## スクリプト詳細

### 1. `scripts/run_aiperf_profile.sh`

AIPerfの`profile`コマンドを実行するラッパースクリプトです。環境変数を読み込み、適切なコマンドラインオプションを構築します。

#### 処理フロー

1. **`.env`ファイルの読み込み**: `set -a; source .env; set +a`で環境変数を自動エクスポート
2. **必須環境変数のチェック**: `MODEL`が設定されているか確認
3. **OpenAI APIの自動検出**: `AIPERF_URL`が空の場合、`OPENAI_API_KEY`をチェックしてOpenAI APIを使用
4. **デフォルト値の設定**: 各パラメータにデフォルト値を設定（`.env`で上書き可能）
5. **実行モードの判定**: 引数（warmup/profile/sweep_*）に応じてArtifactディレクトリを決定
6. **AIPerfコマンドの構築**: 基本オプション（`-m`, `--endpoint-type chat`, `--streaming`, `--ui-type none`など）を設定
7. **条件付きオプションの追加**:
   - APIキー: `--api-key ${OPENAI_API_KEY}`
   - 入力モード: `--input-file`（カスタムプロンプト）または`--synthetic-input-tokens-mean`（Synthetic mode）
   - Tokenizer: `--tokenizer ${TOKENIZER}`（OpenAI API使用時は`gpt2`を自動設定）
   - macOS固有のタイムアウト設定: `AIPERF_SERVICE__*`環境変数をエクスポート
   - 追加パラメータ: `--extra-inputs`（カンマ区切りで複数指定可能）
8. **コマンド実行**: `eval ${CMD}`でAIPerfを実行

#### 重要なポイント

1. **OpenAI APIの自動検出**: `AIPERF_URL`が空で`OPENAI_API_KEY`が設定されている場合、自動的にOpenAI APIを使用します。

2. **Tokenizerの自動設定**: OpenAI API使用時は、HuggingFaceモデル名が存在しないため、デフォルトで`gpt2`をTokenizerとして使用します。

3. **APIキーの渡し方**: AIPerfは`--api-key`コマンドラインオプションでAPIキーを受け取ります（環境変数だけでは不十分）。

4. **macOS固有の設定**: pydantic-settingsのネスト設定形式（`AIPERF_SERVICE__REGISTRATION_TIMEOUT`）で環境変数をエクスポートします。

5. **柔軟な入力モード**: `INPUT_FILE`が設定されている場合はカスタムプロンプトファイルを使用、そうでない場合はSynthetic modeを使用します。

---

### 2. `scripts/smoke_stream.py`

OpenAI互換APIへのストリーミング接続をテストするPythonスクリプトです。

#### 処理フロー

1. **環境変数の取得**: `.env`から`AIPERF_URL`, `MODEL`, `OPENAI_API_KEY`を読み込み
2. **OpenAI APIの検出**: `AIPERF_URL`が空またはOpenAIのURLの場合、OpenAI SDKのデフォルト設定を使用
3. **クライアントの作成**:
   - OpenAI API使用時: `OpenAI(api_key=api_key)`（`base_url`はデフォルト）
   - カスタムAPI使用時: `OpenAI(base_url=url, api_key=api_key or "dummy-key")`
4. **ストリーミングリクエストの送信**: `chat.completions.create(stream=True, max_tokens=50)`で1リクエスト送信
5. **ストリーミング応答の受信**: 
   - 最初のトークン受信を検出（TTFT確認）
   - トークン数と応答長をカウント
6. **エラーハンドリング**: 接続エラー、認証エラー、モデル名不一致などをキャッチして、トラブルシューティングのヒントを表示

#### 重要なポイント

- **TTFT確認**: 最初のトークン受信を検出して`"✓ First token received (TTFT OK)"`と表示
- **OpenAI API自動検出**: URLが空の場合、自動的にOpenAI APIを使用
- **柔軟な認証**: カスタムAPIで認証不要な場合はダミーキーを使用

---

### 3. `scripts/summarize_export.py`

AIPerfのexport結果からp50/p95/p99を算出してTSVサマリを生成するPythonスクリプトです。

#### 処理フロー

1. **最新のartifactディレクトリを検出**: `artifacts/`から更新時刻でソートして最新のディレクトリを選択
2. **exportファイルの検索**: `profile_export.jsonl`または`profile_export*.json`を探す
3. **データの読み込み**: 
   - JSONL形式: 1行1JSONとして読み込み
   - JSON形式: 配列の場合は展開、単一オブジェクトの場合はそのまま追加
4. **メトリクス値の抽出**: 
   - `metrics.{metric_name}`から値を抽出
   - 辞書形式（`{'value': ..., 'unit': 'ms'}`）の場合は`value`を取得
   - 別名（`ttft`, `latency`, `itl`など）も検索
   - 単位変換（ナノ秒→ms、秒→ms）を実行
5. **パーセンタイルの計算**: p50/p95/p99を線形補間で計算、平均値も算出
6. **エラー数のカウント**: `error`, `status`, `success`フィールドをチェック
7. **TSV出力**: `summary.tsv`（Slack貼り付け用）を生成
8. **Markdown出力**: `summary.md`（人間読み用）を生成

#### 重要なポイント

- **柔軟なメトリクス抽出**: 複数のフィールド名や別名に対応（`time_to_first_token`, `ttft`, `time_to_first_token_ms`など）
- **単位変換のヒューリスティック**:
  - 非常に大きい値（> 1,000,000,000）: ナノ秒 → ms
  - 小さい値（< 1）: 秒 → ms
  - それ以外: ms単位と仮定
- **辞書形式の対応**: AIPerfのexport形式`{'value': ..., 'unit': 'ms'}`から`value`キーを抽出
- **パーセンタイルの線形補間**: 正確なp50/p95/p99を計算

---

## テスト

### 概要

`tests/`ディレクトリに、主要なPythonスクリプトの単体テストが含まれています。pytestフレームワークを使用しています。

### テストファイル

| ファイル | 対象スクリプト | テスト内容 |
|---------|--------------|------------|
| `test_smoke_stream.py` | `smoke_stream.py` | OpenAI API検出、URL正規化、クライアント作成、ストリーミング処理 |
| `test_summarize_export.py` | `summarize_export.py` | メトリクス抽出、単位変換、パーセンタイル計算、エラーカウント |

### テストの実行

```bash
# すべてのテストを実行
make test

# または直接pytestを実行
python -m pytest tests/ -v

# 特定のテストファイルのみ実行
python -m pytest tests/test_summarize_export.py -v

# 特定のテストクラスのみ実行
python -m pytest tests/test_summarize_export.py::TestExtractMetricValues -v
```

### テストカバレッジ

現在、以下の機能がテストされています：

**smoke_stream.py**:
- OpenAI API自動検出ロジック（10テスト）
- URL正規化
- クライアント作成（OpenAI API / カスタムAPI）
- ストリーミングリクエスト構造

**summarize_export.py**:
- メトリクス値の抽出（辞書形式、別名対応）（8テスト）
- 単位変換（秒→ms、ナノ秒→ms、ms単位）
- パーセンタイル計算（p50/p95/p99）（4テスト）
- エラー数のカウント（5テスト）

**合計**: 27テスト

### テスト設定

- **pytest.ini**: pytest設定ファイル
- **requirements.txt**: `pytest>=7.0.0`, `pytest-mock>=3.10.0`を含む

---

## Docker構成

### 1. `docker/Dockerfile`

Python 3.11-slimベースのDockerイメージを定義します。

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY Makefile .
COPY scripts/ ./scripts/
COPY prompts/ ./prompts/
COPY docker/entrypoint.sh /entrypoint.sh

# スクリプトに実行権限を付与
RUN chmod +x scripts/*.sh scripts/*.py /entrypoint.sh

# Artifactsディレクトリの作成
RUN mkdir -p artifacts

# エントリーポイント
ENTRYPOINT ["/entrypoint.sh"]
CMD ["help"]
```

**ポイント**:
- `python:3.11-slim`をベースイメージとして使用
- システムパッケージ: `bash`, `curl`
- Python依存関係を事前にインストール
- スクリプトに実行権限を付与
- `entrypoint.sh`をエントリーポイントとして設定

---

### 2. `docker/docker-compose.yml`

Docker Compose設定で、ボリュームマウントとネットワーク設定を定義します。

```yaml
version: '3.8'

services:
  aiperf-client:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    image: aiperf-client:latest
    volumes:
      # .envファイルをマウント（読み取り専用）
      - ../.env:/app/.env:ro
      # Artifactsディレクトリをマウント（結果をホストに保存）
      - ../artifacts:/app/artifacts
      # Promptsディレクトリをマウント（読み取り専用）
      - ../prompts:/app/prompts:ro
    networks:
      - aiperf-network
    command: ["help"]

networks:
  aiperf-network:
    driver: bridge
```

**ポイント**:
- `.env`ファイルを読み取り専用でマウント
- `artifacts/`ディレクトリをマウント（結果をホストに保存）
- `prompts/`ディレクトリを読み取り専用でマウント
- `aiperf-network`ネットワークを作成

**使用方法**:
```bash
# イメージのビルド
cd docker
docker-compose build

# Smoke test
docker-compose run --rm aiperf-client smoke

# Profile実行
docker-compose run --rm aiperf-client profile

# Summary生成
docker-compose run --rm aiperf-client summary
```

---

### 3. `docker/entrypoint.sh`

Dockerコンテナのエントリーポイントスクリプトです。

**処理内容**:
1. `.env`ファイルの存在をチェック
2. コマンドライン引数に応じて適切なスクリプトを実行:
   - `setup`: 情報表示（依存関係は既にインストール済み）
   - `smoke`: `scripts/smoke_stream.py`を実行
   - `warmup`: `scripts/run_aiperf_profile.sh warmup`を実行
   - `profile`: `scripts/run_aiperf_profile.sh profile`を実行
   - `summary`: `scripts/summarize_export.py`を実行
   - `sweep`: Concurrency sweep実行後に`summarize_export.py`を実行
   - その他: ヘルプを表示

**ポイント**:
- コマンドライン引数で動作を切り替え
- `.env`ファイルのマウントが必須
- `Makefile`のターゲットと同じコマンド名を使用

---

## データフローと処理パイプライン

### ベンチマーク実行フロー

```
┌─────────────────────────────────────────────────────────────┐
│                     make setup                              │
│  - Python仮想環境の作成（venv、Python 3.12必須）            │
│  - 依存関係のインストール（aiperf, openai, python-dotenv）  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     make smoke                              │
│  - scripts/smoke_stream.py                                  │
│  - 1リクエストでストリーミング接続をテスト                  │
│  - TTFT確認、エラーハンドリング                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    make warmup                              │
│  - scripts/run_aiperf_profile.sh warmup                     │
│  - 軽い負荷（CONCURRENCY=3, REQUEST_COUNT=9）               │
│  - artifacts/warmup_ISL{INPUT}_OSL{OUTPUT}_CON{CONCURRENCY} │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    make profile                             │
│  - scripts/run_aiperf_profile.sh profile                    │
│  - フルベンチマーク（.envの設定に基づく）                   │
│  - artifacts/ISL{INPUT}_OSL{OUTPUT}_CON{CONCURRENCY}        │
│    ├── profile_export.jsonl                                 │
│    ├── profile_export.json                                  │
│    ├── benchmark_results.jsonl                              │
│    └── logs/                                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    make summary                             │
│  - scripts/summarize_export.py                              │
│  - 最新のartifactディレクトリを自動検出                     │
│  - profile_export.jsonlからメトリクス抽出                   │
│  - p50/p95/p99を計算                                        │
│  - summary.tsv（Slack貼り付け用）                           │
│  - summary.md（人間読み用）                                 │
└─────────────────────────────────────────────────────────────┘
```

### AIPerfコマンド構築フロー

```
.env ファイル
    ↓
┌─────────────────────────────────────────────────┐
│ scripts/run_aiperf_profile.sh                   │
│                                                 │
│ 1. .envファイルの読み込み                       │
│    └─ set -a; source .env; set +a              │
│                                                 │
│ 2. 必須環境変数のチェック                       │
│    └─ MODEL                                     │
│                                                 │
│ 3. OpenAI API自動検出                           │
│    └─ AIPERF_URL が空 → OpenAI API使用         │
│                                                 │
│ 4. デフォルト値の設定                           │
│    └─ CONCURRENCY, REQUEST_COUNT, etc.         │
│                                                 │
│ 5. Artifactディレクトリの決定                   │
│    └─ warmup/profile/sweep_{c} に応じて決定    │
│                                                 │
│ 6. AIPerfコマンドの構築                         │
│    ├─ 基本オプション                            │
│    │   -m, --endpoint-type, --streaming, etc.  │
│    ├─ APIキー（--api-key）                      │
│    ├─ 入力モード                                │
│    │   └─ INPUT_FILE または synthetic mode     │
│    ├─ Tokenizer（--tokenizer）                  │
│    │   └─ OpenAI API使用時は gpt2 を自動設定   │
│    ├─ macOS固有のタイムアウト設定               │
│    │   └─ AIPERF_SERVICE__REGISTRATION_*       │
│    └─ 追加パラメータ（--extra-inputs）          │
│                                                 │
│ 7. コマンド実行                                 │
│    └─ eval ${CMD}                               │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ aiperf profile                                  │
│  - OpenAI互換APIにリクエスト送信                │
│  - メトリクス測定（TTFT, Latency, ITL）         │
│  - 結果をartifactディレクトリに保存             │
└─────────────────────────────────────────────────┘
```

---

## 実装の重要ポイント

### 1. Python バージョンの互換性

**問題**: AIPerf 0.4.0はPython 3.14と互換性がありません（`AttributeError: 'ForwardRef' object has no attribute 'default_parameter'`）。

**解決策**: Python 3.12を優先的に使用します。

- `Makefile`の`setup`ターゲットでPython 3.12を必須として検出
- `pyenv`でインストールされたPython 3.12.7を自動検出
- `venv`ディレクトリに仮想環境を作成
- Python 3.12が見つからない場合はエラー終了

### 2. OpenAI API統合

**問題**: OpenAIモデル名（`gpt-3.5-turbo`など）はHuggingFace Hubに存在しないため、TokenizerがエラーになりTokenizerの読み込みに失敗します。

**解決策**:
- OpenAI API使用時は、自動的に`gpt2`をTokenizerとして設定
- `AIPERF_URL`が空の場合、`OPENAI_API_KEY`をチェックしてOpenAI APIを使用
- `--api-key`コマンドラインオプションでAPIキーを明示的に渡す

### 3. macOS サービス登録タイムアウト

**問題**: macOSでAIPerfのサービス登録がタイムアウトすることがあります。

**解決策**:
- `AIPERF_SERVICE__REGISTRATION_TIMEOUT`などの環境変数を延長
- pydantic-settingsのネスト設定形式（`__`で区切る）で環境変数をエクスポート
- デフォルト値: `REGISTRATION_TIMEOUT=120.0`, `REGISTRATION_INTERVAL=2.0`, `REGISTRATION_MAX_ATTEMPTS=20`, `START_TIMEOUT=60.0`

### 4. メトリクスの単位変換

**問題**: AIPerfのexport結果の単位が不明瞭で、値の範囲が広い場合があります。

**解決策**:
- 辞書形式（`{'value': ..., 'unit': 'ms'}`）から`value`キーの値を抽出
- 単位変換のヒューリスティック:
  - 非常に大きい値（> 1,000,000,000）: ナノ秒 → ms
  - 小さい値（< 1）: 秒 → ms
  - それ以外: ms単位と仮定

### 5. 柔軟な入力モード

**設計**: Synthetic modeとカスタムプロンプトファイルの両方をサポートします。

**実装**:
- `INPUT_FILE`が設定されている場合: `--input-file` と `--custom-dataset-type` を使用
- それ以外: `--synthetic-input-tokens-mean`, `--synthetic-input-tokens-stddev`, `--output-tokens-mean` を使用

### 6. Dockerでの移植性

**設計**: macOSとLinuxの両方で同じコマンドで動作するようにします。

**実装**:
- `.env`ファイルをボリュームマウント
- `artifacts/`ディレクトリをボリュームマウント（結果をホストに保存）
- `entrypoint.sh`で引数に応じて適切なスクリプトを実行

---

## トラブルシューティング

### 1. Python バージョンの問題

**症状**:
```
AttributeError: 'ForwardRef' object has no attribute 'default_parameter'
```

**原因**: AIPerf 0.4.0はPython 3.14と互換性がありません。

**解決策**:
```bash
# Python 3.12をインストール（pyenv使用）
pyenv install 3.12.7

# venvを作成
make setup

# venvをアクティベート
source venv/bin/activate
```

---

### 2. Tokenizerの読み込みエラー

**症状**:
```
RepositoryNotFoundError: gpt-3.5-turbo is not a valid model identifier
```

**原因**: OpenAIモデル名はHuggingFace Hubに存在しないため、Tokenizerの読み込みに失敗します。

**解決策**: `scripts/run_aiperf_profile.sh`でOpenAI API使用時に自動的に`gpt2`をTokenizerとして設定しています。`.env`で明示的に指定することもできます:
```bash
TOKENIZER=gpt2
```

---

### 3. 認証エラー（401 Unauthorized）

**症状**:
```
401 Unauthorized
```

**原因**: APIキーが正しく渡されていません。

**解決策**: `OPENAI_API_KEY`を`.env`に設定してください:
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

`scripts/run_aiperf_profile.sh`で`--api-key`コマンドラインオプションを使用してAPIキーを明示的に渡しています。

---

### 4. サービス登録タイムアウト（macOS）

**症状**:
```
TimeoutError: Service registration timeout
```

**原因**: macOSでAIPerfのサービス登録がタイムアウトしています。

**解決策**: `.env`でタイムアウト設定を延長してください:
```bash
AIPERF_SERVICE_REGISTRATION_TIMEOUT=120.0
AIPERF_SERVICE_REGISTRATION_INTERVAL=2.0
AIPERF_SERVICE_REGISTRATION_MAX_ATTEMPTS=20
AIPERF_SERVICE_START_TIMEOUT=60.0
```

`scripts/run_aiperf_profile.sh`でデフォルト値が設定されているため、通常は`.env`に追加する必要はありません。

---

### 5. サマリが空になる

**症状**:
```
Warning: No values found for time_to_first_token
```

**原因**: `profile_export.jsonl`の形式が想定と異なる、または値が抽出できていません。

**解決策**:
1. `profile_export.jsonl`の形式を確認:
   ```bash
   cat artifacts/ISL100_OSL200_CON10/profile_export.jsonl | head -n 5
   ```

2. メトリクスが`metrics.{metric_name}`に含まれているか確認

3. 辞書形式（`{'value': ..., 'unit': 'ms'}`）の場合は`value`キーを確認

4. 単位変換のヒューリスティックを調整（必要に応じて`summarize_export.py`を編集）

---

### 6. Request Latencyが異常に小さい

**症状**:
```
Request Latency  1.41  2.34  3.45  1.50  30  0
```

**原因**: 単位変換が二重に適用されている可能性があります。

**解決策**: `summarize_export.py`の単位変換ロジックを確認してください。AIPerfのexportは通常ms単位で出力されるため、既にms単位の値はそのまま使用されるべきです。

---

### 7. Docker実行時の.envファイルエラー

**症状**:
```
Error: .env file not found. Please mount it as a volume.
```

**原因**: `.env`ファイルがコンテナにマウントされていません。

**解決策**:
1. ホスト側に`.env`ファイルが存在することを確認
2. `docker-compose.yml`でボリュームマウントが設定されていることを確認:
   ```yaml
   volumes:
     - ../.env:/app/.env:ro
   ```
3. `docker-compose run`コマンドを使用:
   ```bash
   docker-compose run --rm aiperf-client profile
   ```

---

## 参考資料

- [NVIDIA AIPerf公式ドキュメント](https://github.com/NVIDIA/AIPerf)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)
- [pydantic-settingsドキュメント](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/)

---

## 更新履歴

- **2024-12**: 初版作成
  - Python 3.12必須（`venv`）
  - OpenAI API統合
  - macOS固有のタイムアウト設定
  - Tokenizer自動設定
  - 単位変換ロジックの改善
