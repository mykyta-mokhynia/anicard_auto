#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Line Endings - Исправление окончаний строк для macOS
"""

import os
import glob

def fix_line_endings(file_path):
    """Исправляет окончания строк в файле"""
    try:
        # Читаем файл в бинарном режиме
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Заменяем CRLF на LF
        content = content.replace(b'\r\n', b'\n')
        
        # Записываем обратно
        with open(file_path, 'wb') as f:
            f.write(content)
        
        print(f"✅ Исправлен: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при исправлении {file_path}: {e}")
        return False

def main():
    """Исправляет окончания строк во всех .command файлах"""
    print("🔧 Исправление окончаний строк для macOS...")
    print()
    
    # Ищем все .command файлы
    command_files = []
    command_files.extend(glob.glob("tools/macos/*.command"))
    command_files.extend(glob.glob("*.command"))
    
    if not command_files:
        print("❌ .command файлы не найдены")
        return
    
    print(f"📁 Найдено {len(command_files)} .command файлов:")
    for file_path in command_files:
        print(f"  - {file_path}")
    print()
    
    success_count = 0
    for file_path in command_files:
        if fix_line_endings(file_path):
            success_count += 1
    
    print()
    print(f"🎉 Исправлено {success_count} из {len(command_files)} файлов")
    
    # Даем права на выполнение
    print()
    print("🔐 Устанавливаем права на выполнение...")
    for file_path in command_files:
        try:
            os.chmod(file_path, 0o755)
            print(f"✅ Права установлены: {file_path}")
        except Exception as e:
            print(f"❌ Ошибка установки прав для {file_path}: {e}")

if __name__ == "__main__":
    main()
