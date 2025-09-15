@echo off
echo ⏰ Планировщик карт
echo ==================

REM Проверяем наличие виртуального окружения
if not exist ".venv" (
    echo ❌ Виртуальное окружение не найдено
    echo Запустите сначала: python setup.py
    pause
    exit /b 1
)

REM Активируем виртуальное окружение и запускаем скрипт
call .venv\Scripts\activate.bat
python anicard_auto.py cards_schedule

pause
