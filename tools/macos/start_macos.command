#!/bin/bash

# Anicard Auto - macOS Launcher

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"

echo "🔍 Отладочная информация:"
echo "  Скрипт: $SCRIPT_DIR"
echo "  Корень: $ROOT_DIR"
echo ""

cd "$ROOT_DIR"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите его с https://www.python.org/downloads/"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

echo "=========================================="
echo "  Запуск Anicard Auto - Главное меню"
echo "=========================================="
echo ""

# Проверяем, что main.py существует
if [ ! -f "main.py" ]; then
    echo "❌ Файл main.py не найден в директории: $ROOT_DIR"
    echo "📁 Содержимое директории:"
    ls -la
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

python3 main.py

echo ""
echo "=========================================="
echo "  Программа завершена."
echo "=========================================="
read -p "Нажмите Enter для выхода..."