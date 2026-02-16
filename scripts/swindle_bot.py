#!/usr/bin/env python3
"""
Golf Swindle WhatsApp Bot v4 - Headless Version
Monitors WhatsApp group and sends updates to you only
"""

import os
import re
import sqlite3
import subprocess
import time
import hashlib
from datetime import datetime
from typing import List, Optional, Dict
import schedule
import threading
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# ==================== CONFIGURATION ====================
class Config:
    GROUP_NAME = "Sunday Swindle"  # Change to your WhatsApp group name (exact match)
    MY_NUMBER = "YOUR_PHONE_NUMBER"     # Change to your WhatsApp number (no + or spaces)
    TEE_TIMES = ["8:24", "8:32", "8:40", "8:48", "8:56", "9:04", "9:12"]
    MAX_GROUP_SIZE = 4
    MIN_GROUP_SIZE = 3
    DB_PATH = "swindle.db"
    USER_DATA_DIR = "./chrome_profile"
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                phone TEXT,
                is_guest BOOLEAN DEFAULT 0,
                guest_of TEXT,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'confirmed',
                preferences TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tee_sheet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_of DATE,
                group_number INTEGER,
                tee_time TEXT,
                player_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_hash TEXT UNIQUE,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_participant(self, name: str, phone: Optional[str], 
                       is_guest: bool, guest_of: Optional[str], 
                       preferences: Optional[str]):
        """Add or update a participant"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM participants WHERE name = ?", (name,))
        cursor.execute("""
            INSERT INTO participants (name, phone, is_guest, guest_of, preferences)
            VALUES (?, ?, ?, ?, ?)
        """, (name, phone, is_guest, guest_of, preferences))
        
        conn.commit()
        conn.close()
    
    def remove_participant(self, name: str):
        """Remove a participant and their guests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM participants WHERE name = ?", (name,))
        cursor.execute("DELETE FROM participants WHERE guest_of = ?", (name,))
        
        conn.commit()
        conn.close()
    
    def get_participants(self) -> List[Dict]:
        """Get all participants"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM participants ORDER BY added_at")
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def clear_participants(self):
        """Clear all participants for new week"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM participants")
        conn.commit()
        conn.close()
    
    def is_message_processed(self, message_hash: str) -> bool:
        """Check if message already processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM processed_messages WHERE message_hash = ?", (message_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def mark_message_processed(self, message_hash: str):
        """Mark message as processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO processed_messages (message_hash) VALUES (?)", (message_hash,))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
    
    def save_tee_sheet(self, groups: List[List[Dict]], tee_times: List[str]):
        """Save tee sheet to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        week_of = datetime.now().date().isoformat()
        cursor.execute("DELETE FROM tee_sheet WHERE week_of = ?", (week_of,))
        
        for group_num, group in enumerate(groups):
            tee_time = tee_times[group_num] if group_num < len(tee_times) else "TBC"
            for player in group:
                cursor.execute("""
                    INSERT INTO tee_sheet (week_of, group_number, tee_time, player_name)
                    VALUES (?, ?, ?, ?)
                """, (week_of, group_num + 1, tee_time, player['name']))
        
        conn.commit()
        conn.close()


# ==================== MESSAGE PARSER ====================
class MessageParser:
    """AI-powered message parser using Claude API"""

    def __init__(self, api_key: str):
        """Initialize with Anthropic API key"""
        self.client = anthropic.Anthropic(api_key=api_key)

    def classify_message(self, message: str) -> Dict[str, any]:
        """Use Claude to classify the message"""
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cheap model
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this WhatsApp message about a golf game and classify it.

Message: "{message}"

Respond with ONLY a JSON object (no other text) with these fields:
- "action": "signup", "dropout", or "none"
- "has_guest": true/false (if they're bringing a +1/guest)
- "preferences": string or null (any tee time preferences mentioned)

Examples:
"I'm in" -> {{"action": "signup", "has_guest": false, "preferences": null}}
"Can't make it" -> {{"action": "dropout", "has_guest": false, "preferences": null}}
"Count me in +1" -> {{"action": "signup", "has_guest": true, "preferences": null}}
"I'm in, prefer early" -> {{"action": "signup", "has_guest": false, "preferences": "early tee time"}}"""
                }]
            )

            # Parse the JSON response
            import json
            result = json.loads(response.content[0].text)
            return result

        except Exception as e:
            print(f"⚠️  AI classification error: {e}")
            # Fallback to simple pattern matching
            return self._fallback_classify(message)

    def _fallback_classify(self, message: str) -> Dict[str, any]:
        """Fallback pattern matching if AI fails"""
        message_lower = message.lower().strip()

        # Check for signup
        signup_patterns = [r'\bme please\b', r'\byes please\b', r'\bi\'?m in\b', r'\bcount me in\b']
        is_signup = any(re.search(p, message_lower) for p in signup_patterns)

        # Check for dropout
        dropout_patterns = [r'\bout\b', r'\bcan\'?t make', r'\bsorry.*not\b', r'\bnot playing\b']
        is_dropout = any(re.search(p, message_lower) for p in dropout_patterns)

        # Check for guest
        has_guest = any(term in message_lower for term in ['+1', 'plus 1', 'guest', 'bring a'])

        # Check preferences
        prefs = None
        if 'early' in message_lower:
            prefs = 'early tee time'
        elif 'late' in message_lower:
            prefs = 'late tee time'

        action = "signup" if is_signup else "dropout" if is_dropout else "none"
        return {"action": action, "has_guest": has_guest, "preferences": prefs}

    def is_signup(self, message: str) -> bool:
        """Check if message is a sign-up"""
        result = self.classify_message(message)
        return result["action"] == "signup"

    def is_signup_with_guest(self, message: str) -> bool:
        """Check if message includes a guest"""
        result = self.classify_message(message)
        return result["has_guest"]

    def is_dropout(self, message: str) -> bool:
        """Check if message is a dropout"""
        result = self.classify_message(message)
        return result["action"] == "dropout"

    def extract_preferences(self, message: str) -> Optional[str]:
        """Extract player preferences from message"""
        result = self.classify_message(message)
        return result["preferences"]


# ==================== TEE SHEET GENERATOR ====================
class TeeSheetGenerator:
    """Generate tee sheets from participant list"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate(self, participants: List[Dict]) -> tuple:
        """Generate formatted tee sheet"""
        if not participants:
            return '⛳ *No participants for tee sheet*', []
        
        groups = self._create_groups(participants)
        three_balls = [g for g in groups if len(g) == 3]
        four_balls = [g for g in groups if len(g) == 4]
        sorted_groups = three_balls + four_balls
        message = self._format_tee_sheet(sorted_groups, participants)
        
        return message, sorted_groups
    
    def _create_groups(self, participants: List[Dict]) -> List[List[Dict]]:
        """Create groups from participants"""
        early_birds = [p for p in participants if p.get('preferences') and 'early' in p['preferences']]
        late_birds = [p for p in participants if p.get('preferences') and 'late' in p['preferences']]
        no_preference = [p for p in participants if p not in early_birds and p not in late_birds]
        
        all_players = early_birds + no_preference + late_birds
        groups = []
        current_group = []
        
        for player in all_players:
            current_group.append(player)
            if len(current_group) == self.config.MAX_GROUP_SIZE:
                groups.append(current_group[:])
                current_group = []
        
        if current_group:
            if len(current_group) >= self.config.MIN_GROUP_SIZE:
                groups.append(current_group)
            elif groups:
                groups[-1].extend(current_group)
            else:
                groups.append(current_group)
        
        return groups
    
    def _format_tee_sheet(self, groups: List[List[Dict]], participants: List[Dict]) -> str:
        """Format tee sheet message"""
        message = f"⛳ *SUNDAY SWINDLE TEE SHEET*\n\n"
        message += f"Date: {datetime.now().strftime('%d/%m/%Y')}\n"
        message += f"Total Players: {len(participants)}\n"
        message += f"Groups: {len(groups)}\n\n"
        
        for i, group in enumerate(groups):
            tee_time = self.config.TEE_TIMES[i] if i < len(self.config.TEE_TIMES) else 'TBC'
            message += f"🕐 *{tee_time}* - Group {i + 1}\n"
            for player in group:
                message += f"   • {player['name']}\n"
            message += "\n"
        
        return message


# ==================== WHATSAPP BOT ====================
class WhatsAppBot:
    """WhatsApp Web bot using Selenium"""
    
    def __init__(self, config: Config):
        self.config = config
        self.driver = None
        self.wait = None
    
    def initialize(self):
        """Initialize Chrome and WhatsApp Web"""
        print("🧹 Cleaning up old processes and locks...")

        # Kill any leftover processes
        subprocess.run(['killall', '-9', 'chromedriver', 'chrome', 'chromium'],
                      stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        # Remove lock files
        lock_files = [
            os.path.join(self.config.USER_DATA_DIR, 'SingletonLock'),
            os.path.join(self.config.USER_DATA_DIR, 'DevToolsActivePort')
        ]
        for lock_file in lock_files:
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            except:
                pass

        # Give processes time to fully terminate
        time.sleep(1)

        print("🚀 Initializing Chrome in headless mode...")

        service = Service('/usr/bin/chromedriver')
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'--user-data-dir={self.config.USER_DATA_DIR}')
        chrome_options.add_argument('--window-size=1920,1080')

        # Make headless browser less detectable
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

        # Hide webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("📱 Opening WhatsApp Web...")
        self.driver.get('https://web.whatsapp.com')

        # Wait for page to load
        print("⏳ Waiting for page to load...")
        time.sleep(8)

        if self._is_logged_in():
            print("✅ Already logged in!")
            return True
        
        print("\n" + "="*60)
        print("⚠️  FIRST TIME SETUP - QR CODE REQUIRED")
        print("="*60)
        print("\nWaiting for QR code to load...")

        try:
            # Wait for QR code canvas element to appear
            qr_code = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//canvas[@aria-label="Scan this QR code to link a device!"]'))
            )
            print("✅ QR code loaded!")

            # Wait a bit more to ensure it's fully rendered
            time.sleep(3)

            # Take screenshot
            self.driver.save_screenshot('qr_code.png')
            print(f"\n✅ Screenshot saved: {os.path.abspath('qr_code.png')}")
            print("\nFrom your Windows machine, download it:")
            print(f"   scp phatwell@192.168.1.72:{os.path.abspath('qr_code.png')} .")
            print("\nWaiting for you to scan the QR code...")
            
            for i in range(120):
                if self._is_logged_in():
                    print("\n✅ Successfully logged in!")
                    return True
                time.sleep(1)
                if i % 10 == 0:
                    print(f"... still waiting ({120-i}s remaining)")
            
            print("\n❌ Timeout waiting for QR scan")
            return False
            
        except Exception as e:
            print(f"\n❌ Error during login: {e}")
            return False
    
    def _is_logged_in(self) -> bool:
        """Check if already logged into WhatsApp"""
        try:
            self.driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
            return True
        except NoSuchElementException:
            return False
    
    def _clean_message(self, message: str) -> str:
        """Remove non-BMP characters (emojis, special chars) that ChromeDriver can't handle"""
        # Keep only characters in the Basic Multilingual Plane
        return ''.join(c for c in message if ord(c) < 0x10000)

    def send_message(self, phone_number: str, message: str):
        """Send a message to a phone number"""
        try:
            url = f'https://web.whatsapp.com/send?phone={phone_number}'
            self.driver.get(url)
            time.sleep(3)

            msg_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
            )

            # Clean message to remove emojis and special characters
            clean_msg = self._clean_message(message)

            # Replace \n with Shift+Enter to create multi-line messages
            lines = clean_msg.split('\n')
            for i, line in enumerate(lines):
                msg_box.send_keys(line)
                if i < len(lines) - 1:  # Don't add newline after last line
                    msg_box.send_keys(Keys.SHIFT + Keys.ENTER)

            time.sleep(1)

            # Wait for send button to appear and click it
            send_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Send" or contains(@aria-label, "Send")]'))
            )
            send_button.click()

            print(f"✅ Message sent to {phone_number}")
            time.sleep(3)

            # Navigate back to main WhatsApp Web page
            self.driver.get('https://web.whatsapp.com')
            time.sleep(2)

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            # Navigate back even on error
            try:
                self.driver.get('https://web.whatsapp.com')
                time.sleep(2)
            except:
                pass
    
    def get_group_messages(self, group_name: str) -> List[Dict]:
        """Get recent messages from a group"""
        try:
            # Wait for page to be ready
            time.sleep(3)

            # Clear search and search for group
            search_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
            )
            # Clear search box by clicking the clear button or sending escape
            search_box.click()
            time.sleep(0.5)

            # Try to clear any existing text multiple ways
            try:
                # First try ESC to close any open searches
                search_box.send_keys(Keys.ESCAPE)
                time.sleep(0.3)
            except:
                pass

            # Select all and delete
            for _ in range(3):  # Try multiple times to ensure it's cleared
                search_box.send_keys(Keys.CONTROL + "a")
                search_box.send_keys(Keys.DELETE)
                time.sleep(0.2)

            # Type group name
            search_box.send_keys(group_name)
            time.sleep(5)  # Give more time for search results

            # Find the group span - use find_elements instead of wait.until as it's more reliable
            group_spans = self.driver.find_elements(By.XPATH, f'//span[@title="{group_name}"]')

            if not group_spans:
                # Take screenshot on failure
                self.driver.save_screenshot('error_search.png')
                print(f"❌ Group not found. Screenshot saved: error_search.png")
                raise Exception(f"Could not find group: {group_name}")

            # Use the first matching element
            group_span = group_spans[0]
            print(f"✅ Found group span")
            # Click on the parent container (go up 5 levels - works reliably)
            parent = group_span.find_element(By.XPATH, './ancestor::div[5]')
            parent.click()
            time.sleep(3)
            
            messages = []
            # Get incoming messages using modern WhatsApp Web structure
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, '.message-in')

            for elem in message_elements[-50:]:
                try:
                    # Get sender from data-pre-plain-text attribute
                    # Format: [time, date] phone: or [time, date] name:
                    sender_elem = elem.find_element(By.XPATH, './/*[@data-pre-plain-text]')
                    pre_text = sender_elem.get_attribute('data-pre-plain-text')

                    # Extract sender name/phone from pre_text like "[11:29, 2/15/2026] +44 7850 450853: "
                    sender = "Unknown"
                    if pre_text and ']:' in pre_text:
                        sender = pre_text.split(']')[1].strip().rstrip(':').strip()

                    # Get message text from copyable-text element
                    message_elem = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
                    text = message_elem.text if message_elem else ""

                    # Clean up text (remove sender name that appears at start)
                    lines = text.split('\n')
                    if len(lines) > 1:
                        text = '\n'.join(lines[1:]).strip()  # Skip first line (sender name)

                    if text:
                        msg_hash = hashlib.md5(f"{sender}{text}".encode()).hexdigest()
                        messages.append({
                            'sender': sender,
                            'text': text,
                            'hash': msg_hash
                        })
                except:
                    continue
            
            return messages

        except Exception as e:
            import traceback
            print(f"❌ Error getting group messages: {e}")
            print(f"Error details: {traceback.format_exc()}")
            return None  # Return None to indicate failure (empty list means success with no messages)
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()


# ==================== MAIN BOT CONTROLLER ====================
class SwindleBot:
    """Main bot controller"""
    
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.DB_PATH)
        self.parser = MessageParser(self.config.ANTHROPIC_API_KEY)
        self.tee_generator = TeeSheetGenerator(self.config)
        self.whatsapp = WhatsAppBot(self.config)
        self.is_after_saturday_5pm = False
        self.running = True
    
    def check_time_context(self):
        """Check if we're before or after Saturday 5pm"""
        now = datetime.now()
        day_of_week = now.weekday()
        
        if day_of_week == 5 and now.hour >= 17:
            self.is_after_saturday_5pm = True
        elif day_of_week == 6:
            self.is_after_saturday_5pm = True
        else:
            self.is_after_saturday_5pm = False
    
    def send_to_me(self, message: str):
        """Send a message to yourself"""
        self.whatsapp.send_message(self.config.MY_NUMBER, message)
    
    def generate_participant_list(self) -> str:
        """Generate formatted participant list"""
        participants = self.db.get_participants()
        
        if not participants:
            return '📋 *Sunday Swindle Update*\n\nNo participants yet.'
        
        message = f"📋 *Sunday Swindle Update*\n\n"
        message += f"Total Players: {len(participants)}\n\n"
        
        for i, p in enumerate(participants, 1):
            message += f"{i}. {p['name']}"
            if p['preferences']:
                message += f" ({p['preferences']})"
            message += "\n"
        
        return message
    
    def handle_message(self, msg_data: Dict):
        """Handle incoming WhatsApp message"""
        sender = msg_data['sender']
        text = msg_data['text']
        msg_hash = msg_data['hash']
        
        if self.db.is_message_processed(msg_hash):
            return
        
        self.check_time_context()
        
        if self.parser.is_signup(text):
            preferences = self.parser.extract_preferences(text)
            self.db.add_participant(sender, None, False, None, preferences)
            self.db.mark_message_processed(msg_hash)
            
            if not self.is_after_saturday_5pm:
                self.send_to_me(f"✅ {sender} added\nPreferences: {preferences or 'None'}")
            else:
                self.regenerate_tee_sheet()
            
            if self.parser.is_signup_with_guest(text):
                guest_name = f"{sender}-guest-1"
                self.db.add_participant(guest_name, None, True, sender, None)
                
                if not self.is_after_saturday_5pm:
                    self.send_to_me(f"✅ Guest added for {sender}")
                else:
                    self.regenerate_tee_sheet()
        
        elif self.parser.is_dropout(text):
            self.db.remove_participant(sender)
            self.db.mark_message_processed(msg_hash)
            
            if not self.is_after_saturday_5pm:
                self.send_to_me(f"❌ {sender} removed")
            else:
                self.regenerate_tee_sheet()
    
    def regenerate_tee_sheet(self):
        """Regenerate and send updated tee sheet"""
        participants = self.db.get_participants()
        tee_sheet, groups = self.tee_generator.generate(participants)
        
        if groups:
            self.db.save_tee_sheet(groups, self.config.TEE_TIMES)
        
        self.send_to_me(f"🔄 *UPDATED TEE SHEET*\n\n{tee_sheet}")
    
    def send_daily_update(self):
        """Send daily 8pm participant list"""
        print("⏰ Sending daily update...")
        participant_list = self.generate_participant_list()
        self.send_to_me(participant_list)
    
    def generate_saturday_tee_sheet(self):
        """Generate Saturday 5pm tee sheet"""
        print("⏰ Generating Saturday tee sheet...")
        participants = self.db.get_participants()
        tee_sheet, groups = self.tee_generator.generate(participants)
        
        if groups:
            self.db.save_tee_sheet(groups, self.config.TEE_TIMES)
        
        self.send_to_me(tee_sheet)
        self.is_after_saturday_5pm = True
    
    def clear_weekly_data(self):
        """Clear participants for new week"""
        print("⏰ Clearing participants for new week...")
        self.db.clear_participants()
        self.is_after_saturday_5pm = False

    def send_health_check(self):
        """Send daily midday health check message"""
        print("⏰ Sending health check...")
        now = datetime.now()
        message = f"HEALTH CHECK\n\nBot is running normally\nTime: {now.strftime('%d/%m/%Y %H:%M')}"
        self.send_to_me(message)

    def send_startup_message(self):
        """Send message when bot starts"""
        print("📤 Sending startup message...")
        now = datetime.now()
        message = f"BOT STARTED\n\nGolf Swindle Bot v4 is now online\nStarted: {now.strftime('%d/%m/%Y %H:%M')}\nMonitoring: {self.config.GROUP_NAME}"
        self.send_to_me(message)

    def schedule_jobs(self):
        """Schedule recurring jobs"""
        # Daily health check at midday
        schedule.every().day.at("12:00").do(self.send_health_check)

        # Daily participant updates
        schedule.every().monday.at("20:00").do(self.send_daily_update)
        schedule.every().tuesday.at("20:00").do(self.send_daily_update)
        schedule.every().wednesday.at("20:00").do(self.send_daily_update)
        schedule.every().thursday.at("20:00").do(self.send_daily_update)
        schedule.every().friday.at("20:00").do(self.send_daily_update)

        # Weekly events
        schedule.every().saturday.at("17:00").do(self.generate_saturday_tee_sheet)

        # Clear data Monday morning at 12:01 AM (ready for new week)
        schedule.every().monday.at("00:01").do(self.clear_weekly_data)

        print("✅ Scheduled jobs configured")
    
    def run_scheduler(self):
        """Run scheduled jobs in background"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)
    
    def monitor_messages(self):
        """Monitor WhatsApp group for new messages"""
        print(f"\n👀 Monitoring group: {self.config.GROUP_NAME}")
        print(f"⏱️  Checking every 1 hour")

        consecutive_failures = 0
        max_consecutive_failures = 3
        last_week_check = None

        while self.running:
            try:
                # Check if it's a new week (Monday) and clear old data
                now = datetime.now()
                current_week = now.isocalendar()[1]  # Get week number

                if last_week_check != current_week and now.weekday() == 0:  # Monday
                    print(f"\n📅 New week detected - clearing old data from previous week")
                    self.clear_weekly_data()
                    last_week_check = current_week

                # On Sunday, only monitor until first tee time
                if now.weekday() == 6:  # Sunday
                    # Get first tee time (e.g., "08:00" from ["08:00", "08:10", ...])
                    first_tee_time = self.config.TEE_TIMES[0] if self.config.TEE_TIMES else "08:00"
                    tee_hour, tee_minute = map(int, first_tee_time.split(':'))

                    # Check if we're past the first tee time
                    if now.hour > tee_hour or (now.hour == tee_hour and now.minute >= tee_minute):
                        print(f"\n😴 Past tee time ({first_tee_time}) - resting until Monday")
                        time.sleep(3600)  # Sleep 1 hour
                        continue
                    else:
                        print(f"\n⏰ Sunday before tee time ({first_tee_time}) - still monitoring")

                messages = self.whatsapp.get_group_messages(self.config.GROUP_NAME)

                if messages is None:
                    # Failed to get messages
                    consecutive_failures += 1
                    print(f"⚠️  Failed to get messages ({consecutive_failures}/{max_consecutive_failures})")

                    if consecutive_failures >= max_consecutive_failures:
                        print(f"❌ Failed {max_consecutive_failures} times in a row. Stopping to prevent infinite loop.")
                        print("   Check error_search.png if it exists for debugging.")
                        self.running = False
                        break
                else:
                    # Successfully got messages (even if empty)
                    consecutive_failures = 0

                    for msg in messages:
                        self.handle_message(msg)

                    print(f"✅ Checked messages at {now.strftime('%H:%M')}")

                time.sleep(3600)  # Sleep 1 hour (3600 seconds)

            except KeyboardInterrupt:
                print("\n\n👋 Shutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Error monitoring messages: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(f"❌ Too many errors. Stopping.")
                    self.running = False
                    break
                time.sleep(30)
    
    def run(self):
        """Main run loop"""
        print("="*60)
        print(" GOLF SWINDLE WHATSAPP BOT v4")
        print("="*60)
        
        if not self.whatsapp.initialize():
            print("\n❌ Failed to initialize WhatsApp")
            return
        
        self.schedule_jobs()

        scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()

        print("\n✅ Bot is running!")
        print(f"📱 Monitoring: {self.config.GROUP_NAME}")
        print(f"📞 Sending updates to: {self.config.MY_NUMBER}")
        print("\nPress Ctrl+C to stop\n")

        # Send startup notification
        self.send_startup_message()

        try:
            self.monitor_messages()
        finally:
            self.whatsapp.close()


if __name__ == "__main__":
    bot = SwindleBot()
    bot.run()