#!/usr/bin/env python3
"""Test what happens when you request 'Show tee sheet' now"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot_v5_admin import Database, TeeSheetGenerator, Config

print("="*70)
print(" TESTING 'SHOW TEE SHEET' COMMAND NOW")
print("="*70)

db = Database("golf_swindle.db")
config = Config()
generator = TeeSheetGenerator(config)

# Check current participants
participants = db.get_participants()

print(f"\n📊 Current Database Status:")
print(f"   Participants in database: {len(participants)}")

if participants:
    print("\n   Players:")
    for p in participants:
        guests = ', '.join(p['guests']) if p['guests'] else 'no guests'
        pref = p.get('preferences', 'none')
        print(f"   • {p['name']} ({guests}) - {pref}")
else:
    print("   ⚠️  No participants in database yet")

# Get constraints
partner_prefs = db.get_partner_preferences()
avoidances = db.get_avoidances()

print(f"\n🤝 Active Constraints:")
if partner_prefs:
    for player, partners in partner_prefs.items():
        for partner in partners:
            print(f"   • {player} plays with {partner}")
else:
    print("   No constraints")

# Get tee time settings
tee_times = db.generate_tee_times()
print(f"\n⏰ Tee Time Settings:")
print(f"   Available times: {', '.join(tee_times[:5])}... ({len(tee_times)} total)")

print("\n" + "="*70)
print(" GENERATING TEE SHEET")
print("="*70)

# Generate tee sheet
result = generator.generate(
    participants,
    partner_prefs,
    avoidances,
    tee_times
)

# Handle different return values (2 or 3 depending on participants)
if len(result) == 3:
    tee_sheet, groups, assigned_times = result
else:
    tee_sheet, groups = result
    assigned_times = {}

print("\n" + tee_sheet)

print("\n" + "="*70)
print(" WHAT THIS MEANS")
print("="*70)

if not participants:
    print("""
⚠️  NO PARTICIPANTS IN DATABASE

This means the bot hasn't analyzed any messages yet, OR
the participants were cleared for a new week.

To test with real data, you have two options:

OPTION 1: Wait for bot to analyze WhatsApp
- The bot checks the main group every hour
- It will extract players from WhatsApp messages
- Then 'Show tee sheet' will work with real data

OPTION 2: Add test participants manually
- Run: python3 add_test_participants.py
- This will add sample players to test the tee sheet
- Then you can see how constraints are applied
""")
else:
    print(f"""
✅ TEE SHEET GENERATED

The bot found {len(participants)} participants and created {len(groups)} groups.
Constraints were applied: {len(partner_prefs)} partner preferences active.

This is what you would see if you sent 'Show tee sheet' in
the admin WhatsApp group right now.
""")
