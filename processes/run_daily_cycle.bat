@echo off
echo ========================================
echo   Anicard Daily Cycle - Ежедневный цикл
echo ========================================
echo.

REM Проверяем, существует ли виртуальное окружение
if not exist ".venv" (
    echo Создаем виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo Ошибка создания виртуального окружения!
        pause
        exit /b 1
    )
)

REM Активируем виртуальное окружение
echo Активируем виртуальное окружение...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Ошибка активации виртуального окружения!
    pause
    exit /b 1
)

REM Устанавливаем зависимости
echo Устанавливаем зависимости...
pip install -r requirements.txt
if errorlevel 1 (
    echo Ошибка установки зависимостей!
    pause
    exit /b 1
)

REM Запускаем ежедневный цикл
echo.
echo Запускаем ежедневный цикл...
echo.
python daily_cycle.py

REM Пауза перед закрытием
echo.
echo Нажмите любую клавишу для выхода...
pause >nul
