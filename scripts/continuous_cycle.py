#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anicard Continuous Cycle - Непрерывный цикл
Запускает ежедневный цикл в 22:01 UTC и цикл карт каждые 4ч 10с
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
import pytz

# Добавляем родительскую директорию в путь для импорта
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Импортируем функции из combined_cycle
try:
    from combined_cycle import run_daily_cycle, run_card_cycle
except ImportError:
    # Если импорт не удался, добавляем текущую директорию в путь
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from combined_cycle import run_daily_cycle, run_card_cycle

# Блокировка для предотвращения одновременного запуска циклов
cycle_lock = asyncio.Lock()

async def wait_until_daily_time():
    """
    Ждет до 22:01 UTC
    """
    utc = pytz.UTC
    now = datetime.now(utc)
    
    # Создаем время 22:01 UTC на сегодня
    target_time = now.replace(hour=22, minute=1, second=0, microsecond=0)
    
    # Если время уже прошло, планируем на завтра
    if now >= target_time:
        target_time += timedelta(days=1)
    
    wait_seconds = (target_time - now).total_seconds()
    
    print(f"🕐 Текущее время UTC: {now.strftime('%H:%M:%S')}")
    print(f"⏰ Следующий ежедневный цикл в: {target_time.strftime('%H:%M:%S UTC')}")
    print(f"⏳ Ожидание: {wait_seconds/3600:.1f} часов")
    
    await asyncio.sleep(wait_seconds)

async def continuous_cycle():
    """
    Непрерывный цикл: ежедневный в 22:01 UTC + карты каждые 4 часа 10 секунд
    """
    print("🚀 Запуск непрерывного цикла Anicard Auto")
    print("=" * 50)
    
    # Запускаем задачи параллельно
    daily_task = asyncio.create_task(daily_cycle_scheduler())
    card_task = asyncio.create_task(card_cycle_scheduler())
    
    try:
        # Ждем завершения обеих задач
        await asyncio.gather(daily_task, card_task)
    except KeyboardInterrupt:
        print("\n🛑 Остановка непрерывного цикла...")
        daily_task.cancel()
        card_task.cancel()
    except Exception as e:
        print(f"\n❌ Ошибка в непрерывном цикле: {e}")

async def daily_cycle_scheduler():
    """
    Планировщик ежедневного цикла (22:01 UTC)
    """
    while True:
        try:
            # Проверяем блокировку
            if cycle_lock.locked():
                print(f"⏳ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ежедневный цикл ждет завершения другого цикла...")
                await asyncio.sleep(60)  # Ждем 1 минуту
                continue
            
            # Запускаем ежедневный цикл с блокировкой
            async with cycle_lock:
                print(f"\n🌅 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск ежедневного цикла...")
                await run_daily_cycle()
                print(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ежедневный цикл завершен!")
            
            # Ждем до следующего 22:01 UTC
            print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ожидание следующего ежедневного цикла...")
            await wait_until_daily_time()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\n❌ Ошибка в ежедневном цикле: {e}")
            print("⏰ Повтор через 5 минут...")
            await asyncio.sleep(300)  # 5 минут

async def card_cycle_scheduler():
    """
    Планировщик цикла карт (каждые 4 часа 10 секунд)
    """
    while True:
        try:
            # Проверяем блокировку
            if cycle_lock.locked():
                print(f"⏳ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Цикл карт ждет завершения другого цикла...")
                await asyncio.sleep(60)  # Ждем 1 минуту
                continue
            
            # Запускаем цикл карт с блокировкой
            async with cycle_lock:
                print(f"\n🎴 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск цикла карт...")
                await run_card_cycle()
                print(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Цикл карт завершен!")
            
            # Ждем 4 часа 10 секунд
            print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ожидание следующего цикла карт (4 часа 10 секунд)...")
            await asyncio.sleep(4 * 3600 + 10)  # 4 часа 10 секунд
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\n❌ Ошибка в цикле карт: {e}")
            print("⏰ Повтор через 5 минут...")
            await asyncio.sleep(300)  # 5 минут

async def card_cycle_only():
    """
    Только цикл карт каждые 4 часа 10 секунд
    """
    print("🎴 Запуск цикла карт каждые 4 часа 10 секунд")
    print("=" * 50)
    
    while True:
        try:
            print(f"\n🎴 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск цикла карт...")
            await run_card_cycle()
            
            # Ждем 4 часа 10 секунд
            wait_time = 4 * 60 * 60 + 10  # 4 часа 10 секунд
            print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Следующий цикл карт через {wait_time} секунд...")
            await asyncio.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("\n🛑 Остановка цикла карт...")
            break
        except Exception as e:
            print(f"\n❌ Ошибка в цикле карт: {e}")
            print("⏰ Повтор через 5 минут...")
            await asyncio.sleep(300)  # 5 минут

async def daily_cycle_only():
    """
    Только ежедневный цикл в 22:01 UTC
    """
    print("🌅 Запуск ежедневного цикла в 22:01 UTC")
    print("=" * 50)
    
    while True:
        try:
            # Ждем до 22:01 UTC
            await wait_until_daily_time()
            
            print(f"\n🌅 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск ежедневного цикла...")
            await run_daily_cycle()
            
        except KeyboardInterrupt:
            print("\n🛑 Остановка ежедневного цикла...")
            break
        except Exception as e:
            print(f"\n❌ Ошибка в ежедневном цикле: {e}")
            print("⏰ Повтор через 5 минут...")
            await asyncio.sleep(300)  # 5 минут

async def main():
    """
    Главная функция
    """
    if len(sys.argv) > 1:
        if sys.argv[1] == "continuous":
            await continuous_cycle()
        elif sys.argv[1] == "cards":
            await card_cycle_only()
        elif sys.argv[1] == "daily":
            await daily_cycle_only()
        else:
            print("Использование: python continuous_cycle.py [continuous|cards|daily]")
    else:
        # По умолчанию запускаем непрерывный цикл
        print("♾️ Запуск непрерывного цикла...")
        await continuous_cycle()

if __name__ == "__main__":
    asyncio.run(main())
