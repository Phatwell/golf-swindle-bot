#!/usr/bin/env python3
"""Debug script that mimics exact bot search behavior"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
time.sleep(5)

group_name = "Sunday Swindle"

print("\n=== Step 1: Find search box ===")
try:
    search_box = wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    print("✅ Search box found")
except Exception as e:
    print(f"❌ Error finding search box: {e}")
    driver.quit()
    exit(1)

print("\n=== Step 2: Clear search box (bot method) ===")
search_box.click()
time.sleep(0.5)

try:
    search_box.send_keys(Keys.ESCAPE)
    time.sleep(0.3)
except:
    pass

# Select all and delete (like the bot does)
for i in range(3):
    search_box.send_keys(Keys.CONTROL + "a")
    search_box.send_keys(Keys.DELETE)
    time.sleep(0.2)
    print(f"   Clear attempt {i+1}/3")

print("\n=== Step 3: Type group name ===")
search_box.send_keys(group_name)
print(f"🔍 Typed: {group_name}")
time.sleep(5)  # Same 5 second wait as bot

# Take screenshot after search
driver.save_screenshot('/tmp/debug_after_search.png')
print("Screenshot saved: /tmp/debug_after_search.png")

print("\n=== Step 4: Wait for group span (bot method with WebDriverWait) ===")
try:
    print(f"⏳ Waiting up to 30 seconds for: //span[@title=\"{group_name}\"]")
    start_time = time.time()
    group_span = wait.until(
        EC.presence_of_element_located((By.XPATH, f'//span[@title="{group_name}"]'))
    )
    elapsed = time.time() - start_time
    print(f"✅ Found group span after {elapsed:.2f} seconds")
    print(f"   Text: {group_span.text}")
    print(f"   Title: {group_span.get_attribute('title')}")

    # Try to find parent
    print("\n=== Step 5: Find parent element ===")
    try:
        parent = group_span.find_element(By.XPATH, './ancestor::div[5]')
        print("✅ Found parent (5 levels up)")
        print(f"   Tag: {parent.tag_name}")
        print(f"   Displayed: {parent.is_displayed()}")

        # Try clicking
        print("\n=== Step 6: Click parent ===")
        parent.click()
        print("✅ Clicked successfully")
        time.sleep(3)

        # Take screenshot after click
        driver.save_screenshot('/tmp/debug_after_click.png')
        print("Screenshot saved: /tmp/debug_after_click.png")

    except Exception as e:
        print(f"❌ Error with parent: {e}")
        driver.save_screenshot('/tmp/debug_parent_error.png')

except Exception as e:
    print(f"❌ Timeout waiting for group span: {e}")
    driver.save_screenshot('/tmp/debug_timeout.png')
    print("Screenshot saved: /tmp/debug_timeout.png")

    # Try immediate search to see if element exists
    print("\n=== Checking if element exists without wait ===")
    elements = driver.find_elements(By.XPATH, f'//span[@title="{group_name}"]')
    print(f"Found {len(elements)} elements with immediate search")
    if elements:
        for i, elem in enumerate(elements[:3]):
            print(f"   Element {i+1}: text='{elem.text}', displayed={elem.is_displayed()}")

driver.quit()
print("\n=== Debug complete ===")
