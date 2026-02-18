#!/bin/bash
# Stop Golf Swindle Bot

echo "Stopping Golf Swindle Bot..."
pkill -f swindle_bot_v5_admin.py

if [ $? -eq 0 ]; then
    echo "✅ Bot stopped"
else
    echo "⚠️  No running bot found"
fi