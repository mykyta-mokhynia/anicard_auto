@echo off
chcp 65001 >nul
echo ========================================
echo      Anicard Combined Cycle Menu
echo ========================================
echo.
echo Choose mode:
echo.
echo 1. Daily cycle (now)
echo 2. Card cycle (now)
echo 3. Both cycles (now)
echo 4. Continuous cycle (full)
echo 5. Continuous card cycle
echo 6. Continuous daily cycle
echo 7. Exit
echo.
set /p choice="Enter number (1-7): "

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
    echo Goodbye!
    exit /b 0
) else (
    echo Invalid choice!
    pause
    call start_menu.bat
)
