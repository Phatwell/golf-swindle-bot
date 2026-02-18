#!/usr/bin/env python3
"""Test grouping with 14 players (should create 2x4 and 2x3)"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot_v5_admin import TeeSheetGenerator, Config

print("="*60)
print(" TEST: 14 Players Grouping")
print("="*60)

# Create 14 participants
participants = [
    {'name': f'Player{i}', 'guests': [], 'preferences': None}
    for i in range(1, 15)
]

print(f"\n📊 Total participants: {len(participants)}")
print("Expected: 2 groups of 4 + 2 groups of 3 = 4 tee times\n")

config = Config()
generator = TeeSheetGenerator(config)

# No constraints for this test
partner_prefs = {}
avoidances = {}

tee_sheet, groups = generator.generate(participants, partner_prefs, avoidances)

print(tee_sheet)

print("\n" + "="*60)
print(" GROUP SIZE ANALYSIS")
print("="*60)

total_groups = len(groups)
group_sizes = [len(g) for g in groups]

print(f"\nTotal tee times used: {total_groups}")
print(f"Group sizes: {group_sizes}")

# Count groups by size
size_counts = {}
for size in group_sizes:
    size_counts[size] = size_counts.get(size, 0) + 1

print("\nBreakdown:")
for size in sorted(size_counts.keys(), reverse=True):
    count = size_counts[size]
    players = size * count
    print(f"  • {count} group(s) of {size} = {players} players")

print(f"\n✅ Total players: {sum(group_sizes)}")

# Check if grouping is optimal
if total_groups <= 4 and min(group_sizes) >= 3:
    print("✅ OPTIMAL: Groups are well-filled (all groups have 3+ players)")
elif total_groups <= 4:
    print("⚠️  ACCEPTABLE: Minimal tee times but some small groups")
else:
    print("❌ NEEDS IMPROVEMENT: Too many tee times")

print("\n" + "="*60)
