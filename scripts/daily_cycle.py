import asyncio, json, os, random, re, datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError

load_dotenv()

# Загружаем API ключи из .env
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MESSAGE_TIMEOUT_MS = int(os.getenv("MESSAGE_TIMEOUT", "700"))  # Миллисекунды
MESSAGE_TIMEOUT = MESSAGE_TIMEOUT_MS / 1000.0  # Конвертируем в секунды (0.7 секунды)

# Создаем папку для карт если её нет
CARDS_FOLDER = "accounts/cards"
if not os.path.exists(CARDS_FOLDER):
    os.makedirs(CARDS_FOLDER)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

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

    def norm(s): return (s or "") if not case_insensitive else (s or "").lower()
    for b in flat:
        bt = b.text or ""
        if text and norm(bt) == norm(text):
            await b.click(); return True
        if regex and re.search(regex, bt, re.I if case_insensitive else 0):
            await b.click(); return True
    return False

async def send_message_and_wait(client, entity, message, timeout=MESSAGE_TIMEOUT):
    """
    Отправляет сообщение и ждет ответ
    """
    await client.send_message(entity, message)
    return await wait_new_from(client, entity, timeout=timeout)

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
        return None
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в click_button_and_wait: {e}")
        return None

# === ФУНКЦИИ ДЛЯ РАБОТЫ С КАРТАМИ ===

def load_rare_cards_filter():
    """
    Загружает список редких карт из JSON файла для фильтрации
    """
    try:
        with open("rare_cards_filter.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("cards", {})
    except FileNotFoundError:
        print("⚠️ Файл rare_cards_filter.json не найден, фильтрация по названию отключена")
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
                rating = card.get("strength", None)  # Берем рейтинг из поля strength
                return category, rating
    
    return None, None

def parse_card_response(text, card_type):
    """
    Парсит ответ бота на получение карты и извлекает информацию о редких картах
    Проверяет редкость как по ключевым словам, так и по названию из списка фильтрации
    Возвращает dict с информацией о карте или None если карта не редкая
    """
    # Парсим информацию о карте независимо от редкости
    card_info = {
        "type": card_type,
        "name": "",
        "universe": "",
        "element": "",
        "character": "",
        "rating": None,
        "rarity": None,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Для боевых карт
    if card_type == "battle":
        # Ищем имя карты
        name_match = re.search(r'🎴 Карта: (.+)', text)
        if name_match:
            card_info["name"] = name_match.group(1).strip()
        
        # Ищем вселенную
        universe_match = re.search(r'🔮 Вселенная: (.+)', text)
        if universe_match:
            card_info["universe"] = universe_match.group(1).strip()
        
        # Ищем элемент/стихию
        element_match = re.search(r'Элемент: (.+)', text)
        if element_match:
            card_info["element"] = element_match.group(1).strip()
    
    # Извлекаем рейтинг карты (для всех типов карт)
    rating_match = re.search(r'Рейтинг: (\d+)', text)
    if rating_match:
        card_info["rating"] = int(rating_match.group(1))
    
    # Для коллекционных карт
    elif card_type == "collection":
        # Ищем персонажа
        character_match = re.search(r'👤 Персонаж: (.+)', text)
        if character_match:
            card_info["character"] = character_match.group(1).strip()
    
    # Проверяем редкость карты только по списку фильтрации
    card_name = card_info["name"] or card_info["character"]
    if not card_name:
        return None
    
    # Проверяем по названию из списка фильтрации
    rarity_category, rating_from_list = is_rare_card_by_name(card_name)
    if rarity_category:
        card_info["rarity"] = rarity_category
        # Используем рейтинг из списка, а не из сообщения
        card_info["rating"] = rating_from_list
        print(f"🎯 Найдена редкая карта: {card_name} ({rarity_category}, рейтинг: {rating_from_list})")
        return card_info
    
    # Карта не найдена в списке редких карт
    return None

def save_card_to_file(session_name, card_info):
    """
    Сохраняет информацию о редкой карте в JSON файл аккаунта
    """
    file_path = os.path.join(CARDS_FOLDER, f"{session_name}.json")
    
    # Загружаем существующие данные или создаем новые
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {"epic": [], "legendary": [], "myfics": [], "adamant": []}
    else:
        data = {"epic": [], "legendary": [], "myfics": [], "adamant": []}
    
    # Определяем категорию редкости
    rarity = card_info["rarity"]
    category = rarity  # Теперь rarity уже содержит правильную категорию
    
    # Проверяем, что категория существует
    if category not in data:
        data[category] = []
    
    # Проверяем, нет ли уже такой карты
    card_name = card_info["name"] or card_info["character"]
    for existing_card in data[category]:
        if existing_card.get("name") == card_name:
            print(f"🔄 [{session_name}] Карта {card_name} уже есть в коллекции ({category})")
            return
    
    # Добавляем карту в соответствующую категорию (только имя, элемент, рейтинг)
    card_entry = {
        "name": card_name,
        "rating": card_info["rating"]
    }
    
    if card_info["element"]:
        card_entry["element"] = card_info["element"]
    
    data[category].append(card_entry)
    
    # Сохраняем обновленные данные
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 [{session_name}] Редкая карта сохранена: {card_name} ({category})")

def send_card_notification(session_name, card_info):
    """
    Отправляет уведомление о получении редкой карты
    """
    rarity_emoji = {
        "epic": "🟢",
        "legendary": "🌟",
        "myfics": "✨", 
        "adamant": "💎"
    }
    
    type_emoji = {
        "battle": "⚔️",
        "collection": "🎭"
    }
    
    emoji = rarity_emoji.get(card_info["rarity"], "🎴")
    type_icon = type_emoji.get(card_info["type"], "🎴")
    
    print(f"\n🎉 {emoji} РЕДКАЯ КАРТА! {emoji}")
    print(f"👤 Аккаунт: {session_name}")
    print(f"🔮 Редкость: {card_info['rarity']} {emoji}")
    print(f"📋 Тип: {type_icon} {'Боевая' if card_info['type'] == 'battle' else 'Коллекционная'}")
    
    card_name = card_info["name"] or card_info["character"]
    if card_name:
        print(f"🎴 Название: {card_name}")
    if card_info.get("rating"):
        print(f"⭐ Рейтинг: {card_info['rating']}")
    if card_info["universe"]:
        print(f"🔮 Вселенная: {card_info['universe']}")
    if card_info["element"]:
        print(f"🍃 Элемент: {card_info['element']}")
    
    print("=" * 50)

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
        
        if msg and msg.buttons:
            # Ищем кнопку "Название ➕"
            cards_button = None
            for button_text in [b.text for row in msg.buttons for b in row]:
                if "Название ➕" in button_text:
                    cards_button = button_text
                    break
            
            if cards_button:
                print(f"🎯 [{client.session.filename}] Найдена кнопка: {cards_button}")
                msg = await click_button_and_wait(client, entity, msg, button_text=cards_button)
                
                if msg and "Введите название карты" in msg.raw_text:
                    print(f"📝 [{client.session.filename}] Отправляем название карты: {card_info['name']}")
                    await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                    msg = await send_message_and_wait(client, entity, card_info['name'])
                    
                    if msg and "Выберите нужные фильтры для карт" in msg.raw_text:
                        print(f"🎛️ [{client.session.filename}] Устанавливаем фильтры...")
                        # Устанавливаем фильтры для карты
                        success = await set_card_filters(client, entity, card_info['name'], card_info['type'])
                        if success:
                            print(f"✅ [{client.session.filename}] Фильтры установлены для {card_info['name']}")
                        else:
                            print(f"❌ [{client.session.filename}] Ошибка установки фильтров для {card_info['name']}")
                    else:
                        print(f"ℹ️ [{client.session.filename}] Не получен запрос фильтров")
                else:
                    print(f"ℹ️ [{client.session.filename}] Не получен запрос названия карты")
            else:
                print(f"ℹ️ [{client.session.filename}] Кнопка 'Название ➕' не найдена")
        else:
            print(f"ℹ️ [{client.session.filename}] Нет кнопок в сообщении 'Мои карты'")
            
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка при фильтрации карты: {e}")

async def set_card_filters(client, entity, card_name, card_type):
    """
    Устанавливает фильтры для карт
    """
    try:
        print(f"🎛️ [{client.session.filename}] Устанавливаем фильтры для {card_name}...")
        
        # 1. Устанавливаем тип карт - Боевые ⚔️ или Коллекционные 🎭
        if card_type == "battle":
            print(f"⚔️ [{client.session.filename}] Устанавливаем тип карт: Боевые ⚔️")
            await client.send_message(entity, "Боевые ⚔️")
        else:
            print(f"🎭 [{client.session.filename}] Устанавливаем тип карт: Коллекционные 🎭")
            await client.send_message(entity, "Коллекционные 🎭")
        
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
        
        # 2. Устанавливаем название карты
        print(f"📝 [{client.session.filename}] Устанавливаем название карты: {card_name}")
        await client.send_message(entity, card_name)
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
        
        # 3. Устанавливаем Вселенные - ✖️
        print(f"🌍 [{client.session.filename}] Устанавливаем Вселенные: ✖️")
        await client.send_message(entity, "✖️")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
        
        # 4. Устанавливаем Редкости - ✖️
        print(f"⭐ [{client.session.filename}] Устанавливаем Редкости: ✖️")
        await client.send_message(entity, "✖️")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
        
        # 5. Устанавливаем Стихии - ✖️
        print(f"🔥 [{client.session.filename}] Устанавливаем Стихии: ✖️")
        await client.send_message(entity, "✖️")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
        
        # 6. Устанавливаем сортировку: Сначала - Высокий рейтинг вперёд
        print(f"📊 [{client.session.filename}] Устанавливаем сортировку: Высокий рейтинг вперёд")
        await client.send_message(entity, "Высокий рейтинг вперёд")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
        
        # 7. Устанавливаем сортировку: Потом - Новые вперёд
        print(f"📊 [{client.session.filename}] Устанавливаем сортировку: Новые вперёд")
        await client.send_message(entity, "Новые вперёд")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
        msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
        
        # 8. Ищем кнопку "Карты ⏩"
        if msg and msg.buttons:
            cards_button = None
            for button_text in [b.text for row in msg.buttons for b in row]:
                if "Карты ⏩" in button_text:
                    cards_button = button_text
                    break
            
            if cards_button:
                print(f"🎯 [{client.session.filename}] Найдена кнопка: {cards_button}")
                msg = await click_button_and_wait(client, entity, msg, button_text=cards_button)
                
                if msg and "Найдено карт" in msg.raw_text:
                    print(f"✅ [{client.session.filename}] Фильтры установлены успешно")
                    return True
                else:
                    print(f"ℹ️ [{client.session.filename}] Не получен результат фильтрации")
                    return False
            else:
                print(f"ℹ️ [{client.session.filename}] Кнопка 'Карты ⏩' не найдена")
                return False
        else:
            print(f"ℹ️ [{client.session.filename}] Нет кнопок в сообщении с фильтрами")
            return False
            
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка при установке фильтров: {e}")
        return False

async def use_attempts(client, entity, attempts, card_type):
    """
    Использует попытки для получения карт
    """
    command = "⚔️ Получить карту" if card_type == "battle" else "🏵️ Получить карту"
    emoji = "⚔️" if card_type == "battle" else "🎭"
    
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
                        # Карта уже проверена в parse_card_response и является редкой
                        save_card_to_file(client.session.filename, card_info)
                        send_card_notification(client.session.filename, card_info)
                        print(f"🎉 [{client.session.filename}] Редкая карта: {card_info['name']} ({card_info['rarity']})")
                    else:
                        print(f"📝 [{client.session.filename}] Обычная карта (попытка {i+1})")
                            
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при попытке {i+1}")
            
            if i < attempts - 1:
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между попытками получения карт
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при попытке {i+1}: {e}")

# === ОСНОВНОЙ ЕЖЕДНЕВНЫЙ ЦИКЛ ===

async def daily_cycle_for_account(client, bot_username):
    """
    Ежедневный цикл для одного аккаунта
    """
    try:
        entity = await client.get_entity(bot_username)
        
        print(f"🎯 [{client.session.filename}] Начинаем ежедневный цикл...")
        
        # Добавляем небольшую задержку между аккаунтами
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # 1. Отправляем "Меню"
        print(f"📜 [{client.session.filename}] Отправляем 'Меню'...")
        msg = await send_message_and_wait(client, entity, "📜 Меню")
        print(f"✅ [{client.session.filename}] Меню получено")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

        # 2. Нажимаем на кнопку 🎫 AniPass
        print(f"🎫 [{client.session.filename}] Нажимаем 'AniPass'...")
        
        # Показываем доступные кнопки для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
        
        # Ищем кнопку AniPass
        anipass_clicked = False
        if msg.buttons:
            flat_buttons = [b for row in msg.buttons for b in row]
            for button in flat_buttons:
                if "AniPass" in button.text or "🎫" in button.text:
                    print(f"🎯 [{client.session.filename}] Найдена кнопка: {button.text}")
                    await button.click()
                    anipass_clicked = True
                    break
        
        if not anipass_clicked:
            print(f"❌ [{client.session.filename}] Не удалось найти кнопку AniPass")
            return False
        
        # Ждем ответ после клика
        try:
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] AniPass открыт")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при открытии AniPass, пробуем продолжить...")
            # Пытаемся получить последнее сообщение
            try:
                async for message in client.iter_messages(entity, limit=1):
                    msg = message
                    break
            except:
                print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                return False

        # 3. Проверяем, есть ли кнопка с галочкой ✔️ (AniPass может быть уже забран)
        print(f"🔍 [{client.session.filename}] Проверяем доступность AniPass...")
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
            
            # Ищем кнопку с галочкой ✔️ (только эту)
            checkmark_button = None
            for button_text in button_texts:
                if "✔️" in button_text:
                    checkmark_button = button_text
                    break
            
            if checkmark_button:
                print(f"✔️ [{client.session.filename}] AniPass доступен, нажимаем кнопку с галочкой...")
                msg = await click_button_and_wait(client, entity, msg, button_text=checkmark_button)
                if not msg:
                    print(f"❌ [{client.session.filename}] Не удалось нажать кнопку с галочкой")
                    return False
                print(f"✅ [{client.session.filename}] AniPass получен!")
                
                # 4. Нажимаем "Назад" после получения AniPass
                print(f"🔙 [{client.session.filename}] Нажимаем 'Назад'...")
                msg = await click_button_and_wait(client, entity, msg, button_text="Назад 🔙")
                if not msg:
                    print(f"❌ [{client.session.filename}] Не удалось найти кнопку 'Назад'")
                    return False
                print(f"✅ [{client.session.filename}] Вернулись в главное меню")
            else:
                print(f"ℹ️ [{client.session.filename}] AniPass уже забран за день, пропускаем...")
                # Если AniPass уже забран, просто возвращаемся в главное меню
                print(f"🔙 [{client.session.filename}] Нажимаем 'Назад'...")
                msg = await click_button_and_wait(client, entity, msg, button_text="Назад 🔙")
                if not msg:
                    print(f"❌ [{client.session.filename}] Не удалось найти кнопку 'Назад'")
                    return False
                print(f"✅ [{client.session.filename}] Вернулись в главное меню")
        else:
            print(f"ℹ️ [{client.session.filename}] Нет кнопок в AniPass, возможно уже забран")
            # Пытаемся вернуться в главное меню
            print(f"🔙 [{client.session.filename}] Пытаемся вернуться в главное меню...")
            await client.send_message(entity, "📜 Меню")
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] Вернулись в главное меню")

        # 5. Переходим в "Дары богов"
        print(f"⛩ [{client.session.filename}] Переходим в 'Дары богов'...")
        
        # Показываем доступные кнопки для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
        
        # Ищем кнопку "Дары богов"
        gods_gifts_clicked = False
        if msg.buttons:
            flat_buttons = [b for row in msg.buttons for b in row]
            for button in flat_buttons:
                if "Дары богов" in button.text or "⛩" in button.text:
                    print(f"🎯 [{client.session.filename}] Найдена кнопка: {button.text}")
                    await button.click()
                    gods_gifts_clicked = True
                    break
        
        if not gods_gifts_clicked:
            print(f"❌ [{client.session.filename}] Не удалось найти 'Дары богов'")
            return False
        
        # Ждем ответ после клика
        try:
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] В 'Дары богов'")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при переходе в 'Дары богов', пробуем продолжить...")
            try:
                async for message in client.iter_messages(entity, limit=1):
                    msg = message
                    break
            except:
                print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                return False

        # 6. Получаем награды (с проверками на уже полученные)
        print(f"🎁 [{client.session.filename}] Получаем награды...")
        
        # Мистический жетон (ежедневно)
        print(f"🀄️ [{client.session.filename}] Получаем мистический жетон...")
        await click_button(msg, index=2)  # 3-я кнопка
        try:
            reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            if "сент" in reply.raw_text or "2025" in reply.raw_text or "доступн" in reply.raw_text.lower():
                print(f"ℹ️ [{client.session.filename}] Мистический жетон уже получен")
            else:
                print(f"✅ [{client.session.filename}] Мистический жетон получен")
                if reply.buttons:
                    msg = reply
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при получении жетона")

        await asyncio.sleep(MESSAGE_TIMEOUT)

        # Древний куб удачи (раз в неделю)
        print(f"🎲 [{client.session.filename}] Получаем древний куб удачи...")
        await click_button(msg, index=0)  # 1-я кнопка
        try:
            reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            if "сент" in reply.raw_text or "2025" in reply.raw_text or "доступн" in reply.raw_text.lower():
                print(f"ℹ️ [{client.session.filename}] Древний куб удачи уже получен")
            else:
                print(f"✅ [{client.session.filename}] Древний куб удачи получен")
                if reply.buttons:
                    msg = reply
                    
                # Проверяем попытки
                attempts_match = re.search(r'Вы получаете ⚔️ (\d+) попыток', reply.raw_text)
                if attempts_match:
                    battle_attempts = int(attempts_match.group(1))
                    print(f"🎯 [{client.session.filename}] Получено {battle_attempts} попыток для боевых карт!")
                    await use_attempts(client, entity, battle_attempts, "battle")
                
                collection_attempts_match = re.search(r'Вы получаете 🎭 (\d+) попыток', reply.raw_text)
                if collection_attempts_match:
                    collection_attempts = int(collection_attempts_match.group(1))
                    print(f"🎯 [{client.session.filename}] Получено {collection_attempts} попыток для коллекционных карт!")
                    await use_attempts(client, entity, collection_attempts, "collection")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при получении куба удачи")

        await asyncio.sleep(MESSAGE_TIMEOUT)

        # Рог призыва (раз в неделю)
        print(f"📯 [{client.session.filename}] Получаем рог призыва...")
        await click_button(msg, index=1)  # 2-я кнопка
        try:
            reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            if "сент" in reply.raw_text or "2025" in reply.raw_text or "доступн" in reply.raw_text.lower():
                print(f"ℹ️ [{client.session.filename}] Рог призыва уже получен")
            else:
                print(f"✅ [{client.session.filename}] Рог призыва получен")
                # Рог призыва всегда дает легендарную коллекционную карту
                card_info = parse_card_response(reply.raw_text, "collection")
                if card_info:
                    card_info["rarity"] = "Легендарная"
                    card_info["type"] = "collection"
                    save_card_to_file(client.session.filename, card_info)
                    send_card_notification(client.session.filename, card_info)
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при получении рога призыва")

        # 7. Нажимаем "Назад"
        print(f"🔙 [{client.session.filename}] Нажимаем 'Назад'...")
        msg = await click_button_and_wait(client, entity, msg, button_text="Назад 🔙")
        if not msg:
            print(f"❌ [{client.session.filename}] Не удалось найти кнопку 'Назад'")
            return False
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

        # 8. Переходим в "Крафт меню"
        print(f"🧬 [{client.session.filename}] Переходим в 'Крафт меню'...")
        
        # Показываем доступные кнопки для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
        
        # Ищем кнопку "Крафт меню"
        craft_clicked = False
        if msg.buttons:
            flat_buttons = [b for row in msg.buttons for b in row]
            for button in flat_buttons:
                if "Крафт меню" in button.text or "🧬" in button.text:
                    print(f"🎯 [{client.session.filename}] Найдена кнопка: {button.text}")
                    await button.click()
                    craft_clicked = True
                    break
        
        if not craft_clicked:
            print(f"❌ [{client.session.filename}] Не удалось найти 'Крафт меню'")
            return False
        
        # Ждем ответ после клика
        try:
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] В 'Крафт меню'")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при переходе в 'Крафт меню', пробуем продолжить...")
            try:
                async for message in client.iter_messages(entity, limit=1):
                    msg = message
                    break
            except:
                print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                return False
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

        # 9. Нажимаем "Омут душ"
        print(f"🌊 [{client.session.filename}] Нажимаем 'Омут душ'...")
        
        # Показываем доступные кнопки для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
        
        # Ищем кнопку "Омут душ"
        soul_clicked = False
        if msg.buttons:
            flat_buttons = [b for row in msg.buttons for b in row]
            for button in flat_buttons:
                if "🪞 Омут душ" in button.text or "Омут душ" in button.text or "душ" in button.text.lower():
                    print(f"🎯 [{client.session.filename}] Найдена кнопка: {button.text}")
                    await button.click()
                    soul_clicked = True
                    break
        
        if not soul_clicked:
            print(f"❌ [{client.session.filename}] Не удалось найти 'Омут душ'")
            return False
        
        # Ждем ответ после клика
        try:
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] В 'Омут душ'")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при переходе в 'Омут душ', пробуем продолжить...")
            try:
                async for message in client.iter_messages(entity, limit=1):
                    msg = message
                    break
            except:
                print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                return False

        # 10. Нажимаем "пожертвовать все эссенции/проекции душ"
        print(f"💎 [{client.session.filename}] Пожертвуем все эссенции...")
        
        # Показываем доступные кнопки для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
        
        # Ищем кнопку пожертвования
        donate_clicked = False
        if msg.buttons:
            flat_buttons = [b for row in msg.buttons for b in row]
            for button in flat_buttons:
                if "пожертвовать все эссенции/проекции душ" in button.text or "🔘" in button.text:
                    print(f"🎯 [{client.session.filename}] Найдена кнопка: {button.text}")
                    await button.click()
                    donate_clicked = True
                    break
        
        if not donate_clicked:
            print(f"❌ [{client.session.filename}] Не удалось найти кнопку пожертвования")
            return False
        
        # Ждем ответ после клика
        try:
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] Эссенции пожертвованы")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при пожертвовании, пробуем продолжить...")
            try:
                async for message in client.iter_messages(entity, limit=1):
                    msg = message
                    break
            except:
                print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                return False
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

        # 11. Отправляем "🛡 Мой клан"
        print(f"🛡 [{client.session.filename}] Проверяем клан...")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
        msg = await send_message_and_wait(client, entity, "🛡 Мой клан")
        
        # Проверяем, есть ли клан
        if "нет клана" in msg.raw_text.lower() or "у вас нет клана" in msg.raw_text.lower():
            print(f"ℹ️ [{client.session.filename}] У аккаунта нет клана, пропускаем сокровищницу")
        else:
            print(f"🏰 [{client.session.filename}] У аккаунта есть клан, проверяем сокровищницу...")
            # Ищем кнопку сокровищницы
            if msg.buttons:
                button_texts = [b.text for row in msg.buttons for b in row]
                print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
                
                # Ищем кнопку сокровищницы
                treasure_button = None
                for button_text in button_texts:
                    if "сокровищница" in button_text.lower() or "treasure" in button_text.lower():
                        treasure_button = button_text
                        break
                
                if treasure_button:
                    print(f"💰 [{client.session.filename}] Нажимаем '{treasure_button}'...")
                    msg = await click_button_and_wait(client, entity, msg, button_text=treasure_button)
                    if msg and "💰 Сокровищница вашего клана 💰" in msg.raw_text:
                        print(f"✅ [{client.session.filename}] Сокровищница открыта")
                        # Ищем кнопку "Получить выплату"
                        if msg.buttons:
                            button_texts = [b.text for row in msg.buttons for b in row]
                            if "Получить выплату" in button_texts:
                                print(f"💸 [{client.session.filename}] Получаем выплату...")
                                msg = await click_button_and_wait(client, entity, msg, button_text="Получить выплату")
                                if msg:
                                    print(f"✅ [{client.session.filename}] Выплата получена")
                            else:
                                print(f"ℹ️ [{client.session.filename}] Нет доступных выплат")
                else:
                    print(f"ℹ️ [{client.session.filename}] Кнопка сокровищницы не найдена")

        # 12. Отправляем "🛍 Магазин"
        print(f"🛍 [{client.session.filename}] Переходим в магазин...")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
        msg = await send_message_and_wait(client, entity, "🛍 Магазин")
        print(f"✅ [{client.session.filename}] В магазине")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

        # 13. Нажимаем "крутки за BattleCoin"
        print(f"🎰 [{client.session.filename}] Нажимаем 'крутки за BattleCoin'...")
        
        # Показываем доступные кнопки для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
        
        # Ищем кнопку круток
        spin_clicked = False
        if msg.buttons:
            flat_buttons = [b for row in msg.buttons for b in row]
            for button in flat_buttons:
                if "Крутки за BattleCoin" in button.text or "🎖️" in button.text:
                    print(f"🎯 [{client.session.filename}] Найдена кнопка: {button.text}")
                    await button.click()
                    spin_clicked = True
                    break
        
        if not spin_clicked:
            print(f"❌ [{client.session.filename}] Не удалось найти 'крутки за BattleCoin'")
            return False
        
        # Ждем ответ после клика
        try:
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] В крутках за BattleCoin")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при переходе в крутки, пробуем продолжить...")
            try:
                async for message in client.iter_messages(entity, limit=1):
                    msg = message
                    break
            except:
                print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                return False

        # 14. Нажимаем "10 ⚔️"
        print(f"⚔️ [{client.session.filename}] Нажимаем '10 ⚔️'...")
        
        # Показываем доступные кнопки для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
        
        # Ищем кнопку "10 ⚔️"
        ten_clicked = False
        if msg.buttons:
            flat_buttons = [b for row in msg.buttons for b in row]
            for button in flat_buttons:
                if "10 ⚔️" in button.text or "10" in button.text and "⚔️" in button.text:
                    print(f"🎯 [{client.session.filename}] Найдена кнопка: {button.text}")
                    await button.click()
                    ten_clicked = True
                    break
        
        if not ten_clicked:
            print(f"❌ [{client.session.filename}] Не удалось найти '10 ⚔️'")
            return False
        
        # Ждем ответ после клика
        try:
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"✅ [{client.session.filename}] Крутки за BattleCoin получены")
        except asyncio.TimeoutError:
            print(f"⚠️ [{client.session.filename}] Таймаут при покупке круток, пробуем продолжить...")
            try:
                async for message in client.iter_messages(entity, limit=1):
                    msg = message
                    break
            except:
                print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                return False

        # 15. Отправляем "🎒 Профиль"
        print(f"🎒 [{client.session.filename}] Получаем профиль...")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между текстовыми сообщениями
        msg = await send_message_and_wait(client, entity, "🎒 Профиль")
        print(f"✅ [{client.session.filename}] Профиль получен")
        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями

        # 16. Тратим попытки
        print(f"🎯 [{client.session.filename}] Проверяем попытки...")
        profile_text = msg.raw_text
        
        # Ищем попытки
        attempts_match = re.search(r'Попытки:\s*·\s*⚔️\s*-\s*(\d+)\s*\|\s*🎭\s*-\s*(\d+)', profile_text)
        if attempts_match:
            battle_attempts = int(attempts_match.group(1))
            collection_attempts = int(attempts_match.group(2))
            
            print(f"📊 [{client.session.filename}] Попытки: ⚔️ {battle_attempts} | 🎭 {collection_attempts}")
            
            if battle_attempts > 0:
                await use_attempts(client, entity, battle_attempts, "battle")
            
            if collection_attempts > 0:
                await use_attempts(client, entity, collection_attempts, "collection")
        else:
            print(f"ℹ️ [{client.session.filename}] Попытки не найдены в профиле")

        await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка перед завершением
        print(f"🎉 [{client.session.filename}] Ежедневный цикл завершен!")
        return True
        
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в ежедневном цикле: {e}")
        print(f"🔍 [{client.session.filename}] Тип ошибки: {type(e).__name__}")
        import traceback
        print(f"📋 [{client.session.filename}] Детали ошибки: {traceback.format_exc()}")
        return False

# === РАБОТНИК НА ОДИН АККАУНТ ===

async def worker(acc, api_id, api_hash, bot, sema):
    """
    Работник для одного аккаунта с ограничением concurrency
    """
    session = acc["session"]
    phone = acc.get("phone")
    
    client = TelegramClient(session, api_id, api_hash)

    async with sema:   # ограничение одновременных клиентов
        async with client:
            try:
                print(f"🔐 [{session}] Подключаемся к аккаунту {phone}...")
                
                await client.start(phone=phone)
                
                # Получаем информацию о пользователе
                try:
                    me = await client.get_me()
                    user_info = f"@{me.username}" if me.username else f"{me.first_name or ''} {me.last_name or ''}".strip()
                    if not user_info:
                        user_info = f"ID: {me.id}"
                    print(f"✅ [{session}] Подключен как: {user_info} ({phone})")
                except:
                    print(f"✅ [{session}] Подключен успешно ({phone})")
                
                # Случайная пауза перед началом
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                # Запускаем ежедневный цикл
                result = await daily_cycle_for_account(client, acc.get("bot", bot))
                
                # Финальная пауза
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                return result
                
            except SessionPasswordNeededError:
                print(f"❌ [{session}] Нужен пароль 2FA для {phone}")
                return False
            except FloodWaitError as e:
                print(f"⏰ [{session}] FloodWait для {phone}: подождите {e.seconds} сек.")
                return False
            except Exception as e:
                print(f"❌ [{session}] Ошибка для {phone}: {e}")
                return False

# === ОСНОВНЫЕ ФУНКЦИИ ===

async def run_daily_cycle():
    """
    Запускает ежедневный цикл для всех аккаунтов (максимум 2 одновременно)
    """
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)

        api_id = API_ID
        api_hash = API_HASH
        bot = cfg.get("bot", "@YourTargetBot")
        concurrency = 2  # Максимум 2 аккаунта одновременно
        accounts = cfg["accounts"]

        print(f"🔐 Настроено аккаунтов: {len(accounts)}")
        print(f"⚡ Одновременно работает: {concurrency}")
        print(f"⏱️ Задержка между действиями: {MESSAGE_TIMEOUT_MS} мс")
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc['session']} -> {acc.get('bot', bot)}")
        print()

        sema = asyncio.Semaphore(concurrency)
        tasks = [worker(acc, api_id, api_hash, bot, sema) for acc in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        print(f"🎉 Успешно обработано {success_count} из {len(accounts)} аккаунтов")
        return success_count > 0
        
    except FileNotFoundError:
        print("❌ Файл accounts.json не найден!")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def wait_until_time(target_hour=22, target_minute=1):
    """
    Ждем до указанного времени по UTC (по умолчанию 22:01 UTC)
    """
    import pytz
    
    utc_now = datetime.datetime.now(pytz.UTC)
    target_time_utc = utc_now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    if utc_now >= target_time_utc:
        target_time_utc += datetime.timedelta(days=1)
    
    wait_seconds = (target_time_utc - utc_now).total_seconds()
    
    local_tz = datetime.datetime.now().astimezone().tzinfo
    target_local = target_time_utc.astimezone(local_tz)
    
    print(f"⏰ Ждем до {target_time_utc.strftime('%H:%M UTC')} ({target_local.strftime('%H:%M местного времени')})")
    print(f"⏱️ Осталось ждать: {wait_seconds:.0f} секунд ({wait_seconds/3600:.1f} часов)")
    
    await asyncio.sleep(wait_seconds)
    print("⏰ Время пришло! Запускаем ежедневный цикл...")

def show_time_info():
    """
    Показывает текущее время в UTC и локальном часовом поясе
    """
    import pytz
    
    utc_now = datetime.datetime.now(pytz.UTC)
    local_now = datetime.datetime.now()
    
    print("🕐 Информация о времени:")
    print(f"   UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Локальное: {local_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Разница с UTC: {local_now.astimezone().utcoffset()}")

# === MAIN ===

async def main():
    # Показываем информацию о времени
    show_time_info()
    print()

    # Проверяем аргументы командной строки
    import sys
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "now":
            print("🚀 Запуск ежедневного цикла немедленно")
            await run_daily_cycle()
            return
        
        elif mode == "schedule":
            print("⏰ Запуск ежедневного цикла по расписанию (22:01 UTC)")
            await wait_until_time(22, 1)
            await run_daily_cycle()
            return
        
        elif mode == "test":
            print("🧪 Тестовый режим - проверяем подключение")
            try:
                with open("accounts.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                
                api_id = API_ID
                api_hash = API_HASH
                bot = cfg.get("bot", "@YourTargetBot")
                accounts = cfg["accounts"]
                
                for acc in accounts:
                    client = TelegramClient(acc["session"], api_id, api_hash)
                    try:
                        print(f"🔐 [{acc['session']}] Подключаемся к аккаунту {acc.get('phone')}...")
                        await client.start(phone=acc.get("phone"))
                        
                        me = await client.get_me()
                        user_info = f"@{me.username}" if me.username else f"{me.first_name or ''} {me.last_name or ''}".strip()
                        if not user_info:
                            user_info = f"ID: {me.id}"
                        print(f"✅ [{acc['session']}] Подключен как: {user_info} ({acc.get('phone')})")
                        
                        entity = await client.get_entity(acc.get("bot", bot))
                        await client.send_message(entity, "📜 Меню")
                        msg = await wait_new_from(client, entity, timeout=10)
                        print(f"✅ [{acc['session']}] Подключение к боту работает!")
                        print(f"📱 [{acc['session']}] Получено сообщение: {msg.raw_text[:100]}...")
                    except Exception as e:
                        print(f"❌ [{acc['session']}] Ошибка подключения для {acc.get('phone')}: {e}")
                    finally:
                        await client.disconnect()
            except Exception as e:
                print(f"❌ Ошибка: {e}")
            return

    # Интерактивный режим
    print("🤖 Anicard Daily Cycle - Ежедневный цикл")
    print("=" * 50)
    print("Выберите режим:")
    print("1. 🚀 Запустить цикл сейчас")
    print("2. ⏰ Запустить по расписанию (22:01 UTC)")
    print("3. 🧪 Тест подключения")
    print("4. 🕐 Показать время")
    print("5. 👋 Выход")
    
    while True:
        try:
            choice = input("\nВведите номер (1-5): ").strip()
            
            if choice == "1":
                print("🚀 Запускаем ежедневный цикл...")
                await run_daily_cycle()
                break
            elif choice == "2":
                print("⏰ Запускаем по расписанию...")
                await wait_until_time(22, 1)
                await run_daily_cycle()
                break
            elif choice == "3":
                print("🧪 Тестовый режим...")
                try:
                    with open("accounts.json", "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    
                    api_id = API_ID
                    api_hash = API_HASH
                    bot = cfg.get("bot", "@YourTargetBot")
                    accounts = cfg["accounts"]
                    
                    for acc in accounts:
                        client = TelegramClient(acc["session"], api_id, api_hash)
                        try:
                            print(f"🔐 [{acc['session']}] Подключаемся к аккаунту {acc.get('phone')}...")
                            await client.start(phone=acc.get("phone"))
                            
                            me = await client.get_me()
                            user_info = f"@{me.username}" if me.username else f"{me.first_name or ''} {me.last_name or ''}".strip()
                            if not user_info:
                                user_info = f"ID: {me.id}"
                            print(f"✅ [{acc['session']}] Подключен как: {user_info} ({acc.get('phone')})")
                            
                            entity = await client.get_entity(acc.get("bot", bot))
                            await client.send_message(entity, "📜 Меню")
                            msg = await wait_new_from(client, entity, timeout=10)
                            print(f"✅ [{acc['session']}] Подключение к боту работает!")
                            print(f"📱 [{acc['session']}] Получено сообщение: {msg.raw_text[:100]}...")
                        except Exception as e:
                            print(f"❌ [{acc['session']}] Ошибка подключения для {acc.get('phone')}: {e}")
                        finally:
                            await client.disconnect()
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
                break
            elif choice == "4":
                print("🕐 Показываем время...")
                show_time_info()
                print()
                continue
            elif choice == "5":
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Введите 1, 2, 3, 4 или 5.")
        except KeyboardInterrupt:
            print("\n👋 Выход по Ctrl+C")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())
