#!/usr/bin/env python3
"""Test manual tee time management"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.swindle_bot_v5_admin import Database

print("="*70)
print(" TESTING MANUAL TEE TIME MANAGEMENT")
print("="*70)

db = Database("data/golf_swindle.db")

# Test 1: Show current settings (auto-generated)
print("\n📋 Test 1: Show auto-generated times")
print("-" * 70)
auto_times = db.generate_tee_times()
print(f"Auto-generated times: {', '.join(auto_times)}")

# Test 2: Add manual tee times
print("\n📋 Test 2: Add manual tee times")
print("-" * 70)
times_to_add = ["08:24", "08:32", "08:40", "08:48", "08:56", "09:04", "09:12"]

for time in times_to_add:
    success = db.add_manual_tee_time(time)
    if success:
        print(f"  ✅ Added: {time}")
    else:
        print(f"  ⚠️  Already exists: {time}")

# Test 3: Show manual times
print("\n📋 Test 3: Show all manual times")
print("-" * 70)
manual_times = db.get_manual_tee_times()
print(f"Manual times ({len(manual_times)}): {', '.join(manual_times)}")

# Test 4: generate_tee_times should now return manual times
print("\n📋 Test 4: Verify generate_tee_times uses manual times")
print("-" * 70)
generated = db.generate_tee_times()
print(f"Generated times: {', '.join(generated)}")
if generated == manual_times:
    print("✅ Correctly using manual times!")
else:
    print("❌ Not using manual times correctly")

# Test 5: Remove a tee time
print("\n📋 Test 5: Remove a tee time")
print("-" * 70)
time_to_remove = "08:48"
success = db.remove_manual_tee_time(time_to_remove)
if success:
    print(f"  ✅ Removed: {time_to_remove}")
    manual_times = db.get_manual_tee_times()
    print(f"  Remaining times: {', '.join(manual_times)}")
else:
    print(f"  ❌ Failed to remove: {time_to_remove}")

# Test 6: Try to add duplicate
print("\n📋 Test 6: Try to add duplicate")
print("-" * 70)
success = db.add_manual_tee_time("08:24")
if not success:
    print("  ✅ Correctly rejected duplicate")
else:
    print("  ❌ Should have rejected duplicate")

# Test 7: Clear all manual times
print("\n📋 Test 7: Clear all manual times")
print("-" * 70)
db.clear_manual_tee_times()
manual_times = db.get_manual_tee_times()
print(f"Manual times after clear: {manual_times}")
if not manual_times:
    print("✅ All manual times cleared")
else:
    print("❌ Manual times still exist")

# Test 8: Verify reverts to auto-generated
print("\n📋 Test 8: Verify reverts to auto-generated")
print("-" * 70)
generated = db.generate_tee_times()
print(f"Generated times: {', '.join(generated)}")
if len(generated) > 0:
    print("✅ Reverted to auto-generated times")
else:
    print("❌ No times generated")

print("\n" + "="*70)
print(" TEST COMPLETE")
print("="*70)
