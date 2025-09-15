@echo off
echo Запуск цикла карт каждые 4 часа 10 секунд...
call .venv\Scripts\activate.bat
python card_cycle.py
pause
