@echo off
chcp 65001 >nul
echo ========================================
echo      Anicard Combined Cycle Menu
echo ========================================
echo.
echo Vyberite rezhim raboty:
echo.
echo 1. Ezhednevnyy tsikl (seychas)
echo 2. Tsikl kart (seychas)
echo 3. Oba tsikla (seychas)
echo 4. Nepreryvnyy tsikl (polnyy)
echo 5. Nepreryvnyy tsikl kart
echo 6. Nepreryvnyy ezhednevnyy tsikl
echo 7. Vykhod
echo.
set /p choice="Vvedite nomer (1-7): "

if "%choice%"=="1" (
    call run_combined_daily.bat
) else if "%choice%"=="2" (
    call run_combined_cards.bat
) else if "%choice%"=="3" (
    call run_combined_both.bat
) else if "%choice%"=="4" (
    call run_continuous.bat
) else if "%choice%"=="5" (
    call run_continuous_cards.bat
) else if "%choice%"=="6" (
    call run_continuous_daily.bat
) else if "%choice%"=="7" (
    echo Do svidaniya!
    exit /b 0
) else (
    echo Nevernyy vybor!
    pause
    call start_combined.bat
)
