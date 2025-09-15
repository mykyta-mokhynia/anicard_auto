@echo off
echo ========================================
echo      Anicard Quick Start
echo ========================================
echo.
echo 1. Daily cycle
echo 2. Card cycle  
echo 3. Both cycles
echo 4. Test mode
echo.
set /p choice="Enter number (1-4): "

if "%choice%"=="1" (
    echo Starting daily cycle...
    call run_combined_daily.bat
) else if "%choice%"=="2" (
    echo Starting card cycle...
    call run_combined_cards.bat
) else if "%choice%"=="3" (
    echo Starting both cycles...
    call run_combined_both.bat
) else if "%choice%"=="4" (
    echo Starting test mode...
    call run_test.bat
) else (
    echo Invalid choice!
    pause
    call quick_start.bat
)
