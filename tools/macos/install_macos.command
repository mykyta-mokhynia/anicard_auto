#!/bin/bash

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo "  Anicard Auto - Установка зависимостей"
echo "=========================================="

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите его с https://www.python.org/downloads/"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "⚠️ pip3 не найден, пробуем установить"
    python3 -m ensurepip --upgrade
fi

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
else
    echo "❌ requirements.txt не найден"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

echo "✅ Готово"
read -p "Нажмите Enter для выхода..."


