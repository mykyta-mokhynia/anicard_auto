@echo off
echo 🏃 Запуск основного процесса
echo ============================

REM Проверяем наличие виртуального окружения
if not exist ".venv" (
    echo ❌ Виртуальное окружение не найдено
    echo 🔧 Создаем виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Ошибка создания виртуального окружения
        pause
        exit /b 1
    )
)

REM Активируем виртуальное окружение
echo 🔧 Активируем виртуальное окружение...
call .venv\Scripts\activate.bat

REM Устанавливаем зависимости
echo 📦 Устанавливаем зависимости...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей
    pause
    exit /b 1
)

REM Запускаем основной процесс
echo 🚀 Запускаем multi_account_runner.py...
python multi_account_runner.py

echo.
echo ✅ Процесс завершен
pause