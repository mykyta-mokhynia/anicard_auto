#!/bin/bash

# Anicard Auto - macOS Server Sync Script

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

echo "=========================================="
echo "  Anicard Auto - macOS Server Sync"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"

cd "$ROOT_DIR"

echo "🔄 Синхронизация с сервером..."
echo ""

echo "📥 Загрузка изменений с сервера..."
git pull origin main
if [ $? -eq 0 ]; then
    echo "✅ Изменения загружены успешно."
else
    echo "⚠️ Возможны конфликты или проблемы с подключением."
fi

echo ""
echo "📤 Загрузка изменений на сервер..."
git add .
git commit -m "Auto-sync from macOS $(date)"
git push origin main
if [ $? -eq 0 ]; then
    echo "✅ Изменения загружены на сервер."
else
    echo "⚠️ Ошибка при загрузке на сервер."
fi

echo ""
echo "✅ Синхронизация завершена!"
echo ""
read -p "Нажмите Enter для выхода..."