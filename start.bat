@echo off
chcp 65001 >nul
title Anicard Auto - Главное меню

echo.
echo ========================================
echo    🎮 ANICARD AUTO - ЗАПУСК
echo ========================================
echo.

cd /d "%~dp0"

echo 🔍 Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python найден
echo.

echo 🚀 Запуск главного меню...
python main.py

echo.
echo 👋 Программа завершена
pause