@echo off
echo Запуск цикла карт немедленно...
call .venv\Scripts\activate.bat
python card_cycle.py now
pause
