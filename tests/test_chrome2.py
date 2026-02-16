#!/usr/bin/env python3
"""Test Chrome with Service"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

print("Testing Chrome with Service...")

# Test 1: Let Selenium handle everything
print("\n1. Letting Selenium Manager handle drivers...")
try:
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    # Don't specify binary_location - let Selenium find it
    driver = webdriver.Chrome(options=options)
    print("✅ SUCCESS!")
    print(f"Chrome version: {driver.capabilities['browserVersion']}")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 2: Use chromedriver explicitly
print("\n2. Using explicit chromedriver path...")
try:
    service = Service('/usr/bin/chromedriver')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ SUCCESS!")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")
