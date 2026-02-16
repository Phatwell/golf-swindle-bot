#!/usr/bin/env python3
"""Test Phase 2 manual adjustment commands"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import AdminCommandHandler
import os

print("="*60)
print(" TESTING PHASE 2 MANUAL ADJUSTMENT COMMANDS")
print("="*60)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ No API key found")
    exit(1)

handler = AdminCommandHandler(api_key)

# Test commands
test_commands = [
    # Show commands (Phase 1)
    ("Show list", "show_list"),
    ("Show tee sheet", "show_tee_sheet"),

    # Add player (Phase 2)
    ("Add John Smith", "add_player"),
    ("add player Mike Jones", "add_player"),
    ("Put David in", "add_player"),

    # Remove player (Phase 2)
    ("Remove John Smith", "remove_player"),
    ("remove player Mike", "remove_player"),
    ("Take out Alex", "remove_player"),
    ("Delete David", "remove_player"),

    # Add guest (Phase 2)
    ("Add guest Tom for Alex", "add_guest"),
    ("Alex bringing John", "add_guest"),
    ("add John as guest of Mike", "add_guest"),

    # Remove guest (Phase 2)
    ("Remove guest Tom", "remove_guest"),
    ("remove Tom from Alex", "remove_guest"),
    ("delete guest for Mike", "remove_guest"),
]

print(f"\nTesting {len(test_commands)} commands...\n")

passed = 0
failed = 0

for cmd, expected_command in test_commands:
    result = handler.parse_command(cmd, "ADMIN_USER")

    command = result.get('command', 'unknown')
    confidence = result.get('confidence', 'unknown')
    params = result.get('params', {})

    if command == expected_command:
        status = "✅"
        passed += 1
    else:
        status = "❌"
        failed += 1

    print(f"{status} \"{cmd}\"")
    print(f"   → {command} (expected: {expected_command})")
    print(f"   Confidence: {confidence}")
    if params:
        print(f"   Params: {params}")
    print()

print("="*60)
print(f"Results: {passed} passed, {failed} failed")
print("="*60)
