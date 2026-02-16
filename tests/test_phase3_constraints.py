#!/usr/bin/env python3
"""Test Phase 3 constraint system"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import AdminCommandHandler, Database, TeeSheetGenerator, Config
import os

print("="*60)
print(" TESTING PHASE 3 CONSTRAINT SYSTEM")
print("="*60)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ No API key found")
    exit(1)

# Test 1: Command Parsing
print("\n" + "="*60)
print(" TEST 1: Command Parsing")
print("="*60)

handler = AdminCommandHandler(api_key)

test_commands = [
    ("Mike plays with John", "set_partner_preference"),
    ("pair Alex with Tom", "set_partner_preference"),
    ("don't pair Mike with David", "set_avoidance"),
    ("keep Alex away from Tom", "set_avoidance"),
    ("show constraints", "show_constraints"),
    ("remove Mike's partner preference", "remove_partner_preference"),
    ("remove avoidance for Alex", "remove_avoidance"),
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

# Test 2: Database Constraints
print("="*60)
print(" TEST 2: Database Constraint Operations")
print("="*60)

db = Database("/tmp/test_phase3.db")

# Clear any existing constraints
print("\n📝 Testing constraint operations...")

# Add partner preferences
print("\n✅ Adding partner preferences:")
db.add_constraint('partner_preference', 'Mike', 'John')
db.add_constraint('partner_preference', 'Alex', 'Tom')
print("   • Mike plays with John")
print("   • Alex plays with Tom")

# Add avoidances
print("\n⚠️  Adding avoidances:")
db.add_constraint('avoid', 'David', 'Steve')
print("   • David avoids Steve")

# Get constraints
print("\n📋 Getting all constraints:")
constraints = db.get_constraints()
for c in constraints:
    print(f"   • {c['type']}: {c['player']} -> {c['target']}")

print(f"\nTotal constraints: {len(constraints)}")

# Get partner preferences
partner_prefs = db.get_partner_preferences()
print(f"\n🤝 Partner preferences dict: {partner_prefs}")

# Get avoidances
avoidances = db.get_avoidances()
print(f"⚠️  Avoidances dict: {avoidances}")

# Test 3: Tee Sheet Generation with Constraints
print("\n" + "="*60)
print(" TEST 3: Tee Sheet Generation with Constraints")
print("="*60)

# Add test participants
participants = [
    {'name': 'Mike', 'guests': [], 'preferences': None},
    {'name': 'John', 'guests': [], 'preferences': None},
    {'name': 'Alex', 'guests': [], 'preferences': None},
    {'name': 'Tom', 'guests': [], 'preferences': None},
    {'name': 'David', 'guests': [], 'preferences': None},
    {'name': 'Steve', 'guests': [], 'preferences': None},
    {'name': 'Paul', 'guests': [], 'preferences': None},
    {'name': 'Chris', 'guests': [], 'preferences': None},
]

config = Config()
generator = TeeSheetGenerator(config)

print("\nParticipants:")
for p in participants:
    print(f"  • {p['name']}")

print("\nConstraints:")
print(f"  • Mike plays with John")
print(f"  • Alex plays with Tom")
print(f"  • David avoids Steve")

print("\n🏌️ Generating tee sheet...")
tee_sheet, groups = generator.generate(participants, partner_prefs, avoidances)

print("\n" + tee_sheet)

print("\n📊 Group Analysis:")
for i, group in enumerate(groups, 1):
    names = [p['name'] for p in group]
    print(f"  Group {i}: {', '.join(names)}")

    # Check if partner preferences are respected
    if 'Mike' in names and 'John' in names:
        print(f"    ✅ Mike and John paired together")
    if 'Alex' in names and 'Tom' in names:
        print(f"    ✅ Alex and Tom paired together")

    # Check if avoidances are respected
    if 'David' in names and 'Steve' in names:
        print(f"    ❌ WARNING: David and Steve in same group (avoidance violated!)")

print("\n" + "="*60)
print(" PHASE 3 TESTS COMPLETE")
print("="*60)
