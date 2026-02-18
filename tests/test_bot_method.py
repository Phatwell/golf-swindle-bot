#!/usr/bin/env python3
"""Test the actual bot's get_group_messages method"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot import WhatsAppBot, Config

print("Creating bot instance...")
config = Config()
bot = WhatsAppBot(config)

print("Initializing Chrome...")
if not bot.initialize():
    print("Failed to initialize")
    exit(1)

print("\n=== Bot initialized successfully ===\n")

# Try to get messages 3 times to simulate the loop
for i in range(3):
    print(f"\n=== ATTEMPT {i+1} ===")
    try:
        messages = bot.get_group_messages("Your Golf Group")

        if messages is None:
            print(f"❌ RESULT: None (failure)")
        elif len(messages) == 0:
            print(f"✅ RESULT: Empty list (success, no new messages)")
        else:
            print(f"✅ RESULT: {len(messages)} messages")
            for msg in messages[:3]:
                print(f"   - {msg['sender']}: {msg['text'][:50]}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        break
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

    print(f"Waiting 5 seconds before next attempt...\n")
    import time
    time.sleep(5)

print("\n=== Closing bot ===")
bot.close()
