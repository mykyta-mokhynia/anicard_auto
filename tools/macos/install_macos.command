#!/bin/bash

# Anicard Auto - macOS Installation Script

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

echo "=========================================="
echo "  Anicard Auto - macOS Installation"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"

echo "🔍 Информация о системе:"
echo "  macOS Version: $(sw_vers -productVersion)"
echo "  Architecture: $(uname -m)"
echo "  Python Version: $(python3 --version 2>/dev/null || echo 'Python 3 не найден')"
echo ""

cd "$ROOT_DIR"

echo "📦 Установка зависимостей Python..."
if [ -f "requirements.txt" ]; then
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "✅ Зависимости установлены успешно!"
    else
        echo "❌ Ошибка при установке зависимостей."
        read -p "Нажмите Enter для выхода..."
        exit 1
    fi
else
    echo "❌ Файл requirements.txt не найден."
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

echo ""
echo "🔧 Настройка прав доступа..."
chmod +x tools/macos/*.command
echo "✅ Права доступа настроены."

echo ""
echo "✅ Установка завершена!"
echo "Теперь вы можете запустить:"
echo "  ./tools/macos/start_macos.command"
echo ""
read -p "Нажмите Enter для выхода..."