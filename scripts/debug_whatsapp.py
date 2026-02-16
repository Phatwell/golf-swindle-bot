#!/usr/bin/env python3
"""Debug WhatsApp Web page structure"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

service = Service('/usr/bin/chromedriver')
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=service, options=chrome_options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

print("Opening WhatsApp Web...")
driver.get('https://web.whatsapp.com')

print("Waiting for page to load...")
time.sleep(8)

print("\n=== Looking for QR code elements ===")

# Try different selectors
selectors = [
    ('Canvas with aria-label', By.XPATH, '//canvas[@aria-label]'),
    ('Any canvas', By.TAG_NAME, 'canvas'),
    ('QR code div', By.XPATH, '//*[contains(@class, "qr")]'),
    ('Landing wrapper', By.XPATH, '//*[contains(@class, "landing")]'),
]

for name, by_type, selector in selectors:
    try:
        elements = driver.find_elements(by_type, selector)
        if elements:
            print(f"\n✅ Found {len(elements)} element(s) for: {name}")
            for i, elem in enumerate(elements[:3]):  # Show first 3
                print(f"   Element {i+1}:")
                if by_type == By.TAG_NAME or 'canvas' in name.lower():
                    print(f"      Tag: {elem.tag_name}")
                    print(f"      Displayed: {elem.is_displayed()}")
                try:
                    aria_label = elem.get_attribute('aria-label')
                    if aria_label:
                        print(f"      aria-label: {aria_label}")
                except:
                    pass
        else:
            print(f"\n❌ No elements found for: {name}")
    except Exception as e:
        print(f"\n❌ Error with {name}: {e}")

print("\n=== Taking screenshot ===")
driver.save_screenshot('/tmp/debug_whatsapp.png')
print(f"Screenshot saved: /tmp/debug_whatsapp.png")

print("\n=== Page source (first 2000 chars) ===")
print(driver.page_source[:2000])

driver.quit()
