#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anicard Auto - Главное меню
Удобный интерфейс для запуска различных скриптов
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def clear_screen():
    """Очищает экран"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Выводит заголовок"""
    print("=" * 60)
    print("🎮 ANICARD AUTO - ГЛАВНОЕ МЕНЮ")
    print("=" * 60)
    print()

def print_menu():
    """Выводит главное меню"""
    print("📋 ВЫБЕРИТЕ ДЕЙСТВИЕ:")
    print()
    print("🔄 ОСНОВНЫЕ ЦИКЛЫ:")
    print("  1. Ежедневный цикл (22:01 UTC)")
    print("  2. Цикл карт (каждые 4ч 10с)")
    print("  3. Оба цикла (ежедневный + карты)")
    print("  4. Непрерывный цикл (работает постоянно)")
    print("  4a. Только цикл карт (непрерывно)")
    print("  4b. Только ежедневный цикл (непрерывно)")
    print()
    print("🎴 КАРТЫ И КОЛЛЕКЦИЯ:")
    print("  5. Просмотр редких карт")
    print("  6. Статистика карт по аккаунтам")
    print("  7. Поиск карты по названию")
    print()
    print("👤 УПРАВЛЕНИЕ АККАУНТАМИ:")
    print("  8. Авторизация новых аккаунтов")
    print("  9. Просмотр списка аккаунтов")
    print("  10. Тест подключения к боту")
    print("  11. Активация промо для всех аккаунтов")
    print()
    print("⚙️ НАСТРОЙКИ И УТИЛИТЫ:")
    print("  12. Просмотр логов ошибок")
    print("  13. Очистка старых логов")
    print("  14. Проверка конфигурации")
    print("  15. Обновление зависимостей")
    print()
    print("❌ ВЫХОД:")
    print("  0. Выход из программы")
    print()

def run_script(script_path, args=None):
    """Запускает Python скрипт"""
    try:
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при запуске скрипта: {e}")
    except FileNotFoundError:
        print(f"❌ Файл {script_path} не найден")

def view_rare_cards():
    """Просмотр редких карт"""
    print("\n🎴 ПРОСМОТР РЕДКИХ КАРТ")
    print("=" * 40)
    
    cards_folder = Path("accounts/cards")
    if not cards_folder.exists():
        print("❌ Папка с картами не найдена")
        return
    
    card_files = list(cards_folder.glob("*.json"))
    if not card_files:
        print("📭 Редких карт пока нет")
        return
    
    # Собираем все карты из всех аккаунтов
    all_cards = []
    
    for card_file in card_files:
        try:
            with open(card_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            account_name = card_file.stem
            
            for rarity, cards in data.items():
                for card in cards:
                    # Определяем рейтинг карты
                    rating = card.get('rating', 0)
                    if rating == 0 and rarity == 'adamantine':
                        rating = 101
                    elif rating == 0 and rarity == 'mythic':
                        rating = 99
                    elif rating == 0 and rarity == 'legendary':
                        rating = 87
                    elif rating == 0 and rarity == 'epic':
                        rating = 80
                    
                    # Извлекаем эмодзи из поля element
                    element = card.get('element', '')
                    element_emoji = "⚪"  # По умолчанию
                    
                    # Извлекаем эмодзи из строки element
                    import re
                    emoji_match = re.search(r'([🔥💧🌍💨🍃⚡🧊💡🌑⭐🌟✨💎🔮])', element)
                    if emoji_match:
                        element_emoji = emoji_match.group(1)
                    
                    all_cards.append({
                        'name': card['name'],
                        'rating': rating,
                        'element_emoji': element_emoji,
                        'account': account_name
                    })
                        
        except Exception as e:
            print(f"❌ Ошибка при чтении {card_file}: {e}")
    
    if not all_cards:
        print("📭 Редких карт пока нет")
        return
    
    # Сортируем по рейтингу (более редкие сверху)
    all_cards.sort(key=lambda x: x['rating'], reverse=True)
    
    # Выводим все карты в нужном формате
    print()
    for card in all_cards:
        print(f"{card['element_emoji']}{card['name']} - {card['rating']} ({card['account']})")
    
    print(f"\n📊 Всего редких карт: {len(all_cards)}")

def view_accounts():
    """Просмотр списка аккаунтов"""
    print("\n👤 СПИСОК АККАУНТОВ")
    print("=" * 40)
    
    try:
        with open("accounts/accounts.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        accounts = data.get("accounts", [])
        if not accounts:
            print("❌ Аккаунты не найдены")
            return
        
        print(f"📱 Всего аккаунтов: {len(accounts)}")
        print(f"⚙️ Concurrency: {data.get('concurrency', 'не указано')}")
        print(f"🤖 Бот: {data.get('bot', 'не указано')}")
        print()
        
        for i, acc in enumerate(accounts, 1):
            print(f"{i:2d}. {acc['session']} - {acc['phone']}")
            
    except FileNotFoundError:
        print("❌ Файл accounts.json не найден")
    except Exception as e:
        print(f"❌ Ошибка при чтении accounts.json: {e}")


def view_logs():
    """Просмотр логов ошибок"""
    print("\n📋 ЛОГИ ОШИБОК")
    print("=" * 40)
    
    logs_folder = Path("errors")
    if not logs_folder.exists():
        print("❌ Папка с логами не найдена")
        return
    
    log_files = list(logs_folder.glob("*.ndjson"))
    if not log_files:
        print("📭 Логов ошибок нет")
        return
    
    for log_file in log_files:
        print(f"\n📄 {log_file.name}:")
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   Всего записей: {len(lines)}")
                if lines:
                    print("   Последние 3 записи:")
                    for line in lines[-3:]:
                        try:
                            log_entry = json.loads(line.strip())
                            print(f"   • {log_entry.get('ts', 'N/A')} - {log_entry.get('kind', 'N/A')} - {log_entry.get('detail', 'N/A')}")
                        except:
                            print(f"   • {line.strip()[:50]}...")
        except Exception as e:
            print(f"   ❌ Ошибка при чтении: {e}")

def check_config():
    """Проверка конфигурации"""
    print("\n⚙️ ПРОВЕРКА КОНФИГУРАЦИИ")
    print("=" * 40)
    
    # Проверяем .env файл
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env файл найден")
    else:
        print("❌ .env файл не найден")
    
    # Проверяем accounts.json
    accounts_file = Path("accounts/accounts.json")
    if accounts_file.exists():
        print("✅ accounts.json найден")
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"   Аккаунтов: {len(data.get('accounts', []))}")
            print(f"   Concurrency: {data.get('concurrency', 'не указано')}")
        except Exception as e:
            print(f"   ❌ Ошибка при чтении: {e}")
    else:
        print("❌ accounts.json не найден")
    
    # Проверяем папку с картами
    cards_folder = Path("accounts/cards")
    if cards_folder.exists():
        card_files = list(cards_folder.glob("*.json"))
        print(f"✅ Папка с картами найдена ({len(card_files)} файлов)")
    else:
        print("❌ Папка с картами не найдена")
    
    # Проверяем requirements.txt
    req_file = Path("requirements.txt")
    if req_file.exists():
        print("✅ requirements.txt найден")
    else:
        print("❌ requirements.txt не найден")

def main():
    """Главная функция"""
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        try:
            choice = input("👉 Введите номер действия (0-15, 4a, 4b): ").strip()
            print()
            
            if choice == "0":
                print("👋 До свидания!")
                break
            elif choice == "1":
                print("🔄 Запуск ежедневного цикла...")
                run_script("scripts/run_daily.py")
            elif choice == "2":
                print("🎴 Запуск цикла карт...")
                run_script("scripts/run_cards.py")
            elif choice == "3":
                print("🔄 Запуск обоих циклов...")
                run_script("scripts/run_both.py")
            elif choice == "4":
                print("♾️ Запуск непрерывного цикла...")
                run_script("scripts/continuous_cycle.py")
            elif choice == "4a":
                print("🎴 Запуск непрерывного цикла карт...")
                run_script("scripts/continuous_cycle.py", ["cards"])
            elif choice == "4b":
                print("🌅 Запуск непрерывного ежедневного цикла...")
                run_script("scripts/continuous_cycle.py", ["daily"])
            elif choice == "5":
                view_rare_cards()
            elif choice == "6":
                print("📊 Статистика карт...")
                run_script("scripts/card_stats.py")
            elif choice == "7":
                print("🔍 Поиск карты...")
                run_script("scripts/card_stats.py")
            elif choice == "8":
                print("👤 Запуск авторизации...")
                run_script("scripts/auth_manager.py")
            elif choice == "9":
                view_accounts()
            elif choice == "10":
                print("🔗 Тест подключения к боту...")
                run_script("scripts/test_connection.py")
            elif choice == "11":
                print("🎁 Активация промо для всех аккаунтов...")
                run_script("scripts/activate_promo.py")
            elif choice == "12":
                view_logs()
            elif choice == "13":
                print("🧹 Очистка логов...")
                run_script("scripts/clean_logs.py")
            elif choice == "14":
                check_config()
            elif choice == "15":
                print("📦 Обновление зависимостей...")
                run_script("pip", ["install", "-r", "requirements.txt"])
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
            
            if choice != "0":
                input("\n⏸️ Нажмите Enter для продолжения...")
                
        except KeyboardInterrupt:
            print("\n\n👋 Программа прервана пользователем")
            break
        except Exception as e:
            print(f"❌ Произошла ошибка: {e}")
            input("\n⏸️ Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()