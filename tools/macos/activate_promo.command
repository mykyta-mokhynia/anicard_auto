#!/bin/bash

# Anicard Auto - Activate Promo

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo "  Anicard Auto - Активация промо"
echo "=========================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите его с https://www.python.org/downloads/"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

python3 scripts/activate_promo.py

echo ""
echo "=========================================="
echo "  Программа завершена."
echo "=========================================="
read -p "Нажмите Enter для выхода..."
