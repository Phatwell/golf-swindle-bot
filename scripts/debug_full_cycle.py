#!/usr/bin/env python3
"""Debug full cycle: navigate away and back, then search"""

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

group_name = "Your Golf Group"

print("\n=== FIRST SEARCH (should work) ===")
try:
    search_box = wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    search_box.click()
    time.sleep(0.5)
    search_box.send_keys(Keys.ESCAPE)
    time.sleep(0.3)
    for _ in range(3):
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.DELETE)
        time.sleep(0.2)
    search_box.send_keys(group_name)
    time.sleep(5)

    group_span = wait.until(
        EC.presence_of_element_located((By.XPATH, f'//span[@title="{group_name}"]'))
    )
    print(f"✅ First search successful - found '{group_span.text}'")

except Exception as e:
    print(f"❌ First search failed: {e}")
    driver.quit()
    exit(1)

print("\n=== SIMULATE NAVIGATION (like after sending message) ===")
print("Navigating to main page...")
driver.get('https://web.whatsapp.com')
time.sleep(2)
print("✅ Navigated back")

print("\n=== SECOND SEARCH (after navigation - this is where bot fails) ===")
try:
    # Same as get_group_messages
    time.sleep(3)  # Wait for page to be ready

    print("Looking for search box...")
    search_box = wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    print("✅ Search box found")

    # Check if search box has any existing text
    existing_text = search_box.text
    print(f"   Current search box text: '{existing_text}'")

    search_box.click()
    time.sleep(0.5)

    try:
        search_box.send_keys(Keys.ESCAPE)
        time.sleep(0.3)
    except:
        pass

    print("Clearing search box...")
    for i in range(3):
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.DELETE)
        time.sleep(0.2)

    print(f"Typing '{group_name}'...")
    search_box.send_keys(group_name)
    print(f"   Waiting 5 seconds for results...")
    time.sleep(5)

    # Take screenshot
    driver.save_screenshot('/tmp/debug_second_search.png')
    print("Screenshot saved: /tmp/debug_second_search.png")

    print(f"Waiting for span with title='{group_name}'...")
    start = time.time()
    try:
        group_span = wait.until(
            EC.presence_of_element_located((By.XPATH, f'//span[@title="{group_name}"]'))
        )
        elapsed = time.time() - start
        print(f"✅ Second search successful after {elapsed:.2f}s - found '{group_span.text}'")
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Second search FAILED after {elapsed:.2f}s timeout")
        driver.save_screenshot('/tmp/debug_second_search_failed.png')
        print("Screenshot saved: /tmp/debug_second_search_failed.png")

        # Try immediate search
        print("\nTrying immediate search...")
        elements = driver.find_elements(By.XPATH, f'//span[@title="{group_name}"]')
        print(f"Found {len(elements)} elements immediately")

        # Check if search box still has correct text
        search_value = driver.execute_script("return arguments[0].textContent", search_box)
        print(f"Search box content: '{search_value}'")

        raise

except Exception as e:
    print(f"❌ Error: {e}")

driver.quit()
print("\n=== Complete ===")
