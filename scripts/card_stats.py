#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Card Statistics - Статистика карт
Показывает подробную статистику по редким картам
"""

import json
import os
from pathlib import Path
from collections import Counter
from datetime import datetime

def load_cards_data():
    """Загружает данные о картах из всех файлов"""
    cards_folder = Path("accounts/cards")
    if not cards_folder.exists():
        return {}
    
    all_cards = {}
    for card_file in cards_folder.glob("*.json"):
        try:
            with open(card_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            all_cards[card_file.stem] = data
        except Exception as e:
            print(f"❌ Ошибка при чтении {card_file}: {e}")
    
    return all_cards

def print_general_stats(all_cards):
    """Выводит общую статистику"""
    print("📊 ОБЩАЯ СТАТИСТИКА")
    print("=" * 50)
    
    total_cards = 0
    rarity_counts = Counter()
    account_counts = {}
    
    for account, data in all_cards.items():
        account_total = 0
        for rarity, cards in data.items():
            count = len(cards)
            total_cards += count
            account_total += count
            rarity_counts[rarity] += count
        
        account_counts[account] = account_total
    
    print(f"👤 Аккаунтов с картами: {len(account_counts)}")
    print(f"🎴 Всего редких карт: {total_cards}")
    print()
    
    print("📈 ПО РЕДКОСТИ:")
    rarity_emojis = {"epic": "🟣", "legendary": "🟡", "mythic": "🔴", "adamantine": "💎"}
    for rarity, count in rarity_counts.most_common():
        emoji = rarity_emojis.get(rarity, "⚪")
        percentage = (count / total_cards * 100) if total_cards > 0 else 0
        print(f"  {emoji} {rarity.upper()}: {count} карт ({percentage:.1f}%)")
    
    print()
    print("👤 ПО АККАУНТАМ:")
    for account, count in sorted(account_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {account}: {count} карт")

def print_account_details(all_cards):
    """Выводит детальную статистику по аккаунтам"""
    print("\n📋 ДЕТАЛЬНАЯ СТАТИСТИКА ПО АККАУНТАМ")
    print("=" * 50)
    
    for account, data in all_cards.items():
        print(f"\n👤 {account}:")
        
        total = 0
        for rarity, cards in data.items():
            if cards:
                emoji = {"epic": "🟣", "legendary": "🟡", "mythic": "🔴", "adamantine": "💎"}.get(rarity, "⚪")
                print(f"  {emoji} {rarity.upper()}: {len(cards)} карт")
                total += len(cards)
                
                # Показываем топ-3 карты по рейтингу
                sorted_cards = sorted(cards, key=lambda x: x.get('rating', 0), reverse=True)
                for card in sorted_cards[:3]:
                    print(f"    • {card['name']} (Рейтинг: {card['rating']})")
                if len(cards) > 3:
                    print(f"    ... и еще {len(cards) - 3} карт")
        
        print(f"  📊 Всего: {total} карт")

def print_rare_cards_list(all_cards, min_rating=90):
    """Выводит список самых редких карт"""
    print(f"\n💎 САМЫЕ РЕДКИЕ КАРТЫ (рейтинг {min_rating}+)")
    print("=" * 50)
    
    rare_cards = []
    for account, data in all_cards.items():
        for rarity, cards in data.items():
            for card in cards:
                if card.get('rating', 0) >= min_rating:
                    rare_cards.append({
                        'account': account,
                        'name': card['name'],
                        'rating': card['rating'],
                        'rarity': rarity,
                        'universe': card.get('universe', ''),
                        'element': card.get('element', '')
                    })
    
    # Сортируем по рейтингу
    rare_cards.sort(key=lambda x: x['rating'], reverse=True)
    
    if not rare_cards:
        print(f"📭 Карт с рейтингом {min_rating}+ не найдено")
        return
    
    rarity_emojis = {"epic": "🟣", "legendary": "🟡", "mythic": "🔴", "adamantine": "💎"}
    
    for i, card in enumerate(rare_cards[:20], 1):  # Показываем топ-20
        emoji = rarity_emojis.get(card['rarity'], "⚪")
        print(f"{i:2d}. {emoji} {card['name']} (Рейтинг: {card['rating']}) - {card['account']}")
        if card['universe']:
            print(f"    🌍 Вселенная: {card['universe']}")
        if card['element']:
            print(f"    🍃 Элемент: {card['element']}")
    
    if len(rare_cards) > 20:
        print(f"\n... и еще {len(rare_cards) - 20} карт")

def search_cards(all_cards, search_term):
    """Поиск карт по названию"""
    print(f"\n🔍 ПОИСК КАРТ: '{search_term}'")
    print("=" * 50)
    
    found_cards = []
    for account, data in all_cards.items():
        for rarity, cards in data.items():
            for card in cards:
                if search_term.lower() in card['name'].lower():
                    found_cards.append({
                        'account': account,
                        'name': card['name'],
                        'rating': card['rating'],
                        'rarity': rarity,
                        'universe': card.get('universe', ''),
                        'element': card.get('element', '')
                    })
    
    if not found_cards:
        print(f"📭 Карты с названием '{search_term}' не найдены")
        return
    
    print(f"✅ Найдено карт: {len(found_cards)}")
    print()
    
    rarity_emojis = {"epic": "🟣", "legendary": "🟡", "mythic": "🔴", "adamantine": "💎"}
    
    for card in found_cards:
        emoji = rarity_emojis.get(card['rarity'], "⚪")
        print(f"🎴 {emoji} {card['name']} (Рейтинг: {card['rating']}) - {card['account']}")
        if card['universe']:
            print(f"   🌍 Вселенная: {card['universe']}")
        if card['element']:
            print(f"   🍃 Элемент: {card['element']}")
        print()

def main():
    """Главная функция"""
    print("🎴 СТАТИСТИКА РЕДКИХ КАРТ")
    print("=" * 50)
    
    all_cards = load_cards_data()
    
    if not all_cards:
        print("❌ Карты не найдены. Запустите скрипт получения карт.")
        return
    
    while True:
        print("\n📋 ВЫБЕРИТЕ ДЕЙСТВИЕ:")
        print("1. Общая статистика")
        print("2. Детальная статистика по аккаунтам")
        print("3. Самые редкие карты (90+)")
        print("4. Самые редкие карты (100+)")
        print("5. Поиск карты по названию")
        print("0. Выход")
        
        choice = input("\n👉 Введите номер: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            print_general_stats(all_cards)
        elif choice == "2":
            print_account_details(all_cards)
        elif choice == "3":
            print_rare_cards_list(all_cards, 90)
        elif choice == "4":
            print_rare_cards_list(all_cards, 100)
        elif choice == "5":
            search_term = input("🔍 Введите название карты для поиска: ").strip()
            if search_term:
                search_cards(all_cards, search_term)
        else:
            print("❌ Неверный выбор")
        
        if choice != "0":
            input("\n⏸️ Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()

