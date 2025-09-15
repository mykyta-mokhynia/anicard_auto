#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Cards Cycle - Запуск только цикла карт
"""

import os
import sys
import asyncio

# Добавляем родительскую директорию в путь для импорта combined_cycle.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from combined_cycle import run_card_cycle


async def main():
    """Запускает только цикл карт"""
    print("🎴 Запуск цикла карт...")
    await run_card_cycle()


if __name__ == "__main__":
    asyncio.run(main())


