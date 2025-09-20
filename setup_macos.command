#!/bin/bash

# Anicard Auto - Complete macOS Setup
# Полная настройка для macOS 10.15+

# Устанавливаем кодировку UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Anicard Auto - Полная настройка macOS"
echo "=========================================="
echo ""

# Проверяем версию macOS
echo "🍎 Проверяем версию macOS..."
macos_version=$(sw_vers -productVersion)
echo "✅ macOS версия: $macos_version"

# Проверяем, что версия 10.15 или выше
if [[ $(echo "$macos_version" | cut -d. -f1) -lt 10 ]] || [[ $(echo "$macos_version" | cut -d. -f2) -lt 15 ]]; then
    echo "⚠️ Внимание: Рекомендуется macOS 10.15 или выше"
    echo "   Текущая версия: $macos_version"
    echo ""
fi

# Шаг 1: Исправление прав доступа
echo "🔧 Шаг 1: Исправление прав доступа..."
chmod +x *.command
if [ $? -eq 0 ]; then
    echo "✅ Права доступа установлены"
else
    echo "❌ Ошибка при установке прав доступа"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

# Шаг 2: Проверка Python
echo ""
echo "🐍 Шаг 2: Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Пожалуйста, установите Python 3.x."
    echo "   (https://www.python.org/downloads/)"
    echo ""
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python версия: $PYTHON_VERSION"

# Шаг 3: Установка зависимостей
echo ""
echo "📦 Шаг 3: Установка зависимостей..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "✅ Зависимости установлены"
    else
        echo "❌ Ошибка при установке зависимостей"
        read -p "Нажмите Enter для выхода..."
        exit 1
    fi
else
    echo "❌ Файл requirements.txt не найден"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

# Шаг 4: Настройка Git
echo ""
echo "🔧 Шаг 4: Настройка Git..."
if ! command -v git &> /dev/null; then
    echo "❌ Git не найден. Пожалуйста, установите Git."
    echo "   (https://git-scm.com/downloads)"
    echo ""
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

echo "✅ Git найден"

# Проверяем, является ли директория Git репозиторием
if [ ! -d ".git" ]; then
    echo "ℹ️ Git репозиторий не инициализирован"
    echo "   Запустите setup_git.command для настройки Git"
else
    echo "✅ Git репозиторий уже настроен"
fi

# Шаг 5: Создание необходимых папок
echo ""
echo "📁 Шаг 5: Создание необходимых папок..."
mkdir -p accounts/cards
mkdir -p errors
mkdir -p scripts/errors

if [ $? -eq 0 ]; then
    echo "✅ Папки созданы"
else
    echo "❌ Ошибка при создании папок"
fi

# Шаг 6: Проверка конфигурации
echo ""
echo "⚙️ Шаг 6: Проверка конфигурации..."

# Проверяем .env
if [ -f ".env" ]; then
    echo "✅ Файл .env найден"
else
    echo "⚠️ Файл .env не найден. Создайте его согласно README"
fi

# Проверяем accounts.json
if [ -f "accounts/accounts.json" ]; then
    echo "✅ Файл accounts.json найден"
else
    echo "⚠️ Файл accounts.json не найден. Запустите авторизацию аккаунтов"
fi

# Итоговый отчет
echo ""
echo "=========================================="
echo "  Настройка завершена!"
echo "=========================================="
echo ""
echo "🎯 Что можно делать дальше:"
echo ""
echo "1. 🚀 Запуск программы:"
echo "   - Двойной клик на start_macos.command"
echo "   - Или: python3 main.py"
echo ""
echo "2. 🔧 Настройка Git (если не настроен):"
echo "   - Двойной клик на setup_git.command"
echo ""
echo "3. 🌿 Создание ветки разработки:"
echo "   - Двойной клик на create_hidden_branch.command"
echo ""
echo "4. 🔄 Синхронизация с сервером:"
echo "   - Двойной клик на sync_server.command"
echo "   - Или: auto_sync.command для всех веток"
echo ""
echo "5. 👤 Авторизация аккаунтов:"
echo "   - Запустите программу и выберите пункт 8"
echo ""
echo "📚 Документация:"
echo "   - README.md - основная документация"
echo "   - README_macOS.md - документация для macOS"
echo ""
echo "🎉 Готово к работе!"
echo ""
read -p "Нажмите Enter для выхода..."

