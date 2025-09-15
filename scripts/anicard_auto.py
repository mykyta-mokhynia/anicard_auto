import asyncio, json, os, random, re, datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError

load_dotenv()

# Загружаем API ключи из .env
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MESSAGE_TIMEOUT = int(os.getenv("MESSAGE_TIMEOUT", "30"))

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

# === ФУНКЦИИ ДЛЯ РАБОТЫ С КАРТАМИ ===

def parse_card_response(text, card_type):
    """
    Парсит ответ бота на получение карты и извлекает информацию о редких картах
    Возвращает dict с информацией о карте или None если карта не редкая
    """
    # Определяем редкости для каждого типа карт
    if card_type == "battle":
        rare_keywords = ["Легендарная", "Мифическая", "Адамантиновая"]
    elif card_type == "collection":
        rare_keywords = ["Легендарная", "Мифическая"]
    else:
        return None
    
    # Ищем редкость в тексте
    rarity = None
    for keyword in rare_keywords:
        if keyword in text:
            rarity = keyword
            break
    
    if not rarity:
        return None
    
    # Парсим информацию о карте
    card_info = {
        "rarity": rarity,
        "type": card_type,
        "name": "",
        "universe": "",
        "element": "",
        "character": "",
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
        
        # Ищем элемент
        element_match = re.search(r'Элемент: (.+)', text)
        if element_match:
            card_info["element"] = element_match.group(1).strip()
    
    # Для коллекционных карт
    elif card_type == "collection":
        # Ищем персонажа
        character_match = re.search(r'👤 Персонаж: (.+)', text)
        if character_match:
            card_info["character"] = character_match.group(1).strip()
    
    return card_info

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
            data = {"legendary": [], "mythic": [], "adamantine": []}
    else:
        data = {"legendary": [], "mythic": [], "adamantine": []}
    
    # Определяем категорию редкости
    rarity = card_info["rarity"]
    if rarity == "Легендарная":
        category = "legendary"
    elif rarity == "Мифическая":
        category = "mythic"
    elif rarity == "Адамантиновая":
        category = "adamantine"
    else:
        return
    
    # Добавляем карту в соответствующую категорию
    card_entry = {"name": card_info["name"] or card_info["character"]}
    if card_info["universe"]:
        card_entry["universe"] = card_info["universe"]
    if card_info["element"]:
        card_entry["element"] = card_info["element"]
    if card_info["character"]:
        card_entry["character"] = card_info["character"]
    
    data[category].append(card_entry)
    
    # Сохраняем обновленные данные
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_card_notification(session_name, card_info):
    """
    Отправляет уведомление о получении редкой карты
    """
    rarity_emoji = {
        "Легендарная": "🌟",
        "Мифическая": "✨", 
        "Адамантиновая": "💎"
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
    
    if card_info["name"]:
        print(f"🎴 Карта: {card_info['name']}")
    if card_info["character"]:
        print(f"👤 Персонаж: {card_info['character']}")
    if card_info["universe"]:
        print(f"🔮 Вселенная: {card_info['universe']}")
    if card_info["element"]:
        print(f"🍃 Элемент: {card_info['element']}")
    
    print("=" * 50)

async def get_current_accounts():
    """
    Загружает текущий список аккаунтов из accounts.json
    """
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("accounts", [])
    except FileNotFoundError:
        print("❌ Файл accounts.json не найден!")
        return []
    except Exception as e:
        print(f"❌ Ошибка загрузки аккаунтов: {e}")
        return []

async def use_battle_attempts(client, entity, attempts):
    """
    Использует попытки для получения боевых карт
    """
    print(f"⚔️ [{client.session.filename}] Используем {attempts} попыток для боевых карт...")
    
    for i in range(attempts):
        try:
            print(f"⚔️ [{client.session.filename}] Попытка {i+1}/{attempts}...")
            await client.send_message(entity, "⚔️ Получить карту")
            
            # Ждем ответ
            try:
                reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                if reply and reply.raw_text:
                    # Парсим карту
                    card_info = parse_card_response(reply.raw_text, "battle")
                    if card_info:
                        # Сохраняем в файл
                        save_card_to_file(client.session.filename, card_info)
                        # Отправляем уведомление
                        send_card_notification(client.session.filename, card_info)
                    else:
                        print(f"📝 [{client.session.filename}] Обычная карта (попытка {i+1})")
                            
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при попытке {i+1}")
            
            # Задержка между попытками
            if i < attempts - 1:
                await asyncio.sleep(MESSAGE_TIMEOUT)
                
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при попытке {i+1}: {e}")

async def use_collection_attempts(client, entity, attempts):
    """
    Использует попытки для получения коллекционных карт
    """
    print(f"🎭 [{client.session.filename}] Используем {attempts} попыток для коллекционных карт...")
    
    for i in range(attempts):
        try:
            print(f"🎭 [{client.session.filename}] Попытка {i+1}/{attempts}...")
            await client.send_message(entity, "🏵️ Получить карту")
            
            # Ждем ответ
            try:
                reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                if reply and reply.raw_text:
                    # Проверяем, не повторная ли карта
                    if "повторная карта" in reply.raw_text.lower():
                        print(f"🔄 [{client.session.filename}] Повторная карта (попытка {i+1})")
                    else:
                        # Парсим карту
                        card_info = parse_card_response(reply.raw_text, "collection")
                        if card_info:
                        # Сохраняем в файл
                        save_card_to_file(client.session.filename, card_info)
                        # Отправляем уведомление
                        send_card_notification(client.session.filename, card_info)
                    else:
                        print(f"📝 [{client.session.filename}] Обычная карта (попытка {i+1})")
                            
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при попытке {i+1}")
            
            # Задержка между попытками
            if i < attempts - 1:
                await asyncio.sleep(MESSAGE_TIMEOUT)
                
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при попытке {i+1}: {e}")

# === СЦЕНАРИЙ ДЛЯ ОДНОГО АККАУНТА ===

async def run_daily_rewards(client, bot_username):
    """
    Ежедневный сценарий получения наград для одного аккаунта:
    1) Открыть меню
    2) Перейти в "⛩ Дары богов" (4-я кнопка)
    3) Получить награды по очереди:
       - 🀄️ Мистический жетон (3-я кнопка) - ежедневно
       - 🎲 Древний куб удачи (1-я кнопка) - раз в неделю
       - 📯 Рог призыва (2-я кнопка) - раз в неделю
    """
    try:
        entity = await client.get_entity(bot_username)
        
        print(f"🎯 [{client.session.filename}] Начинаем получение ежедневных наград...")

        # 1) Открываем меню
        try:
            await client.send_message(entity, "📜 Меню")
            msg = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
            print(f"📋 [{client.session.filename}] Меню открыто")
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при открытии меню: {e}")
            return False
        
        # Задержка перед переходом в подменю
        print(f"⏱️ [{client.session.filename}] Ждем {MESSAGE_TIMEOUT} сек...")
        await asyncio.sleep(MESSAGE_TIMEOUT)

        # 2) Переходим в "Дары богов" (4-я кнопка)
        try:
            print(f"🔍 [{client.session.filename}] Ищем кнопку 'Дары богов'...")
            
            # Показываем доступные кнопки для отладки
            if msg.buttons:
                button_texts = [b.text for row in msg.buttons for b in row]
                print(f"📋 [{client.session.filename}] Доступные кнопки: {button_texts}")
            
            clicked = await click_button(msg, text="⛩ Дары богов")
            print(f"🔍 [{client.session.filename}] Результат клика по тексту: {clicked}")
            
            if not clicked:
                # Если не нашли по тексту, пробуем по индексу (4-я кнопка = индекс 3)
                print(f"🔍 [{client.session.filename}] Пробуем кликнуть по индексу 3...")
                clicked = await click_button(msg, index=3)
                print(f"🔍 [{client.session.filename}] Результат клика по индексу: {clicked}")
            
            if not clicked:
                print(f"❌ [{client.session.filename}] Не удалось найти кнопку 'Дары богов'")
                return False
            
            print(f"🎁 [{client.session.filename}] Переходим в 'Дары богов'")
            
            # Ждем ответ после клика (увеличиваем таймаут)
            try:
                msg = await wait_new_from(client, entity, timeout=10)  # 10 секунд вместо MESSAGE_TIMEOUT
                print(f"✅ [{client.session.filename}] Успешно перешли в 'Дары богов'")
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при переходе в 'Дары богов', пробуем продолжить...")
                # Попробуем получить последнее сообщение
                try:
                    async for message in client.iter_messages(entity, limit=1):
                        msg = message
                        print(f"📱 [{client.session.filename}] Используем последнее сообщение")
                        break
                except:
                    print(f"❌ [{client.session.filename}] Не удалось получить сообщения")
                    return False
            
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при переходе в 'Дары богов': {e}")
            return False
        
        # Задержка перед получением наград
        print(f"⏱️ [{client.session.filename}] Ждем {MESSAGE_TIMEOUT} сек перед получением наград...")
        await asyncio.sleep(MESSAGE_TIMEOUT)

        # Показываем доступные кнопки наград для отладки
        if msg.buttons:
            button_texts = [b.text for row in msg.buttons for b in row]
            print(f"📋 [{client.session.filename}] Кнопки наград: {button_texts}")

        # 3) Получаем мистический жетон (3-я кнопка, индекс 2) - ежедневно
        try:
            print(f"🀄️ [{client.session.filename}] Получаем мистический жетон...")
            await click_button(msg, index=2)
            
            # Ждем любое новое сообщение после клика (увеличиваем таймаут)
            try:
                print(f"⏳ [{client.session.filename}] Ждем ответ от бота...")
                reply = await wait_new_from(client, entity, timeout=15)
                print(f"📱 [{client.session.filename}] Получен ответ: {reply.raw_text[:100]}...")
                
                # Проверяем, есть ли popup с информацией о времени
                if "сент" in reply.raw_text or "2025" in reply.raw_text or "доступн" in reply.raw_text.lower():
                    print(f"ℹ️ [{client.session.filename}] Награда уже получена, следующая будет доступна позже")
                    # Продолжаем с тем же меню
                elif reply.buttons:
                    msg = reply
                    button_texts = [b.text for row in msg.buttons for b in row]
                    print(f"✅ [{client.session.filename}] Мистический жетон получен! Новое меню: {button_texts}")
                else:
                    print(f"✅ [{client.session.filename}] Мистический жетон получен! (без кнопок)")
                    
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при получении мистического жетона")
                # Попробуем получить последнее сообщение
                try:
                    async for message in client.iter_messages(entity, limit=1):
                        if message.buttons:
                            msg = message
                            print(f"📱 [{client.session.filename}] Используем последнее сообщение с кнопками")
                        break
                except:
                    print(f"❌ [{client.session.filename}] Не удалось получить последнее сообщение")
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при получении мистического жетона: {e}")

        # Задержка между наградами
        print(f"⏱️ [{client.session.filename}] Ждем {MESSAGE_TIMEOUT} сек перед следующей наградой...")
        await asyncio.sleep(MESSAGE_TIMEOUT)

        # 4) Получаем древний куб удачи (1-я кнопка, индекс 0) - раз в неделю
        try:
            print(f"🎲 [{client.session.filename}] Получаем древний куб удачи...")
            await click_button(msg, index=0)
            
            try:
                reply = await wait_new_from(client, entity, timeout=10)
                print(f"📱 [{client.session.filename}] Получен ответ: {reply.raw_text[:100]}...")
                
                # Проверяем, есть ли popup с информацией о времени
                if "сент" in reply.raw_text or "2025" in reply.raw_text or "доступн" in reply.raw_text.lower():
                    print(f"ℹ️ [{client.session.filename}] Награда уже получена, следующая будет доступна позже")
                    # Продолжаем с тем же меню
                elif reply.buttons:
                    msg = reply
                    button_texts = [b.text for row in msg.buttons for b in row]
                    print(f"✅ [{client.session.filename}] Древний куб удачи получен! Новое меню: {button_texts}")
                    
                    # Проверяем, есть ли попытки для круток
                    attempts_match = re.search(r'Вы получаете ⚔️ (\d+) попыток', reply.raw_text)
                    if attempts_match:
                        battle_attempts = int(attempts_match.group(1))
                        print(f"🎯 [{client.session.filename}] Получено {battle_attempts} попыток для боевых карт!")
                        
                        # Используем попытки
                        await use_battle_attempts(client, entity, battle_attempts)
                    
                    # Проверяем коллекционные попытки
                    collection_attempts_match = re.search(r'Вы получаете 🎭 (\d+) попыток', reply.raw_text)
                    if collection_attempts_match:
                        collection_attempts = int(collection_attempts_match.group(1))
                        print(f"🎯 [{client.session.filename}] Получено {collection_attempts} попыток для коллекционных карт!")
                        
                        # Используем попытки
                        await use_collection_attempts(client, entity, collection_attempts)
                        
                else:
                    print(f"✅ [{client.session.filename}] Древний куб удачи получен! (без кнопок)")
                    
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при получении древнего куба удачи")
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при получении древнего куба удачи: {e}")

        # Задержка между наградами
        print(f"⏱️ [{client.session.filename}] Ждем {MESSAGE_TIMEOUT} сек перед следующей наградой...")
        await asyncio.sleep(MESSAGE_TIMEOUT)

        # 5) Получаем рог призыва (2-я кнопка, индекс 1) - раз в неделю
        try:
            print(f"📯 [{client.session.filename}] Получаем рог призыва...")
            await click_button(msg, index=1)
            
            try:
                reply = await wait_new_from(client, entity, timeout=10)
                print(f"📱 [{client.session.filename}] Получен ответ: {reply.raw_text[:100]}...")
                
                # Проверяем, есть ли popup с информацией о времени
                if "сент" in reply.raw_text or "2025" in reply.raw_text or "доступн" in reply.raw_text.lower():
                    print(f"ℹ️ [{client.session.filename}] Награда уже получена, следующая будет доступна позже")
                    # Продолжаем с тем же меню
                elif reply.buttons:
                    msg = reply
                    button_texts = [b.text for row in msg.buttons for b in row]
                    print(f"✅ [{client.session.filename}] Рог призыва получен! Новое меню: {button_texts}")
                else:
                    print(f"✅ [{client.session.filename}] Рог призыва получен! (без кнопок)")
                    
                    # Рог призыва всегда дает легендарную коллекционную карту
                    # Парсим ответ как легендарную коллекционную карту
                    card_info = parse_card_response(reply.raw_text, "collection")
                    if card_info:
                        # Принудительно устанавливаем редкость как легендарную
                        card_info["rarity"] = "Легендарная"
                        card_info["type"] = "collection"
                        
                        # Сохраняем в файл
                        save_card_to_file(client.session.filename, card_info)
                        # Отправляем уведомление
                        send_card_notification(client.session.filename, card_info)
                    else:
                        print(f"📝 [{client.session.filename}] Обычная карта от рога призыва")
                    
            except asyncio.TimeoutError:
                print(f"⚠️ [{client.session.filename}] Таймаут при получении рога призыва")
        except Exception as e:
            print(f"❌ [{client.session.filename}] Ошибка при получении рога призыва: {e}")

        print(f"🎉 [{client.session.filename}] Все награды получены!")
        return True
        
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в run_daily_rewards: {e}")
        return False

async def get_cards(client, bot_username, card_type="both", count=1):
    """
    Получение карт для одного аккаунта:
    - card_type: "collection" (🏵️), "battle" (⚔️), "both" (обе)
    - count: количество карт для получения
    """
    try:
        entity = await client.get_entity(bot_username)
        
        print(f"🎴 [{client.session.filename}] Начинаем получение карт...")
        print(f"📊 [{client.session.filename}] Тип: {card_type}, Количество: {count}")

        # Определяем команды для отправки
        card_commands = []
        if card_type in ["collection", "both"]:
            for _ in range(count):
                card_commands.append("🏵️ Получить карту")
        if card_type in ["battle", "both"]:
            for _ in range(count):
                card_commands.append("⚔️ Получить карту")
        
        for i, command in enumerate(card_commands):
            try:
                print(f"🎴 [{client.session.filename}] Отправляем: {command}")
                await client.send_message(entity, command)
                
                # Задержка между командами (0.7 секунды)
                if i < len(card_commands) - 1:  # Не ждем после последней команды
                    print(f"⏱️ [{client.session.filename}] Ждем {MESSAGE_TIMEOUT} сек перед следующей командой...")
                    await asyncio.sleep(MESSAGE_TIMEOUT)
                
                # Ждем подтверждение
                try:
                    reply = await wait_new_from(client, entity, timeout=MESSAGE_TIMEOUT)
                    print(f"✅ [{client.session.filename}] Карта получена: {command}")
                    
                    # Парсим ответ на предмет редких карт
                    if reply and reply.raw_text:
                        # Проверяем, не повторная ли карта
                        if "повторная карта" in reply.raw_text.lower():
                            print(f"🔄 [{client.session.filename}] Повторная карта: {command}")
                        else:
                            # Определяем тип карты по команде
                            current_card_type = "battle" if "⚔️" in command else "collection"
                            
                            # Парсим ответ
                            card_info = parse_card_response(reply.raw_text, current_card_type)
                            if card_info:
                                # Сохраняем в файл
                                save_card_to_file(client.session.filename, card_info)
                                # Отправляем уведомление
                                send_card_notification(client.session.filename, card_info)
                            else:
                                print(f"📝 [{client.session.filename}] Обычная карта: {command}")
                            
                except asyncio.TimeoutError:
                    print(f"⚠️ [{client.session.filename}] Таймаут при получении карты: {command}")
                    
            except Exception as e:
                print(f"❌ [{client.session.filename}] Ошибка при отправке {command}: {e}")
                # Продолжаем с следующей командой
                continue

        print(f"🎉 [{client.session.filename}] Все карты получены!")
        return True
        
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в get_cards: {e}")
        return False

async def run_combined_tasks(client, bot_username):
    """
    Комбинированный запуск: карты + награды
    1) Получение карт (с задержкой 0.7 сек между командами)
    2) Получение наград из даров (с задержкой 0.7 сек между действиями)
    """
    try:
        print(f"🚀 [{client.session.filename}] Запуск комбинированных задач...")
        
        # 1) Получаем карты
        print(f"🎴 [{client.session.filename}] === ЭТАП 1: ПОЛУЧЕНИЕ КАРТ ===")
        cards_success = await get_cards(client, bot_username, "both", 1)
        
        # Задержка между этапами
        print(f"⏱️ [{client.session.filename}] Ждем {MESSAGE_TIMEOUT} сек между этапами...")
        await asyncio.sleep(MESSAGE_TIMEOUT)
        
        # 2) Получаем награды
        print(f"🎁 [{client.session.filename}] === ЭТАП 2: ПОЛУЧЕНИЕ НАГРАД ===")
        rewards_success = await run_daily_rewards(client, bot_username)
        
        if cards_success and rewards_success:
            print(f"🎉 [{client.session.filename}] Все задачи выполнены успешно!")
            return True
        else:
            print(f"⚠️ [{client.session.filename}] Некоторые задачи завершились с ошибками")
            return False
            
    except Exception as e:
        print(f"❌ [{client.session.filename}] Ошибка в run_combined_tasks: {e}")
        return False

async def run_continuous_loop(selected_accounts=None):
    """
    Непрерывный цикл: награды + карты
    """
    print("🔄 Запуск непрерывного цикла...")
    print("⏰ Награды будут получаться каждые 24 часа")
    print("🎴 Карты будут получаться каждые 4 часа 1 минуту")
    print("👥 Автоматическая проверка новых аккаунтов включена")
    print("🛑 Для остановки нажмите Ctrl+C")
    
    while True:
        try:
            # Проверяем наличие новых аккаунтов
            current_accounts = await get_current_accounts()
            if selected_accounts is None:
                selected_accounts = current_accounts
                print(f"👥 Загружено {len(current_accounts)} аккаунтов из конфигурации")
            
            # Проверяем новые аккаунты перед получением наград
            new_accounts = await get_current_accounts()
            if len(new_accounts) > len(selected_accounts):
                new_count = len(new_accounts) - len(selected_accounts)
                print(f"🆕 Обнаружено {new_count} новых аккаунтов! Обновляем список...")
                
                # Показываем информацию о новых аккаунтах
                existing_sessions = [acc["session"] for acc in selected_accounts]
                for new_acc in new_accounts:
                    if new_acc["session"] not in existing_sessions:
                        print(f"   ➕ {new_acc['session']} ({new_acc.get('phone', 'N/A')})")
                
                selected_accounts = new_accounts
                print(f"👥 Теперь активных аккаунтов: {len(selected_accounts)}")
            
            # Получаем награды (только в 22:01 UTC)
            print("🎁 === ПОЛУЧЕНИЕ НАГРАД ===")
            await run_scenario_for_selected_accounts(run_daily_rewards, selected_accounts)
            
            # Получаем карты каждые 4 часа 1 минуту до следующего дня
            while True:
                # Проверяем новые аккаунты перед каждым циклом карт
                new_accounts = await get_current_accounts()
                if len(new_accounts) > len(selected_accounts):
                    new_count = len(new_accounts) - len(selected_accounts)
                    print(f"🆕 Обнаружено {new_count} новых аккаунтов! Обновляем список...")
                    
                    # Показываем информацию о новых аккаунтах
                    existing_sessions = [acc["session"] for acc in selected_accounts]
                    for new_acc in new_accounts:
                        if new_acc["session"] not in existing_sessions:
                            print(f"   ➕ {new_acc['session']} ({new_acc.get('phone', 'N/A')})")
                    
                    selected_accounts = new_accounts
                    print(f"👥 Теперь активных аккаунтов: {len(selected_accounts)}")
                
                print("🎴 === ПОЛУЧЕНИЕ КАРТ ===")
                # Создаем функцию-обертку для get_cards с параметрами по умолчанию
                async def get_cards_wrapper(client, bot_username):
                    return await get_cards(client, bot_username, "both", 1)
                await run_scenario_for_selected_accounts(get_cards_wrapper, selected_accounts)
                
                # Ждем 4 часа 1 минуту до следующего получения карт
                print("⏰ Ждем 4 часа 1 минуту до следующего получения карт...")
                await wait_until_cards_time()
                
                # Проверяем, не пора ли получать награды (22:01 UTC)
                import pytz
                utc_now = datetime.datetime.now(pytz.UTC)
                if utc_now.hour == 22 and utc_now.minute >= 1:
                    print("⏰ Время получения наград! Переходим к наградам...")
                    break
            
        except KeyboardInterrupt:
            print("\n🛑 Остановка непрерывного цикла...")
            break
        except Exception as e:
            print(f"❌ Ошибка в непрерывном цикле: {e}")
            print("⏰ Ждем 5 минут перед повтором...")
            await asyncio.sleep(300)

async def show_cards_statistics(selected_accounts=None):
    """
    Показывает статистику карт (коллекционные + боевые) через команду "🎒 Профиль"
    """
    print("📊 Получаем статистику карт...")
    
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        
        api_id = API_ID
        api_hash = API_HASH
        bot = cfg.get("bot", "@YourTargetBot")
        
        # Если не указаны конкретные аккаунты, берем все
        if selected_accounts is None:
            accounts = cfg["accounts"]
        else:
            accounts = selected_accounts
        
        if not accounts:
            print("❌ Нет аккаунтов для обработки!")
            return
        
        print("\n📊 Статистика по аккаунтам:")
        print("=" * 60)
        
        for acc in accounts:
            client = TelegramClient(acc["session"], api_id, api_hash)
            try:
                await client.start(phone=acc.get("phone"))
                entity = await client.get_entity(acc.get("bot", bot))
                
                # Отправляем команду для получения профиля
                print(f"🔍 [{acc['session']}] Запрашиваем профиль...")
                await client.send_message(entity, "🎒 Профиль")
                
                # Ждем ответ с профилем
                try:
                    profile_msg = await wait_new_from(client, entity, timeout=10)
                    profile_text = profile_msg.raw_text
                    
                    # Парсим информацию из профиля
                    collection_cards = 0
                    battle_cards = 0
                    anicoin = 0
                    tokens = 0
                    battlecoin = 0
                    battle_attempts = 0
                    collection_attempts = 0
                    
                    # Ищем количество карт в строке "Карты"
                    cards_match = re.search(r'Карты\s*·\s*⚔️\s*-\s*(\d+)\s*\|\s*🎭\s*-\s*(\d+)', profile_text)
                    if cards_match:
                        battle_cards = int(cards_match.group(1))
                        collection_cards = int(cards_match.group(2))
                    
                    # Ищем баланс
                    balance_match = re.search(r'Баланс:\s*·\s*🪙\s*Anicoin\s*-\s*(\d+)\s*·\s*🀄️\s*Жетоны\s*-\s*(\d+)\s*·\s*🎖\s*BattleCoin\s*-\s*(\d+)', profile_text)
                    if balance_match:
                        anicoin = int(balance_match.group(1))
                        tokens = int(balance_match.group(2))
                        battlecoin = int(balance_match.group(3))
                    
                    # Ищем попытки
                    attempts_match = re.search(r'Попытки:\s*·\s*⚔️\s*-\s*(\d+)\s*\|\s*🎭\s*-\s*(\d+)', profile_text)
                    if attempts_match:
                        battle_attempts = int(attempts_match.group(1))
                        collection_attempts = int(attempts_match.group(2))
                    
                    # Выводим статистику для аккаунта
                    print(f"👤 [{acc['session']}] ({acc.get('phone', 'N/A')})")
                    print(f"   ⚔️ Боевые карты: {battle_cards}")
                    print(f"   🎭 Коллекционные карты: {collection_cards}")
                    print(f"   🪙 Anicoin: {anicoin}")
                    print(f"   🀄️ Жетоны: {tokens}")
                    print(f"   🎖 BattleCoin: {battlecoin}")
                    print(f"   🔄 Попытки: ⚔️ {battle_attempts} | 🎭 {collection_attempts}")
                    print()
                    
                except asyncio.TimeoutError:
                    print(f"⚠️ [{acc['session']}] Таймаут при получении профиля")
                except Exception as e:
                    print(f"❌ [{acc['session']}] Ошибка парсинга профиля: {e}")
                
            except Exception as e:
                print(f"❌ [{acc['session']}] Ошибка подключения: {e}")
            finally:
                await client.disconnect()
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")

def show_rare_cards(selected_accounts=None):
    """
    Показывает сохраненные редкие карты для выбранных аккаунтов
    """
    print("🎴 Просмотр редких карт...")
    
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        
        # Если не указаны конкретные аккаунты, берем все
        if selected_accounts is None:
            accounts = cfg["accounts"]
        else:
            accounts = selected_accounts
        
        if not accounts:
            print("❌ Нет аккаунтов для обработки!")
            return
        
        print("\n🎴 Редкие карты по аккаунтам:")
        print("=" * 60)
        
        for acc in accounts:
            session_name = acc["session"]
            file_path = os.path.join(CARDS_FOLDER, f"{session_name}.json")
            
            print(f"\n👤 [{session_name}] ({acc.get('phone', 'N/A')})")
            
            if not os.path.exists(file_path):
                print("   📝 Нет сохраненных карт")
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Показываем карты по категориям
                for category, cards in data.items():
                    if not cards:
                        continue
                    
                    category_name = {
                        "legendary": "🌟 Легендарные",
                        "mythic": "✨ Мифические", 
                        "adamantine": "💎 Адамантиновые"
                    }.get(category, category)
                    
                    print(f"   {category_name}: {len(cards)}")
                    for card in cards:
                        name = card.get("name", card.get("character", "Неизвестно"))
                        print(f"      • {name}")
                        if card.get("universe"):
                            print(f"        🔮 {card['universe']}")
                        if card.get("element"):
                            print(f"        🍃 {card['element']}")
                        if card.get("character") and card.get("name"):
                            print(f"        👤 {card['character']}")
                
                if not any(data.values()):
                    print("   📝 Нет редких карт")
                    
            except Exception as e:
                print(f"   ❌ Ошибка чтения файла: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# === ПЛАНИРОВЩИКИ ===

async def wait_until_time(target_hour=22, target_minute=1):
    """
    Ждем до указанного времени по UTC (по умолчанию 22:01 UTC)
    """
    import pytz
    
    # Получаем текущее время в UTC
    utc_now = datetime.datetime.now(pytz.UTC)
    target_time_utc = utc_now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    # Если время уже прошло сегодня, ждем до завтра
    if utc_now >= target_time_utc:
        target_time_utc += datetime.timedelta(days=1)
    
    wait_seconds = (target_time_utc - utc_now).total_seconds()
    
    # Показываем время в UTC и локальном времени
    local_tz = datetime.datetime.now().astimezone().tzinfo
    target_local = target_time_utc.astimezone(local_tz)
    
    print(f"⏰ Ждем до {target_time_utc.strftime('%H:%M UTC')} ({target_local.strftime('%H:%M местного времени')})")
    print(f"⏱️ Осталось ждать: {wait_seconds:.0f} секунд ({wait_seconds/3600:.1f} часов)")
    
    await asyncio.sleep(wait_seconds)
    print("⏰ Время пришло! Запускаем получение наград...")

async def wait_until_cards_time():
    """
    Ждем 4 часа и 1 минуту с момента вызова функции
    """
    import pytz
    
    utc_now = datetime.datetime.now(pytz.UTC)
    
    # Добавляем 4 часа и 1 минуту к текущему времени
    target_time_utc = utc_now + datetime.timedelta(hours=4, minutes=1)
    
    wait_seconds = (target_time_utc - utc_now).total_seconds()
    
    # Показываем время в UTC и локальном времени
    local_tz = datetime.datetime.now().astimezone().tzinfo
    target_local = target_time_utc.astimezone(local_tz)
    
    print(f"⏰ Ждем до {target_time_utc.strftime('%H:%M UTC')} ({target_local.strftime('%H:%M местного времени')})")
    print(f"⏱️ Осталось ждать: {wait_seconds:.0f} секунд ({wait_seconds/3600:.1f} часов)")
    
    await asyncio.sleep(wait_seconds)
    print("⏰ Время получения карт пришло! Запускаем...")

# === РАБОТНИК НА ОДИН АККАУНТ ===

async def worker(acc, api_id, api_hash, bot, sema, scenario_func):
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
                
                # при первом запуске попросит код/2FA; дальше будет использовать .session
                await client.start(phone=phone)
                
                # Получаем информацию о пользователе для отображения
                try:
                    me = await client.get_me()
                    user_info = f"@{me.username}" if me.username else f"{me.first_name or ''} {me.last_name or ''}".strip()
                    if not user_info:
                        user_info = f"ID: {me.id}"
                    print(f"✅ [{session}] Подключен как: {user_info} ({phone})")
                except:
                    print(f"✅ [{session}] Подключен успешно ({phone})")
                
                # случайная пауза перед сценарием, чтобы не работать синхронно
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # запускаем сценарий
                result = await scenario_func(client, acc.get("bot", bot))
                
                # финальная пауза, чтобы не завершать все одновременные сессии в один момент
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                return result
                
            except SessionPasswordNeededError:
                print(f"❌ [{session}] Нужен пароль 2FA для {phone} — введите в консоли при старте.")
                return False
            except FloodWaitError as e:
                print(f"⏰ [{session}] FloodWait для {phone}: подождите {e.seconds} сек.")
                return False
            except Exception as e:
                print(f"❌ [{session}] Ошибка для {phone}: {e}")
                return False

# === ОСНОВНЫЕ ФУНКЦИИ ===

async def run_scenario_for_all_accounts(scenario_func):
    """
    Запускает сценарий для всех аккаунтов с ограничением concurrency
    """
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # API ключи берем из .env файла
        api_id = API_ID
        api_hash = API_HASH
        bot = cfg.get("bot", "@YourTargetBot")
        concurrency = int(cfg.get("concurrency", 2))  # максимум 2 аккаунта одновременно
        accounts = cfg["accounts"]

        print(f"🔐 Настроено аккаунтов: {len(accounts)}")
        print(f"⚡ Одновременно работает: {concurrency}")
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc['session']} -> {acc.get('bot', bot)}")
        print()

        sema = asyncio.Semaphore(concurrency)
        tasks = [worker(acc, api_id, api_hash, bot, sema, scenario_func) for acc in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        print(f"🎉 Успешно обработано {success_count} из {len(accounts)} аккаунтов")
        return success_count > 0
        
    except FileNotFoundError:
        print("❌ Файл accounts.json не найден!")
        print("📝 Создайте файл accounts.json по примеру из README.md")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def run_cards_loop():
    """
    Непрерывный цикл получения карт каждые 4 часа и 1 минуту для всех аккаунтов
    """
    print("🔄 Запуск непрерывного цикла получения карт...")
    print("⏰ Карты будут получаться каждые 4 часа и 1 минуту")
    print("🛑 Для остановки нажмите Ctrl+C")
    
    while True:
        try:
            # Получаем карты для всех аккаунтов
            await run_scenario_for_all_accounts(get_cards)
            
            # Ждем 4 часа и 1 минуту
            print("⏰ Ждем 4 часа и 1 минуту до следующего получения карт...")
            await wait_until_cards_time()
            
        except KeyboardInterrupt:
            print("\n🛑 Остановка цикла получения карт...")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле карт: {e}")
            print("⏰ Ждем 5 минут перед повтором...")
            await asyncio.sleep(300)  # Ждем 5 минут при ошибке

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

# === ВЫБОР АККАУНТОВ ===

def select_card_type():
    """
    Позволяет выбрать тип карт для получения
    Возвращает кортеж (card_type, count)
    """
    print("\n🎴 Выберите тип карт:")
    print("1. 🏵️ Коллекционные карты")
    print("2. ⚔️ Боевые карты")
    print("3. 🔄 Оба типа карт")
    print("4. ❌ Отмена")
    
    while True:
        try:
            choice = input("\nВыберите тип карт (1-4): ").strip()
            
            if choice == "1":
                card_type = "collection"
                break
            elif choice == "2":
                card_type = "battle"
                break
            elif choice == "3":
                card_type = "both"
                break
            elif choice == "4":
                print("❌ Отмена выбора")
                return None, 0
            else:
                print("❌ Неверный выбор. Введите 1, 2, 3 или 4.")
        except KeyboardInterrupt:
            print("\n❌ Отмена выбора")
            return None, 0
    
    # Запрашиваем количество карт
    while True:
        try:
            count_input = input(f"\nВведите количество карт для получения (1-100): ").strip()
            count = int(count_input)
            
            if 1 <= count <= 100:
                print(f"✅ Выбрано: {card_type}, количество: {count}")
                return card_type, count
            else:
                print("❌ Количество должно быть от 1 до 100")
        except ValueError:
            print("❌ Введите корректное число")
        except KeyboardInterrupt:
            print("\n❌ Отмена выбора")
            return None, 0

def select_accounts():
    """
    Позволяет выбрать конкретные аккаунты или все аккаунты
    Возвращает список выбранных аккаунтов или None для всех
    """
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        
        accounts = cfg["accounts"]
        
        if not accounts:
            print("❌ Нет аккаунтов в конфигурации!")
            return None
        
        print("\n👥 Доступные аккаунты:")
        print("=" * 40)
        for i, acc in enumerate(accounts, 1):
            print(f"{i}. {acc['session']} ({acc.get('phone', 'N/A')})")
        print(f"{len(accounts) + 1}. 🔄 Все аккаунты")
        print(f"{len(accounts) + 2}. ❌ Отмена")
        
        while True:
            try:
                choice = input(f"\nВыберите аккаунт (1-{len(accounts) + 2}): ").strip()
                
                if choice == str(len(accounts) + 1):
                    print("🔄 Выбраны все аккаунты")
                    return None  # None означает все аккаунты
                elif choice == str(len(accounts) + 2):
                    print("❌ Отмена выбора")
                    return []
                else:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(accounts):
                        selected_acc = accounts[choice_num - 1]
                        print(f"✅ Выбран аккаунт: {selected_acc['session']} ({selected_acc.get('phone', 'N/A')})")
                        return [selected_acc]
                    else:
                        print(f"❌ Неверный выбор. Введите число от 1 до {len(accounts) + 2}")
            except ValueError:
                print("❌ Введите корректное число")
            except KeyboardInterrupt:
                print("\n❌ Отмена выбора")
                return []
                
    except FileNotFoundError:
        print("❌ Файл accounts.json не найден!")
        return None
    except Exception as e:
        print(f"❌ Ошибка при выборе аккаунтов: {e}")
        return None

async def run_cards_for_selected_accounts(selected_accounts=None, card_type="both", count=1):
    """
    Запускает получение карт для выбранных аккаунтов с указанным типом и количеством
    """
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # API ключи берем из .env файла
        api_id = API_ID
        api_hash = API_HASH
        bot = cfg.get("bot", "@YourTargetBot")
        concurrency = int(cfg.get("concurrency", 2))  # максимум 2 аккаунта одновременно
        
        # Если не указаны конкретные аккаунты, берем все
        if selected_accounts is None:
            accounts = cfg["accounts"]
        else:
            accounts = selected_accounts
        
        if not accounts:
            print("❌ Нет аккаунтов для обработки!")
            return False

        print(f"🔐 Настроено аккаунтов: {len(accounts)}")
        print(f"⚡ Одновременно работает: {concurrency}")
        print(f"🎴 Тип карт: {card_type}, Количество: {count}")
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc['session']} -> {acc.get('bot', bot)}")
        print()

        # Создаем функцию-обертку для get_cards с параметрами
        async def get_cards_wrapper(client, bot_username):
            return await get_cards(client, bot_username, card_type, count)

        sema = asyncio.Semaphore(concurrency)
        tasks = [worker(acc, api_id, api_hash, bot, sema, get_cards_wrapper) for acc in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        print(f"🎉 Успешно обработано {success_count} из {len(accounts)} аккаунтов")
        return success_count > 0
        
    except FileNotFoundError:
        print("❌ Файл accounts.json не найден!")
        print("📝 Создайте файл accounts.json по примеру из README.md")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def run_scenario_for_selected_accounts(scenario_func, selected_accounts=None):
    """
    Запускает сценарий для выбранных аккаунтов
    Если selected_accounts is None - запускает для всех аккаунтов
    Если selected_accounts is [] - не запускает ничего
    """
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # API ключи берем из .env файла
        api_id = API_ID
        api_hash = API_HASH
        bot = cfg.get("bot", "@YourTargetBot")
        concurrency = int(cfg.get("concurrency", 2))  # максимум 2 аккаунта одновременно
        
        # Если не указаны конкретные аккаунты, берем все
        if selected_accounts is None:
            accounts = cfg["accounts"]
        else:
            accounts = selected_accounts
        
        if not accounts:
            print("❌ Нет аккаунтов для обработки!")
            return False

        print(f"🔐 Настроено аккаунтов: {len(accounts)}")
        print(f"⚡ Одновременно работает: {concurrency}")
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc['session']} -> {acc.get('bot', bot)}")
        print()

        sema = asyncio.Semaphore(concurrency)
        tasks = [worker(acc, api_id, api_hash, bot, sema, scenario_func) for acc in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        print(f"🎉 Успешно обработано {success_count} из {len(accounts)} аккаунтов")
        return success_count > 0
        
    except FileNotFoundError:
        print("❌ Файл accounts.json не найден!")
        print("📝 Создайте файл accounts.json по примеру из README.md")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

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
            print("🚀 Запуск в режиме 'сейчас' - получаем награды немедленно")
            await run_scenario_for_all_accounts(run_daily_rewards)
            return
        
        elif mode == "schedule":
            print("⏰ Запуск в режиме 'планировщик' - ждем 22:01 UTC")
            await wait_until_time(22, 1)
            await run_scenario_for_all_accounts(run_daily_rewards)
            return
        
        elif mode == "cards":
            print("🎴 Запуск в режиме 'карты' - получаем карты немедленно")
            await run_scenario_for_all_accounts(get_cards)
            return
        
        elif mode == "cards_schedule":
            print("⏰ Запуск в режиме 'планировщик карт' - ждем 4 часа 1 минуту")
            await wait_until_cards_time()
            await run_scenario_for_all_accounts(get_cards)
            return
        
        elif mode == "cards_loop":
            print("🔄 Запуск в режиме 'цикл карт' - непрерывное получение каждые 4 часа 1 минуту")
            await run_cards_loop()
            return
        
        elif mode == "test":
            print("🧪 Тестовый режим - проверяем подключение к боту")
            try:
                with open("accounts.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                
                # API ключи берем из .env файла
                api_id = API_ID
                api_hash = API_HASH
                bot = cfg.get("bot", "@YourTargetBot")
                accounts = cfg["accounts"]
                
                for acc in accounts:
                    client = TelegramClient(acc["session"], api_id, api_hash)
                    try:
                        print(f"🔐 [{acc['session']}] Подключаемся к аккаунту {acc.get('phone')}...")
                        await client.start(phone=acc.get("phone"))
                        
                        # Получаем информацию о пользователе
                        try:
                            me = await client.get_me()
                            user_info = f"@{me.username}" if me.username else f"{me.first_name or ''} {me.last_name or ''}".strip()
                            if not user_info:
                                user_info = f"ID: {me.id}"
                            print(f"✅ [{acc['session']}] Подключен как: {user_info} ({acc.get('phone')})")
                        except:
                            print(f"✅ [{acc['session']}] Подключен успешно ({acc.get('phone')})")
                        
                        entity = await client.get_entity(acc.get("bot", bot))
                        await client.send_message(entity, "Меню")
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
    print("🤖 Anicard Auto - Автоматизация получения наград")
    print("=" * 50)
    print("Выберите режим:")
    print("1. 🎁 Получить награды сейчас")
    print("2. 🎴 Получить карты сейчас")
    print("3. 🔄 Непрерывный цикл (награды + карты)")
    print("4. 📊 Статистика карт (коллекционные + боевые)")
    print("5. 🎴 Просмотр редких карт")
    print("6. 🧪 Тест подключения")
    print("7. 🕐 Показать время")
    print("8. 👋 Выход")
    
    while True:
        try:
            choice = input("\nВведите номер (1-8): ").strip()
            
            if choice == "1":
                print("🎁 Получаем награды сейчас...")
                # Выбор аккаунтов
                selected_accounts = select_accounts()
                if selected_accounts != []:  # Не отмена (None = все аккаунты, [] = отмена)
                    await run_scenario_for_selected_accounts(run_daily_rewards, selected_accounts)
                break
            elif choice == "2":
                print("🎴 Получаем карты сейчас...")
                # Выбор типа карт и количества
                card_type, count = select_card_type()
                if card_type is not None:  # Не отмена
                    # Выбор аккаунтов
                    selected_accounts = select_accounts()
                    if selected_accounts != []:  # Не отмена (None = все аккаунты, [] = отмена)
                        await run_cards_for_selected_accounts(selected_accounts, card_type, count)
                break
            elif choice == "3":
                print("🔄 Запуск непрерывного цикла (награды + карты)...")
                # Выбор аккаунтов
                selected_accounts = select_accounts()
                if selected_accounts != []:  # Не отмена (None = все аккаунты, [] = отмена)
                    await run_continuous_loop(selected_accounts)
                break
            elif choice == "4":
                print("📊 Показываем статистику карт...")
                # Выбор аккаунтов
                selected_accounts = select_accounts()
                if selected_accounts != []:  # Не отмена (None = все аккаунты, [] = отмена)
                    await show_cards_statistics(selected_accounts)
                break
            elif choice == "5":
                print("🎴 Показываем редкие карты...")
                # Выбор аккаунтов
                selected_accounts = select_accounts()
                if selected_accounts != []:  # Не отмена (None = все аккаунты, [] = отмена)
                    show_rare_cards(selected_accounts)
                break
            elif choice == "6":
                print("🧪 Тестовый режим...")
                # Выбор аккаунтов
                selected_accounts = select_accounts()
                if selected_accounts != []:  # Не отмена (None = все аккаунты, [] = отмена)
                    try:
                        with open("accounts.json", "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        
                        # API ключи берем из .env файла
                        api_id = API_ID
                        api_hash = API_HASH
                        bot = cfg.get("bot", "@YourTargetBot")
                        
                        # Если не указаны конкретные аккаунты, берем все
                        if selected_accounts is None:
                            accounts = cfg["accounts"]
                        else:
                            accounts = selected_accounts
                        
                        for acc in accounts:
                            client = TelegramClient(acc["session"], api_id, api_hash)
                            try:
                                print(f"🔐 [{acc['session']}] Подключаемся к аккаунту {acc.get('phone')}...")
                                await client.start(phone=acc.get("phone"))
                                
                                # Получаем информацию о пользователе
                                try:
                                    me = await client.get_me()
                                    user_info = f"@{me.username}" if me.username else f"{me.first_name or ''} {me.last_name or ''}".strip()
                                    if not user_info:
                                        user_info = f"ID: {me.id}"
                                    print(f"✅ [{acc['session']}] Подключен как: {user_info} ({acc.get('phone')})")
                                except:
                                    print(f"✅ [{acc['session']}] Подключен успешно ({acc.get('phone')})")
                                
                                entity = await client.get_entity(acc.get("bot", bot))
                                await client.send_message(entity, "Меню")
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
            elif choice == "7":
                print("🕐 Показываем время...")
                show_time_info()
                print()
                continue
            elif choice == "8":
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Введите 1, 2, 3, 4, 5, 6, 7 или 8.")
        except KeyboardInterrupt:
            print("\n👋 Выход по Ctrl+C")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())