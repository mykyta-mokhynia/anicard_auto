@echo off
title AniCard Auto - Главное меню
color 0A

:menu
cls
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🤖 AniCard Auto 🤖                        ║
echo ║              Автоматизация получения наград                  ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Выберите действие:
echo.
echo 1. 🚀 Запуск интерактивного меню
echo 2. 🎁 Получить награды сейчас
echo 3. 🎴 Получить карты сейчас
echo 4. 🔄 Непрерывный цикл (награды + карты)
echo 5. 🧪 Тест подключения
echo 6. 🔐 Добавить новый аккаунт
echo 7. 📊 Показать статистику карт
echo 8. 🕐 Показать время
echo 9. 🌅 Ежедневный цикл (сейчас)
echo 10. ⏰ Ежедневный цикл (22:01 UTC)
echo 11. 🎴 Цикл карт (сейчас)
echo 12. ⏰ Цикл карт (каждые 4ч 10с)
echo 13. ❌ Выход
echo.
set /p choice="Введите номер (1-13): "

if "%choice%"=="1" (
    call run.bat
    goto menu
)
if "%choice%"=="2" (
    call run_rewards.bat
    goto menu
)
if "%choice%"=="3" (
    call run_cards.bat
    goto menu
)
if "%choice%"=="4" (
    call run_continuous.bat
    goto menu
)
if "%choice%"=="5" (
    call run_test.bat
    goto menu
)
if "%choice%"=="6" (
    call run_auth.bat
    goto menu
)
if "%choice%"=="7" (
    call run.bat
    goto menu
)
if "%choice%"=="8" (
    call run.bat
    goto menu
)
if "%choice%"=="9" (
    call run_daily_cycle.bat
    goto menu
)
if "%choice%"=="10" (
    call run_daily_schedule.bat
    goto menu
)
if "%choice%"=="11" (
    call run_card_cycle.bat
    goto menu
)
if "%choice%"=="12" (
    call run_card_schedule.bat
    goto menu
)
if "%choice%"=="13" (
    echo 👋 До свидания!
    exit /b 0
)

echo ❌ Неверный выбор. Попробуйте снова.
timeout /t 2 >nul
goto menu

