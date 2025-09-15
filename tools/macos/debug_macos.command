#!/bin/bash

# Anicard Auto - macOS Debug
# Диагностика проблем на macOS

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"

echo "=========================================="
echo "  Anicard Auto - Диагностика macOS"
echo "=========================================="
echo ""

echo "🔍 Информация о системе:"
echo "  macOS версия: $(sw_vers -productVersion)"
echo "  Архитектура: $(uname -m)"
echo "  Пользователь: $(whoami)"
echo ""

echo "📁 Информация о путях:"
echo "  Скрипт: $SCRIPT_DIR"
echo "  Корень проекта: $ROOT_DIR"
echo "  Текущая директория: $(pwd)"
echo ""

echo "🐍 Информация о Python:"
if command -v python3 &> /dev/null; then
    echo "  Python3: $(which python3)"
    echo "  Версия: $(python3 --version)"
    echo "  Путь Python: $(python3 -c 'import sys; print(sys.executable)')"
else
    echo "  ❌ Python3 не найден"
fi
echo ""

echo "📂 Структура проекта:"
cd "$ROOT_DIR"
echo "  Корневая директория: $(pwd)"
echo "  Содержимое:"
ls -la
echo ""

echo "🔍 Проверка ключевых файлов:"
if [ -f "main.py" ]; then
    echo "  ✅ main.py найден"
else
    echo "  ❌ main.py не найден"
fi

if [ -f "combined_cycle.py" ]; then
    echo "  ✅ combined_cycle.py найден"
else
    echo "  ❌ combined_cycle.py не найден"
fi

if [ -f "requirements.txt" ]; then
    echo "  ✅ requirements.txt найден"
else
    echo "  ❌ requirements.txt не найден"
fi

if [ -d "scripts" ]; then
    echo "  ✅ папка scripts найдена"
    echo "  Содержимое scripts:"
    ls -la scripts/
else
    echo "  ❌ папка scripts не найдена"
fi
echo ""

echo "🔧 Проверка прав доступа:"
echo "  Права на .command файлы:"
find . -name "*.command" -exec ls -la {} \;
echo ""

echo "📦 Проверка зависимостей Python:"
if command -v python3 &> /dev/null; then
    echo "  Установленные пакеты:"
    python3 -m pip list | grep -E "(telethon|python-dotenv|asyncio)"
else
    echo "  ❌ Python3 недоступен"
fi
echo ""

echo "🧪 Тест импорта:"
if command -v python3 &> /dev/null; then
    echo "  Тестируем импорт combined_cycle..."
    python3 -c "
import sys
import os
sys.path.insert(0, '.')
try:
    from combined_cycle import run_daily_cycle
    print('  ✅ Импорт combined_cycle успешен')
except Exception as e:
    print(f'  ❌ Ошибка импорта: {e}')
"
else
    echo "  ❌ Python3 недоступен"
fi
echo ""

echo "=========================================="
echo "  Диагностика завершена"
echo "=========================================="
echo ""
read -p "Нажмите Enter для выхода..."
