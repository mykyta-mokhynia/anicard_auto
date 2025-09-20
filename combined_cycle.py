#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anicard Combined Cycle - Объединенный цикл
Сочетает ежедневный цикл (22:01 UTC) и цикл карт (каждые 4ч 10с)
"""

import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# Загружаем переменные окружения
load_dotenv()

# === КОНФИГУРАЦИЯ ===
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MESSAGE_TIMEOUT_MS = int(os.getenv("MESSAGE_TIMEOUT", "700"))
MESSAGE_TIMEOUT = MESSAGE_TIMEOUT_MS / 1000.0

# Папка для сохранения редких карт
CARDS_FOLDER = "accounts/cards"
if not os.path.exists(CARDS_FOLDER):
    os.makedirs(CARDS_FOLDER)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def is_rare_card(rating):
    """
    Проверяет, является ли карта редкой по рейтингу
    Сохраняем только: 80, 87-90, 99-101
    """
    if rating == 101:
        return "adamantine"
    elif rating >= 99 and rating <= 100:
        return "mythic"
    elif rating >= 87 and rating <= 90:
        return "legendary"
    elif rating == 80:
        return "epic"
    else:
        return None

def parse_card_response(text, card_type):
    """
    Парсит ответ бота о получении карты
    """
    try:
        # Парсим рейтинг
        rating_match = re.search(r'(\d+)\s*\|', text)
        if not rating_match:
            return None
        
        rating = int(rating_match.group(1))
        
        # Парсим название карты
        name_match = re.search(r'\|\s*([^🔮\n]+)', text)
        name = name_match.group(1).strip() if name_match else "Неизвестно"
        
        # Парсим вселенную
        universe_match = re.search(r'🔮\s*Вселенная:\s*([^\n]+)', text)
        universe = universe_match.group(1).strip() if universe_match else ""
        
        # Парсим элемент
        element_match = re.search(r'🍃\s*Элемент:\s*([^\n]+)', text)
        element = element_match.group(1).strip() if element_match else ""
        
        return {
            "name": name,
            "rating": rating,
            "universe": universe,
            "element": element,
            "type": card_type
        }
    except Exception as e:
        print(f"❌ Ошибка при парсинге карты: {e}")
        return None

def save_card_to_file(session_name, card_info):
    """
    Сохраняет редкую карту в файл
    """
    try:
        rarity = is_rare_card(card_info["rating"])
        if not rarity:
            return
        
        file_path = os.path.join(CARDS_FOLDER, f"{session_name}.json")
        
        # Загружаем существующие данные
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"legendary": [], "mythic": [], "adamantine": [], "epic": []}
        
        # Проверяем, нет ли уже такой карты
        for existing_card in data[rarity]:
            if existing_card["name"] == card_info["name"]:
                print(f"🔄 [{session_name}] Карта {card_info['name']} уже есть в коллекции")
                return
        
        # Добавляем новую карту
        data[rarity].append({
            "name": card_info["name"],
            "universe": card_info["universe"],
            "element": card_info["element"],
            "rating": card_info["rating"],
            "type": card_info["type"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Сортируем по названию
        data[rarity].sort(key=lambda x: x["name"])
        
        # Сохраняем
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 [{session_name}] Редкая карта сохранена: {card_info['name']} ({rarity})")
        
    except Exception as e:
        print(f"❌ [{session_name}] Ошибка сохранения карты: {e}")

def send_card_notification(session_name, card_info):
    """
    Отправляет уведомление о получении редкой карты
    """
    rarity_emoji = {
        "epic": "🟣",
        "legendary": "🟡", 
        "mythic": "🔴",
        "adamantine": "💎"
    }
    
    emoji = rarity_emoji.get(card_info["rarity"], "⚪")
    print(f"🎉 [{session_name}] НОВАЯ РЕДКАЯ КАРТА! {emoji} {card_info['name']} (Рейтинг: {card_info['rating']}, {card_info['rarity']})")

async def wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT, regex=None, contains=None):
    """
    Ждём НОВОЕ сообщение от entity (бота).
    Можно фильтровать по подстроке (contains) или regex.
    Игнорирует видео, квесты и системные сообщения.
    """
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    @client.on(events.NewMessage(from_users=entity))
    async def handler(event):
        text = event.raw_text or ""
        
        # Игнорируем видео сообщения
        if event.message.video:
            print(f"🎥 [{client.session.filename}] Получено видео сообщение - игнорируем")
            return
            
        # Игнорируем системные сообщения бота
        system_messages = [
            "Получена новая",
            "Вам попалась повторная карта", 
            "Следующая попытка будет доступна",
            "повторная карта",
            "следующая попытка",
            "будет доступна"
        ]
        
        if any(sys_msg.lower() in text.lower() for sys_msg in system_messages):
            print(f"ℹ️ [{client.session.filename}] Системное сообщение: {text[:50]}...")
            return
            
        # Игнорируем квестовые сообщения (обычно содержат "квест", "задание", "миссия")
        quest_keywords = ["квест", "задание", "миссия", "quest", "mission"]
        if any(keyword in text.lower() for keyword in quest_keywords):
            print(f"📋 [{client.session.filename}] Квестовое сообщение: {text[:50]}...")
            return
        
        # Применяем пользовательские фильтры
        if (contains and contains.lower() in text.lower()) or \
           (regex and re.search(regex, text, re.I)) or \
           (not contains and not regex):
            if not fut.done():
                fut.set_result(event.message)

    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    finally:
        client.remove_event_handler(handler)

async def click_button(msg, *, text=None, regex=None, index=None, case_insensitive=True):
    """
    Клик по инлайн-кнопке в сообщении:
    - text: точное совпадение подписи
    - regex: регулярка по подписи
    - index: порядковый номер (0..N-1), слева направо, сверху вниз
    Возвращает True/False.
    """
    if not msg or not msg.buttons:
        return False
    flat = [b for row in msg.buttons for b in row]
    if index is not None:
        if 0 <= index < len(flat):
            await flat[index].click()
            return True
        return False

    def norm(s):
        return (s or "") if not case_insensitive else (s or "").lower()

    for b in flat:
        bt = b.text or ""
        if text and norm(bt) == norm(text):
            await b.click()
            return True
        if regex and re.search(regex, bt, re.I if case_insensitive else 0):
            await b.click()
            return True
    return False

async def send_message_and_wait(client, entity, message, timeout=MESSAGE_TIMEOUT):
    """
    Отправляет сообщение и ждет ответ
    """
    await client.send_message(entity, message)
    await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после отправки
    try:
        return await wait_new_from(client, entity, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"⚠️ [{client.session.filename}] Таймаут при ожидании ответа на '{message}'")
        # Пытаемся получить последнее сообщение
        try:
            async for message in client.iter_messages(entity, limit=1):
                return message
        except:
            return None

async def click_button_and_wait(client, entity, msg, button_text=None, button_index=None, timeout=MESSAGE_TIMEOUT):
    """
    Нажимает кнопку и ждет новое сообщение
    """
    try:
        if button_text:
            clicked = await click_button(msg, text=button_text)
        elif button_index is not None:
            clicked = await click_button(msg, index=button_index)
        else:
            return None
        
        if clicked:
            try:
                return await wait_new_from(client, entity, timeout=timeout)
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при ожидании ответа после клика")
                # Пытаемся получить последнее сообщение
                try:
                    async for message in client.iter_messages(entity, limit=1):
                        return message
                except:
                    return None
        else:
            print(f"⚠️ [{client.session.filename}] Кнопка не найдена: {button_text or f'index {button_index}'}")
        return None
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в click_button_and_wait: {e}")
        return None

# === ЕЖЕДНЕВНЫЙ ЦИКЛ ===

async def daily_cycle_for_account(client, bot_username):
    """
    Ежедневный цикл для одного аккаунта
    """
    try:
        entity = await client.get_entity(bot_username)
        print(f"🎯 [{client.session.filename}] Начинаем ежедневный цикл...")
        
        # Добавляем небольшую задержку между аккаунтами
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # 1. Отправляем "📜 Меню"
        print(f"📜 [{client.session.filename}] Отправляем 'Меню'...")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
        msg = await send_message_and_wait(client, entity, "📜 Меню")
        print(f"✅ [{client.session.filename}] Меню получено")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

        # 2. AniPass
        print(f"🎫 [{client.session.filename}] Нажимаем 'AniPass'...")
        try:
            # Ищем кнопку AniPass
            if msg and msg.buttons:
                button_texts = [b.text for row in msg.buttons for b in row]
                print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                
                # Ищем кнопку AniPass
                anipass_button = None
                for button_text in button_texts:
                    if "AniPass" in button_text or "🎫" in button_text:
                        anipass_button = button_text
                        break
                
                if anipass_button:
                    print(f"🎫 [{client.session.filename}] Найдена кнопка: {anipass_button}")
                    msg = await click_button_and_wait(client, entity, msg, button_text=anipass_button)
                    if msg:
                        print(f"✅ [{client.session.filename}] AniPass открыт")
                        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                        
                        # Проверяем доступность AniPass
                        if msg.buttons:
                            button_texts = [b.text for row in msg.buttons for b in row]
                            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                            
                            # Ищем кнопку с галочкой (✔️ - доступен, ✅ - уже забран)
                            checkmark_button = None
                            available_buttons = []
                            taken_buttons = []
                            
                            for button_text in button_texts:
                                if "✔️" in button_text:  # Heavy check mark - доступен для получения
                                    available_buttons.append(button_text)
                                elif "✅" in button_text:  # Check mark - уже забран
                                    taken_buttons.append(button_text)
                            
                            print(f"📊 [{client.session.filename}] Доступные кнопки: {available_buttons}")
                            print(f"📊 [{client.session.filename}] Забранные кнопки: {taken_buttons}")
                            
                            if available_buttons:
                                # Берем первую доступную кнопку
                                checkmark_button = available_buttons[0]
                                print(f"🎯 [{client.session.filename}] Выбрана кнопка для получения: {checkmark_button}")
                            elif taken_buttons:
                                print(f"ℹ️ [{client.session.filename}] Все доступные награды уже забраны")
                            else:
                                print(f"⚠️ [{client.session.filename}] Не найдено ни доступных, ни забранных кнопок AniPass")
                            
                            if checkmark_button:
                                print(f"✅ [{client.session.filename}] AniPass доступен, нажимаем галочку")
                                # Сохраняем ссылку на сообщение с меню AniPass
                                anipass_menu_msg = msg
                                reward_msg = await click_button_and_wait(client, entity, msg, button_text=checkmark_button)
                                if reward_msg:
                                    print(f"✅ [{client.session.filename}] AniPass получен")
                                    await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после получения
                                    # Используем сохраненное сообщение с меню для возврата
                                    msg = anipass_menu_msg
                                else:
                                    print(f"⚠️ [{client.session.filename}] Не удалось получить AniPass")
                            else:
                                print(f"ℹ️ [{client.session.filename}] AniPass уже забран за день, пропускаем...")
                        
                        # Нажимаем "Назад" - теперь используем правильное сообщение с кнопками
                        print(f"🔙 [{client.session.filename}] Нажимаем 'Назад'...")
                        msg = await click_button_and_wait(client, entity, msg, button_text="Назад 🔙")
                        if msg:
                            print(f"✅ [{client.session.filename}] Вернулись в главное меню")
                            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после возврата
                else:
                    print(f"⚠️ [{client.session.filename}] Кнопка AniPass не найдена")
            else:
                print(f"⚠️ [{client.session.filename}] Нет кнопок в сообщении")
        except Exception as e:
            print(f"⚠️ [{client.session.filename}] Ошибка в AniPass: {e}")

        # 3. Дары богов
        print(f"⛩ [{client.session.filename}] Переходим в 'Дары богов'...")
        try:
            # Ищем кнопку "Дары богов"
            if msg and msg.buttons:
                button_texts = [b.text for row in msg.buttons for b in row]
                print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                
                # Ищем кнопку "Дары богов"
                gifts_button = None
                for button_text in button_texts:
                    if "Дары богов" in button_text or "⛩" in button_text:
                        gifts_button = button_text
                        break
                
                if gifts_button:
                    print(f"⛩ [{client.session.filename}] Найдена кнопка: {gifts_button}")
                    msg = await click_button_and_wait(client, entity, msg, button_text=gifts_button)
                    if msg:
                        print(f"✅ [{client.session.filename}] Дары богов открыты")
                        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                        
                        # Получаем награды
                        print(f"🎁 [{client.session.filename}] Получаем награды...")
                        
                        # Мистический жетон (ежедневно)
                        print(f"🀄️ [{client.session.filename}] Получаем мистический жетон...")
                        try:
                            reward_msg = await click_button_and_wait(client, entity, msg, button_text="🀄️ Мистический жетон")
                            if reward_msg:
                                print(f"🀄️ [{client.session.filename}] Награда получена, ждем новое сообщение с артефактами...")
                                # Ждем новое сообщение с артефактами после получения жетона
                                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT*2, contains="Прикоснись к  древним артефактам")
                                if msg:
                                    print(f"✅ [{client.session.filename}] Получено обновленное сообщение с артефактами")
                                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после получения
                        except Exception as e:
                            print(f"⚠️ [{client.session.filename}] Таймаут при получении жетона")
                        
                        # Древний куб удачи (еженедельно)
                        print(f"🎲 [{client.session.filename}] Получаем древний куб удачи...")
                        try:
                            reward_msg = await click_button_and_wait(client, entity, msg, button_text="🎲 Древний куб удачи")
                            if reward_msg:
                                print(f"🎲 [{client.session.filename}] Награда получена, ждем новое сообщение с артефактами...")
                                # Ждем новое сообщение с артефактами после получения куба
                                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT*2, contains="Прикоснись к  древним артефактам")
                                if msg:
                                    print(f"✅ [{client.session.filename}] Получено обновленное сообщение с артефактами")
                                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после получения
                        except Exception as e:
                            print(f"⚠️ [{client.session.filename}] Таймаут при получении куба удачи")
                        
                        # Рог призыва (еженедельно)
                        print(f"📯 [{client.session.filename}] Получаем рог призыва...")
                        try:
                            reward_msg = await click_button_and_wait(client, entity, msg, button_text="📯 Рог призыва")
                            if reward_msg:
                                print(f"📯 [{client.session.filename}] Награда получена, ждем новое сообщение с артефактами...")
                                # Ждем новое сообщение с артефактами после получения рога
                                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT*2, contains="Прикоснись к  древним артефактам")
                                if msg:
                                    print(f"✅ [{client.session.filename}] Получено обновленное сообщение с артефактами")
                                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после получения
                        except Exception as e:
                            print(f"⚠️ [{client.session.filename}] Таймаут при получении рога призыва")
                        
                        # Убеждаемся, что у нас есть актуальное сообщение с кнопкой "Назад"
                        if not msg or "Прикоснись к  древним артефактам" not in msg.raw_text:
                            print(f"🪤 [{client.session.filename}] Получаем актуальное сообщение с артефактами...")
                            try:
                                async for message in client.iter_messages(entity, limit=1):
                                    msg = message
                                    break
                            except Exception as e:
                                print(f"⚠️ [{client.session.filename}] Ошибка при получении последнего сообщения: {e}")
                        
                        # Нажимаем "Назад" - теперь в правильном сообщении
                        print(f"🔙 [{client.session.filename}] Нажимаем 'Назад'...")
                        msg = await click_button_and_wait(client, entity, msg, button_text="Назад 🔙")
                        if msg:
                            print(f"✅ [{client.session.filename}] Вернулись в главное меню")
                            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после возврата
                else:
                    print(f"⚠️ [{client.session.filename}] Кнопка 'Дары богов' не найдена")
            else:
                print(f"⚠️ [{client.session.filename}] Нет кнопок в сообщении")
        except Exception as e:
            print(f"⚠️ [{client.session.filename}] Ошибка в 'Дары богов': {e}")

        # 4. Крафт меню
        print(f"🧬 [{client.session.filename}] Переходим в 'Крафт меню'...")
        try:
            # Ищем кнопку "Крафт меню"
            if msg and msg.buttons:
                button_texts = [b.text for row in msg.buttons for b in row]
                print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                
                # Ищем кнопку "Крафт меню"
                craft_button = None
                for button_text in button_texts:
                    if "Крафт" in button_text or "🧬" in button_text:
                        craft_button = button_text
                        break
                
                if craft_button:
                    print(f"🧬 [{client.session.filename}] Найдена кнопка: {craft_button}")
                    craft_msg = await click_button_and_wait(client, entity, msg, button_text=craft_button)
                    if craft_msg:
                        print(f"✅ [{client.session.filename}] Крафт меню открыто, ждем новое сообщение...")
                        # Ждем новое сообщение с вариантами получения карт
                        try:
                            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT*2, contains="В Аникарде есть много способов получить новые карты")
                            if msg:
                                print(f"✅ [{client.session.filename}] Получено сообщение с вариантами получения карт")
                            else:
                                print(f"⚠️ [{client.session.filename}] Не получено ожидаемое сообщение, используем последнее")
                                msg = craft_msg
                        except Exception as e:
                            print(f"⚠️ [{client.session.filename}] Ошибка при ожидании нового сообщения: {e}")
                            msg = craft_msg
                        
                        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                        
                        # Омут душ
                        print(f"🌊 [{client.session.filename}] Нажимаем 'Омут душ'...")
                        try:
                            msg = await click_button_and_wait(client, entity, msg, button_text="🪞 Омут душ")
                            if msg:
                                print(f"✅ [{client.session.filename}] Омут душ открыт")
                                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                                
                                # Пожертвовать все эссенции
                                print(f"💎 [{client.session.filename}] Пожертвуем все эссенции...")
                                try:
                                    msg = await click_button_and_wait(client, entity, msg, button_text="🔘 Пожертвовать все эссенции/проекции душ 🔘")
                                    if msg:
                                        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после пожертвования
                                except Exception as e:
                                    print(f"⚠️ [{client.session.filename}] Таймаут при пожертвовании, пробуем продолжить...")
                        except Exception as e:
                            print(f"⚠️ [{client.session.filename}] Таймаут при переходе в 'Омут душ', пробуем продолжить...")
                else:
                    print(f"⚠️ [{client.session.filename}] Кнопка 'Крафт меню' не найдена")
            else:
                print(f"⚠️ [{client.session.filename}] Нет кнопок в сообщении")
        except Exception as e:
            print(f"⚠️ [{client.session.filename}] Ошибка в 'Крафт меню': {e}")

        # 5. Клан
        print(f"🛡 [{client.session.filename}] Проверяем клан...")
        try:
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
            msg = await send_message_and_wait(client, entity, "🛡 Мой клан")
            
            if msg and "У вас нет клана" in msg.raw_text:
                print(f"ℹ️ [{client.session.filename}] У аккаунта нет клана, пропускаем сокровищницу")
            else:
                print(f"🏰 [{client.session.filename}] У аккаунта есть клан, проверяем сокровищницу...")
                if msg and msg.buttons:
                    button_texts = [b.text for row in msg.buttons for b in row]
                    print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                    
                    # Ищем кнопку сокровищницы
                    treasury_button = None
                    for button_text in button_texts:
                        if "Сокровищница" in button_text or "💰" in button_text:
                            treasury_button = button_text
                            break
                    
                    if treasury_button:
                        print(f"💰 [{client.session.filename}] Найдена кнопка: {treasury_button}")
                        msg = await click_button_and_wait(client, entity, msg, button_text=treasury_button)
                        if msg:
                            print(f"✅ [{client.session.filename}] Сокровищница открыта")
                            
                            # Проверяем доступные выплаты и нажимаем кнопку
                            if "Нет доступных выплат" in msg.raw_text:
                                print(f"ℹ️ [{client.session.filename}] Нет доступных выплат")
                            else:
                                print(f"💰 [{client.session.filename}] Есть доступные выплаты")
                                
                                # Ищем кнопку "Получить выплату"
                                if msg.buttons:
                                    button_texts = [b.text for row in msg.buttons for b in row]
                                    print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                                    
                                    payout_button = None
                                    for button_text in button_texts:
                                        if "Получить выплату" in button_text or "выплату" in button_text.lower():
                                            payout_button = button_text
                                            break
                                    
                                    if payout_button:
                                        print(f"💰 [{client.session.filename}] Нажимаем '{payout_button}'...")
                                        msg = await click_button_and_wait(client, entity, msg, button_text=payout_button)
                                        if msg:
                                            print(f"✅ [{client.session.filename}] Выплата получена")
                                        else:
                                            print(f"⚠️ [{client.session.filename}] Не удалось получить выплату")
                                    else:
                                        print(f"⚠️ [{client.session.filename}] Кнопка 'Получить выплату' не найдена")
                    else:
                        print(f"⚠️ [{client.session.filename}] Кнопка 'Сокровищница' не найдена")
                else:
                    print(f"⚠️ [{client.session.filename}] Нет кнопок в сообщении")
        except Exception as e:
            print(f"⚠️ [{client.session.filename}] Ошибка при проверке клана: {e}")

        # 6. Магазин
        print(f"🛍 [{client.session.filename}] Переходим в магазин...")
        try:
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
            msg = await send_message_and_wait(client, entity, "🛍 Магазин")
            print(f"✅ [{client.session.filename}] В магазине")
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
            
            # Крутки за BattleCoin
            print(f"🎰 [{client.session.filename}] Нажимаем 'крутки за BattleCoin'...")
            try:
                # Ищем кнопку "Крутки за BattleCoin"
                if msg and msg.buttons:
                    button_texts = [b.text for row in msg.buttons for b in row]
                    print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                    
                    # Ищем кнопку "Крутки за BattleCoin"
                    battlecoin_button = None
                    for button_text in button_texts:
                        if "BattleCoin" in button_text or "🎖️" in button_text:
                            battlecoin_button = button_text
                            break
                    
                    if battlecoin_button:
                        print(f"🎰 [{client.session.filename}] Найдена кнопка: {battlecoin_button}")
                        msg = await click_button_and_wait(client, entity, msg, button_text=battlecoin_button)
                        if msg:
                            print(f"✅ [{client.session.filename}] Крутки открыты")
                            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                            
                            # Покупаем 10 ⚔️
                            print(f"⚔️ [{client.session.filename}] Нажимаем '10 ⚔️'...")
                            try:
                                msg = await click_button_and_wait(client, entity, msg, button_text="10 ⚔️")
                                if msg:
                                    await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после покупки
                            except Exception as e:
                                print(f"⚠️ [{client.session.filename}] Таймаут при покупке круток, пробуем продолжить...")
                    else:
                        print(f"⚠️ [{client.session.filename}] Кнопка 'Крутки за BattleCoin' не найдена")
                else:
                    print(f"⚠️ [{client.session.filename}] Нет кнопок в сообщении")
            except Exception as e:
                print(f"⚠️ [{client.session.filename}] Таймаут при переходе в крутки, пробуем продолжить...")
        except Exception as e:
            print(f"⚠️ [{client.session.filename}] Ошибка в магазине: {e}")

        # 7. Профиль и попытки
        print(f"🎒 [{client.session.filename}] Получаем профиль...")
        try:
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
            msg = await send_message_and_wait(client, entity, "🎒 Профиль")
            print(f"✅ [{client.session.filename}] Профиль получен")
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

            # Парсим попытки
            profile_text = msg.raw_text
            attempts_match = re.search(r'Попытки:\s*·\s*⚔️\s*-\s*(\d+)\s*\|\s*🎭\s*-\s*(\d+)', profile_text)
            
            # Инициализируем список редких карт
            rare_cards = []
            
            if attempts_match:
                battle_attempts = int(attempts_match.group(1))
                collection_attempts = int(attempts_match.group(2))
                print(f"📊 [{client.session.filename}] Попытки: ⚔️ {battle_attempts} | 🎭 {collection_attempts}")
                
                # Тратим попытки
                if battle_attempts > 0 or collection_attempts > 0:
                    print(f"🎯 [{client.session.filename}] Проверяем попытки...")
                    
                    if battle_attempts > 0:
                        battle_rare = await use_attempts(client, entity, battle_attempts, "battle")
                        rare_cards.extend(battle_rare)
                    
                    if collection_attempts > 0:
                        collection_rare = await use_attempts(client, entity, collection_attempts, "collection")
                        rare_cards.extend(collection_rare)
                else:
                    print(f"ℹ️ [{client.session.filename}] Нет попыток для траты")
            else:
                print(f"ℹ️ [{client.session.filename}] Попытки не найдены в профиле")
            
            # Тратим по 1 крутке каждого вида (дополнительно)
            print(f"🎯 [{client.session.filename}] Тратим по 1 крутке каждого вида...")
            
            # Тратим боевую крутку
            battle_rare = await use_attempts(client, entity, 1, "battle")
            rare_cards.extend(battle_rare)
            
            # Задержка между крутками
            await asyncio.sleep(MESSAGE_TIMEOUT)
            
            # Тратим коллекционную крутку
            collection_rare = await use_attempts(client, entity, 1, "collection")
            rare_cards.extend(collection_rare)
            
            # Фильтруем все редкие карты
            for card_info in rare_cards:
                await filter_rare_card(client, entity, card_info)
        except Exception as e:
            print(f"⚠️ [{client.session.filename}] Ошибка при работе с профилем: {e}")

        print(f"🎉 [{client.session.filename}] Ежедневный цикл завершен!")
        
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в ежедневном цикле: {e}")

async def use_attempts(client, entity, attempts, card_type):
    """
    Использует попытки для получения карт
    Возвращает список редких карт
    """
    command = "⚔️ Получить карту" if card_type == "battle" else "🏵️ Получить карту"
    emoji = "⚔️" if card_type == "battle" else "🎭"
    rare_cards = []
    
    print(f"{emoji} [{client.session.filename}] Используем {attempts} попыток для {card_type} карт...")
    
    for i in range(attempts):
        try:
            print(f"{emoji} [{client.session.filename}] Попытка {i+1}/{attempts}...")
            await client.send_message(entity, command)
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после отправки команды
            
            try:
                reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                if reply and reply.raw_text:
                    card_info = parse_card_response(reply.raw_text, card_type)
                    if card_info:
                        rarity = is_rare_card(card_info["rating"])
                        if rarity:
                            card_info["rarity"] = rarity
                            save_card_to_file(client.session.filename, card_info)
                            send_card_notification(client.session.filename, card_info)
                            rare_cards.append(card_info)
                            print(f"🎉 [{client.session.filename}] Редкая карта: {card_info['name']} (Рейтинг: {card_info['rating']})")
                        else:
                            print(f"📝 [{client.session.filename}] Обычная карта: {card_info['name']} (Рейтинг: {card_info['rating']})")
                    else:
                        print(f"📝 [{client.session.filename}] Не удалось распарсить карту (попытка {i+1})")
                            
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при попытке {i+1}")
            
            if i < attempts - 1:
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между попытками получения карт
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при попытке {i+1}: {e}")
    
    return rare_cards

async def filter_rare_card(client, entity, card_info):
    """
    Выполняет фильтрацию для редких карт
    """
    try:
        print(f"🔍 [{client.session.filename}] Фильтруем редкую карту: {card_info['name']} (Рейтинг: {card_info['rating']})")
        
        # Отправляем "Мои карты"
        print(f"🧳 [{client.session.filename}] Отправляем 'Мои карты'...")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await send_message_and_wait(client, entity, "🧳 Мои карты")
        
        if msg and "Введите название карты" in msg.raw_text:
            print(f"📝 [{client.session.filename}] Отправляем название карты: {card_info['name']}")
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
            msg = await send_message_and_wait(client, entity, card_info['name'])
            
            if msg and "Выберите нужные фильтры" in msg.raw_text:
                print(f"⚙️ [{client.session.filename}] Устанавливаем фильтры...")
                
                # Устанавливаем тип карт
                if card_info['type'] == 'battle':
                    print(f"⚔️ [{client.session.filename}] Устанавливаем тип: Боевые ⚔️")
                    await client.send_message(entity, "Боевые ⚔️")
                else:
                    print(f"🎭 [{client.session.filename}] Устанавливаем тип: Коллекционные 🎭")
                    await client.send_message(entity, "Коллекционные 🎭")
                
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                
                # Устанавливаем название карты
                print(f"📝 [{client.session.filename}] Устанавливаем название карты: {card_info['name']}")
                await client.send_message(entity, card_info['name'])
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                
                # Устанавливаем Вселенные: ✖️
                print(f"🌍 [{client.session.filename}] Устанавливаем Вселенные: ✖️")
                await client.send_message(entity, "✖️")
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                
                # Устанавливаем Редкости: ✖️
                print(f"⭐ [{client.session.filename}] Устанавливаем Редкости: ✖️")
                await client.send_message(entity, "✖️")
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                
                # Устанавливаем Стихии: ✖️
                print(f"🔥 [{client.session.filename}] Устанавливаем Стихии: ✖️")
                await client.send_message(entity, "✖️")
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                
                # Устанавливаем сортировку: Высокий рейтинг вперёд
                print(f"📊 [{client.session.filename}] Устанавливаем сортировку: Высокий рейтинг вперёд")
                await client.send_message(entity, "Высокий рейтинг вперёд")
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                
                # Устанавливаем сортировку: Новые вперёд
                print(f"📊 [{client.session.filename}] Устанавливаем сортировку: Новые вперёд")
                await client.send_message(entity, "Новые вперёд")
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                
                # Нажимаем "Карты ⏩"
                if msg and msg.buttons:
                    button_texts = [b.text for row in msg.buttons for b in row]
                    print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                    
                    # Ищем кнопку "Карты ⏩"
                    cards_button = None
                    for button_text in button_texts:
                        if "Карты" in button_text and "⏩" in button_text:
                            cards_button = button_text
                            break
                    
                    if cards_button:
                        print(f"⏩ [{client.session.filename}] Нажимаем '{cards_button}'...")
                        msg = await click_button_and_wait(client, entity, msg, button_text=cards_button)
                        if msg:
                            print(f"✅ [{client.session.filename}] Перешли к картам")
                            
                            # Проверяем рейтинг карт по кнопкам
                            if msg.buttons:
                                button_texts = [b.text for row in msg.buttons for b in row]
                                print(f"📋 [{client.session.filename}] Кнопки карт: {button_texts}")
                                
                                # Ищем карту с нужным рейтингом
                                for button_text in button_texts:
                                    if "|" in button_text:
                                        # Парсим рейтинг из кнопки (например: "81 | Ваннилла Айс")
                                        rating_match = re.search(r'(\d+)\s*\|', button_text)
                                        if rating_match:
                                            rating = int(rating_match.group(1))
                                            if rating == card_info['rating']:
                                                print(f"🎯 [{client.session.filename}] Найдена карта с рейтингом {rating}: {button_text}")
                                                break
                    else:
                        print(f"⚠️ [{client.session.filename}] Кнопка 'Карты ⏩' не найдена")
                else:
                    print(f"⚠️ [{client.session.filename}] Нет кнопок для перехода к картам")
            else:
                print(f"⚠️ [{client.session.filename}] Не получено сообщение о фильтрах")
        else:
            print(f"⚠️ [{client.session.filename}] Не получено сообщение о вводе названия карты")
            
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка при фильтрации карты: {e}")

# === ЦИКЛ КАРТ ===

async def card_cycle_for_account(client, bot_username):
    """
    Цикл получения карт для одного аккаунта
    """
    try:
        entity = await client.get_entity(bot_username)
        print(f"🎯 [{client.session.filename}] Начинаем цикл карт...")
        
        # Добавляем небольшую задержку между аккаунтами
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # 1. Активируем бота
        print(f"🚀 [{client.session.filename}] Активируем бота...")
        await client.send_message(entity, "/start")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после отправки
        
        # 2. Проверяем профиль на наличие попыток
        print(f"🎒 [{client.session.filename}] Проверяем профиль...")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
        msg = await send_message_and_wait(client, entity, "🎒 Профиль")
        if msg:
            print(f"✅ [{client.session.filename}] Профиль получен")
        else:
            print(f"⚠️ [{client.session.filename}] Не удалось получить профиль, пробуем продолжить...")
            return
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        
        # Парсим попытки
        profile_text = msg.raw_text
        attempts_match = re.search(r'Попытки:\s*·\s*⚔️\s*-\s*(\d+)\s*\|\s*🎭\s*-\s*(\d+)', profile_text)
        
        if attempts_match:
            battle_attempts = int(attempts_match.group(1))
            collection_attempts = int(attempts_match.group(2))
            print(f"📊 [{client.session.filename}] Попытки: ⚔️ {battle_attempts} | 🎭 {collection_attempts}")
        else:
            print(f"ℹ️ [{client.session.filename}] Попытки не найдены в профиле")
            battle_attempts = 0
            collection_attempts = 0
        
        # 2. Сначала тратим попытки из профиля (если есть)
        rare_cards = []
        if battle_attempts > 0 or collection_attempts > 0:
            print(f"🎯 [{client.session.filename}] Тратим попытки из профиля...")
            
            if battle_attempts > 0:
                battle_rare = await use_attempts(client, entity, battle_attempts, "battle")
                rare_cards.extend(battle_rare)
            
            if collection_attempts > 0:
                collection_rare = await use_attempts(client, entity, collection_attempts, "collection")
                rare_cards.extend(collection_rare)
        
        # 3. Тратим по 1 крутке каждого вида (дополнительно)
        print(f"🎯 [{client.session.filename}] Тратим по 1 крутке каждого вида...")
        
        # Тратим боевую крутку
        battle_rare = await use_attempts(client, entity, 1, "battle")
        rare_cards.extend(battle_rare)
        
        # Задержка между крутками
        await asyncio.sleep(MESSAGE_TIMEOUT)
        
        # Тратим коллекционную крутку
        collection_rare = await use_attempts(client, entity, 1, "collection")
        rare_cards.extend(collection_rare)
        
        # 4. Фильтруем редкие карты
        for card_info in rare_cards:
            await filter_rare_card(client, entity, card_info)

        print(f"🎉 [{client.session.filename}] Цикл карт завершен!")
        
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в цикле карт: {e}")
        import traceback
        traceback.print_exc()

# === ОСНОВНЫЕ ФУНКЦИИ ===

async def run_daily_cycle():
    """
    Запускает ежедневный цикл для всех аккаунтов
    """
    try:
        # Загружаем конфигурацию аккаунтов
        with open("accounts/accounts.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        bot_username = config.get("bot", "@anicardplaybot")
        concurrency = config.get("concurrency", 2)
        accounts = config.get("accounts", [])
        
        print(f"🔐 Настроено аккаунтов: {len(accounts)}")
        print(f"⚡ Одновременно работает: {concurrency}")
        print(f"⏱️ Задержка между действиями: {MESSAGE_TIMEOUT_MS} мс")
        
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc['session']} -> {bot_username}")
        
        # Создаем семафор для ограничения одновременных подключений
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_account(acc):
            async with semaphore:
                session_name = acc["session"]
                phone = acc.get("phone", "Неизвестно")
                
                print(f"🔐 [{session_name}] Подключаемся к аккаунту {phone}...")
                
                client = TelegramClient(f"accounts/{session_name}", API_ID, API_HASH)
                
                try:
                    await client.start(phone=phone)
                    user = await client.get_me()
                    print(f"✅ [{session_name}] Подключен как: @{user.username} ({user.phone})")
                    
                    # Запускаем ежедневный цикл
                    await daily_cycle_for_account(client, bot_username)
                    
                except Exception as e:
                    print(f"❌ [{session_name}] Ошибка: {e}")
                finally:
                    await client.disconnect()
        
        # Запускаем все аккаунты
        tasks = [process_account(acc) for acc in accounts]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print("🎉 Ежедневный цикл завершен для всех аккаунтов!")
        
    except Exception as e:
        print(f"❌ Ошибка при запуске ежедневного цикла: {e}")

async def run_card_cycle():
    """
    Запускает цикл карт для всех аккаунтов
    """
    try:
        # Загружаем конфигурацию аккаунтов
        with open("accounts/accounts.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        bot_username = config.get("bot", "@anicardplaybot")
        concurrency = config.get("concurrency", 2)
        accounts = config.get("accounts", [])
        
        print(f"🔐 Настроено аккаунтов: {len(accounts)}")
        print(f"⚡ Одновременно работает: {concurrency}")
        print(f"⏱️ Задержка между действиями: {MESSAGE_TIMEOUT_MS} мс")
        
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc['session']} -> {bot_username}")
        
        # Создаем семафор для ограничения одновременных подключений
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_account(acc):
            async with semaphore:
                session_name = acc["session"]
                phone = acc.get("phone", "Неизвестно")
                
                print(f"🔐 [{session_name}] Подключаемся к аккаунту {phone}...")
                
                client = TelegramClient(f"accounts/{session_name}", API_ID, API_HASH)
                
                try:
                    await client.start(phone=phone)
                    user = await client.get_me()
                    print(f"✅ [{session_name}] Подключен как: @{user.username} ({user.phone})")
                    
                    # Запускаем цикл карт
                    await card_cycle_for_account(client, bot_username)
                    
                except Exception as e:
                    print(f"❌ [{session_name}] Ошибка: {e}")
                finally:
                    await client.disconnect()
        
        # Запускаем все аккаунты
        tasks = [process_account(acc) for acc in accounts]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print("🎉 Цикл карт завершен для всех аккаунтов!")
        
    except Exception as e:
        print(f"❌ Ошибка при запуске цикла карт: {e}")

async def main():
    """
    Главная функция
    """
    if len(sys.argv) > 1:
        if sys.argv[1] == "daily":
            print("🌅 Запуск ежедневного цикла...")
            await run_daily_cycle()
        elif sys.argv[1] == "cards":
            print("🎴 Запуск цикла карт...")
            await run_card_cycle()
        elif sys.argv[1] == "both":
            print("🔄 Запуск обоих циклов...")
            await run_daily_cycle()
            await asyncio.sleep(5)  # Небольшая пауза между циклами
            await run_card_cycle()
        elif sys.argv[1] == "promo":
            if len(sys.argv) > 2:
                promo_input = " ".join(sys.argv[2:])
                print("🎁 Активация промо для всех аккаунтов...")
                await activate_promo_for_all_accounts(promo_input)
            else:
                print("❌ Укажите промо-код или ссылку")
                print("Использование: python combined_cycle.py promo <промо-код или ссылка>")
        else:
            print("Использование: python combined_cycle.py [daily|cards|both|promo]")
    else:
        print("Использование: python combined_cycle.py [daily|cards|both|promo]")

async def activate_promo_for_all_accounts(promo_input):
    """
    Активирует промо для всех аккаунтов
    Поддерживает как ссылки (https://t.me/anicardplaybot?start=...), так и команды (/promo text)
    """
    try:
        # Загружаем конфигурацию
        with open("accounts/accounts.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        accounts = config.get("accounts", [])
        bot_username = config.get("bot", "@anicardplaybot")
        
        if not accounts:
            print("❌ Аккаунты не найдены в accounts.json")
            return
        
        # Определяем тип промо и извлекаем данные
        if promo_input.startswith("https://t.me/anicardplaybot?start="):
            # Это ссылка, извлекаем параметр start
            promo_code = promo_input.split("start=")[1]
            promo_type = "link"
            print(f"🔗 Активируем промо-ссылку: {promo_code}")
        elif promo_input.startswith("/promo"):
            # Это команда /promo
            promo_code = promo_input.replace("/promo", "").strip()
            promo_type = "command"
            print(f"💬 Активируем промо-команду: /promo {promo_code}")
        else:
            print("❌ Неверный формат промо. Используйте:")
            print("   - Ссылку: https://t.me/anicardplaybot?start=CODE")
            print("   - Команду: /promo CODE")
            return
        
        print(f"🤖 Бот: {bot_username}")
        print(f"👤 Аккаунтов для активации: {len(accounts)}")
        print()
        
        success_count = 0
        error_count = 0
        
        for acc in accounts:
            session_name = acc["session"]
            phone = acc.get("phone", "Неизвестно")
            
            print(f"🔐 [{session_name}] Активируем промо для {phone}...")
            
            client = TelegramClient(f"accounts/{session_name}", API_ID, API_HASH)
            
            try:
                await client.start(phone=phone)
                user = await client.get_me()
                print(f"✅ [{session_name}] Подключен как: @{user.username}")
                
                # Активируем промо
                try:
                    entity = await client.get_entity(bot_username)
                    
                    if promo_type == "link":
                        # Отправляем ссылку с параметром start
                        message = f"https://t.me/anicardplaybot?start={promo_code}"
                    else:
                        # Отправляем команду /promo
                        message = f"/promo {promo_code}" if promo_code else "/promo"
                    
                    await client.send_message(entity, message)
                    print(f"📤 [{session_name}] Отправлено: {message}")
                    
                    # Ждем ответ от бота
                    try:
                        response = await wait_new_from(client, entity, timeout=15)
                        response_text = response.raw_text
                        print(f"📱 [{session_name}] Ответ бота: {response_text[:100]}...")
                        
                        # Проверяем успешность активации
                        if any(word in response_text.lower() for word in ["активирован", "получен", "промо", "успешно", "активация"]):
                            print(f"✅ [{session_name}] Промо успешно активировано!")
                            success_count += 1
                        else:
                            print(f"⚠️ [{session_name}] Неясный ответ от бота")
                            success_count += 1  # Считаем успешным, если бот ответил
                            
                    except asyncio.TimeoutError:
                        print(f"⏰ [{session_name}] Таймаут ожидания ответа от бота")
                        error_count += 1
                    except Exception as e:
                        print(f"❌ [{session_name}] Ошибка при получении ответа: {e}")
                        error_count += 1
                    
                except Exception as e:
                    print(f"❌ [{session_name}] Ошибка отправки промо: {e}")
                    error_count += 1
                
            except Exception as e:
                print(f"❌ [{session_name}] Ошибка авторизации: {e}")
                error_count += 1
            finally:
                await client.disconnect()
            
            print()
            await asyncio.sleep(2)  # Пауза между аккаунтами
        
        print("=" * 50)
        print(f"🎉 Активация промо завершена!")
        print(f"✅ Успешно: {success_count}")
        print(f"❌ Ошибок: {error_count}")
        print(f"📊 Всего аккаунтов: {len(accounts)}")
        
    except Exception as e:
        print(f"❌ Ошибка при активации промо: {e}")

async def test_bot_connection():
    """
    Тестирует подключение к боту для всех аккаунтов
    """
    try:
        # Загружаем конфигурацию
        with open("accounts/accounts.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        accounts = config.get("accounts", [])
        bot_username = config.get("bot", "@anicardplaybot")
        
        if not accounts:
            print("❌ Аккаунты не найдены в accounts.json")
            return
        
        print(f"🤖 Тестируем подключение к боту: {bot_username}")
        print(f"👤 Аккаунтов для проверки: {len(accounts)}")
        print()
        
        for acc in accounts:
            session_name = acc["session"]
            phone = acc.get("phone", "Неизвестно")
            
            print(f"🔐 [{session_name}] Тестируем {phone}...")
            
            client = TelegramClient(f"accounts/{session_name}", API_ID, API_HASH)
            
            try:
                await client.start(phone=phone)
                user = await client.get_me()
                print(f"✅ [{session_name}] Подключен как: @{user.username}")
                
                # Тестируем подключение к боту
                try:
                    entity = await client.get_entity(bot_username)
                    await client.send_message(entity, "Меню")
                    msg = await wait_new_from(client, entity, timeout=10)
                    print(f"✅ [{session_name}] Подключение к боту работает!")
                    print(f"📱 [{session_name}] Получено сообщение: {msg.raw_text[:50]}...")
                except Exception as e:
                    print(f"❌ [{session_name}] Ошибка подключения к боту: {e}")
                
            except Exception as e:
                print(f"❌ [{session_name}] Ошибка авторизации: {e}")
            finally:
                await client.disconnect()
            
            print()
        
        print("🎉 Тестирование завершено!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")

if __name__ == "__main__":
    asyncio.run(main())
