# NVIDIA AIPerf を使った OpenAI互換 Chat Completions ベンチマーク

macOS上で動作する、OpenAI互換APIのchat completions（ストリーミング対応）ベンチマークプロトタイプです。

## 概要

- **目的**: ローカルMacから別ホストの推論サーバに対して負荷を生成し、パフォーマンス指標を測定
- **対象API**: OpenAI互換のchat completionsエンドポイント（ストリーミング対応）
- **主要指標**: TTFT (Time To First Token), Request Latency, Inter-Token Latency の p50/p95/p99、Output Tokens/sec (avg)
- **出力**: Artifacts（JSON/JSONL）とTSVサマリ（Slack貼り付け用）

## 前提条件

- macOS（Linuxでも動作可能）
- Python 3.11以上
- 推論サーバがOpenAI互換APIを提供していること
- 推論サーバへのネットワーク接続が可能なこと

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd sample-aiperf
```

### 2. Python環境のセットアップ

#### オプションA: venvを使用

```bash
make setup
source venv/bin/activate
```

**注意**: Python 3.11以上が必要です。適切なバージョンがインストールされていない場合、`make setup`はエラーで終了します。

#### オプションB: uvを使用（推奨）

```bash
# uvがインストールされていない場合
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストール
uv pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、推論サーバの情報を設定します：

```bash
cp .env.example .env
```

#### OpenAI APIを使用する場合（推奨：プロトタイプ用）

.env ファイルを以下のように設定：

```bash
# OpenAI APIを使用（AIPERF_URLは空にするか https://api.openai.com/v1）
AIPERF_URL=

# API Key（必須）
API_KEY=sk-your-api-key-here

# モデル名（例: gpt-4-small, gpt-4o-mini, gpt-4o）
MODEL=gpt-4-small
```

#### カスタムOpenAI互換サーバを使用する場合

.env ファイルを以下のように設定：

```bash
# OpenAI互換推論サーバのURL
AIPERF_URL=http://192.168.1.100:8000

# API Key（認証が必要な場合のみ）
API_KEY=

# モデル名（推論サーバが認識するモデル名）
MODEL=tsuzumi2

# Tokenizer（任意。トークン数計算に使用）
# 無い場合でもTTFT/Latencyのp95/p99は算出可能
TOKENIZER=

# 並行リクエスト数
CONCURRENCY=10

# リクエスト総数（デフォルト: CONCURRENCY * 3）
REQUEST_COUNT=30

# 入力トークン数の平均値（synthetic mode用）
INPUT_TOKENS_MEAN=100

# 入力トークン数の標準偏差（synthetic mode用）
INPUT_TOKENS_STDDEV=20

# 出力トークン数の平均値（synthetic mode用）
OUTPUT_TOKENS_MEAN=200

# リクエストタイムアウト（秒）
REQUEST_TIMEOUT_SECONDS=300

# 任意プロンプト入力ファイル（trace.jsonl形式）
# 指定した場合、synthetic modeの代わりにこのファイルを使用
INPUT_FILE=

# カスタムデータセットタイプ（INPUT_FILE使用時）
# 例: single_turn
CUSTOM_DATASET_TYPE=multi_turn

# 追加パラメータ（推論サーバが対応している場合のみ）
# 例: min_tokens:50,ignore_eos:true
# カンマ区切りで複数指定可能
EXTRA_INPUTS=
```

`.env` ファイルを編集して、OpenAI API Keyを設定：

```bash
# API Keyを設定（必須）
API_KEY=sk-your-api-key-here

# モデル名を確認（必要に応じて変更）
MODEL=gpt-4-small
```

**注意**: OpenAI API Keyは[OpenAI Platform](https://platform.openai.com/api-keys)で取得できます。

## 使い方

### 最短で動かす手順

1. **ユニットテスト実行（推奨）**
   ```bash
   make test
   ```
   スクリプトの単体テストを実行し、動作を確認します。

2. **疎通確認（Smoke Test）**
   ```bash
   make smoke
   ```
   1リクエストを送信して、接続とストリーミング応答を確認します。

3. **Warmup実行**
   ```bash
   make warmup
   ```
   軽い負荷でwarmupを実行し、システムを準備します。

4. **本番プロファイル実行**
   ```bash
   make profile
   ```
   本番レベルのベンチマークを実行します。結果は `artifacts/` ディレクトリに保存されます。

5. **サマリ生成**
   ```bash
   make summary
   ```
   最新のartifactからp50/p95/p99を算出し、`summary.tsv` と `summary.md` を生成します。

### 詳細な使い方

#### 環境変数の設定

`.env` ファイルで以下の変数を設定できます：

| 変数名 | 説明 | デフォルト |
|--------|------|------------|
| `AIPERF_URL` | 推論サーバのURL（OpenAI API使用時は空） | - |
| `MODEL` | モデル名（必須） | - |
| `API_KEY` | APIキー（OpenAI API使用時は必須、カスタムサーバでは認証が必要な場合のみ） | - |
| `CONCURRENCY` | 並行リクエスト数 | 10 |
| `REQUEST_COUNT` | リクエスト総数 | CONCURRENCY * 3 |
| `INPUT_TOKENS_MEAN` | 入力トークン数の平均（synthetic mode） | 100 |
| `INPUT_TOKENS_STDDEV` | 入力トークン数の標準偏差 | 20 |
| `OUTPUT_TOKENS_MEAN` | 出力トークン数の平均 | 200 |
| `REQUEST_TIMEOUT_SECONDS` | リクエストタイムアウト（秒） | 300 |
| `INPUT_FILE` | カスタムプロンプトファイル（trace.jsonl） | - |
| `CUSTOM_DATASET_TYPE` | カスタムデータセットタイプ | single_turn |
| `EXTRA_INPUTS` | 追加パラメータ（カンマ区切り） | - |
| `TOKENIZER` | Tokenizer名（任意） | - |
| `AIPERF_SERVICE_REGISTRATION_TIMEOUT` | サービス登録タイムアウト（秒、macOS問題回避用） | 120.0 |
| `AIPERF_SERVICE_REGISTRATION_INTERVAL` | サービス登録試行間隔（秒） | 2.0 |
| `AIPERF_SERVICE_REGISTRATION_MAX_ATTEMPTS` | サービス登録最大試行回数 | 20 |
| `AIPERF_SERVICE_START_TIMEOUT` | サービス起動タイムアウト（秒） | 60.0 |

**Synthetic mode とは？** `INPUT_FILE` が未設定、またはファイルが存在しない場合に使用される入力モードです。  
この場合、実プロンプトではなく、`INPUT_TOKENS_MEAN/STDDEV` と `OUTPUT_TOKENS_MEAN` で指定したトークン長の疑似リクエストを生成して負荷をかけます。  
`INPUT_FILE` を指定するとファイル入力モードになり、Synthetic mode 用のパラメータは使用されません。

#### 任意プロンプト入力（ファイル入力モード）

カスタムプロンプトを使用する場合：

1. サンプル `prompts/trace.jsonl.example` をコピーして `prompts/trace.jsonl` を作成（`trace.jsonl` はローカル用）
   ```bash
   cp prompts/trace.jsonl.example prompts/trace.jsonl
   ```
   必要に応じて `prompts/trace.jsonl` を編集します。

2. `.env` で `INPUT_FILE` を設定
   ```bash
   INPUT_FILE=prompts/trace.jsonl
   ```

3. `make profile` を実行

詳細は `prompts/README.md` を参照してください。

#### Concurrency Sweep

複数の並行度でベンチマークを実行：

```bash
make sweep
```

デフォルトでは、concurrency 1, 5, 10, 20, 50 で実行します。

#### 追加パラメータの使用

推論サーバが `min_tokens` や `ignore_eos` などの追加パラメータをサポートしている場合：

```bash
# .env
EXTRA_INPUTS=min_tokens:50,ignore_eos:true
```

## 出力結果

### Artifacts

ベンチマーク実行後、`artifacts/` ディレクトリに以下のような構造で結果が保存されます：

```
artifacts/
  └── ISL100_OSL200_CON10/
      ├── profile_export.jsonl
      └── profile_export.json
```

### サマリファイル

`make summary` を実行すると、以下が生成されます：

- **summary.tsv**: Slack貼り付け用のTSV形式サマリ
  ```
  metric	p50_ms	p95_ms	p99_ms	avg_ms	count	errors
  TTFT	123.45	234.56	345.67	150.00	30	0
  Request Latency	567.89	890.12	1234.56	600.00	30	0
  ```

- **summary.md**: 人間が読みやすいMarkdown形式のサマリ

## トラブルシューティング

### エラー: AIPERF_URL is not set

`.env` ファイルが存在しないか、`AIPERF_URL` が設定されていません。
`.env.example` をコピーして `.env` を作成し、設定を確認してください。

### エラー: Connection refused / Timeout

推論サーバへの接続に失敗しています。以下を確認してください：

1. `AIPERF_URL` が正しいか
2. ネットワーク接続が可能か（`curl http://<host>:<port>/health` などで確認）
3. ファイアウォール設定

### エラー: Model not found

モデル名が推論サーバで認識されていません。以下を確認してください：

1. `MODEL` の値が正しいか
2. 推論サーバがサポートしているモデル名一覧を確認

### エラー: Authentication failed

認証が必要な場合、`API_KEY` を設定してください。

### Smoke testが失敗する

`make smoke` で接続確認ができない場合：

1. OpenAI SDKがインストールされているか確認（`pip install openai`）
2. URLとモデル名が正しいか確認
3. 推論サーバがストリーミングをサポートしているか確認

### Warning: resource_tracker: There appear to be leaked semaphore objects

ベンチマーク実行後に以下のような警告が表示される場合があります：

```
UserWarning: resource_tracker: There appear to be 3 leaked semaphore objects to clean up at shutdown
```

**原因**: AIPerfがmultiprocessingを使用しており、終了時にセマフォが適切にクリーンアップされていないためです。

**対処方法**: 
- この警告は機能的な問題を引き起こしません。無視して問題ありません。
- 警告を抑制したい場合は、環境変数を設定：
  ```bash
  export PYTHONWARNINGS="ignore::UserWarning:multiprocessing.resource_tracker"
  ```
- または、`make profile`実行時に設定：
  ```bash
  PYTHONWARNINGS="ignore::UserWarning:multiprocessing.resource_tracker" make profile
  ```

## Linux検証サーバへの移行

このリポジトリは、Linux検証サーバでも同じコマンドで動作するように設計されています。

### 実行方法の選択

| 実行方法 | メリット | デメリット | 推奨環境 |
|---------|---------|----------|---------|
| **Docker** | 環境の違いを吸収、Pythonバージョン管理不要、クリーンな環境 | 初回ビルドに時間、若干のオーバーヘッド | 本番検証サーバ（推奨） |
| **ネイティブ** | 高速な反復実行、デバッグが容易、システムリソースを直接利用 | Python環境の構築が必要、環境依存の問題が発生しうる | 開発環境 |

### Dockerを使用する場合（推奨）

#### 前提条件

- Docker Engine 20.10以降
- Docker Compose 1.29以降

#### セットアップ手順

1. **イメージのビルド**
   ```bash
   cd docker
   docker-compose build
   ```

2. **実行**
   ```bash
   # Smoke test
   docker-compose run --rm aiperf-client smoke

   # Profile実行
   docker-compose run --rm aiperf-client profile

   # Summary生成
   docker-compose run --rm aiperf-client summary
   ```

3. **環境変数の設定**
   
   `docker-compose.yml` で `.env` ファイルをマウントしているため、
   ホスト側の `.env` ファイルを編集すれば、コンテナ内でも同じ設定が使用されます。

### 直接実行する場合

#### Linux固有の前提条件

**Ubuntu/Debian系の場合:**

```bash
# システムパッケージのインストール
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip git

# または Python 3.11
sudo apt-get install -y python3.11 python3.11-venv python3-pip git
```

**CentOS/RHEL系の場合:**

```bash
# EPEL リポジトリの有効化（必要に応じて）
sudo yum install -y epel-release

# システムパッケージのインストール
sudo yum install -y python3.12 python3.12-devel git

# または Python 3.11
sudo yum install -y python3.11 python3.11-devel git
```

#### セットアップ手順

**オプション1: 自動セットアップスクリプト（推奨）**

Linux環境用のワンストップセットアップスクリプトを使用：

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd sample-aiperf

# 2. 自動セットアップスクリプトを実行
bash scripts/linux-setup.sh

# 3. 環境変数の設定
cp .env.example .env
# .env を編集

# 4. 実行
source venv/bin/activate  # 既にアクティブな場合は不要
make smoke
make warmup
make profile
make summary
```

**オプション2: 手動セットアップ**

Linuxサーバ上で、macOSと同じ手順でセットアップ：

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd sample-aiperf

# 2. Python環境のセットアップ
make setup
source venv/bin/activate

# 3. 環境変数の設定
cp .env.example .env
# .env を編集

# 4. 実行
make smoke
make warmup
make profile
make summary
```

### macOS固有の設定について

`AIPERF_SERVICE__*` 環境変数はmacOSでのサービス登録タイムアウト問題を回避するための設定ですが、
Linux環境でも無害に動作します。これらの設定は `scripts/run_aiperf_profile.sh` で自動的に設定されるため、
特別な変更は不要です。

### トラブルシューティング（Linux固有）

#### Python 3.11/3.12が見つからない

- **症状**: `make setup` で "Python 3.11 or later not found" エラー
- **対処**: 上記の「Linux固有の前提条件」セクションを参照してPythonをインストール

#### venv作成に失敗する

- **症状**: `Error: Failed to create venv`
- **対処**: `python3-venv`パッケージをインストール
  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3.12-venv
  
  # CentOS/RHEL
  sudo yum install python3.12-devel
  ```

#### Permission denied エラー

- **症状**: スクリプト実行時に権限エラー
- **対処**: スクリプトに実行権限を付与
  ```bash
  chmod +x scripts/*.sh scripts/*.py
  ```

## ディレクトリ構造

```
sample-aiperf/
├── README.md                 # このファイル
├── Makefile                  # メインのMakefile
├── requirements.txt          # Python依存関係
├── .env.example              # 環境変数のテンプレート
├── .gitignore                # Git除外設定
├── scripts/
│   ├── run_aiperf_profile.sh # AIPerf実行スクリプト
│   ├── smoke_stream.py       # 疎通確認スクリプト
│   ├── summarize_export.py   # サマリ生成スクリプト
│   └── linux-setup.sh        # Linux環境用自動セットアップ
├── prompts/
│   ├── trace.jsonl.example   # カスタムプロンプトのサンプル（Git管理）
│   └── README.md             # trace.jsonlのスキーマ説明
├── docker/
│   ├── Dockerfile            # Dockerイメージ定義
│   ├── docker-compose.yml    # Docker Compose設定
│   └── entrypoint.sh        # Dockerエントリーポイント
└── artifacts/                # ベンチマーク結果（gitignore対象）
```

## 注意事項

- **p95/p99の算出**: AIPerfの標準出力にはp95が含まれない可能性があるため、`make summary` でexportファイルから後処理で算出しています
- **Tokenizer**: Tokenizerが設定されていない場合でも、TTFT/Latencyのp95/p99は算出可能です
- **UI無効化**: `--ui-type none` オプションでUIを無効化し、「素のLLM」の性能を測定します
- **Artifacts**: `artifacts/` ディレクトリは `.gitignore` に含まれているため、Gitにはコミットされません

## 参考資料

- [NVIDIA AIPerf公式ドキュメント](https://github.com/ai-dynamo/aiperf)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)

## ライセンス

（プロジェクトのライセンスに応じて記載）
