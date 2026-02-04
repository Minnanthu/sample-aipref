#!/bin/bash
set -euo pipefail

# Linux環境用ワンストップセットアップスクリプト
# Ubuntu/Debian および CentOS/RHEL 系をサポート

echo "=========================================="
echo "AIPerf Benchmark - Linux Setup Script"
echo "=========================================="
echo ""

# OSの検出
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    echo "Error: Cannot detect OS. /etc/os-release not found." >&2
    exit 1
fi

echo "Detected OS: $OS $OS_VERSION"
echo ""

# Pythonバージョンのチェック
check_python_version() {
    local python_cmd=$1
    if command -v $python_cmd >/dev/null 2>&1; then
        local version=$($python_cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
            echo "$python_cmd"
            return 0
        fi
    fi
    return 1
}

# Python 3.11以上を探す
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3; do
    if PYTHON_CMD=$(check_python_version $cmd 2>/dev/null); then
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Python 3.11 or later not found. Installing..."
    echo ""
    
    case $OS in
        ubuntu|debian)
            echo "Installing Python 3.12 on Ubuntu/Debian..."
            if [ "$EUID" -ne 0 ]; then
                echo "Note: This requires sudo privileges."
                sudo apt-get update
                sudo apt-get install -y python3.12 python3.12-venv python3-pip git
            else
                apt-get update
                apt-get install -y python3.12 python3.12-venv python3-pip git
            fi
            PYTHON_CMD="python3.12"
            ;;
        centos|rhel|rocky|almalinux)
            echo "Installing Python 3.12 on CentOS/RHEL..."
            if [ "$EUID" -ne 0 ]; then
                echo "Note: This requires sudo privileges."
                sudo yum install -y epel-release || true
                sudo yum install -y python3.12 python3.12-devel git
            else
                yum install -y epel-release || true
                yum install -y python3.12 python3.12-devel git
            fi
            PYTHON_CMD="python3.12"
            ;;
        *)
            echo "Error: Unsupported OS: $OS" >&2
            echo "Please install Python 3.11 or later manually and run 'make setup' instead." >&2
            exit 1
            ;;
    esac
    
    # 再度チェック
    if ! check_python_version $PYTHON_CMD >/dev/null 2>&1; then
        echo "Error: Python installation failed or version is too old." >&2
        exit 1
    fi
fi

PY_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
echo "✓ Python found: $PYTHON_CMD ($PY_VERSION)"
echo ""

# venvの作成
if [ -d venv ]; then
    echo "✓ Virtual environment already exists (venv/)"
else
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ ! -d venv ]; then
        echo "Error: Failed to create virtual environment" >&2
        exit 1
    fi
    echo "✓ Virtual environment created"
fi

# venvのアクティベート
source venv/bin/activate

# pipのアップグレード
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# 依存関係のインストール
echo ""
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet

echo ""
echo "=========================================="
echo "✓ Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Copy and configure .env file:"
echo "     cp .env.example .env"
echo "     # Edit .env with your settings"
echo ""
echo "  2. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  3. Run smoke test:"
echo "     make smoke"
echo ""
echo "  4. Run benchmark:"
echo "     make profile"
echo "     make summary"
echo ""
