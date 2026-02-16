#!/usr/bin/env python3
"""Debug admin commands and name extraction"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import AdminCommandHandler
import os

print("="*60)
print(" DEBUGGING ADMIN COMMANDS")
print("="*60)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ No API key found")
    exit(1)

handler = AdminCommandHandler(api_key)

# Test commands that should work
test_commands = [
    "Show list",
    "Show list of players",
    "Show me the list of players",
    "Who's playing",
    "Show tee sheet",
    "Show the tee sheet",
    "What's the tee sheet look like",
]

print(f"\nTesting {len(test_commands)} commands...\n")

for cmd in test_commands:
    result = handler.parse_command(cmd, "ADMIN_USER")

    command = result.get('command', 'unknown')
    confidence = result.get('confidence', 'unknown')

    if command == 'show_list':
        status = "✅"
    elif command == 'show_tee_sheet':
        status = "✅"
    elif command == 'unknown':
        status = "❌"
    else:
        status = "⚠️"

    print(f"{status} \"{cmd}\"")
    print(f"   → {command} (confidence: {confidence})")
    print(f"   Full result: {result}\n")

print("="*60)
