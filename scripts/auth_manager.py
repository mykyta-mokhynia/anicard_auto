# auth_manager.py
import asyncio, json, os, sys, getpass, pathlib, datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon import errors as te

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

ERROR_LOG = pathlib.Path("../errors/auth_errors.ndjson")
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

def log_err(kind, session, phone, detail=""):
    rec = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "kind": kind,
        "session": session,
        "phone": phone,
        "detail": str(detail)
    }
    with ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[AUTH][{session}] {kind}: {detail}")

def add_account_to_config(session, phone):
    """
    Добавляет новый аккаунт в accounts.json
    """
    accounts_file = "accounts/accounts.json"
    
    # Загружаем существующую конфигурацию или создаем новую
    if os.path.exists(accounts_file):
        try:
            with open(accounts_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except:
            config = {
                "bot": "@anicardplaybot",
                "concurrency": 2,
                "accounts": []
            }
    else:
        config = {
            "bot": "@anicardplaybot",
            "concurrency": 2,
            "accounts": []
        }
    
    # Проверяем, есть ли уже такой аккаунт
    existing_accounts = [acc["session"] for acc in config["accounts"]]
    if session in existing_accounts:
        print(f"[AUTH][{session}] Аккаунт уже существует в конфигурации")
        return
    
    # Добавляем новый аккаунт
    new_account = {
        "session": session,
        "phone": phone
    }
    config["accounts"].append(new_account)
    
    # Сохраняем обновленную конфигурацию
    try:
        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"[AUTH][{session}] ✅ Аккаунт добавлен в {accounts_file}")
    except Exception as e:
        print(f"[AUTH][{session}] ❌ Ошибка сохранения в {accounts_file}: {e}")

async def auth_one(session: str, phone: str):
    client = TelegramClient(session, API_ID, API_HASH)
    await client.connect()
    try:
        if await client.is_user_authorized():
            print(f"[AUTH][{session}] Уже авторизован.")
            return

        # Проверяем базовые ошибки номера
        try:
            # Отправляем код — на этом шаге всплывут несуществующие/некорректные номера
            await client.send_code_request(phone)
        except te.PhoneNumberInvalidError:
            log_err("PHONE_INVALID", session, phone, "Неверный формат номера")
            return
        except te.PhoneNumberUnoccupiedError:
            log_err("PHONE_NOT_REGISTERED", session, phone, "Номер не зарегистрирован в Telegram")
            return
        except te.FloodWaitError as e:
            log_err("FLOOD_WAIT", session, phone, f"Подождите {e.seconds} сек")
            return
        except Exception as e:
            log_err("SEND_CODE_ERROR", session, phone, e)
            return

        # Просим код у пользователя (в консоли)
        code = input(f"[AUTH][{session}] Введите код из Telegram для {phone}: ").strip()

        try:
            await client.sign_in(phone=phone, code=code)
        except te.SessionPasswordNeededError:
            pwd = getpass.getpass(f"[AUTH][{session}] Введите 2FA пароль: ")
            await client.sign_in(password=pwd)
        except te.PhoneCodeInvalidError:
            log_err("CODE_INVALID", session, phone, "Неверный код подтверждения")
            return
        except te.PhoneCodeExpiredError:
            log_err("CODE_EXPIRED", session, phone, "Код истёк")
            return

        if await client.is_user_authorized():
            print(f"[AUTH][{session}] ✅ Успех. Создан файл сессии.")
            # Добавляем аккаунт в конфигурацию
            add_account_to_config(session, phone)
        else:
            log_err("AUTH_UNKNOWN", session, phone, "Авторизация не подтверждена")

    finally:
        await client.disconnect()

def usage():
    print("Использование:")
    print("python scripts/auth_manager.py --session account_3 --phone +10000000003")
    print("python scripts/auth_manager.py --phone +10000000003  # автоматически создаст account_X")
    print("или пакетно из json:")
    print("  python scripts/auth_manager.py --batch phones.json")
    print("phones.json пример: {\"items\": [{\"session\": \"account_3\", \"phone\": \"+100...\"}]}")
    print("или без session (автоматически): {\"items\": [{\"phone\": \"+100...\"}]}")
    print("")
    print("При успешной авторизации аккаунт автоматически добавляется в accounts.json")

def get_next_account_name():
    """
    Получает следующее доступное имя аккаунта (account_1, account_2, etc.)
    """
    accounts_file = "accounts/accounts.json"
    
    if not os.path.exists(accounts_file):
        return "account_1"
    
    try:
        with open(accounts_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        existing_accounts = [acc["session"] for acc in config.get("accounts", [])]
        
        # Ищем следующий доступный номер
        counter = 1
        while f"account_{counter}" in existing_accounts:
            counter += 1
        
        return f"account_{counter}"
    except:
        return "account_1"

async def main():
    if "--help" in sys.argv or len(sys.argv) == 1:
        usage(); return

    tasks = []
    if "--batch" in sys.argv:
        path = sys.argv[sys.argv.index("--batch") + 1]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for it in data.get("items", []):
            # Если session не указан, генерируем автоматически
            session = it.get("session")
            if not session:
                session = get_next_account_name()
            tasks.append(auth_one(session, it["phone"]))
    else:
        session = sys.argv[sys.argv.index("--session") + 1] if "--session" in sys.argv else None
        phone   = sys.argv[sys.argv.index("--phone") + 1] if "--phone" in sys.argv else None
        
        # Если session не указан, генерируем автоматически
        if not session and phone:
            session = get_next_account_name()
            print(f"[AUTH] Автоматически создано имя сессии: {session}")
        
        if not session or not phone:
            usage(); return
        tasks.append(auth_one(session, phone))

    for coro in tasks:
        await coro

if __name__ == "__main__":
    asyncio.run(main())
