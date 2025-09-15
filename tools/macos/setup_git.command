#!/bin/bash

# Anicard Auto - macOS Git Setup Script

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

echo "=========================================="
echo "  Anicard Auto - macOS Git Setup"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"

cd "$ROOT_DIR"

echo "🔧 Настройка Git..."
git config core.autocrlf false
git config core.safecrlf true
echo "✅ Git настроен для правильной работы с окончаниями строк."

echo ""
echo "📁 Инициализация Git репозитория..."
if [ ! -d ".git" ]; then
    git init
    echo "✅ Git репозиторий инициализирован."
else
    echo "✅ Git репозиторий уже существует."
fi

echo ""
echo "📝 Добавление файлов в Git..."
git add .
git status

echo ""
echo "💾 Создание первого коммита..."
git commit -m "Initial commit - Anicard Auto setup"

echo ""
echo "✅ Git настройка завершена!"
echo "Теперь вы можете:"
echo "  - Добавить удаленный репозиторий: git remote add origin <URL>"
echo "  - Загрузить изменения: git push -u origin main"
echo ""
read -p "Нажмите Enter для выхода..."