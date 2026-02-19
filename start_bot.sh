#!/bin/bash
# Golf Swindle Bot Startup Script

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

# Stop any existing bot + Chrome processes first
./stop_bot.sh 2>/dev/null
sleep 2

# Start bot
echo "Starting Golf Swindle Bot..."
nohup ./venv/bin/python3 -u src/swindle_bot_v5_admin.py > logs/bot.log 2>&1 &

BOT_PID=$!
echo "✅ Bot started in background"
echo "PID: $BOT_PID"
echo ""
echo "Commands:"
echo "  View logs:  tail -f logs/bot.log"
echo "  Stop bot:   ./stop_bot.sh"
echo "  Check status: ps aux | grep swindle_bot"