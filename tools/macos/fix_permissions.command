#!/bin/bash

# Anicard Auto - Fix Permissions
# Исправление прав доступа для macOS

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo "  Anicard Auto - Исправление прав доступа"
echo "=========================================="
echo ""

echo "🔧 Исправляем права доступа для .command файлов..."

# Исправляем права для всех .command файлов
find . -name "*.command" -exec chmod +x {} \;

if [ $? -eq 0 ]; then
    echo "✅ Права доступа исправлены успешно!"
    echo ""
    echo "📋 Исправленные файлы:"
    find . -name "*.command" -exec ls -la {} \;
else
    echo "❌ Ошибка при исправлении прав доступа"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

echo ""
echo "=========================================="
echo "  Готово! Теперь можно запускать .command файлы"
echo "=========================================="
echo ""
echo "Доступные команды:"
echo "  - tools/macos/start_macos.command (запуск программы)"
echo "  - tools/macos/install_macos.command (установка зависимостей)"
echo "  - tools/macos/setup_git.command (настройка Git)"
echo "  - tools/macos/sync_server.command (синхронизация с сервером)"
echo "  - tools/macos/activate_promo.command (активация промо)"
echo ""
read -p "Нажмите Enter для выхода..."
