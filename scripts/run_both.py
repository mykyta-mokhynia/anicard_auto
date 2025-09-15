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

from combined_cycle import run_daily_cycle, run_card_cycle


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


