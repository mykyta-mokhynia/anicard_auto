#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Both Cycles - Запуск обоих циклов
"""

import os
import sys
import asyncio

# Добавляем родительскую директорию в путь для импорта combined_cycle.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Проверяем, что combined_cycle.py существует
combined_cycle_path = os.path.join(PARENT_DIR, "combined_cycle.py")
if not os.path.exists(combined_cycle_path):
    print(f"❌ Файл combined_cycle.py не найден по пути: {combined_cycle_path}")
    print(f"📁 Текущая директория: {os.getcwd()}")
    print(f"📁 Директория скрипта: {CURRENT_DIR}")
    print(f"📁 Родительская директория: {PARENT_DIR}")
    sys.exit(1)

try:
    from combined_cycle import run_daily_cycle, run_card_cycle
except ImportError as e:
    print(f"❌ Ошибка импорта combined_cycle: {e}")
    print(f"📁 Python path: {sys.path}")
    sys.exit(1)


async def main():
    """Запускает оба цикла последовательно"""
    print("🔄 Запуск обоих циклов...")

    # Сначала ежедневный цикл
    print("🌅 Выполняем ежедневный цикл...")
    await run_daily_cycle()

    # Небольшая пауза между циклами
    print("⏸️ Пауза 5 секунд между циклами...")
    await asyncio.sleep(5)

    # Затем цикл карт
    print("🎴 Выполняем цикл карт...")
    await run_card_cycle()

    print("🎉 Оба цикла завершены!")


if __name__ == "__main__":
    asyncio.run(main())


