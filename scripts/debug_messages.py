#!/usr/bin/env python3
"""Debug what messages are being extracted and sent to AI"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import WhatsAppBot, Config
import time

print("="*60)
print(" DEBUG: MESSAGE EXTRACTION")
print("="*60)

config = Config()
bot = WhatsAppBot(config)

print("\n🚀 Initializing Chrome...")
if not bot.initialize():
    print("❌ Failed to initialize")
    exit(1)

print("✅ Chrome initialized\n")

try:
    print("="*60)
    print(f" FETCHING FROM: {config.GROUP_NAME}")
    print("="*60)

    messages = bot.get_all_messages(config.GROUP_NAME)

    if not messages:
        print("❌ No messages found")
    else:
        print(f"\n✅ Found {len(messages)} messages\n")

        # Show last 20 messages with sender names
        print("LAST 20 MESSAGES:")
        print("-" * 60)
        for i, msg in enumerate(messages[-20:], 1):
            sender = msg.get('sender', 'MISSING')
            text = msg.get('text', '')[:60]

            # Highlight potential issues
            if sender == "Unknown":
                marker = "⚠️  UNKNOWN SENDER"
            elif sender == "MISSING":
                marker = "❌ NO SENDER"
            else:
                marker = "✅"

            print(f"{i:2}. {marker}")
            print(f"    Sender: '{sender}'")
            print(f"    Text: {text}...")
            print()

        # Count unknowns
        unknown_count = sum(1 for msg in messages if msg.get('sender') == 'Unknown')
        print("-" * 60)
        print(f"Summary:")
        print(f"  Total messages: {len(messages)}")
        print(f"  Unknown senders: {unknown_count}")
        print(f"  Valid senders: {len(messages) - unknown_count}")

        if unknown_count > 0:
            print(f"\n⚠️  WARNING: {unknown_count} messages have 'Unknown' as sender")
            print("   This will cause AI to output 'unknown player'")
            print("   Issue: Name extraction from WhatsApp is failing for some messages")

except KeyboardInterrupt:
    print("\n\n👋 Interrupted")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("\n\n🧹 Closing Chrome...")
    bot.close()
    print("✅ Done")
