@echo off
echo 🕐 Показ времени UTC и локального
echo ================================

REM Проверяем наличие виртуального окружения
if not exist ".venv" (
    echo ❌ Виртуальное окружение не найдено
    echo Запустите сначала: python setup.py
    pause
    exit /b 1
)

REM Активируем виртуальное окружение и запускаем скрипт
call .venv\Scripts\activate.bat
python -c "import datetime, pytz; utc=datetime.datetime.now(pytz.UTC); local=datetime.datetime.now(); print(f'UTC: {utc.strftime(\"%Y-%m-%d %H:%M:%S\")}'); print(f'Локальное: {local.strftime(\"%Y-%m-%d %H:%M:%S\")}'); print(f'Разница с UTC: {local.astimezone().utcoffset()}')"

pause
