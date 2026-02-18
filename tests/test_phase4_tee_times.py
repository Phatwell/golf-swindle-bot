#!/usr/bin/env python3
"""Test Phase 4: Dynamic Tee Time Management"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot_v5_admin import AdminCommandHandler, Database, TeeSheetGenerator, Config

print("="*70)
print(" TESTING PHASE 4: DYNAMIC TEE TIME MANAGEMENT")
print("="*70)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ No API key found")
    exit(1)

# Test 1: Command Parsing
print("\n" + "="*70)
print(" TEST 1: Command Parsing for Tee Time Management")
print("="*70)

handler = AdminCommandHandler(api_key)

test_commands = [
    ("show tee times", "show_tee_times"),
    ("set tee times from 8:00", "set_tee_times"),
    ("configure tee times starting at 8am", "set_tee_times"),
    ("Mike prefers early", "set_time_preference"),
    ("Dave wants late tee time", "set_time_preference"),
]

passed = 0
failed = 0

for cmd, expected in test_commands:
    result = handler.parse_command(cmd, "ADMIN_USER")
    command = result.get('command', 'unknown')

    if command == expected:
        status = "✅"
        passed += 1
    else:
        status = "❌"
        failed += 1

    print(f"{status} \"{cmd}\" → {command}")
    if result.get('params'):
        print(f"   Params: {result['params']}")

print(f"\nCommand Parsing: {passed} passed, {failed} failed\n")

# Test 2: Tee Time Configuration
print("="*70)
print(" TEST 2: Tee Time Configuration")
print("="*70)

db = Database("/tmp/test_phase4.db")

print("\n📝 Setting tee time configuration...")
success = db.set_tee_time_settings("08:00", 8, 12)
print(f"   {'✅' if success else '❌'} Set settings: 08:00, 8min intervals, 12 slots")

print("\n📋 Getting tee time settings...")
settings = db.get_tee_time_settings()
if settings:
    print(f"   ✅ Start: {settings['start_time']}")
    print(f"   ✅ Interval: {settings['interval_minutes']} minutes")
    print(f"   ✅ Slots: {settings['num_slots']}")
else:
    print(f"   ❌ Failed to get settings")

print("\n⏰ Generating tee times...")
tee_times = db.generate_tee_times()
print(f"   Generated {len(tee_times)} tee times:")
for i, t in enumerate(tee_times[:5]):
    print(f"   {i+1}. {t}")
if len(tee_times) > 5:
    print(f"   ... and {len(tee_times)-5} more")

# Test 3: Tee Sheet with Time Preferences
print("\n" + "="*70)
print(" TEST 3: Tee Sheet Generation with Time Preferences")
print("="*70)

# Create participants with time preferences
participants = [
    {'name': 'Mike', 'guests': [], 'preferences': 'early'},  # Early preference
    {'name': 'John', 'guests': [], 'preferences': 'early'},  # Early preference
    {'name': 'Alex', 'guests': [], 'preferences': 'late'},   # Late preference
    {'name': 'Tom', 'guests': [], 'preferences': 'late'},    # Late preference
    {'name': 'David', 'guests': [], 'preferences': None},    # No preference
    {'name': 'Steve', 'guests': [], 'preferences': None},    # No preference
    {'name': 'Paul', 'guests': [], 'preferences': None},     # No preference
    {'name': 'Chris', 'guests': [], 'preferences': None},    # No preference
]

print("\nParticipants and preferences:")
for p in participants:
    pref = p['preferences'] or 'no preference'
    print(f"  • {p['name']}: {pref}")

config = Config()
generator = TeeSheetGenerator(config)

# No constraints for this test
partner_prefs = {}
avoidances = {}

print("\n🏌️ Generating tee sheet with time preferences...")
tee_sheet, groups, assigned_times = generator.generate(
    participants, partner_prefs, avoidances, tee_times
)

print("\n" + tee_sheet)

print("\n" + "="*70)
print(" VERIFICATION: Time Preferences Respected?")
print("="*70)

# Analyze if preferences were respected
early_players = [p['name'] for p in participants if p.get('preferences') == 'early']
late_players = [p['name'] for p in participants if p.get('preferences') == 'late']

print(f"\nEarly preference players: {', '.join(early_players)}")
print(f"Late preference players: {', '.join(late_players)}")

# Check which times each group got
for i, group in enumerate(groups, 1):
    time = list(assigned_times.values())[i-1] if i <= len(assigned_times) else "Unknown"
    players_in_group = [p['name'] for p in group if not p.get('is_guest')]

    has_early = any(name in early_players for name in players_in_group)
    has_late = any(name in late_players for name in players_in_group)

    print(f"\nGroup {i} ({time}):")
    print(f"  Players: {', '.join(players_in_group)}")

    if has_early and not has_late:
        # Check if this is an early time (before midpoint)
        time_idx = tee_times.index(time) if time in tee_times else -1
        midpoint = len(tee_times) // 2
        if time_idx < midpoint:
            print(f"  ✅ Early preference group assigned to early time")
        else:
            print(f"  ⚠️  Early preference but got later time")
    elif has_late and not has_early:
        time_idx = tee_times.index(time) if time in tee_times else -1
        midpoint = len(tee_times) // 2
        if time_idx >= midpoint:
            print(f"  ✅ Late preference group assigned to late time")
        else:
            print(f"  ⚠️  Late preference but got earlier time")
    else:
        print(f"  ℹ️  Mixed or no preference")

print("\n" + "="*70)
print(" PHASE 4 TESTS COMPLETE")
print("="*70)
