#!/usr/bin/env python3
"""Add partner preferences to the database"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import Database

print("="*60)
print(" ADDING PARTNER PREFERENCES")
print("="*60)

db = Database("golf_swindle.db")

# Add partner preferences
preferences = [
    ("Lloyd", "Segan"),
    ("Chris Hatwell", "Daryl Gilbert"),
    ("Sam Healy", "Ricky")
]

print("\nAdding preferences...")
for player, partner in preferences:
    success = db.add_constraint('partner_preference', player, partner)
    if success:
        print(f"✅ {player} plays with {partner}")
    else:
        print(f"⚠️  {player} + {partner} already exists or error occurred")

print("\n" + "="*60)
print(" CURRENT CONSTRAINTS")
print("="*60)

# Show all current constraints
constraints = db.get_constraints()

if not constraints:
    print("\nNo constraints set")
else:
    partner_prefs = [c for c in constraints if c['type'] == 'partner_preference']
    avoidances = [c for c in constraints if c['type'] == 'avoid']

    if partner_prefs:
        print("\n🤝 Partner Preferences:")
        for c in partner_prefs:
            print(f"  • {c['player']} plays with {c['target']}")

    if avoidances:
        print("\n⚠️  Avoidances:")
        for c in avoidances:
            print(f"  • {c['player']} avoids {c['target']}")

print("\n" + "="*60)
print(" DONE - Constraints saved to database!")
print("="*60)
print("\nThese will be applied automatically every week when")
print("generating the tee sheet. You never need to set them again!")
print("\nTo view: Send 'Show constraints' in admin WhatsApp group")
