#!/usr/bin/env python3
"""Test to narrow down the issue"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os

print("Testing different configurations...")

# Test 1: Working config from test_chrome2.py
print("\n1. Known working config...")
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

# Test 2: With user-data-dir (new directory)
print("\n2. With NEW user-data-dir...")
try:
    service = Service('/usr/bin/chromedriver')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-data-dir=./test_profile_new')
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ SUCCESS!")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 3: Check if chrome_profile directory exists and has permissions
print("\n3. Checking chrome_profile directory...")
profile_dir = "./chrome_profile"
if os.path.exists(profile_dir):
    print(f"   Directory exists: {os.path.abspath(profile_dir)}")
    try:
        # Try to list contents
        files = os.listdir(profile_dir)
        print(f"   Contains {len(files)} files/directories")
    except Exception as e:
        print(f"   Error reading directory: {e}")
else:
    print(f"   Directory does not exist yet")

# Test 4: With existing chrome_profile if it exists
print("\n4. With EXISTING chrome_profile...")
try:
    service = Service('/usr/bin/chromedriver')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-data-dir=./chrome_profile')
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ SUCCESS!")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 5: With disable-gpu flag
print("\n5. With --disable-gpu flag...")
try:
    service = Service('/usr/bin/chromedriver')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--user-data-dir=./chrome_profile2')
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ SUCCESS!")
    driver.quit()
except Exception as e:
    print(f"❌ FAILED: {e}")
