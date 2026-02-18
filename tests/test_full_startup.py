#!/usr/bin/env python3
"""Test the full startup sequence"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot import WhatsAppBot, Config
import time

print("Creating bot instance...")
config = Config()
bot_whatsapp = WhatsAppBot(config)

print("Initializing Chrome...")
if not bot_whatsapp.initialize():
    print("Failed to initialize")
    exit(1)

print("\n=== Bot initialized successfully ===\n")

# Simulate sending startup message
print("=== Simulating startup message ===")
try:
    # This is what send_to_me does
    bot_whatsapp.send_message(config.MY_NUMBER, "TEST STARTUP MESSAGE\n\nThis is a test\nLine 3")
    print("✅ Startup message sent")
except Exception as e:
    print(f"❌ Error sending startup message: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Now trying to monitor (get messages) ===")

# Try to get messages like monitor would
for i in range(3):
    print(f"\n--- Attempt {i+1} ---")
    try:
        messages = bot_whatsapp.get_group_messages("Your Golf Group")

        if messages is None:
            print(f"❌ RESULT: None (failure)")
        elif len(messages) == 0:
            print(f"✅ RESULT: Empty list (success, no new messages)")
        else:
            print(f"✅ RESULT: {len(messages)} messages")

    except KeyboardInterrupt:
        print("\nInterrupted")
        break
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

    time.sleep(5)

print("\n=== Closing bot ===")
bot_whatsapp.close()
