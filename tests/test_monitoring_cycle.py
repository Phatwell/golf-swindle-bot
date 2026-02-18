#!/usr/bin/env python3
"""Test one complete monitoring cycle"""

import sys, os
import signal
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swindle_bot import SwindleBot
import time

# Handler for timeout
def timeout_handler(signum, frame):
    print("\n\n⏰ Test timeout reached")
    raise TimeoutError("Test took too long")

print("Creating SwindleBot instance...")
bot = SwindleBot()

print("\n=== Starting bot (this will send startup message) ===\n")

# Set a 40 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(40)

try:
    # Initialize
    if not bot.whatsapp.initialize():
        print("❌ Failed to initialize")
        exit(1)

    print("\n✅ Initialized successfully\n")

    # Send startup message
    bot.send_startup_message()
    print("\n✅ Startup message sent\n")

    # Try to get messages once (simulating one monitoring cycle)
    print("=== Testing one monitoring cycle ===")
    messages = bot.whatsapp.get_group_messages(bot.config.GROUP_NAME)

    if messages is None:
        print("❌ Failed to get messages (returned None)")
    elif len(messages) == 0:
        print("✅ Successfully got messages (0 new messages)")
    else:
        print(f"✅ Successfully got {len(messages)} messages")
        print(f"   Latest: {messages[-1]['sender']}: {messages[-1]['text'][:50]}")

    print("\n✅ TEST PASSED - Bot monitoring cycle works!")

except TimeoutError as e:
    print(f"\n❌ TEST FAILED - {e}")
except Exception as e:
    print(f"\n❌ TEST FAILED - Exception: {e}")
    import traceback
    traceback.print_exc()
finally:
    signal.alarm(0)  # Cancel alarm
    print("\nCleaning up...")
    bot.whatsapp.close()
    print("Done")
