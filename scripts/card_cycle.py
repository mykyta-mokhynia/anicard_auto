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
WAIT_TIMEOUT = 10.0  # Таймаут для ожидания ответов от бота

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
    Клик по инлайн-кнопке в сообщении
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
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после клика
            try:
                return await wait_new_from(client, entity, timeout=timeout)
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при ожидании ответа после клика")
                # Пытаемся получить последнее сообщение
                try:
                    async for message in client.iter_messages(entity, limit=1):
                        return message
                except:
                    print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                    return None
        return None
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка при клике: {e}")
        return None

def parse_card_response(text, card_type):
    """
    Парсит ответ с картой и извлекает информацию
    """
    try:
        # Ищем рейтинг карты
        rating_match = re.search(r'(\d+)\s*\|\s*([^|]+)', text)
        if rating_match:
            rating = int(rating_match.group(1))
            name = rating_match.group(2).strip()
            
            # Определяем редкость по рейтингу
            if rating >= 101:
                rarity = "adamantine"
            elif rating >= 91:
                rarity = "mythic"
            elif rating >= 81:
                rarity = "legendary"
            elif rating >= 76:
                rarity = "epic"
            else:
                rarity = "common"
            
            # Ищем вселенную и элемент
            universe = ""
            element = ""
            
            universe_match = re.search(r'Вселенная:\s*([^\n]+)', text)
            if universe_match:
                universe = universe_match.group(1).strip()
            
            element_match = re.search(r'Элемент:\s*([^\n]+)', text)
            if element_match:
                element = element_match.group(1).strip()
            
            return {
                "name": name,
                "rating": rating,
                "rarity": rarity,
                "universe": universe,
                "element": element,
                "type": card_type
            }
    except Exception as e:
        print(f"❌ Ошибка при парсинге карты: {e}")
    
    return None

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

def save_card_to_file(session_name, card_info):
    """
    Сохраняет редкую карту в файл
    """
    try:
        # Убираем .session из имени файла
        clean_name = session_name.replace('.session', '')
        file_path = os.path.join(CARDS_FOLDER, f"{clean_name}.json")
        
        # Загружаем существующие карты
        cards = {"legendary": [], "mythic": [], "adamantine": [], "epic": []}
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                cards = json.load(f)
        
        # Определяем редкость
        rarity = is_rare_card(card_info["rating"])
        if not rarity:
            return
        
        # Проверяем дубликаты
        for existing_card in cards[rarity]:
            if existing_card["name"] == card_info["name"]:
                print(f"🔄 [{session_name}] Карта {card_info['name']} уже есть в коллекции")
                return
        
        # Добавляем новую карту
        cards[rarity].append({
            "name": card_info["name"],
            "rating": card_info["rating"],
            "universe": card_info["universe"],
            "element": card_info["element"],
            "type": card_info["type"],
            "rarity": rarity,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Сохраняем обратно
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cards, f, ensure_ascii=False, indent=2)
        
        print(f"💾 [{session_name}] Редкая карта сохранена: {card_info['name']} ({rarity})")
        
    except Exception as e:
        print(f"❌ [{session_name}] Ошибка при сохранении карты: {e}")

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

async def use_attempts(client, entity, attempts, card_type):
    """
    Использует попытки для получения карт
    Возвращает (timeout, last_card_info)
    """
    command = "⚔️ Получить карту" if card_type == "battle" else "🏵️ Получить карту"
    emoji = "⚔️" if card_type == "battle" else "🎭"
    
    print(f"{emoji} [{client.session.filename}] Используем {attempts} попыток для {card_type} карт...")
    
    last_card_info = None
    
    for i in range(attempts):
        try:
            print(f"{emoji} [{client.session.filename}] Попытка {i+1}/{attempts}...")
            await client.send_message(entity, command)
            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка после отправки команды
            
            try:
                reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                if reply and reply.raw_text:
                    # Проверяем на сообщение о таймауте
                    if "следующая попытка будет доступна через" in reply.raw_text.lower():
                        print(f"⏰ [{client.session.filename}] Обнаружен таймаут: {reply.raw_text}")
                        # Парсим время таймаута
                        time_match = re.search(r'через (\d+) ч (\d+) мин', reply.raw_text)
                        if time_match:
                            hours = int(time_match.group(1))
                            minutes = int(time_match.group(2))
                            total_minutes = hours * 60 + minutes + 1  # +1 минута
                            print(f"⏰ [{client.session.filename}] Устанавливаем таймаут на {total_minutes} минут")
                            return (total_minutes, last_card_info)
                        return (240, last_card_info)  # 4 часа по умолчанию
                    
                    card_info = parse_card_response(reply.raw_text, card_type)
                    if card_info:
                        last_card_info = card_info  # Сохраняем информацию о последней карте
                        rarity = is_rare_card(card_info["rating"])
                        if rarity:
                            card_info["rarity"] = rarity
                            save_card_to_file(client.session.filename, card_info)
                            send_card_notification(client.session.filename, card_info)
                            print(f"🎉 [{client.session.filename}] Редкая карта: {card_info['name']} (Рейтинг: {card_info['rating']})")
                        else:
                            print(f"📝 [{client.session.filename}] Обычная карта: {card_info['name']} (Рейтинг: {card_info['rating']})")
                            
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при попытке {i+1}")
            
            if i < attempts - 1:
                await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между попытками получения карт
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при попытке {i+1}: {e}")
    
    return (0, last_card_info)  # Нет таймаута

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

# === ОСНОВНОЙ ЦИКЛ КАРТ ===

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
        print(f"✅ [{client.session.filename}] Профиль получен")
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
        last_battle_card = None
        last_collection_card = None
        
        if battle_attempts > 0 or collection_attempts > 0:
            print(f"🎯 [{client.session.filename}] Тратим попытки из профиля...")
            
            if battle_attempts > 0:
                timeout, last_battle_card = await use_attempts(client, entity, battle_attempts, "battle")
                if timeout > 0:
                    print(f"⏰ [{client.session.filename}] Установлен таймаут: {timeout} минут")
                    return timeout
            
            if collection_attempts > 0:
                timeout, last_collection_card = await use_attempts(client, entity, collection_attempts, "collection")
                if timeout > 0:
                    print(f"⏰ [{client.session.filename}] Установлен таймаут: {timeout} минут")
                    return timeout
        
        # 3. Тратим по 1 крутке каждого вида (дополнительно)
        print(f"🎯 [{client.session.filename}] Тратим по 1 крутке каждого вида...")
        
        # Тратим боевую крутку
        timeout, battle_card = await use_attempts(client, entity, 1, "battle")
        if battle_card:
            last_battle_card = battle_card
        if timeout > 0:
            print(f"⏰ [{client.session.filename}] Установлен таймаут: {timeout} минут")
            return timeout
        
        # Задержка между крутками
        await asyncio.sleep(MESSAGE_TIMEOUT)
        
        # Тратим коллекционную крутку
        timeout, collection_card = await use_attempts(client, entity, 1, "collection")
        if collection_card:
            last_collection_card = collection_card
        if timeout > 0:
            print(f"⏰ [{client.session.filename}] Установлен таймаут: {timeout} минут")
            return timeout
        
        # 4. Ищем и фильтруем полученные карты (только если есть редкие карты)
        rare_cards = []
        if last_battle_card and is_rare_card(last_battle_card["rating"]):
            rare_cards.append(last_battle_card)
        if last_collection_card and is_rare_card(last_collection_card["rating"]):
            rare_cards.append(last_collection_card)
        
        if rare_cards:
            print(f"🎉 [{client.session.filename}] Найдено {len(rare_cards)} редких карт, выполняем фильтрацию...")
            
            for card in rare_cards:
                print(f"🔍 [{client.session.filename}] Фильтруем карту: {card['name']} (Рейтинг: {card['rating']})")
                
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
                            print(f"📝 [{client.session.filename}] Отправляем название карты: {card['name']}")
                            await asyncio.sleep(MESSAGE_TIMEOUT)  # Задержка между действиями
                            msg = await send_message_and_wait(client, entity, card['name'])
                            
                            if msg and "Выберите нужные фильтры для карт" in msg.raw_text:
                                print(f"🎛️ [{client.session.filename}] Устанавливаем фильтры...")
                                # Устанавливаем фильтры для карты
                                success = await set_card_filters(client, entity, card['name'], card['type'])
                                if success:
                                    print(f"✅ [{client.session.filename}] Фильтры установлены для {card['name']}")
                                else:
                                    print(f"❌ [{client.session.filename}] Ошибка установки фильтров для {card['name']}")
                            else:
                                print(f"ℹ️ [{client.session.filename}] Не получен запрос фильтров")
                        else:
                            print(f"ℹ️ [{client.session.filename}] Не получен запрос названия карты")
                    else:
                        print(f"ℹ️ [{client.session.filename}] Кнопка 'Название ➕' не найдена")
                else:
                    print(f"ℹ️ [{client.session.filename}] Нет кнопок в сообщении 'Мои карты'")
        else:
            print(f"ℹ️ [{client.session.filename}] Нет редких карт для фильтрации")

        print(f"🎉 [{client.session.filename}] Цикл карт завершен!")
        return 0  # Нет таймаута
        
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в цикле карт: {e}")
        print(f"🔍 [{client.session.filename}] Тип ошибки: {type(e).__name__}")
        import traceback
        print(f"📋 [{client.session.filename}] Детали ошибки: {traceback.format_exc()}")
        return 0

async def run_card_cycle():
    """
    Запускает цикл карт для всех аккаунтов
    Возвращает максимальный таймаут среди всех аккаунтов
    """
    try:
        # Загружаем конфигурацию аккаунтов
        with open("accounts.json", "r", encoding="utf-8") as f:
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
                
                client = TelegramClient(session_name, API_ID, API_HASH)
                
                try:
                    await client.start()
                    user = await client.get_me()
                    print(f"✅ [{session_name}] Подключен как: @{user.username} ({user.phone})")
                    
                    # Запускаем цикл карт
                    timeout = await card_cycle_for_account(client, bot_username)
                    
                    if timeout > 0:
                        print(f"⏰ [{session_name}] Следующий цикл через {timeout} минут")
                    else:
                        print(f"✅ [{session_name}] Цикл завершен без таймаута")
                    
                    return timeout
                    
                except Exception as e:
                    print(f"❌ [{session_name}] Ошибка: {e}")
                    return 0
                finally:
                    await client.disconnect()
        
        # Запускаем все аккаунты и собираем таймауты
        tasks = [process_account(acc) for acc in accounts]
        timeouts = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтруем только успешные таймауты (исключаем исключения)
        valid_timeouts = [t for t in timeouts if isinstance(t, int) and t >= 0]
        
        print("🎉 Цикл карт завершен для всех аккаунтов!")
        
        # Возвращаем максимальный таймаут среди всех аккаунтов
        if valid_timeouts:
            max_timeout = max(valid_timeouts)
            if max_timeout > 0:
                print(f"⏰ Максимальный таймаут: {max_timeout} минут")
                return max_timeout
        
        return 0  # Нет таймаутов
        
    except Exception as e:
        print(f"❌ Ошибка при запуске цикла карт: {e}")
        return 0

async def main():
    """
    Главная функция
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "now":
        print("🚀 Запуск цикла карт немедленно")
        await run_card_cycle()
    else:
        print("🕐 Запуск цикла карт каждые 4 часа 10 секунд...")
        
        while True:
            try:
                # Запускаем цикл и получаем таймаут
                timeout_minutes = await run_card_cycle()
                
                if timeout_minutes > 0:
                    # Используем таймаут от бота + 1 минута
                    wait_time = timeout_minutes * 60 + 60  # минуты в секунды + 1 минута
                    print(f"⏰ Следующий цикл через {timeout_minutes} минут (установлено ботом)")
                else:
                    # Используем стандартный интервал 4 часа 10 секунд
                    wait_time = 4 * 60 * 60 + 10  # 4 часа 10 секунд
                    print(f"⏰ Следующий цикл через 4 часа 10 секунд (стандартный интервал)")
                
                print(f"⏰ Ожидание {wait_time} секунд...")
                await asyncio.sleep(wait_time)
                
            except KeyboardInterrupt:
                print("🛑 Остановка цикла карт...")
                break
            except Exception as e:
                print(f"❌ Ошибка в главном цикле: {e}")
                print("⏰ Повтор через 5 минут...")
                await asyncio.sleep(300)  # 5 минут

if __name__ == "__main__":
    asyncio.run(main())
