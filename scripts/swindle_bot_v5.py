#!/usr/bin/env python3
"""
Golf Swindle WhatsApp Bot v5 - AI-Native Redesign
Simpler, more robust, powered by Claude AI
"""

import os
import sqlite3
import subprocess
import time
import json
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


# ==================== CONFIGURATION ====================
class Config:
    GROUP_NAME = "Sunday Swindle"
    MY_NUMBER = "YOUR_PHONE_NUMBER"
    TEE_TIMES = ["8:24", "8:32", "8:40", "8:48", "8:56", "9:04", "9:12"]
    MAX_GROUP_SIZE = 4
    MIN_GROUP_SIZE = 3
    DB_PATH = "swindle.db"
    USER_DATA_DIR = "./chrome_profile"
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Chrome session management
    CHROME_RESTART_HOURS = 12  # Restart Chrome every 12 hours to avoid crashes


# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize simplified database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Simple participants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                guests TEXT,
                preferences TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tee sheet table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tee_sheet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_of DATE,
                group_number INTEGER,
                tee_time TEXT,
                player_name TEXT
            )
        """)

        # Last messages snapshot (for change detection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS last_snapshot (
                id INTEGER PRIMARY KEY,
                messages_json TEXT,
                analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def get_participants(self) -> List[Dict]:
        """Get all participants"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, guests, preferences FROM participants ORDER BY name")
        rows = cursor.fetchall()
        conn.close()

        participants = []
        for row in rows:
            guests = json.loads(row[1]) if row[1] else []
            participants.append({
                'name': row[0],
                'guests': guests,
                'preferences': row[2]
            })
        return participants

    def update_participants(self, players: List[Dict]):
        """Replace all participants with new list from AI"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clear existing
        cursor.execute("DELETE FROM participants")

        # Insert new
        for player in players:
            guests_json = json.dumps(player.get('guests', []))
            cursor.execute("""
                INSERT INTO participants (name, guests, preferences, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (player['name'], guests_json, player.get('preferences')))

        conn.commit()
        conn.close()

    def clear_participants(self):
        """Clear all participants for new week"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM participants")
        cursor.execute("DELETE FROM last_snapshot")
        conn.commit()
        conn.close()

    def save_snapshot(self, messages: List[Dict]):
        """Save messages snapshot for change detection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM last_snapshot")
        cursor.execute("""
            INSERT INTO last_snapshot (id, messages_json, analyzed_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
        """, (json.dumps(messages),))
        conn.commit()
        conn.close()

    def get_last_snapshot(self) -> Optional[List[Dict]]:
        """Get last messages snapshot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT messages_json FROM last_snapshot WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None


# ==================== AI ANALYZER ====================
class AIAnalyzer:
    """Uses Claude to analyze all messages and extract player state"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze_messages(self, messages: List[Dict]) -> Dict:
        """
        Analyze all messages and return complete player state

        Returns:
        {
            "players": [
                {"name": "Alex", "status": "playing", "guests": ["Guest1"], "preferences": "early tee time"},
                {"name": "John", "status": "playing", "guests": ["Tom"], "preferences": null}
            ],
            "summary": "8 players confirmed for Sunday...",
            "changes": ["Alex added a guest", "Sarah dropped out"]
        }
        """

        # Format messages for AI
        messages_text = "\n".join([
            f"[{msg['sender']}]: {msg['text']}"
            for msg in messages
        ])

        prompt = f"""You are analyzing messages from a golf WhatsApp group for their weekly Sunday game.

MESSAGES (Monday through Sunday morning):
{messages_text}

TASK: Analyze ALL messages and determine who is playing this Sunday.

RULES:
1. Latest message from each person is the truth (people change their minds)
2. Understand natural language:
   - "I'm in", "yes please", "count me in", "I'll be there" = PLAYING
   - "I'm out", "can't make it", "not playing", illness mentions = NOT PLAYING
3. Track guests CAREFULLY:
   - "+1", "plus 1" = 1 unnamed guest (use "Guest" as name)
   - "bringing my friend [Name]" = named guest
   - "with [Name]" = named guest
   - Guests MUST be associated with the person who brought them
   - Each player's guests array shows who they're bringing
4. Guest association examples:
   - "Alex: I'm in +1" → Alex brings 1 guest: ["Alex-Guest"]
   - "John: Me please, bringing Tom" → John brings Tom: ["Tom"]
   - "Mike: Count me in with Dave and Steve" → Mike brings 2: ["Dave", "Steve"]
5. Note preferences if mentioned:
   - Tee time preferences (early/late)
   - Playing partners ("want to play with X")
6. If someone says they're out, they're OUT (remove them AND their guests)
7. Only include people who explicitly said they're playing

IMPORTANT:
- Guests belong to whoever mentioned bringing them
- Named guests use their actual name, unnamed use "[Host]-Guest"
- Keep track of who's bringing whom for proper grouping

OUTPUT (valid JSON only, no markdown):
{{
    "players": [
        {{"name": "PlayerName", "guests": ["GuestName1", "GuestName2"], "preferences": "any preferences or null"}}
    ],
    "total_count": number,
    "summary": "brief summary of who's playing",
    "changes": ["list", "of", "notable", "changes"]
}}

Return ONLY the JSON, nothing else."""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",  # Fast and cheap for this task
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)
            return result

        except Exception as e:
            print(f"❌ AI Analysis error: {e}")
            return {
                "players": [],
                "total_count": 0,
                "summary": "Error analyzing messages",
                "changes": []
            }


# ==================== WHATSAPP BOT ====================
class WhatsAppBot:
    """Simplified WhatsApp interface - just scrape messages"""

    def __init__(self, config: Config):
        self.config = config
        self.driver = None
        self.wait = None
        self.session_start_time = None

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
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        self.session_start_time = time.time()

        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("📱 Opening WhatsApp Web...")
        self.driver.get('https://web.whatsapp.com')

        print("⏳ Waiting for page to load...")
        time.sleep(5)

        # Check if logged in
        try:
            self.wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')))
            print("✅ Already logged in!")
            return True
        except:
            print("❌ Not logged in - QR code scan needed")
            return False

    def needs_restart(self) -> bool:
        """Check if Chrome session should be restarted"""
        if not self.session_start_time:
            return True

        hours_running = (time.time() - self.session_start_time) / 3600
        return hours_running >= self.config.CHROME_RESTART_HOURS

    def restart_session(self):
        """Restart Chrome session"""
        print("🔄 Restarting Chrome session...")
        self.close()
        time.sleep(2)
        return self.initialize()

    def get_all_messages(self, group_name: str) -> List[Dict]:
        """Get ALL messages from the group (no filtering)"""
        try:
            time.sleep(3)

            # Find search box
            search_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
            )

            # Clear search
            search_box.click()
            time.sleep(0.5)
            try:
                search_box.send_keys(Keys.ESCAPE)
                time.sleep(0.3)
            except:
                pass

            for _ in range(3):
                search_box.send_keys(Keys.CONTROL + "a")
                search_box.send_keys(Keys.DELETE)
                time.sleep(0.2)

            # Search for group
            search_box.send_keys(group_name)
            time.sleep(5)

            # Find and click group
            group_spans = self.driver.find_elements(By.XPATH, f'//span[@title="{group_name}"]')

            if not group_spans:
                print(f"❌ Group '{group_name}' not found")
                return None

            group_span = group_spans[0]
            parent = group_span.find_element(By.XPATH, './ancestor::div[5]')
            parent.click()
            time.sleep(3)

            # Get ALL messages (scroll to load more if needed)
            messages = []
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, '.message-in')

            for elem in message_elements[-100:]:  # Last 100 messages
                try:
                    sender_elem = elem.find_element(By.XPATH, './/*[@data-pre-plain-text]')
                    pre_text = sender_elem.get_attribute('data-pre-plain-text')

                    sender = "Unknown"
                    if pre_text and ']:' in pre_text:
                        sender = pre_text.split(']')[1].strip().rstrip(':').strip()

                    message_elem = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
                    text = message_elem.text if message_elem else ""

                    lines = text.split('\n')
                    if len(lines) > 1:
                        text = '\n'.join(lines[1:]).strip()

                    if text:
                        messages.append({
                            'sender': sender,
                            'text': text
                        })
                except:
                    continue

            return messages

        except Exception as e:
            print(f"❌ Error getting messages: {e}")
            return None

    def send_message(self, phone_number: str, message: str):
        """Send message to a phone number"""
        try:
            self.driver.get(f'https://web.whatsapp.com/send?phone={phone_number}')
            time.sleep(5)

            msg_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
            )

            clean_msg = message.strip()
            lines = clean_msg.split('\n')
            for i, line in enumerate(lines):
                msg_box.send_keys(line)
                if i < len(lines) - 1:
                    msg_box.send_keys(Keys.SHIFT + Keys.ENTER)

            time.sleep(1)

            send_button = self.driver.find_element(By.XPATH, '//button[@aria-label="Send"]')
            send_button.click()

            print(f"✅ Message sent to {phone_number}")
            time.sleep(3)

            self.driver.get('https://web.whatsapp.com')
            time.sleep(2)

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            try:
                self.driver.get('https://web.whatsapp.com')
                time.sleep(2)
            except:
                pass

    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


# ==================== TEE SHEET GENERATOR ====================
class TeeSheetGenerator:
    """Generate tee sheets from player list"""

    def __init__(self, config: Config):
        self.config = config

    def generate(self, participants: List[Dict]) -> tuple:
        """Generate tee sheet from participants - keeps guests with their hosts"""
        # Build player groups (host + their guests together)
        player_groups = []
        for p in participants:
            group = [{'name': p['name'], 'handicap': 0, 'is_host': True}]
            for guest_name in p.get('guests', []):
                group.append({'name': guest_name, 'handicap': 0, 'is_guest': True, 'brought_by': p['name']})
            player_groups.append(group)

        # Count total players
        total_players = sum(len(g) for g in player_groups)

        if total_players == 0:
            return "No participants yet.", []

        # Distribute into tee time groups, keeping hosts with their guests
        tee_groups = []
        current_group = []

        for player_group in player_groups:
            # If adding this player group would exceed max size, start new group
            if len(current_group) + len(player_group) > self.config.MAX_GROUP_SIZE:
                if current_group:  # Save current group if not empty
                    tee_groups.append(current_group)
                    current_group = []

            # If this player group alone is bigger than max, split it
            if len(player_group) > self.config.MAX_GROUP_SIZE:
                # Keep as many together as possible
                tee_groups.append(player_group[:self.config.MAX_GROUP_SIZE])
                remaining = player_group[self.config.MAX_GROUP_SIZE:]
                if remaining:
                    current_group = remaining
            else:
                current_group.extend(player_group)

        # Add last group if not empty
        if current_group:
            tee_groups.append(current_group)

        # Format tee sheet
        lines = ["🏌️ *SUNDAY SWINDLE TEE SHEET* 🏌️\n"]
        lines.append(f"📅 {datetime.now().strftime('%d/%m/%Y')}\n")
        lines.append(f"👥 {total_players} players, {len(tee_groups)} groups\n")

        for i, group in enumerate(tee_groups):
            tee_time = self.config.TEE_TIMES[i] if i < len(self.config.TEE_TIMES) else "TBC"
            lines.append(f"\n⏰ *Group {i+1} - {tee_time}*")
            for player in group:
                if player.get('is_guest'):
                    lines.append(f"  • {player['name']} (guest of {player['brought_by']})")
                else:
                    lines.append(f"  • {player['name']}")

        return '\n'.join(lines), tee_groups


# ==================== MAIN BOT ====================
class SwindleBot:
    """Main bot controller - simplified AI-native version"""

    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.DB_PATH)
        self.ai = AIAnalyzer(self.config.ANTHROPIC_API_KEY)
        self.whatsapp = WhatsAppBot(self.config)
        self.tee_generator = TeeSheetGenerator(self.config)
        self.running = True

    def send_to_me(self, message: str):
        """Send message to yourself"""
        self.whatsapp.send_message(self.config.MY_NUMBER, message)

    def generate_participant_list(self) -> str:
        """Generate formatted participant list"""
        participants = self.db.get_participants()

        if not participants:
            return '📋 *Sunday Swindle Update*\n\nNo participants yet.'

        total = sum(1 + len(p.get('guests', [])) for p in participants)

        lines = ['📋 *Sunday Swindle Update*\n']
        lines.append(f'👥 {len(participants)} signed up ({total} total with guests)\n')

        for p in participants:
            guests = p.get('guests', [])
            if guests:
                guest_names = ', '.join(guests)
                guest_text = f" (bringing: {guest_names})"
            else:
                guest_text = ""
            pref_text = f" - {p['preferences']}" if p.get('preferences') else ""
            lines.append(f"• {p['name']}{guest_text}{pref_text}")

        return '\n'.join(lines)

    def clear_weekly_data(self):
        """Clear data for new week"""
        print("⏰ Clearing data for new week...")
        self.db.clear_participants()

    def send_health_check(self):
        """Send health check"""
        print("⏰ Sending health check...")
        now = datetime.now()
        message = f"HEALTH CHECK\n\nBot is running normally\nTime: {now.strftime('%d/%m/%Y %H:%M')}"
        self.send_to_me(message)

    def send_startup_message(self):
        """Send startup message"""
        print("📤 Sending startup message...")
        now = datetime.now()
        message = f"BOT STARTED\n\nGolf Swindle Bot v5 (AI-Native) is online\nStarted: {now.strftime('%d/%m/%Y %H:%M')}\nMonitoring: {self.config.GROUP_NAME}"
        self.send_to_me(message)

    def send_daily_update(self):
        """Send daily 8pm update"""
        print("⏰ Sending daily update...")
        participant_list = self.generate_participant_list()
        self.send_to_me(participant_list)

    def generate_saturday_tee_sheet(self):
        """Generate Saturday 5pm tee sheet"""
        print("⏰ Generating Saturday tee sheet...")
        participants = self.db.get_participants()
        tee_sheet, groups = self.tee_generator.generate(participants)
        self.send_to_me(f"🔄 *FINAL TEE SHEET*\n\n{tee_sheet}")

    def schedule_jobs(self):
        """Schedule recurring jobs"""
        schedule.every().day.at("12:00").do(self.send_health_check)
        schedule.every().monday.at("20:00").do(self.send_daily_update)
        schedule.every().tuesday.at("20:00").do(self.send_daily_update)
        schedule.every().wednesday.at("20:00").do(self.send_daily_update)
        schedule.every().thursday.at("20:00").do(self.send_daily_update)
        schedule.every().friday.at("20:00").do(self.send_daily_update)
        schedule.every().saturday.at("17:00").do(self.generate_saturday_tee_sheet)
        schedule.every().monday.at("00:01").do(self.clear_weekly_data)
        print("✅ Scheduled jobs configured")

    def run_scheduler(self):
        """Run scheduled jobs in background"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)

    def monitor_messages(self):
        """Monitor and analyze messages with AI"""
        print(f"\n👀 Monitoring group: {self.config.GROUP_NAME}")
        print(f"🤖 AI-powered analysis every 1 hour")

        consecutive_failures = 0
        max_consecutive_failures = 3

        while self.running:
            try:
                now = datetime.now()

                # Check if we need to restart Chrome
                if self.whatsapp.needs_restart():
                    print("\n🔄 Chrome session expired, restarting...")
                    if not self.whatsapp.restart_session():
                        print("❌ Failed to restart Chrome")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            self.running = False
                            break
                        time.sleep(60)
                        continue

                # Clear data on Monday
                if now.weekday() == 0 and now.hour == 0:
                    self.clear_weekly_data()

                # Check if we should monitor (not after Sunday tee time)
                if now.weekday() == 6:
                    first_tee_time = self.config.TEE_TIMES[0]
                    tee_hour, tee_minute = map(int, first_tee_time.split(':'))

                    if now.hour > tee_hour or (now.hour == tee_hour and now.minute >= tee_minute):
                        print(f"\n😴 Past tee time ({first_tee_time}) - resting")
                        time.sleep(3600)
                        continue

                # Get ALL messages from group
                print(f"\n📥 Fetching all messages from {self.config.GROUP_NAME}...")
                messages = self.whatsapp.get_all_messages(self.config.GROUP_NAME)

                if messages is None:
                    consecutive_failures += 1
                    print(f"⚠️  Failed to get messages ({consecutive_failures}/{max_consecutive_failures})")

                    if consecutive_failures >= max_consecutive_failures:
                        print(f"❌ Too many failures. Stopping.")
                        self.running = False
                        break

                    time.sleep(60)
                    continue

                consecutive_failures = 0

                # Analyze with AI
                print(f"🤖 Analyzing {len(messages)} messages with AI...")
                result = self.ai.analyze_messages(messages)

                # Update database
                self.db.update_participants(result['players'])
                self.db.save_snapshot(messages)

                # Log results
                print(f"✅ Analysis complete:")
                print(f"   Players: {result['total_count']}")
                print(f"   Summary: {result['summary']}")
                if result.get('changes'):
                    print(f"   Changes: {', '.join(result['changes'])}")

                # Check for significant changes and notify
                if result.get('changes') and len(result['changes']) > 0:
                    change_msg = f"🔔 UPDATE\n\n{result['summary']}\n\nChanges:\n"
                    change_msg += '\n'.join(f"• {c}" for c in result['changes'])
                    self.send_to_me(change_msg)

                print(f"⏰ Next check in 1 hour...")
                time.sleep(3600)

            except KeyboardInterrupt:
                print("\n\n👋 Shutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    self.running = False
                    break
                time.sleep(60)

    def run(self):
        """Main run loop"""
        print("="*60)
        print(" GOLF SWINDLE BOT v5 - AI-NATIVE")
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
        print(f"🤖 AI-powered message analysis\n")
        print("Press Ctrl+C to stop\n")

        self.send_startup_message()

        try:
            self.monitor_messages()
        finally:
            self.whatsapp.close()


if __name__ == "__main__":
    bot = SwindleBot()
    bot.run()
