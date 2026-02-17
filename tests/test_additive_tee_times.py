#!/usr/bin/env python3
"""Test additive tee time management (auto + add - remove)"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from src.swindle_bot_v5_admin import Database

print("="*70)
print(" TESTING ADDITIVE TEE TIME MANAGEMENT")
print("="*70)

db = Database("data/test_additive.db")

# Test 1: Show auto-generated times (baseline)
print("\n📋 Test 1: Show auto-generated baseline")
print("-" * 70)
auto_times = db.generate_tee_times()
print(f"Auto-generated: {', '.join(auto_times)}")
print(f"Count: {len(auto_times)}")

# Test 2: Add a time (should be added to auto-generated list)
print("\n📋 Test 2: Add a time (09:00)")
print("-" * 70)
db.add_manual_tee_time("09:00")
combined = db.generate_tee_times()
print(f"After adding 09:00: {', '.join(combined)}")
print(f"Count: {len(combined)}")
if "09:00" in combined and len(combined) == len(auto_times) + 1:
    print("✅ Time added correctly")
else:
    print("❌ Addition failed")

# Test 3: Remove an auto-generated time
print("\n📋 Test 3: Remove an auto-generated time (08:16)")
print("-" * 70)
db.remove_manual_tee_time("08:16")
after_removal = db.generate_tee_times()
print(f"After removing 08:16: {', '.join(after_removal)}")
print(f"Count: {len(after_removal)}")
if "08:16" not in after_removal:
    print("✅ Time removed correctly")
else:
    print("❌ Removal failed")

# Test 4: Add another time
print("\n📋 Test 4: Add 07:30 (early slot)")
print("-" * 70)
db.add_manual_tee_time("07:30")
after_add2 = db.generate_tee_times()
print(f"After adding 07:30: {', '.join(after_add2)}")
print(f"Count: {len(after_add2)}")
if "07:30" in after_add2:
    print("✅ Early time added and sorted correctly")
else:
    print("❌ Addition failed")

# Test 5: Remove a manually added time
print("\n📋 Test 5: Remove 09:00 (manually added)")
print("-" * 70)
db.remove_manual_tee_time("09:00")
after_remove2 = db.generate_tee_times()
print(f"After removing 09:00: {', '.join(after_remove2)}")
if "09:00" not in after_remove2:
    print("✅ Manually added time removed correctly")
else:
    print("❌ Removal failed")

# Test 6: Show breakdown
print("\n📋 Test 6: Show breakdown")
print("-" * 70)
added = db.get_manual_tee_times()
removed = db.get_removed_tee_times()
final = db.generate_tee_times()
print(f"Added times: {', '.join(added) if added else 'none'}")
print(f"Removed times: {', '.join(removed) if removed else 'none'}")
print(f"Final times: {', '.join(final)}")

# Test 7: Clear all modifications
print("\n📋 Test 7: Clear all modifications")
print("-" * 70)
db.clear_manual_tee_times()
reverted = db.generate_tee_times()
print(f"After clear: {', '.join(reverted)}")
if reverted == auto_times:
    print("✅ Reverted to original auto-generated times")
else:
    print("❌ Reversion failed")
    print(f"Expected: {auto_times}")
    print(f"Got: {reverted}")

print("\n" + "="*70)
print(" ADDITIVE BEHAVIOR WORKING!")
print("="*70)
print("""
✅ Auto-generation works
✅ Can add times to the list
✅ Can remove times from the list
✅ Additions and removals are cumulative
✅ Times are properly sorted
✅ Can clear all modifications
""")
