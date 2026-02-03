#!/bin/bash
set -euo pipefail

# Dockerコンテナのエントリーポイント
# .envファイルがマウントされていることを前提とする

if [ ! -f .env ]; then
    echo "Error: .env file not found. Please mount it as a volume." >&2
    exit 1
fi

# 引数に応じてコマンドを実行
case "${1:-help}" in
    setup)
        echo "Dependencies are already installed in the image."
        ;;
    smoke)
        python3 scripts/smoke_stream.py
        ;;
    warmup)
        bash scripts/run_aiperf_profile.sh warmup
        ;;
    profile)
        bash scripts/run_aiperf_profile.sh profile
        ;;
    summary)
        python3 scripts/summarize_export.py
        ;;
    sweep)
        bash -c 'for c in 1 5 10 20 50; do CONCURRENCY=$c REQUEST_COUNT=$((c * 3)) bash scripts/run_aiperf_profile.sh sweep_$c; done'
        python3 scripts/summarize_export.py
        ;;
    *)
        echo "Usage: docker run ... [setup|smoke|warmup|profile|summary|sweep]"
        echo ""
        echo "Available commands:"
        echo "  setup    - Show setup info (dependencies already installed)"
        echo "  smoke    - Run smoke test"
        echo "  warmup   - Run warmup benchmark"
        echo "  profile  - Run full profile benchmark"
        echo "  summary  - Generate summary from artifacts"
        echo "  sweep    - Run concurrency sweep"
        exit 1
        ;;
esac
