#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean Logs - Очистка логов
Удаляет старые логи ошибок
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

def clean_old_logs(days=7):
    """Удаляет логи старше указанного количества дней"""
    logs_folder = Path("errors")
    if not logs_folder.exists():
        print("❌ Папка с логами не найдена")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    total_size = 0
    
    print(f"🧹 Очистка логов старше {days} дней...")
    print(f"📅 Удаляем логи до: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    for log_file in logs_folder.glob("*.ndjson"):
        try:
            # Получаем время модификации файла
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            file_size = log_file.stat().st_size
            
            if file_time < cutoff_date:
                print(f"🗑️ Удаляем: {log_file.name} ({file_size} байт, {file_time.strftime('%Y-%m-%d %H:%M:%S')})")
                log_file.unlink()
                deleted_count += 1
                total_size += file_size
            else:
                print(f"✅ Оставляем: {log_file.name} ({file_size} байт, {file_time.strftime('%Y-%m-%d %H:%M:%S')})")
        except Exception as e:
            print(f"❌ Ошибка при обработке {log_file.name}: {e}")
    
    print()
    print(f"📊 Результат:")
    print(f"   Удалено файлов: {deleted_count}")
    print(f"   Освобождено места: {total_size} байт ({total_size / 1024:.1f} КБ)")

def show_log_stats():
    """Показывает статистику логов"""
    logs_folder = Path("errors")
    if not logs_folder.exists():
        print("❌ Папка с логами не найдена")
        return
    
    print("📊 СТАТИСТИКА ЛОГОВ")
    print("=" * 40)
    
    total_files = 0
    total_size = 0
    oldest_file = None
    newest_file = None
    
    for log_file in logs_folder.glob("*.ndjson"):
        try:
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            file_size = log_file.stat().st_size
            
            total_files += 1
            total_size += file_size
            
            if oldest_file is None or file_time < oldest_file[1]:
                oldest_file = (log_file.name, file_time)
            if newest_file is None or file_time > newest_file[1]:
                newest_file = (log_file.name, file_time)
            
            print(f"📄 {log_file.name}: {file_size} байт, {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"❌ Ошибка при чтении {log_file.name}: {e}")
    
    print()
    print(f"📊 Общая статистика:")
    print(f"   Всего файлов: {total_files}")
    print(f"   Общий размер: {total_size} байт ({total_size / 1024:.1f} КБ)")
    if oldest_file:
        print(f"   Самый старый: {oldest_file[0]} ({oldest_file[1].strftime('%Y-%m-%d %H:%M:%S')})")
    if newest_file:
        print(f"   Самый новый: {newest_file[0]} ({newest_file[1].strftime('%Y-%m-%d %H:%M:%S')})")

def main():
    """Главная функция"""
    print("🧹 ОЧИСТКА ЛОГОВ")
    print("=" * 30)
    
    while True:
        print("\n📋 ВЫБЕРИТЕ ДЕЙСТВИЕ:")
        print("1. Показать статистику логов")
        print("2. Очистить логи старше 3 дней")
        print("3. Очистить логи старше 7 дней")
        print("4. Очистить логи старше 30 дней")
        print("5. Удалить все логи")
        print("0. Выход")
        
        choice = input("\n👉 Введите номер: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            show_log_stats()
        elif choice == "2":
            clean_old_logs(3)
        elif choice == "3":
            clean_old_logs(7)
        elif choice == "4":
            clean_old_logs(30)
        elif choice == "5":
            confirm = input("⚠️ Вы уверены, что хотите удалить ВСЕ логи? (yes/no): ").strip().lower()
            if confirm == "yes":
                logs_folder = Path("errors")
                if logs_folder.exists():
                    for log_file in logs_folder.glob("*.ndjson"):
                        try:
                            log_file.unlink()
                            print(f"🗑️ Удален: {log_file.name}")
                        except Exception as e:
                            print(f"❌ Ошибка при удалении {log_file.name}: {e}")
                    print("✅ Все логи удалены")
                else:
                    print("❌ Папка с логами не найдена")
            else:
                print("❌ Операция отменена")
        else:
            print("❌ Неверный выбор")
        
        if choice != "0":
            input("\n⏸️ Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()

