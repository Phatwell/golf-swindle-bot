"""
Test script to check how many messages we can capture with scroll + accumulate.
WhatsApp Web virtualises messages, so we scroll up in steps, collecting messages
at each position and deduplicating them.

STOP THE BOT FIRST before running this (shares Chrome profile).

Usage: python3 test_scroll_scrape.py
"""
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Config
GROUP_NAME = "Sunday Swindle"
USER_DATA_DIR = "./chrome_profile"
MAX_SCROLL_ATTEMPTS = 50
SCROLL_PAUSE = 2
SCROLL_PIXELS = 3000  # How far to scroll up each time

# Kill leftover processes
subprocess.run(['killall', '-9', 'chromedriver', 'chrome', 'chromium'],
              stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
time.sleep(1)

# Start Chrome
print("Starting Chrome...")
service = Service('/usr/bin/chromedriver')
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument(f'--user-data-dir={USER_DATA_DIR}')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36')

driver = webdriver.Chrome(service=service, options=chrome_options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")


def extract_visible_messages(drv):
    """Extract all currently visible messages from the DOM."""
    messages = []
    elements = drv.find_elements(By.CSS_SELECTOR, '.message-in, .message-out')
    for elem in elements:
        try:
            is_outgoing = 'message-out' in elem.get_attribute('class')

            # Get sender
            sender = "Unknown"
            if is_outgoing:
                sender = "Admin"
            else:
                try:
                    spans = elem.find_elements(By.XPATH, './/span[@dir="auto"]')
                    if spans:
                        sender_text = spans[0].text.strip()
                        if sender_text and ':' not in sender_text:
                            sender = sender_text
                except:
                    pass
                if sender == "Unknown":
                    try:
                        pre_text = elem.get_attribute('data-pre-plain-text')
                        if pre_text and ']:' in pre_text:
                            sender = pre_text.split(']')[1].strip().rstrip(':').strip()
                    except:
                        pass

            # Get message text
            text = ""
            try:
                message_elem = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
                text = message_elem.text if message_elem else ""
            except:
                pass

            # Get timestamp from data-pre-plain-text for ordering
            timestamp = ""
            try:
                pre_text = elem.get_attribute('data-pre-plain-text')
                if pre_text:
                    timestamp = pre_text
            except:
                pass

            if text and text.strip():
                messages.append({
                    'sender': sender,
                    'text': text.strip(),
                    'timestamp': timestamp,
                })
        except:
            continue
    return messages


def find_scroll_container(drv):
    """Find the scrollable message pane using walk-up approach."""
    try:
        first_msg = drv.find_element(By.CSS_SELECTOR, '.message-in, .message-out')
        container = drv.execute_script("""
            let el = arguments[0];
            while (el) {
                let style = getComputedStyle(el);
                let isScrollable = (style.overflowY === 'auto' || style.overflowY === 'scroll')
                                   && el.scrollHeight > el.clientHeight;
                if (isScrollable && el.clientHeight > 200) {
                    return el;
                }
                el = el.parentElement;
            }
            return null;
        """, first_msg)

        if not container:
            # Fallback: any scrollable ancestor
            container = drv.execute_script("""
                let el = arguments[0];
                while (el) {
                    if (el.scrollHeight > el.clientHeight && el.clientHeight > 200) {
                        return el;
                    }
                    el = el.parentElement;
                }
                return null;
            """, first_msg)

        return container
    except:
        return None


try:
    print("Opening WhatsApp Web...")
    driver.get('https://web.whatsapp.com')
    time.sleep(10)

    # Check if logged in
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#pane-side'))
        )
        print("Logged in to WhatsApp Web")
    except:
        print("NOT logged in - need to scan QR code first via the bot")
        driver.quit()
        exit(1)

    # Find and click group
    print(f"Opening group: {GROUP_NAME}")
    group_spans = driver.find_elements(By.XPATH, f'//span[@title="{GROUP_NAME}"]')
    if not group_spans:
        print(f"Group '{GROUP_NAME}' not found!")
        driver.quit()
        exit(1)

    parent = group_spans[0].find_element(By.XPATH, './ancestor::div[5]')
    parent.click()
    time.sleep(5)

    # Find scroll container
    scroll_container = find_scroll_container(driver)
    if scroll_container:
        info = driver.execute_script("""
            return {
                scrollHeight: arguments[0].scrollHeight,
                clientHeight: arguments[0].clientHeight,
                scrollTop: arguments[0].scrollTop
            };
        """, scroll_container)
        print(f"Scroll container found: scrollH={info['scrollHeight']} clientH={info['clientHeight']} scrollTop={info['scrollTop']}")
    else:
        print("WARNING: No scroll container found!")
        driver.quit()
        exit(1)

    # Collect initial messages from the bottom
    all_messages = {}  # key: (sender, text_first_80_chars) -> message dict
    initial_msgs = extract_visible_messages(driver)
    for msg in initial_msgs:
        key = (msg['sender'], msg['text'][:80])
        all_messages[key] = msg
    print(f"\nInitial messages in DOM: {len(initial_msgs)}, unique accumulated: {len(all_messages)}")

    # Scroll up and accumulate — stop when we find "taking names"
    STOP_PHRASES = ['taking names for sunday', 'names for sunday']

    def check_for_stop_message(messages_dict):
        """Check if any accumulated message contains the stop phrase."""
        for key, msg in messages_dict.items():
            text_lower = msg['text'].lower()
            for phrase in STOP_PHRASES:
                if phrase in text_lower:
                    return msg
        return None

    print(f"\nScrolling up to accumulate messages (stopping at 'taking names')...")
    no_new_count = 0

    for i in range(MAX_SCROLL_ATTEMPTS):
        # Scroll up
        driver.execute_script(f"arguments[0].scrollBy(0, -{SCROLL_PIXELS});", scroll_container)
        time.sleep(SCROLL_PAUSE)

        # Extract messages at this scroll position
        visible_msgs = extract_visible_messages(driver)
        new_count = 0
        for msg in visible_msgs:
            key = (msg['sender'], msg['text'][:80])
            if key not in all_messages:
                all_messages[key] = msg
                new_count += 1

        scroll_top = driver.execute_script("return arguments[0].scrollTop;", scroll_container)
        print(f"  Scroll {i+1}: visible={len(visible_msgs)}, new={new_count}, total accumulated={len(all_messages)}, scrollTop={scroll_top}")

        # Check if we've found the "taking names" message
        stop_msg = check_for_stop_message(all_messages)
        if stop_msg:
            print(f"\n  >>> FOUND stop message: [{stop_msg['sender']}]: {stop_msg['text'][:100]}")
            print(f"  >>> Stopping scroll — we have all messages from this week")
            break

        if new_count == 0:
            no_new_count += 1
            if no_new_count >= 3:
                print(f"  No new messages for 3 scrolls - reached top of visible history")
                break
        else:
            no_new_count = 0

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Total unique messages accumulated: {len(all_messages)}")
    print(f"{'='*60}")

    # Print all accumulated messages
    print(f"\nALL ACCUMULATED MESSAGES:")
    print(f"{'='*60}")
    for i, (key, msg) in enumerate(all_messages.items(), 1):
        short_text = msg['text'].replace('\n', ' ')[:100]
        print(f"  {i:3d}. [{msg['sender']}]: {short_text}")

    # Check if we found the "taking names" message
    found_taking_names = False
    for key, msg in all_messages.items():
        text_lower = msg['text'].lower()
        if 'taking names' in text_lower or 'names for sunday' in text_lower or 'who\'s playing' in text_lower:
            found_taking_names = True
            print(f"\n>>> FOUND 'taking names' message: [{msg['sender']}]: {msg['text'][:100]}")
            break

    if not found_taking_names:
        print(f"\n>>> WARNING: Did NOT find a 'taking names' message in accumulated messages")

finally:
    print("\nClosing Chrome...")
    driver.quit()
    print("Done!")