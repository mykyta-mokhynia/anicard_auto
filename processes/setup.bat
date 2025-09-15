@echo off
echo 🔧 Настройка AniCard Auto
echo ==========================

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+ с https://python.org
    pause
    exit /b 1
)

echo ✅ Python найден

REM Создаем виртуальное окружение
echo 🔧 Создаем виртуальное окружение...
if exist ".venv" (
    echo ⚠️ Виртуальное окружение уже существует
    echo 🔄 Пересоздаем виртуальное окружение...
    rmdir /s /q .venv
)

python -m venv .venv
if errorlevel 1 (
    echo ❌ Ошибка создания виртуального окружения
    pause
    exit /b 1
)

echo ✅ Виртуальное окружение создано

REM Активируем виртуальное окружение
echo 🔧 Активируем виртуальное окружение...
call .venv\Scripts\activate.bat

REM Обновляем pip
echo 📦 Обновляем pip...
python -m pip install --upgrade pip

REM Устанавливаем зависимости
echo 📦 Устанавливаем зависимости...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей
    pause
    exit /b 1
)

echo ✅ Зависимости установлены

REM Проверяем наличие .env файла
if not exist ".env" (
    echo ⚠️ Файл .env не найден
    echo 📝 Создаем .env из примера...
    if exist "env.example" (
        copy env.example .env
        echo ✅ Файл .env создан
        echo ⚠️ ВАЖНО: Отредактируйте .env файл и добавьте ваши API ключи!
    ) else (
        echo ❌ Файл env.example не найден
    )
)

REM Проверяем наличие accounts.json
if not exist "accounts.json" (
    echo ⚠️ Файл accounts.json не найден
    echo 📝 Создаем accounts.json из примера...
    if exist "accounts.json.example" (
        copy accounts.json.example accounts.json
        echo ✅ Файл accounts.json создан
        echo ⚠️ ВАЖНО: Отредактируйте accounts.json и добавьте ваши аккаунты!
    ) else (
        echo ❌ Файл accounts.json.example не найден
    )
)

echo.
echo 🎉 Настройка завершена!
echo.
echo 📋 Что нужно сделать:
echo 1. Отредактируйте .env файл и добавьте ваши API ключи
echo 2. Отредактируйте accounts.json и добавьте ваши аккаунты
echo 3. Запустите start.bat для начала работы
echo.
echo 🚀 Для запуска используйте: start.bat
echo.

pause

