FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# システムパッケージのインストール（必要に応じて）
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
