#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Connection - Тест подключения к боту
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
    from combined_cycle import test_bot_connection
except ImportError as e:
    print(f"❌ Ошибка импорта combined_cycle: {e}")
    print(f"📁 Python path: {sys.path}")
    sys.exit(1)


async def main():
    """Запускает тест подключения к боту"""
    print("🔗 Тест подключения к боту...")
    await test_bot_connection()


if __name__ == "__main__":
    asyncio.run(main())


