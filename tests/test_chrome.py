#!/usr/bin/env python3
"""Test if Selenium can initialize Chrome"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

print("Testing Chrome with Selenium...")

# Test 1: Without specifying binary location
print("\n1. Testing with auto-detection...")
try:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    print("✅ SUCCESS: Auto-detection works!")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 2: With explicit binary location
print("\n2. Testing with explicit binary path...")
try:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.binary_location = '/opt/google/chrome/chrome'
    driver = webdriver.Chrome(options=options)
    print("✅ SUCCESS: Explicit path works!")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 3: Check if it's the user-data-dir causing issues
print("\n3. Testing with user-data-dir...")
try:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-data-dir=./test_chrome_profile')
    options.binary_location = '/opt/google/chrome/chrome'
    driver = webdriver.Chrome(options=options)
    print("✅ SUCCESS: With user-data-dir works!")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")
