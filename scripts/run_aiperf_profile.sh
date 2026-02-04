#!/bin/bash
set -euo pipefail

# AIPerf profile実行スクリプト
# 環境変数から設定を読み込んで aiperf profile を実行

# .envファイルの読み込み
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "Error: .env file not found. Copy .env.example to .env and configure it." >&2
    exit 1
fi

# 必須環境変数のチェック
if [ -z "${MODEL:-}" ]; then
    echo "Error: MODEL is not set in .env" >&2
    exit 1
fi

# AIPERF_URLが空の場合はOpenAI APIを使用
if [ -z "${AIPERF_URL:-}" ]; then
    if [ -z "${OPENAI_API_KEY:-}" ]; then
        echo "Error: Either AIPERF_URL or OPENAI_API_KEY must be set in .env" >&2
        exit 1
    fi
    # OpenAI APIを使用する場合、URLを設定
    AIPERF_URL="https://api.openai.com/v1"
    echo "Using OpenAI API: ${AIPERF_URL}"
fi

# デフォルト値の設定
CONCURRENCY=${CONCURRENCY:-10}
REQUEST_COUNT=${REQUEST_COUNT:-$((CONCURRENCY * 3))}
INPUT_TOKENS_MEAN=${INPUT_TOKENS_MEAN:-100}
INPUT_TOKENS_STDDEV=${INPUT_TOKENS_STDDEV:-20}
OUTPUT_TOKENS_MEAN=${OUTPUT_TOKENS_MEAN:-200}
REQUEST_TIMEOUT_SECONDS=${REQUEST_TIMEOUT_SECONDS:-300}
CUSTOM_DATASET_TYPE=${CUSTOM_DATASET_TYPE:-single_turn}

# 実行モード（引数から取得、デフォルトはprofile）
MODE=${1:-profile}

# Artifactディレクトリの決定
if [ "$MODE" = "warmup" ]; then
    ARTIFACT_DIR="artifacts/warmup_ISL${INPUT_TOKENS_MEAN}_OSL${OUTPUT_TOKENS_MEAN}_CON${CONCURRENCY}"
elif [ "$MODE" = "profile" ]; then
    ARTIFACT_DIR="artifacts/ISL${INPUT_TOKENS_MEAN}_OSL${OUTPUT_TOKENS_MEAN}_CON${CONCURRENCY}"
else
    ARTIFACT_DIR="artifacts/${MODE}_ISL${INPUT_TOKENS_MEAN}_OSL${OUTPUT_TOKENS_MEAN}_CON${CONCURRENCY}"
fi

# AIPerf CLI（Env対応ラッパー経由。venvがあればvenvのpythonを使う）
PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "${PYTHON_BIN}" ]; then
    if [ -x "venv/bin/python3" ]; then
        PYTHON_BIN="venv/bin/python3"
    elif [ -x "venv/bin/python" ]; then
        PYTHON_BIN="venv/bin/python"
    else
        PYTHON_BIN="python3"
    fi
fi

AIPERF_CLI="${PYTHON_BIN} scripts/aiperf_cli_env.py"

# AIPerfコマンドの構築
CMD="${AIPERF_CLI} profile \
    -m ${MODEL} \
    --endpoint-type chat \
    --streaming \
    --ui-type none \
    --request-timeout-seconds ${REQUEST_TIMEOUT_SECONDS} \
    --concurrency ${CONCURRENCY} \
    --request-count ${REQUEST_COUNT} \
    -u ${AIPERF_URL} \
    --artifact-dir ${ARTIFACT_DIR}"

# APIキーは環境変数で渡す（--api-keyオプションは使用しない）
# Cyclopts Env(config) により、profileサブコマンドのAPIキーは `AIPERF_PROFILE_API_KEY` で渡せる。
# ここでは `.env` の `OPENAI_API_KEY` を橋渡しする。
if [ -n "${OPENAI_API_KEY:-}" ]; then
    export AIPERF_PROFILE_API_KEY="${OPENAI_API_KEY}"
fi

# INPUT_FILEが指定されている場合はファイル入力モード
if [ -n "${INPUT_FILE:-}" ] && [ -f "${INPUT_FILE}" ]; then
    echo "Using input file: ${INPUT_FILE}"
    CMD="${CMD} --input-file ${INPUT_FILE} --custom-dataset-type ${CUSTOM_DATASET_TYPE}"
else
    # Synthetic mode
    CMD="${CMD} --synthetic-input-tokens-mean ${INPUT_TOKENS_MEAN} \
        --synthetic-input-tokens-stddev ${INPUT_TOKENS_STDDEV} \
        --output-tokens-mean ${OUTPUT_TOKENS_MEAN}"
fi

# OPENAI_API_KEYが設定されている場合は追加
if [ -n "${OPENAI_API_KEY:-}" ]; then
    export OPENAI_API_KEY
fi

# AIPerfのタイムアウト設定を延長（macOSでのサービス登録タイムアウト問題回避）
# pydantic-settingsではネストされた設定は__（ダブルアンダースコア）で区切られる
export AIPERF_SERVICE__REGISTRATION_TIMEOUT=${AIPERF_SERVICE_REGISTRATION_TIMEOUT:-120.0}
export AIPERF_SERVICE__REGISTRATION_INTERVAL=${AIPERF_SERVICE_REGISTRATION_INTERVAL:-2.0}
export AIPERF_SERVICE__REGISTRATION_MAX_ATTEMPTS=${AIPERF_SERVICE_REGISTRATION_MAX_ATTEMPTS:-20}
export AIPERF_SERVICE__START_TIMEOUT=${AIPERF_SERVICE_START_TIMEOUT:-60.0}

# EXTRA_INPUTSが設定されている場合は追加
if [ -n "${EXTRA_INPUTS:-}" ]; then
    IFS=',' read -ra EXTRA_ARRAY <<< "${EXTRA_INPUTS}"
    for extra in "${EXTRA_ARRAY[@]}"; do
        CMD="${CMD} --extra-inputs ${extra}"
    done
fi

# Tokenizerが設定されている場合は追加
# OpenAI APIを使用する場合、HuggingFaceモデル名を指定する必要がある
# デフォルトではgpt2を使用（汎用的なTokenizer）
if [ -n "${TOKENIZER:-}" ]; then
    CMD="${CMD} --tokenizer ${TOKENIZER}"
elif [ -z "${AIPERF_URL:-}" ] || [ "${AIPERF_URL}" = "https://api.openai.com/v1" ]; then
    # OpenAI APIを使用する場合、デフォルトでgpt2をTokenizerとして使用
    # （OpenAIモデル名はHuggingFaceに存在しないため）
    CMD="${CMD} --tokenizer gpt2"
fi

echo "=========================================="
echo "Running AIPerf Profile"
echo "Mode: ${MODE}"
echo "URL: ${AIPERF_URL}"
echo "Model: ${MODEL}"
echo "Concurrency: ${CONCURRENCY}"
echo "Request Count: ${REQUEST_COUNT}"
echo "Artifact Dir: ${ARTIFACT_DIR}"
if [ -n "${AIPERF_PROFILE_API_KEY:-}" ]; then
    echo "API Key: Using AIPERF_PROFILE_API_KEY environment variable"
else
    echo "API Key: Not set (public endpoint or authentication not required)"
fi
echo "=========================================="
echo "Command: ${CMD}"
echo "=========================================="

# コマンド実行
eval ${CMD}

echo ""
echo "Profile completed. Artifacts saved to: ${ARTIFACT_DIR}"
