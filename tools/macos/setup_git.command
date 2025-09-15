#!/bin/bash

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"
cd "$ROOT_DIR"

echo "Anicard Auto - Настройка Git"

if ! command -v git &> /dev/null; then
    echo "❌ Git не найден. Установите его: https://git-scm.com/downloads"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

if [ ! -d ".git" ]; then
    git init
fi

read -p "Введите ваше имя: " git_name
read -p "Введите ваш email: " git_email
git config user.name "$git_name"
git config user.email "$git_email"

echo "✅ Git настроен"
read -p "Нажмите Enter для выхода..."


