.PHONY: setup smoke warmup profile sweep summary test help

# デフォルトターゲット
help:
	@echo "Available targets:"
	@echo "  make setup     - Set up Python environment and install dependencies"
	@echo "  make smoke     - Run smoke test (1 request streaming to verify connection)"
	@echo "  make warmup    - Run warmup benchmark (light load, saves artifacts)"
	@echo "  make profile   - Run full profile benchmark (saves artifacts)"
	@echo "  make sweep     - Run concurrency sweep (optional)"
	@echo "  make summary   - Generate summary.tsv from latest artifacts"
	@echo "  make test      - Run unit tests"

# 環境変数の読み込み（.envが存在する場合のみ）
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Python環境のセットアップ
setup:
	@echo "Setting up Python environment..."
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		if [ -d venv312 ]; then \
			echo "Using existing Python 3.12 venv (venv312)"; \
		else \
			echo "Checking for Python 3.12..."; \
			if command -v python3.12 >/dev/null 2>&1 || [ -f "$$HOME/.pyenv/versions/3.12.7/bin/python3" ]; then \
				echo "Creating Python 3.12 virtual environment..."; \
				if [ -f "$$HOME/.pyenv/versions/3.12.7/bin/python3" ]; then \
					$$HOME/.pyenv/versions/3.12.7/bin/python3 -m venv venv312; \
				elif command -v python3.12 >/dev/null 2>&1; then \
					python3.12 -m venv venv312; \
				fi; \
				echo "Activate with: source venv312/bin/activate"; \
			else \
				echo "Python 3.12 not found. Creating default venv..."; \
				python3 -m venv venv || python3 -m venv .venv; \
				echo "Activate with: source venv/bin/activate (or .venv/bin/activate)"; \
			fi; \
		fi; \
	fi
	@echo "Installing dependencies..."
	@if [ -d venv312 ]; then \
		venv312/bin/pip install --upgrade pip; \
		venv312/bin/pip install -r requirements.txt; \
	else \
		pip install --upgrade pip; \
		pip install -r requirements.txt; \
	fi
	@echo "Setup complete! Copy .env.example to .env and configure it."

# 疎通確認（1リクエスト）
smoke:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@echo "Running smoke test..."
	python3 scripts/smoke_stream.py

# Warmup実行（軽い負荷）
warmup:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@echo "Running warmup benchmark..."
	@CONCURRENCY=3 REQUEST_COUNT=9 bash scripts/run_aiperf_profile.sh warmup

# 本番プロファイル実行
profile:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@echo "Running full profile benchmark..."
	bash scripts/run_aiperf_profile.sh profile

# Concurrency sweep（任意）
sweep:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@echo "Running concurrency sweep..."
	@for c in 1 5 10 20 50; do \
		echo "Running with CONCURRENCY=$$c..."; \
		CONCURRENCY=$$c REQUEST_COUNT=$$((c * 3)) bash scripts/run_aiperf_profile.sh sweep_$$c; \
	done
	@echo "Sweep complete. Run 'make summary' to generate summary."

# サマリ生成
summary:
	@echo "Generating summary from latest artifacts..."
	python3 scripts/summarize_export.py
	@echo "Summary generated: summary.tsv and summary.md"

# ユニットテスト実行
test:
	@echo "Running unit tests..."
	python3 -m pytest tests/ -v
	@echo "All tests completed."
