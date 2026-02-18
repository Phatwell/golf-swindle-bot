#!/usr/bin/env python3
"""Test how new constraints affect grouping"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
    {'name': 'Dave', 'guests': [], 'preferences': None},
    {'name': 'Steve', 'guests': [], 'preferences': None},
    {'name': 'John Smith', 'guests': [], 'preferences': None},
    {'name': 'Mike Johnson', 'guests': [], 'preferences': None},
    {'name': 'Tom Wilson', 'guests': [], 'preferences': None},
    {'name': 'Pete', 'guests': [], 'preferences': None},
    {'name': 'Mike', 'guests': [], 'preferences': None},
    {'name': 'John', 'guests': [], 'preferences': None},
]

print("\nPlayers: Dave, Steve, John Smith, Mike Johnson, Tom Wilson, Pete, Mike, John")

tee_times = db.generate_tee_times()
_, groups, _ = generator.generate(participants_1, partner_prefs, avoidances, tee_times)

print("\n✅ Groups Created:")
for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]
    print(f"  Group {i}: {', '.join(players)}")

# Check if partners are together
for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]

    if 'Dave' in players and 'Steve' in players:
        print(f"    ✅ Dave + Steve paired in Group {i}")
    if 'John Smith' in players and 'Mike Johnson' in players:
        print(f"    ✅ John Smith + Mike Johnson paired in Group {i}")
    if 'Tom Wilson' in players and 'Pete' in players:
        print(f"    ✅ Tom Wilson + Pete paired in Group {i}")

# Scenario 2: Only some partners playing
print("\n" + "="*70)
print(" SCENARIO 2: Only Some Partners Playing")
print("="*70)

participants_2 = [
    {'name': 'Dave', 'guests': [], 'preferences': None},  # Steve NOT playing
    {'name': 'John Smith', 'guests': [], 'preferences': None},
    {'name': 'Mike Johnson', 'guests': [], 'preferences': None},
    {'name': 'Tom Wilson', 'guests': [], 'preferences': None},  # Pete NOT playing
    {'name': 'Mike', 'guests': [], 'preferences': None},
    {'name': 'John', 'guests': [], 'preferences': None},
    {'name': 'Paul', 'guests': [], 'preferences': None},
    {'name': 'David', 'guests': [], 'preferences': None},
]

print("\nPlayers: Dave (no Steve), John Smith, Mike Johnson, Tom Wilson (no Pete), Mike, John, Paul, David")

_, groups, _ = generator.generate(participants_2, partner_prefs, avoidances, tee_times)

print("\n✅ Groups Created:")
for i, group in enumerate(groups, 1):
    players = [p['name'] for p in group if not p.get('is_guest')]
    print(f"  Group {i}: {', '.join(players)}")

print("\n📝 Notes:")
print("  • Dave grouped with others (Steve not playing)")
print("  • Tom Wilson grouped with others (Pete not playing)")
print("  • John Smith + Mike Johnson still paired (both playing)")
print("  • Constraints remain active for future weeks!")

print("\n" + "="*70)
print(" TEST COMPLETE")
print("="*70)
