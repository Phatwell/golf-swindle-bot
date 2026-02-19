#!/bin/bash
# Stop Golf Swindle Bot

echo "Stopping Golf Swindle Bot..."
pkill -f swindle_bot_v5_admin.py

if [ $? -eq 0 ]; then
    echo "✅ Bot stopped"
else
    echo "⚠️  No running bot found"
fi

# Clean up Chrome/ChromeDriver processes left behind
echo "Cleaning up Chrome processes..."
pkill -f chromedriver 2>/dev/null
pkill -f "chrome.*user-data-dir=./chrome_profile" 2>/dev/null
sleep 1

# Check for any remaining zombie processes
ZOMBIES=$(ps aux | grep -E "(chromedriver|chrome_profile)" | grep -v grep | wc -l)
if [ "$ZOMBIES" -gt 0 ]; then
    echo "⚠️  Force killing remaining Chrome processes..."
    pkill -9 -f chromedriver 2>/dev/null
    pkill -9 -f "chrome.*user-data-dir=./chrome_profile" 2>/dev/null
fi

echo "✅ All cleaned up"
