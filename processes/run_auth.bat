@echo off
echo 🔐 Авторизация аккаунтов
echo ========================

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

echo.
echo Использование:
echo   run_auth.bat session_name phone_number
echo   run_auth.bat phone_number  (автоматически создаст account_X)
echo.
echo Примеры:
echo   run_auth.bat account_3 +10000000003
echo   run_auth.bat +10000000003
echo.

if "%1"=="" (
    echo ❌ Не указан phone_number
    echo 💡 Используйте: run_auth.bat +1234567890
    pause
    exit /b 1
)

if "%2"=="" (
    echo 🚀 Запускаем авторизацию для %1 (автоматическое имя сессии)...
    python auth_manager.py --phone %1
) else (
    echo 🚀 Запускаем авторизацию для %1 (%2)...
    python auth_manager.py --session %1 --phone %2
)

pause