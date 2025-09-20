#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации работы системы фильтрации редких карт
"""

import json
import sys
import os

# Добавляем путь к скриптам
sys.path.append('scripts')

def load_rare_cards_filter():
    """
    Загружает список редких карт из JSON файла для фильтрации
    """
    try:
        # Ищем файл в текущей директории
        file_path = "rare_cards_filter.json"
        if not os.path.exists(file_path):
            # Если не найден, ищем в родительской директории
            file_path = os.path.join("..", "rare_cards_filter.json")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("cards", {})
    except FileNotFoundError:
        print("⚠️ Файл rare_cards_filter.json не найден")
        return {}
    except Exception as e:
        print(f"❌ Ошибка загрузки rare_cards_filter.json: {e}")
        return {}

def is_rare_card_by_name(card_name):
    """
    Проверяет, является ли карта редкой по названию из списка фильтрации
    Возвращает кортеж (категория, рейтинг) или (None, None)
    """
    rare_cards = load_rare_cards_filter()
    
    if not rare_cards:
        return None, None
    
    # Нормализуем название карты для поиска
    normalized_name = card_name.strip()
    
    # Проверяем по всем категориям редкости
    for category, cards in rare_cards.items():
        for card in cards:
            if card.get("name", "").strip() == normalized_name:
                rating = card.get("strength", None)
                return category, rating
    
    return None, None

def test_card_filter():
    """
    Тестирует систему фильтрации карт
    """
    print("🧪 Тестирование системы фильтрации редких карт")
    print("=" * 50)
    
    # Тестовые сообщения от бота
    test_messages = [
        {
            "text": """🪪 Получена новая боевая карточка

Редкость: Эпическая 🟢
Элемент: Дерево 🍃

🎴 Карта: Ханами
🔮 Вселенная: Магическая битва

Смотри аниме бесплатно прямо в Телеграм (https://t.me/anilibria_bot?start=anicardplaybot) в озвучке AniLibria""",
            "expected": None  # Ханами нет в списке, поэтому не должна сохраняться
        },
        {
            "text": """🪪 Получена новая боевая карточка

Редкость: Легендарная 🟡
Элемент: Огонь 🔥

🎴 Карта: Итачи Учиха
🔮 Вселенная: Наруто

Смотри аниме бесплатно прямо в Телеграм (https://t.me/anilibria_bot?start=anicardplaybot) в озвучке AniLibria""",
            "expected": "epic"  # Итачи Учиха есть в списке epic
        },
        {
            "text": """🪪 Получена новая боевая карточка

Редкость: Обычная 🔵
Элемент: Вода 💧

🎴 Карта: Неизвестная Карта
🔮 Вселенная: Тестовая

Смотри аниме бесплатно прямо в Телеграм (https://t.me/anilibria_bot?start=anicardplaybot) в озвучке AniLibria""",
            "expected": None
        }
    ]
    
    for i, test_case in enumerate(test_messages, 1):
        print(f"\n📝 Тест {i}:")
        text = test_case["text"]
        expected = test_case["expected"]
        
        # Извлекаем название карты и рейтинг
        import re
        name_match = re.search(r'🎴 Карта: (.+)', text)
        rating_match = re.search(r'Рейтинг: (\d+)', text)
        element_match = re.search(r'Элемент: (.+)', text)
        
        if name_match:
            card_name = name_match.group(1).strip()
            print(f"🎴 Название карты: {card_name}")
            
            if rating_match:
                rating = int(rating_match.group(1))
                print(f"⭐ Рейтинг: {rating}")
            
            if element_match:
                element = element_match.group(1).strip()
                print(f"🍃 Элемент: {element}")
            
            # Проверяем фильтрацию
            result = is_rare_card_by_name(card_name)
            if result and len(result) == 2:
                rarity, rating = result
            else:
                rarity, rating = None, None
                
            print(f"🔍 Результат фильтрации: {rarity}")
            if rating:
                print(f"📊 Рейтинг из списка: {rating}")
            print(f"✅ Ожидаемый результат: {expected}")
            
            if rarity == expected:
                print("✅ ТЕСТ ПРОЙДЕН")
            else:
                print("❌ ТЕСТ НЕ ПРОЙДЕН")
        else:
            print("❌ Не удалось извлечь название карты")
    
    print("\n" + "=" * 50)
    print("🎯 Демонстрация работы системы фильтрации завершена")

if __name__ == "__main__":
    test_card_filter()
