@echo off
chcp 65001 > nul
title Anicard Auto - Активация промо

echo.
echo ====================================
echo  Активация промо для всех аккаунтов
echo ====================================
echo.

cd /d "%~dp0\.."

python scripts/activate_promo.py

echo.
echo ====================================
echo  Программа завершена.
echo ====================================
echo.
pause
exit /b 0
