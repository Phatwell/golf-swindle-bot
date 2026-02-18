#!/bin/bash
# Check Golf Swindle Bot Status

echo "🔍 Checking bot status..."
echo ""

PID=$(pgrep -f swindle_bot_v5_admin.py)

if [ -n "$PID" ]; then
    echo "✅ Bot is RUNNING"
    echo "   PID: $PID"
    echo "   Runtime: $(ps -o etime= -p $PID | tr -d ' ')"
    echo ""
    echo "📋 Recent logs (last 10 lines):"
    tail -10 logs/bot.log
else
    echo "❌ Bot is NOT running"
    echo ""
    echo "To start: ./start_bot.sh"
fi