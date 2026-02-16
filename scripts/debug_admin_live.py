#!/usr/bin/env python3
"""Debug live admin group monitoring"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import WhatsAppBot, Config
from selenium.webdriver.common.by import By
import time

print("="*60)
print(" LIVE DEBUG: ADMIN GROUP MESSAGES")
print("="*60)

config = Config()
print(f"\nConfig:")
print(f"  Admin Group: {config.ADMIN_GROUP_NAME}")
print(f"  Admin Users: {config.ADMIN_USERS}")

bot = WhatsAppBot(config)

print("\n🚀 Initializing Chrome...")
if not bot.initialize():
    print("❌ Failed to initialize")
    exit(1)

print("✅ Chrome initialized\n")

print("="*60)
print(" CHECKING ADMIN GROUP MESSAGES")
print("="*60)

try:
    # First check what message elements exist
    print(f"\n📥 Fetching messages from '{config.ADMIN_GROUP_NAME}'...")

    # Debug: Check message element counts
    time.sleep(3)
    bot.driver.get('https://web.whatsapp.com')
    time.sleep(3)

    # Search for group
    search_box = bot.driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
    search_box.click()
    time.sleep(0.5)
    search_box.send_keys(config.ADMIN_GROUP_NAME)
    time.sleep(3)

    group_spans = bot.driver.find_elements(By.XPATH, f'//span[@title="{config.ADMIN_GROUP_NAME}"]')
    if group_spans:
        group_spans[0].find_element(By.XPATH, './ancestor::div[5]').click()
        time.sleep(3)

        msg_in = bot.driver.find_elements(By.CSS_SELECTOR, '.message-in')
        msg_out = bot.driver.find_elements(By.CSS_SELECTOR, '.message-out')
        print(f"   Found {len(msg_in)} incoming messages (.message-in)")
        print(f"   Found {len(msg_out)} outgoing messages (.message-out)")
        print(f"   Total: {len(msg_in) + len(msg_out)}\n")

    admin_messages = bot.get_all_messages(config.ADMIN_GROUP_NAME)

    if admin_messages is None:
        print("❌ Failed to get messages (returned None)")
    elif len(admin_messages) == 0:
        print("✅ Got messages, but list is empty (no messages in group)")
    else:
        print(f"✅ Got {len(admin_messages)} messages\n")

        print("Last 10 messages:")
        print("-" * 60)
        for i, msg in enumerate(admin_messages[-10:], 1):
            sender = msg.get('sender', 'Unknown')
            text = msg.get('text', '')[:50]

            # Check admin match
            sender_cleaned = sender.replace('+', '').replace(' ', '').replace('(', '').replace(')', '')
            is_admin = sender in config.ADMIN_USERS or sender_cleaned in config.ADMIN_USERS
            admin_marker = "✅ ADMIN" if is_admin else "⚠️  NON-ADMIN"

            print(f"\n{i}. {admin_marker}")
            print(f"   Sender: '{sender}'")
            print(f"   Cleaned: '{sender_cleaned}'")
            print(f"   Text: {text}...")

        print("\n" + "="*60)
        print(" ADMIN MATCHING TEST")
        print("="*60)

        last_msg = admin_messages[-1]
        sender = last_msg['sender']
        sender_cleaned = sender.replace('+', '').replace(' ', '').replace('(', '').replace(')', '')

        print(f"\nLast message sender: '{sender}'")
        print(f"Cleaned: '{sender_cleaned}'")
        print(f"Admin users list: {config.ADMIN_USERS}")
        print(f"Direct match: {sender in config.ADMIN_USERS}")
        print(f"Cleaned match: {sender_cleaned in config.ADMIN_USERS}")
        print(f"Is admin: {sender in config.ADMIN_USERS or sender_cleaned in config.ADMIN_USERS}")

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
