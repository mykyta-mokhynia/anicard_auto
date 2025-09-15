#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Activate Promo - Активация промо для всех аккаунтов
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
    from combined_cycle import activate_promo_for_all_accounts
except ImportError as e:
    print(f"❌ Ошибка импорта combined_cycle: {e}")
    print(f"📁 Python path: {sys.path}")
    sys.exit(1)


async def main():
    """Интерактивная активация промо"""
    print("🎁 АКТИВАЦИЯ ПРОМО ДЛЯ ВСЕХ АККАУНТОВ")
    print("=" * 50)
    print()
    print("Поддерживаемые форматы:")
    print("1. Ссылка: https://t.me/anicardplaybot?start=CODE")
    print("2. Команда: /promo CODE")
    print()
    
    while True:
        promo_input = input("Введите промо-код или ссылку (или 'exit' для выхода): ").strip()
        
        if promo_input.lower() in ['exit', 'выход', 'quit']:
            print("👋 Выход из программы")
            break
        
        if not promo_input:
            print("❌ Промо-код не может быть пустым")
            continue
        
        print()
        print("🔄 Активируем промо...")
        print()
        
        await activate_promo_for_all_accounts(promo_input)
        
        print()
        choice = input("Хотите активировать еще одно промо? (y/n): ").strip().lower()
        if choice not in ['y', 'yes', 'да', 'д']:
            break
    
    print("🎉 Программа завершена!")


if __name__ == "__main__":
    asyncio.run(main())
