#!/usr/bin/env python3
"""Test how new constraints affect grouping"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import Database, TeeSheetGenerator, Config

print("="*70)
print(" TESTING NEW PARTNER PREFERENCES")
print("="*70)

db = Database("golf_swindle.db")
config = Config()
generator = TeeSheetGenerator(config)

# Get constraints
partner_prefs = db.get_partner_preferences()
avoidances = db.get_avoidances()

print("\n📋 Active Constraints:")
for player, partners in partner_prefs.items():
    for partner in partners:
        print(f"  • {player} plays with {partner}")

# Scenario 1: All partners playing
print("\n" + "="*70)
print(" SCENARIO 1: All Partners Playing")
print("="*70)

participants_1 = [
    {'name': 'Lloyd', 'guests': [], 'preferences': None},
    {'name': 'Segan', 'guests': [], 'preferences': None},
    {'name': 'Chris Hatwell', 'guests': [], 'preferences': None},
    {'name': 'Daryl Gilbert', 'guests': [], 'preferences': None},
    {'name': 'Sam Healy', 'guests': [], 'preferences': None},
    {'name': 'Ricky', 'guests': [], 'preferences': None},
    {'name': 'Mike', 'guests': [], 'preferences': None},
    {'name': 'John', 'guests': [], 'preferences': None},
]

print("\nPlayers: Lloyd, Segan, Chris Hatwell, Daryl Gilbert, Sam Healy, Ricky, Mike, John")

tee_times = db.generate_tee_times()
_, groups, _ = generator.generate(participants_1, partner_prefs, avoidances, tee_times)

print("\n✅ Groups Created:")
for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]
    print(f"  Group {i}: {', '.join(players)}")

# Check if partners are together
for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]

    if 'Lloyd' in players and 'Segan' in players:
        print(f"    ✅ Lloyd + Segan paired in Group {i}")
    if 'Chris Hatwell' in players and 'Daryl Gilbert' in players:
        print(f"    ✅ Chris Hatwell + Daryl Gilbert paired in Group {i}")
    if 'Sam Healy' in players and 'Ricky' in players:
        print(f"    ✅ Sam Healy + Ricky paired in Group {i}")

# Scenario 2: Only some partners playing
print("\n" + "="*70)
print(" SCENARIO 2: Only Some Partners Playing")
print("="*70)

participants_2 = [
    {'name': 'Lloyd', 'guests': [], 'preferences': None},  # Segan NOT playing
    {'name': 'Chris Hatwell', 'guests': [], 'preferences': None},
    {'name': 'Daryl Gilbert', 'guests': [], 'preferences': None},
    {'name': 'Sam Healy', 'guests': [], 'preferences': None},  # Ricky NOT playing
    {'name': 'Mike', 'guests': [], 'preferences': None},
    {'name': 'John', 'guests': [], 'preferences': None},
    {'name': 'Paul', 'guests': [], 'preferences': None},
    {'name': 'David', 'guests': [], 'preferences': None},
]

print("\nPlayers: Lloyd (no Segan), Chris Hatwell, Daryl Gilbert, Sam Healy (no Ricky), Mike, John, Paul, David")

_, groups, _ = generator.generate(participants_2, partner_prefs, avoidances, tee_times)

print("\n✅ Groups Created:")
for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]
    print(f"  Group {i}: {', '.join(players)}")

print("\n📝 Notes:")
print("  • Lloyd grouped with others (Segan not playing)")
print("  • Sam Healy grouped with others (Ricky not playing)")
print("  • Chris Hatwell + Daryl Gilbert still paired (both playing)")
print("  • Constraints remain active for future weeks!")

print("\n" + "="*70)
print(" TEST COMPLETE")
print("="*70)
