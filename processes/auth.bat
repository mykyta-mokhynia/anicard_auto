@echo off
chcp 65001 >nul
title Anicard Auth Manager

echo ========================================
echo    Anicard Auth Manager
echo ========================================
echo.
echo Выберите действие:
echo 1. Авторизация по номеру (автоматический session)
echo 2. Авторизация с указанием session
echo 3. Пакетная авторизация из JSON
echo 4. Показать справку
echo 5. Выход
echo.
set /p choice="Введите номер (1-5): "

if "%choice%"=="1" (
    echo.
    set /p phone="Введите номер телефона (например +1234567890): "
    echo Запуск авторизации для %phone%...
    cd /d "%~dp0.."
    python scripts/auth_manager.py --phone %phone%
    pause
) else if "%choice%"=="2" (
    echo.
    set /p session="Введите имя session (например account_3): "
    set /p phone="Введите номер телефона (например +1234567890): "
    echo Запуск авторизации для %session% (%phone%)...
    cd /d "%~dp0.."
    python scripts/auth_manager.py --session %session% --phone %phone%
    pause
) else if "%choice%"=="3" (
    echo.
    set /p json_file="Введите путь к JSON файлу: "
    echo Запуск пакетной авторизации из %json_file%...
    cd /d "%~dp0.."
    python scripts/auth_manager.py --batch %json_file%
    pause
) else if "%choice%"=="4" (
    echo.
    cd /d "%~dp0.."
    python scripts/auth_manager.py --help
    pause
) else if "%choice%"=="5" (
    echo Выход...
    exit
) else (
    echo Неверный выбор!
    pause
    goto :eof
)
