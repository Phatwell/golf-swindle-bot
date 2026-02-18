#!/usr/bin/env python3
"""Debug logged-in WhatsApp Web structure"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

service = Service('/usr/bin/chromedriver')
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--user-data-dir=./chrome_profile')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 30)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

print("Opening WhatsApp Web...")
driver.get('https://web.whatsapp.com')

print("Waiting for login check...")
time.sleep(5)

# Check if logged in
try:
    search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
    print("✅ Already logged in!")
except:
    print("❌ Not logged in")
    driver.quit()
    exit(1)

print("\n=== Finding search box ===")
try:
    search_box.click()
    search_box.send_keys("Your Golf Group")
    print("✅ Typed in search box")
    time.sleep(3)
except Exception as e:
    print(f"❌ Error: {e}")

print("\n=== Looking for chat/group elements ===")

# Try various selectors for finding chats
selectors = [
    ('Title attribute', By.XPATH, '//span[@title="Your Golf Group"]'),
    ('Contains title', By.XPATH, '//*[contains(@title, "Golf")]'),
    ('Span with text', By.XPATH, '//span[contains(text(), "Golf")]'),
    ('Chat list items', By.XPATH, '//div[@role="listitem"]'),
    ('Any span with dir', By.XPATH, '//span[@dir="auto"]'),
]

for name, by_type, selector in selectors:
    try:
        elements = driver.find_elements(by_type, selector)
        if elements:
            print(f"\n✅ Found {len(elements)} element(s) for: {name}")
            for i, elem in enumerate(elements[:3]):
                try:
                    text = elem.text[:100] if elem.text else "(no text)"
                    title = elem.get_attribute('title')
                    print(f"   Element {i+1}: text='{text}', title='{title}'")
                except:
                    pass
        else:
            print(f"\n❌ No elements found for: {name}")
    except Exception as e:
        print(f"\n❌ Error with {name}: {e}")

print("\n=== Taking screenshot ===")
driver.save_screenshot('/tmp/whatsapp_logged_in.png')
print("Screenshot saved: /tmp/whatsapp_logged_in.png")

print("\n=== Trying to click on first chat ===")
try:
    # Try to find and click the first result
    chat = driver.find_element(By.XPATH, '//div[@role="listitem"]')
    chat.click()
    print("✅ Clicked on first chat result")
    time.sleep(3)

    print("\n=== Looking for message elements ===")
    msg_selectors = [
        ('message-in class', By.XPATH, '//div[@class="message-in"]'),
        ('message-out class', By.XPATH, '//div[@class="message-out"]'),
        ('Role row', By.XPATH, '//div[@role="row"]'),
        ('Data attributes', By.XPATH, '//*[@data-id]'),
    ]

    for name, by_type, selector in msg_selectors:
        try:
            elements = driver.find_elements(by_type, selector)
            if elements:
                print(f"\n✅ Found {len(elements)} message element(s) for: {name}")
                if len(elements) > 0:
                    # Try to get text from first element
                    try:
                        text = elements[0].text[:200]
                        print(f"   First message preview: {text}")
                    except:
                        pass
            else:
                print(f"\n❌ No elements for: {name}")
        except Exception as e:
            print(f"\n❌ Error with {name}: {e}")

    print("\n=== Taking chat screenshot ===")
    driver.save_screenshot('/tmp/whatsapp_chat.png')
    print("Chat screenshot saved: /tmp/whatsapp_chat.png")

except Exception as e:
    print(f"❌ Error clicking chat: {e}")

driver.quit()
