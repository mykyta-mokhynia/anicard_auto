#!/bin/bash

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"
cd "$ROOT_DIR"

echo "Anicard Auto - Синхронизация с сервером"

if ! command -v git &> /dev/null; then
    echo "❌ Git не найден"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

git add .
git commit -m "Auto-sync: $(date '+%Y-%m-%d %H:%M:%S')" || true
git push origin main || true

echo "✅ Готово"
read -p "Нажмите Enter для выхода..."


