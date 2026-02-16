#!/usr/bin/env python3
"""Test grouping with various player counts"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import TeeSheetGenerator, Config

def test_grouping(num_players):
    participants = [
        {'name': f'P{i}', 'guests': [], 'preferences': None}
        for i in range(1, num_players + 1)
    ]

    config = Config()
    generator = TeeSheetGenerator(config)
    _, groups = generator.generate(participants, {}, {})

    group_sizes = sorted([len(g) for g in groups], reverse=True)
    num_groups = len(groups)
    min_size = min(group_sizes)

    return num_groups, group_sizes, min_size

print("="*70)
print(" GROUPING OPTIMIZATION TEST - Various Player Counts")
print("="*70)
print(f"\n{'Players':<10} {'Groups':<10} {'Sizes':<25} {'Min Size':<12} {'Status'}")
print("-"*70)

test_cases = [8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

for num in test_cases:
    num_groups, sizes, min_size = test_grouping(num)
    sizes_str = str(sizes)

    # Check if optimal (min size >= 3 or total players <= 4)
    if num <= 4:
        status = "✅ Single group"
    elif min_size >= 3:
        status = "✅ Optimal"
    elif min_size == 2:
        status = "⚠️  Has group of 2"
    else:
        status = "❌ Has single player"

    print(f"{num:<10} {num_groups:<10} {sizes_str:<25} {min_size:<12} {status}")

print("\n" + "="*70)
print("Key: Optimal grouping has all groups with 3+ players (or single group)")
print("="*70)
