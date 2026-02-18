#!/usr/bin/env python3
"""Debug message loading consistency - tests fetching the same group multiple times
to understand why message counts differ between calls."""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from selenium.webdriver.common.by import By
from swindle_bot_v5_admin import WhatsAppBot, Config

config = Config()
bot = WhatsAppBot(config)

print("=" * 60)
print(" DEBUG: MESSAGE LOADING CONSISTENCY")
print("=" * 60)

print("\n🚀 Initializing Chrome...")
if not bot.initialize():
    print("❌ Failed to initialize")
    exit(1)

print("✅ Chrome initialized\n")

def count_dom_messages(driver):
    """Count message elements currently in the DOM"""
    msg_in = len(driver.find_elements(By.CSS_SELECTOR, '.message-in'))
    msg_out = len(driver.find_elements(By.CSS_SELECTOR, '.message-out'))
    return msg_in, msg_out, msg_in + msg_out

def fetch_with_diagnostics(bot, group_name, label):
    """Fetch messages with detailed timing and count logging"""
    print(f"\n{'=' * 60}")
    print(f" {label}: Fetching from {group_name}")
    print(f"{'=' * 60}")

    # Check DOM state BEFORE navigating
    in_count, out_count, total = count_dom_messages(bot.driver)
    print(f"  DOM before navigation: {total} messages (in={in_count}, out={out_count})")

    # Navigate to group manually to see loading progress
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC

    time.sleep(2)

    search_box = bot.wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    search_box.click()
    time.sleep(0.5)
    try:
        search_box.send_keys(Keys.ESCAPE)
        time.sleep(0.3)
    except:
        pass
    for _ in range(3):
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.DELETE)
        time.sleep(0.2)

    search_box.send_keys(group_name)
    time.sleep(5)

    group_spans = bot.driver.find_elements(By.XPATH, f'//span[@title="{group_name}"]')
    if not group_spans:
        print(f"  ❌ Group not found!")
        return None

    group_span = group_spans[0]
    parent = group_span.find_element(By.XPATH, './ancestor::div[5]')
    parent.click()

    # Monitor loading over time
    print(f"  Monitoring DOM message count after clicking group:")
    counts = []
    for i in range(20):
        time.sleep(1)
        in_count, out_count, total = count_dom_messages(bot.driver)
        counts.append(total)
        marker = "📈" if i > 0 and total > counts[-2] else "  "
        print(f"    {marker} +{i+1:2}s: {total} messages (in={in_count}, out={out_count})")

        # Stop if stable for 3 seconds
        if len(counts) >= 3 and counts[-1] == counts[-2] == counts[-3] and total > 0:
            print(f"    ✅ Stable for 3 seconds at {total} messages")
            break

    # Now do the actual scrape
    messages = bot.get_all_messages(group_name)
    if messages:
        print(f"\n  📊 get_all_messages returned: {len(messages)} messages")
    else:
        print(f"\n  ❌ get_all_messages returned None")

    return messages

try:
    # Test 1: Fetch main group (fresh - like startup)
    print("\n" + "🔵" * 30)
    print("TEST 1: First fetch of main group (fresh startup)")
    print("🔵" * 30)
    msgs1 = fetch_with_diagnostics(bot, config.GROUP_NAME, "FIRST FETCH")

    # Test 2: Fetch admin group (simulates checking admin)
    print("\n" + "🟡" * 30)
    print("TEST 2: Switch to admin group (simulates admin check)")
    print("🟡" * 30)
    admin_msgs = fetch_with_diagnostics(bot, config.ADMIN_GROUP_NAME, "ADMIN FETCH")

    # Test 3: Fetch main group again (simulates refresh after command)
    print("\n" + "🔴" * 30)
    print("TEST 3: Back to main group (simulates refresh_main_group)")
    print("🔴" * 30)
    msgs2 = fetch_with_diagnostics(bot, config.GROUP_NAME, "SECOND FETCH")

    # Compare results
    print("\n" + "=" * 60)
    print(" COMPARISON")
    print("=" * 60)
    count1 = len(msgs1) if msgs1 else 0
    count2 = len(msgs2) if msgs2 else 0
    print(f"  First fetch:  {count1} messages")
    print(f"  Second fetch: {count2} messages")
    if count1 != count2:
        print(f"  ⚠️  DIFFERENCE: {count1 - count2} messages lost!")
        if msgs1 and msgs2:
            senders1 = set(m['sender'] for m in msgs1)
            senders2 = set(m['sender'] for m in msgs2)
            missing = senders1 - senders2
            if missing:
                print(f"  Missing senders: {missing}")
    else:
        print(f"  ✅ Consistent!")

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
