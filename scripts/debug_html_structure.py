#!/usr/bin/env python3
"""Deep dive into HTML structure of unknown messages"""

import sys
sys.path.insert(0, '/home/phatwell/projects/golf-swindle-bot')

from swindle_bot_v5_admin import WhatsAppBot, Config
from selenium.webdriver.common.by import By
import time

print("="*60)
print(" HTML STRUCTURE INSPECTOR")
print("="*60)

config = Config()
bot = WhatsAppBot(config)

print("\n🚀 Initializing Chrome...")
if not bot.initialize():
    print("❌ Failed to initialize")
    exit(1)

print("✅ Chrome initialized\n")

try:
    # Navigate to group
    time.sleep(3)
    search_box = bot.wait.until(
        lambda d: d.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
    )
    search_box.click()
    time.sleep(0.5)
    for _ in range(3):
        search_box.send_keys('\b' * 50)
    search_box.send_keys(config.GROUP_NAME)
    time.sleep(3)

    group_spans = bot.driver.find_elements(By.XPATH, f'//span[@title="{config.GROUP_NAME}"]')
    if group_spans:
        parent = group_spans[0].find_element(By.XPATH, './ancestor::div[5]')
        parent.click()
        time.sleep(3)

    print("="*60)
    print(f" ANALYZING: {config.GROUP_NAME}")
    print("="*60)

    # Get message elements
    message_elements_in = bot.driver.find_elements(By.CSS_SELECTOR, '.message-in')
    message_elements_out = bot.driver.find_elements(By.CSS_SELECTOR, '.message-out')
    all_messages = message_elements_in + message_elements_out

    print(f"\nFound {len(all_messages)} total messages\n")

    # Analyze last 10 messages
    for idx, elem in enumerate(all_messages[-10:], 1):
        print(f"\n{'='*60}")
        print(f" MESSAGE #{idx}")
        print('='*60)

        try:
            # Get message text
            text_elem = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
            text = text_elem.text[:100] if text_elem.text else "(no text)"
            print(f"Text: {text}...")

            # Check if incoming or outgoing
            is_outgoing = 'message-out' in elem.get_attribute('class')
            print(f"Type: {'Outgoing' if is_outgoing else 'Incoming'}")

            # Show all attributes
            print(f"\nElement attributes:")
            for attr in ['class', 'data-id', 'data-pre-plain-text', 'id', 'aria-label']:
                val = elem.get_attribute(attr)
                if val:
                    print(f"  {attr}: {val[:100]}")

            # Try to find sender-related elements
            print(f"\nSearching for sender info:")

            # Method 1: data-pre-plain-text
            try:
                pre_text_elem = elem.find_element(By.XPATH, './/*[@data-pre-plain-text]')
                pre_text = pre_text_elem.get_attribute('data-pre-plain-text')
                print(f"  ✅ data-pre-plain-text: {pre_text}")
            except:
                print(f"  ❌ No data-pre-plain-text found")

            # Method 2: Look for spans with names
            try:
                name_spans = elem.find_elements(By.XPATH, './/span[@dir="auto"]')
                print(f"  Found {len(name_spans)} spans with dir=auto:")
                for i, span in enumerate(name_spans[:3]):
                    span_text = span.text[:50] if span.text else "(empty)"
                    aria = span.get_attribute('aria-label') or "(no aria-label)"
                    print(f"    {i+1}. text='{span_text}', aria-label='{aria}'")
            except:
                print(f"  ❌ No dir=auto spans")

            # Method 3: Look in parent elements
            try:
                parent = elem.find_element(By.XPATH, '..')
                parent_attrs = {}
                for attr in ['data-id', 'data-testid', 'class', 'id']:
                    val = parent.get_attribute(attr)
                    if val:
                        parent_attrs[attr] = val[:100]
                if parent_attrs:
                    print(f"  Parent attributes: {parent_attrs}")
            except:
                pass

            # Method 4: Look for copyable-text siblings
            try:
                siblings = elem.find_elements(By.XPATH, './/*')
                print(f"  Total child elements: {len(siblings)}")

                # Find elements with useful text
                for child in siblings[:10]:
                    child_text = child.text
                    if child_text and len(child_text) < 50 and '\n' not in child_text:
                        child_class = child.get_attribute('class')
                        print(f"    Child: '{child_text}' (class: {child_class})")
            except:
                pass

        except Exception as e:
            print(f"❌ Error analyzing message: {e}")

    print(f"\n{'='*60}")
    print(" ANALYSIS COMPLETE")
    print('='*60)

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
