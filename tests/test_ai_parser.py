#!/usr/bin/env python3
"""Test AI-powered message parser"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot import MessageParser, Config
import json

print("="*60)
print(" TESTING AI MESSAGE PARSER")
print("="*60)

# Initialize parser
config = Config()
if not config.ANTHROPIC_API_KEY:
    print("❌ ERROR: ANTHROPIC_API_KEY not found in .env file")
    exit(1)

print(f"✅ API Key loaded: {config.ANTHROPIC_API_KEY[:20]}...")
parser = MessageParser(config.ANTHROPIC_API_KEY)

# Test messages
test_cases = [
    # SIGNUPS
    ("I'm in", "signup", False),
    ("Me please", "signup", False),
    ("Yes please", "signup", False),
    ("Count me in", "signup", False),
    ("I'll be there", "signup", False),
    ("Put me down", "signup", False),

    # SIGNUPS WITH GUEST
    ("I'm in +1", "signup", True),
    ("Me please, bringing a guest", "signup", True),
    ("Count me in with my friend", "signup", True),
    ("Yes please plus 1", "signup", True),

    # DROPOUTS
    ("I'm out", "dropout", False),
    ("Can't make it", "dropout", False),
    ("Sorry can't come", "dropout", False),
    ("Not playing this week", "dropout", False),
    ("I'm ill so won't be there", "dropout", False),
    ("Got a cold, can't play", "dropout", False),
    ("Injured, have to sit this one out", "dropout", False),

    # IRRELEVANT
    ("What time are we playing?", "none", False),
    ("Who's playing this week?", "none", False),
    ("Great round last week!", "none", False),
]

print(f"\n🧪 Running {len(test_cases)} test cases...\n")

passed = 0
failed = 0

for message, expected_action, expected_guest in test_cases:
    try:
        result = parser.classify_message(message)

        action_correct = result["action"] == expected_action
        guest_correct = result["has_guest"] == expected_guest if expected_action == "signup" else True

        if action_correct and guest_correct:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"{status} | Message: \"{message}\"")
        print(f"         | Expected: {expected_action}" + (f" +guest" if expected_guest else ""))
        print(f"         | Got: {result['action']}" + (f" +guest" if result['has_guest'] else ""))
        if result["preferences"]:
            print(f"         | Preferences: {result['preferences']}")
        print()

    except Exception as e:
        print(f"❌ ERROR | Message: \"{message}\"")
        print(f"         | Error: {e}\n")
        failed += 1

print("="*60)
print(f" RESULTS: {passed} passed, {failed} failed")
print("="*60)

if failed == 0:
    print("\n🎉 All tests passed! AI parser is working perfectly!")
else:
    print(f"\n⚠️  {failed} test(s) failed. Review the results above.")

# Test the convenience methods
print("\n" + "="*60)
print(" TESTING CONVENIENCE METHODS")
print("="*60)

test_methods = [
    ("I'm in", "is_signup", True),
    ("Can't make it", "is_dropout", True),
    ("I'm in +1", "is_signup_with_guest", True),
    ("What time?", "is_signup", False),
]

for message, method, expected in test_methods:
    result = getattr(parser, method)(message)
    status = "✅" if result == expected else "❌"
    print(f"{status} {method}(\"{message}\") = {result} (expected {expected})")

print("\n✅ AI Parser integration complete!")
