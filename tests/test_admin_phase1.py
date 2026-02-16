#!/usr/bin/env python3
"""Test Phase 1: Admin Commands"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import AdminCommandHandler, Config
import os

print("="*60)
print(" TESTING PHASE 1: ADMIN COMMANDS")
print("="*60)

# Test imports
config = Config()
print(f"\n✅ Config loaded:")
print(f"   Admin Group: {config.ADMIN_GROUP_NAME}")
print(f"   Admin Users: {config.ADMIN_USERS}")

# Test AdminCommandHandler
print("\n" + "="*60)
print(" TESTING AI COMMAND PARSER")
print("="*60)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ No API key found")
    exit(1)

handler = AdminCommandHandler(api_key)

# Test commands
test_commands = [
    "Show me the list",
    "Who's playing this Sunday?",
    "Show tee sheet",
    "What does the tee sheet look like?",
    "Show groups",
    "Who's in?",
    "Random nonsense that shouldn't work",
]

print(f"\nTesting {len(test_commands)} commands...\n")

for cmd in test_commands:
    result = handler.parse_command(cmd, "ADMIN_USER")

    command = result.get('command', 'unknown')
    confidence = result.get('confidence', 'unknown')

    if command == 'show_list':
        icon = "📋"
        status = "✅"
    elif command == 'show_tee_sheet':
        icon = "🏌️"
        status = "✅"
    elif command == 'unknown':
        icon = "❓"
        status = "⚠️ "
    else:
        icon = "🔧"
        status = "🔨"

    print(f"{status} \"{cmd}\"")
    print(f"   {icon} Command: {command} (confidence: {confidence})\n")

print("="*60)
print(" PHASE 1 COMMAND PARSER TEST COMPLETE")
print("="*60)

print("\n✅ Ready to test with real bot!")
print("\nNext steps:")
print("1. Make sure 'Sunday Swindle Bot Admin' WhatsApp group exists")
print("2. Add your number to ADMIN_USERS in config")
print("3. Run: python3 swindle_bot_v5_admin.py")
print("4. In admin group, try: 'Show list' or 'Show tee sheet'")
