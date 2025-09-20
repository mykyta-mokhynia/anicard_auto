#!/bin/bash

# Fix line endings for macOS .command files

echo "🔧 Исправление окончаний строк для macOS..."

# Find all .command files and fix line endings
find tools/macos -name "*.command" -type f -exec sed -i '' 's/\r$//' {} \;

# Make all .command files executable
chmod +x tools/macos/*.command

echo "✅ Окончания строк исправлены!"
echo "✅ Права на выполнение установлены!"

# Test the main script
echo ""
echo "🧪 Тестируем запуск..."
./tools/macos/start_macos.command

