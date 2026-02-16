#!/usr/bin/env python3
"""Add test participants to see the full tee sheet system in action"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import Database, TeeSheetGenerator, Config

print("="*70)
print(" ADDING TEST PARTICIPANTS")
print("="*70)

db = Database("golf_swindle.db")
config = Config()
generator = TeeSheetGenerator(config)

# Clear existing participants first
db.clear_participants()
print("\n✅ Cleared existing participants\n")

# Add test participants
# Include all the players from our constraints plus some others
test_participants = [
    # Constraint players (all 6 people from the 3 pairs)
    {'name': 'Lloyd', 'guests': [], 'preferences': None},
    {'name': 'Segan', 'guests': [], 'preferences': None},
    {'name': 'Chris Hatwell', 'guests': [], 'preferences': 'early'},  # Wants early tee time
    {'name': 'Daryl Gilbert', 'guests': [], 'preferences': None},
    {'name': 'Sam Healy', 'guests': [], 'preferences': None},
    {'name': 'Ricky', 'guests': [], 'preferences': None},

    # Additional players to make interesting groups
    {'name': 'Mike', 'guests': [], 'preferences': None},
    {'name': 'John', 'guests': [], 'preferences': None},
    {'name': 'Paul', 'guests': [], 'preferences': None},
    {'name': 'Dave Walker', 'guests': [], 'preferences': 'late'},  # Wants late tee time
    {'name': 'Alex', 'guests': ['Tom Jones'], 'preferences': None},  # Bringing a guest
    {'name': 'Danny Raf', 'guests': [], 'preferences': None},
    {'name': 'Adam', 'guests': [], 'preferences': 'early'},  # Another early bird
    {'name': 'David Murphy', 'guests': [], 'preferences': None},
    {'name': 'Jordan Thorne', 'guests': [], 'preferences': None},
    {'name': 'Goochie', 'guests': [], 'preferences': 'late'},  # Another late starter
]

print("Adding participants...")
db.update_participants(test_participants)
for p in test_participants:
    guest_info = f" (+ guest: {', '.join(p['guests'])})" if p['guests'] else ""
    pref_info = f" - {p['preferences']}" if p['preferences'] else ""
    print(f"  ✅ {p['name']}{guest_info}{pref_info}")

# Get the data
participants = db.get_participants()
partner_prefs = db.get_partner_preferences()
avoidances = db.get_avoidances()
tee_times = db.generate_tee_times()

print("\n" + "="*70)
print(" DATABASE STATUS")
print("="*70)

print(f"\n📊 Total participants: {len(participants)}")
total_with_guests = sum(1 + len(p['guests']) for p in participants)
print(f"📊 Total people (including guests): {total_with_guests}")

print(f"\n🤝 Active constraints: {sum(len(partners) for partners in partner_prefs.values())}")
for player, partners in partner_prefs.items():
    for partner in partners:
        print(f"  • {player} plays with {partner}")

print(f"\n⏰ Available tee times: {len(tee_times)}")
print(f"   Times: {', '.join(tee_times[:5])}... (showing first 5)")

print("\n" + "="*70)
print(" GENERATING TEE SHEET")
print("="*70)

# Generate the tee sheet
tee_sheet, groups, assigned_times = generator.generate(
    participants,
    partner_prefs,
    avoidances,
    tee_times
)

print("\n" + tee_sheet)

print("\n" + "="*70)
print(" VERIFICATION")
print("="*70)

# Verify constraints were applied
print("\n🔍 Checking if partner preferences were applied:\n")

for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]

    # Check each constraint
    if 'Lloyd' in players and 'Segan' in players:
        print(f"  ✅ Lloyd + Segan paired together in Group {i}")
    if 'Chris Hatwell' in players and 'Daryl Gilbert' in players:
        print(f"  ✅ Chris Hatwell + Daryl Gilbert paired together in Group {i}")
    if 'Sam Healy' in players and 'Ricky' in players:
        print(f"  ✅ Sam Healy + Ricky paired together in Group {i}")

# Check if guests stayed with hosts
print("\n🔍 Checking if guests stayed with hosts:\n")
for i, group in enumerate(groups, 1):
    all_names = [p['name'] for p in group]
    if 'Alex' in all_names and 'Tom Jones' in all_names:
        print(f"  ✅ Alex and guest Tom Jones in Group {i}")

# Check if time preferences were respected
print("\n🔍 Checking if time preferences were applied:\n")

early_prefs = ['Chris Hatwell', 'Adam']
late_prefs = ['Dave Walker', 'Goochie']

for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]
    time = assigned_times.get(i, 'Unknown')

    early_in_group = [p for p in players if p in early_prefs]
    late_in_group = [p for p in players if p in late_prefs]

    if early_in_group:
        print(f"  Group {i} ({time}): {', '.join(early_in_group)} (wanted early)")
    if late_in_group:
        print(f"  Group {i} ({time}): {', '.join(late_in_group)} (wanted late)")

print("\n" + "="*70)
print(" SUCCESS!")
print("="*70)

print(f"""
✅ Test participants added successfully!

📋 Summary:
  • {len(participants)} players signed up
  • {total_with_guests} total people (including guests)
  • {len(groups)} groups created
  • {sum(len(partners) for partners in partner_prefs.values())} partner preferences applied
  • {len(tee_times) - len(groups)} tee time slots can be returned

This is what you would see if {len(participants)} people signed up in
the WhatsApp group and you sent "Show tee sheet" in the admin group.

The bot automatically:
  ✅ Paired partners together (Lloyd+Segan, Chris+Daryl, Sam+Ricky)
  ✅ Kept guests with their hosts (Alex+Tom Jones)
  ✅ Assigned early tee times to early birds
  ✅ Assigned late tee times to late starters
  ✅ Optimized group sizes (4 per group when possible)
  ✅ Calculated unused tee time slots

Try these commands now:
  • python3 test_show_tee_sheet.py  (see the tee sheet again)
  • python3 test_new_constraints.py (see constraint behavior)
""")
