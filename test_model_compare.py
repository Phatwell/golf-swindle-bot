"""
Scrape fresh messages from WhatsApp, then compare Haiku vs Sonnet vs Opus.
STOP THE BOT FIRST before running this (shares Chrome profile).

Usage: python3 test_model_compare.py
"""
import time
import json
import subprocess
import os
from dotenv import load_dotenv
import anthropic
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

# Config
GROUP_NAME = "Sunday Swindle"
USER_DATA_DIR = "./chrome_profile"
MAX_SCROLL_ATTEMPTS = 50
SCROLL_PAUSE = 2
SCROLL_PIXELS = 3000
STOP_PHRASES = ['taking names for sunday', 'names for sunday']

# Kill leftover processes
subprocess.run(['killall', '-9', 'chromedriver', 'chrome', 'chromium'],
              stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
time.sleep(1)


def extract_visible_messages(drv):
    """Extract all currently visible messages from the DOM."""
    messages = []
    elements = drv.find_elements(By.CSS_SELECTOR, '.message-in, .message-out')
    for elem in elements:
        try:
            is_outgoing = 'message-out' in elem.get_attribute('class')
            sender = "Unknown"
            timestamp = ""

            # Get timestamp from copyable-text's data-pre-plain-text
            try:
                copyable = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
                pre_text = copyable.get_attribute('data-pre-plain-text') if copyable else None
                if pre_text:
                    timestamp = pre_text
            except:
                pass

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
                if sender == "Unknown" and timestamp and ']:' in timestamp:
                    try:
                        sender = timestamp.split(']')[1].strip().rstrip(':').strip()
                    except:
                        pass

            # Get message text
            text = ""
            try:
                message_elem = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
                text = message_elem.text if message_elem else ""
            except:
                pass

            if text and text.strip():
                messages.append({
                    'sender': sender,
                    'text': text.strip(),
                    'timestamp': timestamp,
                    'is_outgoing': is_outgoing
                })
        except:
            continue
    return messages


def find_scroll_container(drv):
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


def parse_sort_key(msg):
    ts = msg.get('timestamp', '')
    if ts and '[' in ts and ']' in ts:
        try:
            bracket_content = ts.split('[')[1].split(']')[0]
            parts = bracket_content.split(', ')
            if len(parts) == 2:
                time_str = parts[0].strip()
                date_str = parts[1].strip()
                date_parts = date_str.split('/')
                if len(date_parts) == 3:
                    return f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]} {time_str}"
        except:
            pass
    return "9999/99/99 99:99"


# ========== STEP 1: Scrape fresh messages ==========
print("=" * 70)
print("STEP 1: Scraping fresh messages from WhatsApp")
print("=" * 70)

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

all_messages = {}

try:
    print("Opening WhatsApp Web...")
    driver.get('https://web.whatsapp.com')
    time.sleep(10)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#pane-side'))
    )
    print("Logged in to WhatsApp Web")

    # Open group
    print(f"Opening group: {GROUP_NAME}")
    group_spans = driver.find_elements(By.XPATH, f'//span[@title="{GROUP_NAME}"]')
    if not group_spans:
        print(f"Group '{GROUP_NAME}' not found!")
        driver.quit()
        exit(1)

    parent = group_spans[0].find_element(By.XPATH, './ancestor::div[5]')
    parent.click()
    time.sleep(5)

    # Collect initial messages
    initial_msgs = extract_visible_messages(driver)
    for msg in initial_msgs:
        key = (msg['sender'], msg['text'][:80])
        all_messages[key] = msg
    print(f"Initial messages: {len(initial_msgs)}, unique: {len(all_messages)}")

    # Find scroll container and scroll up
    scroll_container = find_scroll_container(driver)
    if scroll_container:
        no_new_count = 0
        for i in range(MAX_SCROLL_ATTEMPTS):
            driver.execute_script(f"arguments[0].scrollBy(0, -{SCROLL_PIXELS});", scroll_container)
            time.sleep(SCROLL_PAUSE)

            visible_msgs = extract_visible_messages(driver)
            new_count = 0
            for msg in visible_msgs:
                key = (msg['sender'], msg['text'][:80])
                if key not in all_messages:
                    all_messages[key] = msg
                    new_count += 1

            print(f"  Scroll {i+1}: visible={len(visible_msgs)}, new={new_count}, total={len(all_messages)}")

            # Check for stop phrase
            found_stop = False
            for key, msg in all_messages.items():
                if any(p in msg['text'].lower() for p in STOP_PHRASES):
                    found_stop = True
                    break

            if found_stop:
                print(f"  >>> Found 'taking names' — stopping scroll")
                break

            if new_count == 0:
                no_new_count += 1
                if no_new_count >= 3:
                    print(f"  No new messages for 3 scrolls — reached top")
                    break
            else:
                no_new_count = 0
    else:
        print("WARNING: No scroll container found")

finally:
    print("Closing Chrome...")
    driver.quit()

# Sort by timestamp
sorted_messages = sorted(all_messages.values(), key=parse_sort_key)

print(f"\nTotal unique messages: {len(sorted_messages)}")
print(f"\nALL MESSAGES (full text):")
print("=" * 70)
for i, msg in enumerate(sorted_messages, 1):
    ts = msg.get('timestamp', '')
    ts_short = ''
    if ts and '[' in ts and ']' in ts:
        ts_short = ts.split('[')[1].split(']')[0]
    print(f"{i:3d}. [{ts_short}] [{msg['sender']}]:")
    print(f"     {msg['text']}")
    print()

# Format for AI (same as bot does)
def format_msg_line(msg):
    ts = msg.get('timestamp', '')
    if ts and '[' in ts and ']' in ts:
        try:
            time_part = ts.split('[')[1].split(']')[0]
            return f"[{time_part}] [{msg['sender']}]: {msg['text']}"
        except:
            pass
    return f"[{msg['sender']}]: {msg['text']}"

messages_text = "\n".join([format_msg_line(msg) for msg in sorted_messages])

# Save to file for reference
with open('fresh_messages.txt', 'w') as f:
    f.write(messages_text)
print(f"\nSaved formatted messages to fresh_messages.txt")

# ========== STEP 2: Compare models ==========
print(f"\n{'=' * 70}")
print("STEP 2: Comparing Haiku vs Sonnet vs Opus")
print("=" * 70)

client = anthropic.Anthropic()

system_prompt = """You extract golf signup data from WhatsApp messages. Be deterministic and precise.

RULES:
1. Player names = exact [SenderName] from brackets. Never invent names.
2. ORGANIZER posts "now taking names" - NOT a player unless they separately sign up OR list themselves in a recap message.
3. Only messages AFTER "taking names" count. Earlier messages are previous weeks.
4. Latest message per person = truth (people change minds). Messages have timestamps like [HH:MM, DD/MM/YYYY] — use these to determine which message is newest. A later timestamp always overrides an earlier one (e.g. if someone says "please" at 10:30 but "take me off" at 14:00, they are OUT).
5. Skip [Unknown] senders.
6. PLAYING: "I'm in", "yes please", "count me in", "please", "me", "yes"
7. NOT PLAYING: "I'm out", "can't make it", illness mentions
8. IGNORE: questions, banter, emoji reactions, organisational chat
9. QUOTED MESSAGES: When a message starts with another person's name/number/text before the sender's own words, that initial part is a QUOTE. Only the sender's OWN words (after the quote) count. Preferences mentioned in the sender's own words belong to THE SENDER, not the quoted person.
10. Guests: ONLY "+1" or "can I have a guest" = "[HostName]-Guest" (anonymous guest). "bringing [Name]" where [Name] is not a group member = named guest.
11. SIGNING UP OTHERS: "me and X please" or "me and X for MP" or "me X and Y please" = the sender PLUS X and Y as SEPARATE PLAYERS (not guests). Example: [Alex] says "Me and John balls for MP please" = TWO players: Alex AND John Balls. Example: [Maice] says "Me mitch and ken please" = THREE players: Maice, Mitch, Ken. They are independent players, NOT guests.
12. NAME RESOLUTION: If someone is signed up by nickname (e.g. "ken") and later a matching person sends their own message (e.g. [KennyD]), use the [SenderName] as the canonical name. Similarly, use full names from recap messages when available (e.g. recap says "Mitchell Pettengell" for "mitch").
13. Note early/late or specific tee time preferences if mentioned. Attribute preferences to the person who SAID them, not to a quoted person.
14. MP/Match Play pairings: When someone says "me and [Name] for MP" or similar, both are playing AND want to be paired together. Add to "pairings" array as [sender, named_player].
15. RECAP MESSAGES (overrides Rule 1 for names): The organizer may post a numbered or bulleted list of names as a recap/roll call. ALL names in this recap are confirmed players even if they never sent a message themselves. This OVERRIDES Rule 1 - use the name from the recap as their player name. Examples: If recap lists "Scotty (+1)" = Scotty is playing with a guest (Scotty-Guest). If recap lists "Ricky Parkhurst" but no [Ricky Parkhurst] message exists = Ricky Parkhurst is still a confirmed player. You MUST include every single name from the recap list.
16. CRITICAL: Return players in the ORDER they first signed up (earliest message = first in list). This order determines who gets a playing spot vs goes on the reserves list."""

user_prompt = f"""MESSAGES:
{messages_text}

IMPORTANT: Players must be listed in the order they FIRST signed up (earliest signup first in list).
Return ONLY valid JSON:
{{"players": [{{"name": "SenderName", "guests": [], "preferences": null}}], "pairings": [["Player1", "Player2"]], "total_count": 0, "summary": "", "changes": []}}"""

# Pricing per million tokens
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00, "name": "Haiku 4.5"},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00, "name": "Sonnet 4.5"},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00, "name": "Opus 4"},
}

results = {}

for model_id, info in PRICING.items():
    print(f"\n{'─' * 70}")
    print(f"MODEL: {info['name']} ({model_id})")
    print(f"{'─' * 70}")

    start = time.time()
    response = client.messages.create(
        model=model_id,
        max_tokens=4000,
        temperature=0.1,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    elapsed = time.time() - start

    result_text = response.content[0].text.strip()
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    input_cost = (input_tokens / 1_000_000) * info["input"]
    output_cost = (output_tokens / 1_000_000) * info["output"]
    total_cost = input_cost + output_cost

    print(f"Tokens: {input_tokens} in / {output_tokens} out | Time: {elapsed:.1f}s")
    print(f"Cost: ${input_cost:.6f} (in) + ${output_cost:.6f} (out) = ${total_cost:.6f}")

    # Parse JSON
    clean = result_text
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    try:
        data = json.loads(clean)
        players = data.get("players", [])
        player_names = [p['name'] for p in players]

        print(f"\nPlayers ({len(players)}) — total_count: {data.get('total_count', '?')}:")
        for i, p in enumerate(players, 1):
            guests = p.get("guests", [])
            prefs = p.get("preferences")
            line = f"  {i:2d}. {p['name']}"
            if guests:
                line += f"  (guests: {', '.join(guests)})"
            if prefs:
                line += f"  [{prefs}]"
            print(line)

        if data.get("pairings"):
            print(f"\nMP Pairings:")
            for pair in data["pairings"]:
                print(f"  - {pair[0]} & {pair[1]}")

        print(f"\nSummary: {data.get('summary', '')}")
        if data.get("changes"):
            print(f"Changes: {data['changes']}")

        results[info['name']] = {
            'players': player_names,
            'count': len(players),
            'total_count': data.get('total_count', '?'),
            'pairings': data.get('pairings', []),
            'cost': total_cost,
            'time': elapsed,
            'tokens_in': input_tokens,
            'tokens_out': output_tokens,
        }
    except json.JSONDecodeError as e:
        print(f"\nFailed to parse JSON: {e}")
        print(f"Raw (first 500 chars): {result_text[:500]}")
        results[info['name']] = {'error': str(e), 'cost': total_cost}

# ========== STEP 3: Comparison summary ==========
print(f"\n{'=' * 70}")
print("COMPARISON SUMMARY")
print(f"{'=' * 70}")

for name, r in results.items():
    if 'error' in r:
        print(f"\n{name}: ERROR - {r['error']} (cost: ${r['cost']:.6f})")
        continue
    print(f"\n{name}:")
    print(f"  Players: {r['count']} (reported total: {r['total_count']})")
    print(f"  Cost: ${r['cost']:.6f} | Time: {r['time']:.1f}s | Tokens: {r['tokens_in']} in / {r['tokens_out']} out")

# Show differences
model_names = [n for n in results if 'error' not in results[n]]
if len(model_names) >= 2:
    print(f"\n{'─' * 70}")
    print("DIFFERENCES:")

    all_player_sets = {n: set(results[n]['players']) for n in model_names}
    for i, name1 in enumerate(model_names):
        for name2 in model_names[i+1:]:
            only_in_1 = all_player_sets[name1] - all_player_sets[name2]
            only_in_2 = all_player_sets[name2] - all_player_sets[name1]
            if only_in_1 or only_in_2:
                print(f"\n  {name1} vs {name2}:")
                if only_in_1:
                    print(f"    Only in {name1}: {', '.join(only_in_1)}")
                if only_in_2:
                    print(f"    Only in {name2}: {', '.join(only_in_2)}")
            else:
                print(f"\n  {name1} vs {name2}: IDENTICAL player lists")

# Cost comparison
print(f"\n{'─' * 70}")
print("COST PER CALL:")
for name, r in results.items():
    cost = r['cost']
    print(f"  {name:12s}: ${cost:.6f}")

if all('cost' in r for r in results.values()):
    costs = {n: r['cost'] for n, r in results.items()}
    cheapest = min(costs, key=costs.get)
    most_expensive = max(costs, key=costs.get)
    if costs[cheapest] > 0:
        ratio = costs[most_expensive] / costs[cheapest]
        print(f"\n  {most_expensive} is {ratio:.0f}x more expensive than {cheapest}")

    # Daily cost estimate (admin parser runs every 60s, main analyzer every 10 min)
    print(f"\nESTIMATED DAILY COST (admin parser every 60s + main analyzer every 10min):")
    admin_calls_per_day = 1440  # every minute
    main_calls_per_day = 144   # every 10 min
    for name, r in results.items():
        # Rough: admin parser uses ~1/4 the tokens, main uses full
        admin_cost = r['cost'] * 0.15 * admin_calls_per_day  # admin is smaller prompt
        main_cost = r['cost'] * main_calls_per_day
        daily = admin_cost + main_cost
        print(f"  {name:12s}: ~${daily:.2f}/day")