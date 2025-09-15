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

from combined_cycle import test_bot_connection


async def main():
    """Запускает тест подключения к боту"""
    print("🔗 Тест подключения к боту...")
    await test_bot_connection()


if __name__ == "__main__":
    asyncio.run(main())


