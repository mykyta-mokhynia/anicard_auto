#!/bin/bash

# Anicard Auto - macOS Debugging Script

echo "=========================================="
echo "  Anicard Auto - macOS Diagnostic Tool"
echo "=========================================="
echo ""

echo "🔍 1. Информация о системе:"
echo "  macOS Version: $(sw_vers -productVersion)"
echo "  Architecture: $(uname -m)"
echo ""

echo "🔍 2. Информация о Python:"
if command -v python3 &> /dev/null; then
    echo "  ✅ Python 3 найден: $(command -v python3)"
    echo "  Версия Python: $(python3 --version)"
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if (( $(echo "$PYTHON_VERSION < 3.7" | bc -l) )); then
        echo "  ⚠️ Рекомендуется Python 3.7+ для полной совместимости."
    fi
    echo "  Python Path (sys.path):"
    python3 -c 'import sys; print("\n".join(sys.path))' | sed 's/^/    - /'
else
    echo "  ❌ Python 3 не найден. Установите его с https://www.python.org/downloads/"
fi
echo ""

echo "🔍 3. Проверка структуры проекта:"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"
echo "  Текущая директория скрипта: $SCRIPT_DIR"
echo "  Предполагаемая корневая директория проекта: $ROOT_DIR"

if [ -d "$ROOT_DIR" ]; then
    echo "  ✅ Корневая директория проекта существует."
    echo "  Содержимое корневой директории (первые 10 файлов/папок):"
    ls -la "$ROOT_DIR" | head -n 12 | sed 's/^/    /'
else
    echo "  ❌ Корневая директория проекта не найдена: $ROOT_DIR"
fi
echo ""

echo "🔍 4. Проверка прав доступа для .command файлов:"
find "$ROOT_DIR/tools/macos" -name "*.command" -print0 | while IFS= read -r -d $'\0' file; do
    if [ -x "$file" ]; then
        echo "  ✅ Исполняемый: $(basename "$file")"
    else
        echo "  ❌ НЕ исполняемый: $(basename "$file")"
        echo "    -> Решение: chmod +x \"$file\""
    fi
done
echo ""

echo "🔍 5. Проверка зависимостей Python:"
if [ -f "$ROOT_DIR/requirements.txt" ]; then
    echo "  ✅ requirements.txt найден."
    echo "  Установка/проверка зависимостей (это может занять некоторое время):"
    python3 -m pip install -r "$ROOT_DIR/requirements.txt"
    if [ $? -eq 0 ]; then
        echo "  ✅ Все зависимости установлены."
    else
        echo "  ❌ Ошибка при установке зависимостей. Проверьте вывод выше."
    fi
else
    echo "  ❌ requirements.txt не найден. Создайте его."
fi
echo ""

echo "🔍 6. Тест импортов основных скриптов:"
echo "  Тестируем scripts/run_daily.py..."
python3 "$ROOT_DIR/scripts/run_daily.py" --test-import
if [ $? -eq 0 ]; then echo "  ✅ scripts/run_daily.py импортируется успешно."; else echo "  ❌ Ошибка импорта scripts/run_daily.py."; fi

echo "  Тестируем scripts/run_cards.py..."
python3 "$ROOT_DIR/scripts/run_cards.py" --test-import
if [ $? -eq 0 ]; then echo "  ✅ scripts/run_cards.py импортируется успешно."; else echo "  ❌ Ошибка импорта scripts/run_cards.py."; fi

echo "  Тестируем scripts/run_both.py..."
python3 "$ROOT_DIR/scripts/run_both.py" --test-import
if [ $? -eq 0 ]; then echo "  ✅ scripts/run_both.py импортируется успешно."; else echo "  ❌ Ошибка импорта scripts/run_both.py."; fi

echo "  Тестируем scripts/test_connection.py..."
python3 "$ROOT_DIR/scripts/test_connection.py" --test-import
if [ $? -eq 0 ]; then echo "  ✅ scripts/test_connection.py импортируется успешно."; else echo "  ❌ Ошибка импорта scripts/test_connection.py."; fi

echo "  Тестируем scripts/activate_promo.py..."
python3 "$ROOT_DIR/scripts/activate_promo.py" --test-import
if [ $? -eq 0 ]; then echo "  ✅ scripts/activate_promo.py импортируется успешно."; else echo "  ❌ Ошибка импорта scripts/activate_promo.py."; fi
echo ""

echo "=========================================="
echo "  Диагностика завершена."
echo "=========================================="
read -p "Нажмите Enter для выхода..."