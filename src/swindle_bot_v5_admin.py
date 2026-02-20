#!/usr/bin/env python3
"""
Golf Swindle WhatsApp Bot v5 - AI-Native Redesign
Simpler, more robust, powered by Claude AI
"""

import os
import random
import sqlite3
import subprocess
import time
import json
from datetime import datetime, timedelta
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
    """
    Configuration class - loads settings from config.py if available,
    otherwise uses safe defaults.

    To set up: Copy config.example.py to config.py and update with your details
    """

    # Settings that don't contain sensitive data
    MIN_GROUP_SIZE = 3
    USER_DATA_DIR = "./chrome_profile"
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # Always from environment variable

    # Try to import from config.py (user's personal config)
    # Add project root to path to find config.py
    import sys
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    try:
        import config as _config
        GROUP_NAME = _config.GROUP_NAME
        ADMIN_GROUP_NAME = _config.ADMIN_GROUP_NAME
        MY_NUMBER = _config.MY_NUMBER
        ADMIN_USERS = _config.ADMIN_USERS
        NAME_MAPPING = _config.NAME_MAPPING
        MAX_GROUP_SIZE = _config.MAX_GROUP_SIZE
        DB_PATH = _config.DB_PATH
        CHROME_RESTART_HOURS = _config.CHROME_RESTART_HOURS
        DEFAULT_START_TIME = _config.DEFAULT_START_TIME
        DEFAULT_INTERVAL_MINUTES = _config.DEFAULT_INTERVAL_MINUTES
        DEFAULT_NUM_SLOTS = _config.DEFAULT_NUM_SLOTS
        MAX_MESSAGES = _config.MAX_MESSAGES
        MAIN_GROUP_CHECK_MINUTES = _config.MAIN_GROUP_CHECK_MINUTES
        ADMIN_GROUP_CHECK_SECONDS = _config.ADMIN_GROUP_CHECK_SECONDS
        ADMIN_BURST_DURATION_SECONDS = _config.ADMIN_BURST_DURATION_SECONDS
        ADMIN_BURST_CHECK_SECONDS = _config.ADMIN_BURST_CHECK_SECONDS
    except (ImportError, AttributeError) as e:
        # Use safe defaults if config.py doesn't exist
        print("⚠️  Warning: config.py not found. Please copy config.example.py to config.py")
        print("⚠️  Using placeholder values - bot will not work until config.py is created")
        GROUP_NAME = "CONFIGURE_ME"
        ADMIN_GROUP_NAME = "CONFIGURE_ME"
        MY_NUMBER = "CONFIGURE_ME"
        ADMIN_USERS = ["CONFIGURE_ME"]
        NAME_MAPPING = {}
        MAX_GROUP_SIZE = 4
        DEFAULT_START_TIME = "08:00"
        DEFAULT_INTERVAL_MINUTES = 8
        DEFAULT_NUM_SLOTS = 10
        MAX_MESSAGES = 200
        MAIN_GROUP_CHECK_MINUTES = 10
        ADMIN_GROUP_CHECK_SECONDS = 60
        ADMIN_BURST_DURATION_SECONDS = 180
        ADMIN_BURST_CHECK_SECONDS = 5
        DB_PATH = "golf_swindle.db"
        CHROME_RESTART_HOURS = 24


# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def _connect(self):
        """Get a database connection. Always use with try/finally to ensure close."""
        return sqlite3.connect(self.db_path, timeout=10)

    def init_db(self):
        """Initialize simplified database"""
        conn = self._connect()
        cursor = conn.cursor()

        # Participants table with signup order and reserve status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                guests TEXT,
                preferences TEXT,
                signup_order INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'playing',
                manually_added INTEGER NOT NULL DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migrate existing databases: add signup_order and status if missing
        try:
            cursor.execute("SELECT signup_order FROM participants LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE participants ADD COLUMN signup_order INTEGER NOT NULL DEFAULT 0")
            cursor.execute("ALTER TABLE participants ADD COLUMN status TEXT NOT NULL DEFAULT 'playing'")
            rows = cursor.execute("SELECT name FROM participants ORDER BY name").fetchall()
            for idx, (name,) in enumerate(rows, 1):
                cursor.execute("UPDATE participants SET signup_order = ? WHERE name = ?", (idx, name))
            print("   Migrated participants table: added signup_order and status columns")

        # Migrate: add manually_added column if missing
        try:
            cursor.execute("SELECT manually_added FROM participants LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE participants ADD COLUMN manually_added INTEGER NOT NULL DEFAULT 0")
            print("   Migrated participants table: added manually_added column")

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

        # Constraints table (Phase 3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS constraints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                constraint_type TEXT NOT NULL,
                player_name TEXT NOT NULL,
                target_name TEXT,
                value TEXT,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tee time settings table (Phase 4)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tee_time_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                num_slots INTEGER NOT NULL,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Initialize default tee time settings if none exist
        cursor.execute("SELECT COUNT(*) FROM tee_time_settings WHERE active = 1")
        if cursor.fetchone()[0] == 0:
            # Default: Read from Config
            cursor.execute("""
                INSERT INTO tee_time_settings (start_time, interval_minutes, num_slots, active)
                VALUES (?, ?, ?, 1)
            """, (Config.DEFAULT_START_TIME, Config.DEFAULT_INTERVAL_MINUTES, Config.DEFAULT_NUM_SLOTS))

        # Manual tee times table (for adding specific times)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_tee_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tee_time TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Removed tee times table (for removing specific times)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS removed_tee_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tee_time TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Published tee sheet (for stability after Saturday 5pm)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS published_tee_sheet (
                id INTEGER PRIMARY KEY,
                sheet_json TEXT NOT NULL,
                published_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def get_participants(self, status_filter: str = None) -> List[Dict]:
        """Get participants, optionally filtered by status ('playing', 'reserve', or None for all)"""
        conn = self._connect()
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("SELECT name, guests, preferences, signup_order, status FROM participants WHERE status = ? ORDER BY signup_order", (status_filter,))
        else:
            cursor.execute("SELECT name, guests, preferences, signup_order, status FROM participants ORDER BY signup_order")
        rows = cursor.fetchall()
        conn.close()

        participants = []
        for row in rows:
            guests = json.loads(row[1]) if row[1] else []
            participants.append({
                'name': row[0],
                'guests': guests,
                'preferences': row[2],
                'signup_order': row[3],
                'status': row[4]
            })
        return participants

    def update_participants(self, players: List[Dict]) -> Dict:
        """Replace participants with AI list, preserving signup_order for existing players.
        Manually-added players (via admin commands) are preserved even if AI doesn't find them.
        New players get order based on their position in the AI list (= chat signup order).
        Returns {'promoted': [names], 'demoted': [names]} after status recalculation."""
        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Read existing data before delete
            cursor.execute("SELECT name, signup_order, manually_added, guests, preferences FROM participants")
            existing_rows = cursor.fetchall()
            existing_orders = {row[0]: row[1] for row in existing_rows}
            manual_players = {row[0]: {'guests': row[3], 'preferences': row[4], 'order': row[1]}
                            for row in existing_rows if row[2] == 1}
            max_order = max(existing_orders.values()) if existing_orders else 0

            # Build set of AI-found player names
            ai_names = {p['name'] for p in players}

            # Build map of existing preferences so admin-set ones aren't lost
            existing_prefs = {row[0]: row[4] for row in existing_rows if row[4]}

            # Assign signup_order: existing players keep theirs, new players get next available
            ordered_players = []
            for player in players:
                name = player['name']
                if name in existing_orders:
                    order = existing_orders[name]
                else:
                    max_order += 1
                    order = max_order
                # If AI found a manually-added player, merge any manual guests the AI missed
                if name in manual_players:
                    manual_guests = json.loads(manual_players[name]['guests']) if manual_players[name]['guests'] else []
                    ai_guests = player.get('guests', [])
                    for g in manual_guests:
                        if g not in ai_guests:
                            ai_guests.append(g)
                    player['guests'] = ai_guests
                # Preserve existing preference if AI didn't find one
                # (admin-set preferences like "late" shouldn't be wiped by re-analysis)
                if not player.get('preferences') and name in existing_prefs:
                    player['preferences'] = existing_prefs[name]
                ordered_players.append((player, order, 0))

            # Preserve manually-added players that AI didn't find
            for name, data in manual_players.items():
                if name not in ai_names:
                    guests_json = data['guests']
                    prefs = data['preferences']
                    ordered_players.append(
                        ({'name': name, 'guests': json.loads(guests_json) if guests_json else [], 'preferences': prefs},
                         data['order'], 1))

            # Replace all participants
            cursor.execute("DELETE FROM participants")
            for player, order, manual in ordered_players:
                guests_json = json.dumps(player.get('guests', []))
                cursor.execute("""
                    INSERT INTO participants (name, guests, preferences, signup_order, status, manually_added, updated_at)
                    VALUES (?, ?, ?, ?, 'playing', ?, CURRENT_TIMESTAMP)
                """, (player['name'], guests_json, player.get('preferences'), order, manual))
            conn.commit()
        finally:
            conn.close()

        # Recalculate playing/reserve statuses based on capacity
        return self.recalculate_statuses()

    def clear_participants(self):
        """Clear all participants for new week (also clears time preferences)"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM participants")
        cursor.execute("DELETE FROM last_snapshot")
        conn.commit()
        conn.close()

    def clear_time_preferences(self):
        """Clear time preferences from all participants (keeps participants, only clears early/late)"""
        conn = self._connect()
        cursor = conn.cursor()

        # Get all participants
        cursor.execute("SELECT name, preferences FROM participants")
        for name, prefs in cursor.fetchall():
            if prefs:
                # Remove 'early' and 'late' from preferences
                cleaned = ' '.join([word for word in prefs.split() if word.lower() not in ['early', 'late']])
                cursor.execute("UPDATE participants SET preferences = ? WHERE name = ?", (cleaned.strip() or None, name))

        conn.commit()
        conn.close()

    def save_snapshot(self, messages: List[Dict]):
        """Save messages snapshot for change detection"""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM last_snapshot")
            cursor.execute("""
                INSERT INTO last_snapshot (id, messages_json, analyzed_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
            """, (json.dumps(messages),))
            conn.commit()
        finally:
            conn.close()

    def get_last_snapshot(self) -> Optional[List[Dict]]:
        """Get last messages snapshot"""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT messages_json FROM last_snapshot WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()

    def add_player_manually(self, name: str, guests: List[str] = None, preferences: str = None) -> str:
        """Manually add a player. Returns 'playing', 'reserve', 'exists', or 'error'."""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Check if already exists
            cursor.execute("SELECT name FROM participants WHERE name = ?", (name,))
            if cursor.fetchone():
                conn.close()
                return 'exists'

            # Get next signup_order
            cursor.execute("SELECT MAX(signup_order) FROM participants")
            max_order = cursor.fetchone()[0] or 0

            guests_json = json.dumps(guests or [])
            cursor.execute("""
                INSERT INTO participants (name, guests, preferences, signup_order, status, manually_added, updated_at)
                VALUES (?, ?, ?, ?, 'playing', 1, CURRENT_TIMESTAMP)
            """, (name, guests_json, preferences, max_order + 1))

            conn.commit()
            conn.close()

            # Recalculate statuses - this player may end up as reserve
            self.recalculate_statuses()

            # Check what status they got
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM participants WHERE name = ?", (name,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 'error'
        except Exception as e:
            print(f"❌ Error adding player: {e}")
            return 'error'

    def remove_player_manually(self, name: str) -> Dict:
        """Manually remove a player. Returns {'removed': bool, 'was_status': str, 'promoted': [names]}."""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Check current status before removing
            cursor.execute("SELECT status FROM participants WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {'removed': False, 'was_status': None, 'promoted': []}

            was_status = row[0]
            cursor.execute("DELETE FROM participants WHERE name = ?", (name,))
            conn.commit()
            conn.close()

            # Recalculate - may promote reserves if a playing slot freed up
            changes = self.recalculate_statuses()
            return {'removed': True, 'was_status': was_status, 'promoted': changes.get('promoted', [])}
        except Exception as e:
            print(f"❌ Error removing player: {e}")
            return {'removed': False, 'was_status': None, 'promoted': []}

    def add_guest_manually(self, host_name: str, guest_name: str) -> Dict:
        """Manually add a guest to a player's list. Returns {'success': bool, 'promoted': [], 'demoted': []}"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Get current guests
            cursor.execute("SELECT guests FROM participants WHERE name = ?", (host_name,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return {'success': False, 'promoted': [], 'demoted': []}

            guests = json.loads(row[0]) if row[0] else []
            if guest_name not in guests:
                guests.append(guest_name)

            cursor.execute("""
                UPDATE participants
                SET guests = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (json.dumps(guests), host_name))

            conn.commit()
            conn.close()
            # Adding a guest affects capacity usage - recalculate
            changes = self.recalculate_statuses()
            return {'success': True, 'promoted': changes.get('promoted', []), 'demoted': changes.get('demoted', [])}
        except Exception as e:
            print(f"❌ Error adding guest: {e}")
            return {'success': False, 'promoted': [], 'demoted': []}

    def remove_guest_manually(self, guest_name: str, host_name: str = None) -> Dict:
        """Manually remove a guest (from specific host or all hosts). Returns {'success': bool, 'promoted': [], 'demoted': []}"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            if host_name:
                # Remove from specific host
                cursor.execute("SELECT guests FROM participants WHERE name = ?", (host_name,))
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return {'success': False, 'promoted': [], 'demoted': []}

                guests = json.loads(row[0]) if row[0] else []
                if guest_name in guests:
                    guests.remove(guest_name)
                    cursor.execute("""
                        UPDATE participants
                        SET guests = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE name = ?
                    """, (json.dumps(guests), host_name))
            else:
                # Remove from all hosts
                cursor.execute("SELECT name, guests FROM participants")
                rows = cursor.fetchall()
                removed = False

                for name, guests_json in rows:
                    guests = json.loads(guests_json) if guests_json else []
                    if guest_name in guests:
                        guests.remove(guest_name)
                        cursor.execute("""
                            UPDATE participants
                            SET guests = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE name = ?
                        """, (json.dumps(guests), name))
                        removed = True

                if not removed:
                    conn.close()
                    return {'success': False, 'promoted': [], 'demoted': []}

            conn.commit()
            conn.close()
            # Removing a guest frees capacity - recalculate
            changes = self.recalculate_statuses()
            return {'success': True, 'promoted': changes.get('promoted', []), 'demoted': changes.get('demoted', [])}
        except Exception as e:
            print(f"❌ Error removing guest: {e}")
            return {'success': False, 'promoted': [], 'demoted': []}

    # ==================== CONSTRAINT MANAGEMENT (Phase 3) ====================

    def add_constraint(self, constraint_type: str, player_name: str, target_name: str = None, value: str = None) -> bool:
        """Add a constraint (partner preference, avoid, skill level, etc.)"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Check if constraint already exists
            if target_name:
                cursor.execute("""
                    SELECT id FROM constraints
                    WHERE constraint_type = ? AND player_name = ? AND target_name = ? AND active = 1
                """, (constraint_type, player_name, target_name))
            else:
                cursor.execute("""
                    SELECT id FROM constraints
                    WHERE constraint_type = ? AND player_name = ? AND active = 1
                """, (constraint_type, player_name))

            if cursor.fetchone():
                # Constraint already exists
                conn.close()
                return False

            cursor.execute("""
                INSERT INTO constraints (constraint_type, player_name, target_name, value, active, created_at)
                VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (constraint_type, player_name, target_name, value))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error adding constraint: {e}")
            return False

    def remove_constraint(self, constraint_type: str, player_name: str, target_name: str = None) -> bool:
        """Remove a constraint"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            if target_name:
                cursor.execute("""
                    UPDATE constraints SET active = 0
                    WHERE constraint_type = ? AND player_name = ? AND target_name = ? AND active = 1
                """, (constraint_type, player_name, target_name))
            else:
                cursor.execute("""
                    UPDATE constraints SET active = 0
                    WHERE constraint_type = ? AND player_name = ? AND active = 1
                """, (constraint_type, player_name))

            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            return rows_affected > 0
        except Exception as e:
            print(f"❌ Error removing constraint: {e}")
            return False

    def get_constraints(self, player_name: str = None) -> List[Dict]:
        """Get all active constraints (optionally for a specific player)"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            if player_name:
                cursor.execute("""
                    SELECT constraint_type, player_name, target_name, value
                    FROM constraints
                    WHERE player_name = ? AND active = 1
                    ORDER BY constraint_type, player_name
                """, (player_name,))
            else:
                cursor.execute("""
                    SELECT constraint_type, player_name, target_name, value
                    FROM constraints
                    WHERE active = 1
                    ORDER BY constraint_type, player_name
                """)

            rows = cursor.fetchall()
            conn.close()

            constraints = []
            for row in rows:
                constraints.append({
                    'type': row[0],
                    'player': row[1],
                    'target': row[2],
                    'value': row[3]
                })
            return constraints
        except Exception as e:
            print(f"❌ Error getting constraints: {e}")
            return []

    def get_partner_preferences(self) -> Dict[str, List[str]]:
        """Get all partner preferences as a dict {player: [preferred_partners]}
        Includes both season-long partner_preference and weekly_pairing constraints."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT player_name, target_name
                FROM constraints
                WHERE constraint_type IN ('partner_preference', 'weekly_pairing') AND active = 1
            """)
            rows = cursor.fetchall()
            conn.close()

            preferences = {}
            for player, target in rows:
                if player not in preferences:
                    preferences[player] = []
                if target not in preferences[player]:
                    preferences[player].append(target)
            return preferences
        except Exception as e:
            print(f"❌ Error getting partner preferences: {e}")
            return {}

    def save_weekly_pairings(self, pairings: List[list]):
        """Save AI-detected MP pairings as weekly constraints.
        These reset every Monday unlike season-long partner preferences."""
        if not pairings:
            return
        try:
            conn = self._connect()
            cursor = conn.cursor()
            # Clear previous weekly pairings before adding new ones
            cursor.execute("DELETE FROM constraints WHERE constraint_type = 'weekly_pairing'")
            for pair in pairings:
                if len(pair) == 2:
                    p1, p2 = pair[0], pair[1]
                    cursor.execute("""
                        INSERT INTO constraints (constraint_type, player_name, target_name, active)
                        VALUES ('weekly_pairing', ?, ?, 1)
                    """, (p1, p2))
                    print(f"   🤝 MP pairing detected: {p1} ↔ {p2}")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Error saving weekly pairings: {e}")

    def clear_weekly_pairings(self):
        """Clear all AI-detected weekly pairings"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM constraints WHERE constraint_type = 'weekly_pairing'")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Error clearing weekly pairings: {e}")

    def get_avoidances(self) -> Dict[str, List[str]]:
        """Get all avoidances as a dict {player: [players_to_avoid]}"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT player_name, target_name
                FROM constraints
                WHERE constraint_type = 'avoid' AND active = 1
            """)
            rows = cursor.fetchall()
            conn.close()

            avoidances = {}
            for player, target in rows:
                if player not in avoidances:
                    avoidances[player] = []
                avoidances[player].append(target)
            return avoidances
        except Exception as e:
            print(f"❌ Error getting avoidances: {e}")
            return {}

    # ==================== TEE TIME MANAGEMENT (Phase 4) ====================

    def get_tee_time_settings(self) -> Optional[Dict]:
        """Get active tee time settings"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT start_time, interval_minutes, num_slots
                FROM tee_time_settings
                WHERE active = 1
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'start_time': row[0],
                    'interval_minutes': row[1],
                    'num_slots': row[2]
                }
            return None
        except Exception as e:
            print(f"❌ Error getting tee time settings: {e}")
            return None

    def set_tee_time_settings(self, start_time: str, interval_minutes: int, num_slots: int) -> bool:
        """Set new tee time settings (deactivates previous settings)"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Deactivate all previous settings
            cursor.execute("UPDATE tee_time_settings SET active = 0")

            # Insert new settings
            cursor.execute("""
                INSERT INTO tee_time_settings (start_time, interval_minutes, num_slots, active, created_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (start_time, interval_minutes, num_slots))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error setting tee time settings: {e}")
            return False

    def generate_tee_times(self) -> List[str]:
        """Generate list of available tee times (auto-generated + additions - removals)"""
        # Start with auto-generated times
        settings = self.get_tee_time_settings()
        if not settings:
            return []

        from datetime import datetime, timedelta

        # Parse start time
        start_hour, start_min = map(int, settings['start_time'].split(':'))
        current = datetime.now().replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

        tee_times = set()
        for i in range(settings['num_slots']):
            tee_times.add(current.strftime('%H:%M'))
            current += timedelta(minutes=settings['interval_minutes'])

        # Add manually added times
        added_times = self.get_manual_tee_times()
        tee_times.update(added_times)

        # Remove manually removed times
        removed_times = self.get_removed_tee_times()
        tee_times.difference_update(removed_times)

        # Convert back to sorted list
        return sorted(list(tee_times))

    def get_capacity(self) -> int:
        """Max players = number of tee time slots * MAX_GROUP_SIZE"""
        tee_times = self.generate_tee_times()
        return len(tee_times) * Config.MAX_GROUP_SIZE

    def recalculate_statuses(self) -> Dict:
        """Recalculate playing/reserve status based on signup_order and capacity.
        Returns {'promoted': [names], 'demoted': [names]} for notifications."""
        capacity = self.get_capacity()
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, guests, signup_order, status FROM participants ORDER BY signup_order")
            rows = cursor.fetchall()

            spots_used = 0
            promoted = []
            demoted = []

            for name, guests_json, signup_order, old_status in rows:
                guests = json.loads(guests_json) if guests_json else []
                block_size = 1 + len(guests)

                if spots_used + block_size <= capacity:
                    new_status = 'playing'
                    spots_used += block_size
                else:
                    new_status = 'reserve'

                if new_status != old_status:
                    cursor.execute("UPDATE participants SET status = ? WHERE name = ?", (new_status, name))
                    if new_status == 'playing':
                        promoted.append(name)
                    else:
                        demoted.append(name)

            conn.commit()
            return {'promoted': promoted, 'demoted': demoted}
        finally:
            conn.close()

    def add_manual_tee_time(self, time_str: str) -> bool:
        """Add a single tee time manually"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            # Remove from removed list if it was previously removed
            cursor.execute("DELETE FROM removed_tee_times WHERE tee_time = ?", (time_str,))
            cursor.execute("""
                INSERT INTO manual_tee_times (tee_time)
                VALUES (?)
            """, (time_str,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Time already exists in manual list, but still clear from removed
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM removed_tee_times WHERE tee_time = ?", (time_str,))
            conn.commit()
            conn.close()
            return True

    def remove_manual_tee_time(self, time_str: str) -> bool:
        """Mark a tee time as removed (works for auto-generated or manually added times)"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # First, remove from manual_tee_times if it exists there
            cursor.execute("DELETE FROM manual_tee_times WHERE tee_time = ?", (time_str,))

            # Then add to removed_tee_times
            cursor.execute("""
                INSERT INTO removed_tee_times (tee_time)
                VALUES (?)
            """, (time_str,))

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Already in removed list
            return False

    def get_manual_tee_times(self) -> List[str]:
        """Get all manually added tee times"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT tee_time FROM manual_tee_times ORDER BY tee_time")
        times = [row[0] for row in cursor.fetchall()]
        conn.close()
        return times

    def get_removed_tee_times(self) -> List[str]:
        """Get all removed tee times"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT tee_time FROM removed_tee_times ORDER BY tee_time")
        times = [row[0] for row in cursor.fetchall()]
        conn.close()
        return times

    def clear_manual_tee_times(self) -> bool:
        """Clear all manually added and removed tee times (reset to pure auto-generation)"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM manual_tee_times")
        cursor.execute("DELETE FROM removed_tee_times")
        conn.commit()
        conn.close()
        return True

    # ==================== PUBLISHED TEE SHEET ====================

    def save_published_tee_sheet(self, groups: List, assigned_times: Dict, tee_sheet_text: str):
        """Save the published tee sheet for stability after publishing"""
        # Convert groups to serializable format
        sheet_data = {
            'groups': [],
            'tee_sheet_text': tee_sheet_text
        }
        for group in groups:
            if isinstance(group, dict):
                # Already serialized (from swap/move on published sheet)
                sheet_data['groups'].append(group)
            else:
                # Raw format (list of player dicts from generate())
                group_data = {
                    'tee_time': assigned_times.get(id(group), 'TBC'),
                    'players': []
                }
                for player in group:
                    group_data['players'].append({
                        'name': player['name'],
                        'is_guest': player.get('is_guest', False),
                        'brought_by': player.get('brought_by')
                    })
                sheet_data['groups'].append(group_data)

        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM published_tee_sheet")
            cursor.execute("""
                INSERT INTO published_tee_sheet (id, sheet_json, published_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
            """, (json.dumps(sheet_data),))
            conn.commit()
        finally:
            conn.close()

    def get_published_tee_sheet(self) -> Optional[Dict]:
        """Get the published tee sheet if one exists"""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT sheet_json, published_at FROM published_tee_sheet WHERE id = 1")
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                data['published_at'] = row[1]
                return data
            return None
        finally:
            conn.close()

    def clear_published_tee_sheet(self):
        """Clear the published tee sheet (for new week or randomize)"""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM published_tee_sheet")
            conn.commit()
        finally:
            conn.close()


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

        # PRE-FILTER MESSAGES before sending to AI
        # 1. Find the organizer message ("now taking names")
        organizer_keywords = ["now taking names", "taking names for sunday", "taking names this sunday"]
        organizer_idx = -1

        for i, msg in enumerate(messages):
            text_lower = msg['text'].lower()
            if any(keyword in text_lower for keyword in organizer_keywords):
                organizer_idx = i
                break

        # 2. Filter messages: only include from organizer message onward
        if organizer_idx >= 0:
            filtered_messages = messages[organizer_idx:]
        else:
            # "Taking names" message not visible - too many messages since then
            # Run delta analysis on recent messages to catch new signups/dropouts
            print(f"⚠️  'Taking names' message not found in {len(messages)} loaded messages - running delta analysis")
            return self._analyze_delta(messages)

        # 3. Filter out messages that quote the organizer message WITHOUT adding signup text
        final_messages = []
        signup_keywords = ["please", "yes", "i'm in", "count me in", "me", "im in"]

        for msg in filtered_messages:
            # Check if message is quoting the organizer message
            text_lower = msg['text'].lower()
            is_pure_organizer_quote = False

            # If message contains organizer keywords (like "now taking names") but sender didn't send the original
            if any(keyword in text_lower for keyword in organizer_keywords):
                # Check if this is the original organizer message or a quote
                if organizer_idx >= 0:
                    original_organizer = messages[organizer_idx]
                    # If this person isn't the original organizer, they're quoting it
                    if msg['sender'] != original_organizer['sender']:
                        # They're quoting, but check if they added their own signup text
                        # Look at the last 2 lines for signup keywords
                        lines = msg['text'].strip().split('\n')
                        last_lines = ' '.join(lines[-2:]).lower() if len(lines) >= 2 else lines[-1].lower() if lines else ""

                        # Check if they added signup text after the quote
                        has_signup_text = any(keyword in last_lines for keyword in signup_keywords)

                        if not has_signup_text:
                            # Pure quote with no signup - filter it out
                            is_pure_organizer_quote = True

            if not is_pure_organizer_quote:
                final_messages.append(msg)

        # Format messages for AI (include timestamps for chronological context)
        def format_msg_line(msg):
            ts = msg.get('timestamp', '')
            if ts and '[' in ts and ']' in ts:
                try:
                    time_part = ts.split('[')[1].split(']')[0]  # "HH:MM, DD/MM/YYYY"
                    return f"[{time_part}] [{msg['sender']}]: {msg['text']}"
                except:
                    pass
            return f"[{msg['sender']}]: {msg['text']}"

        messages_text = "\n".join([format_msg_line(msg) for msg in final_messages])

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

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4000,
                temperature=0.1,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_prompt
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

    def _analyze_delta(self, messages: List[Dict]) -> Optional[Dict]:
        """Analyze recent messages for new signups/dropouts when 'taking names' is not visible.
        Returns a delta result with 'add' and 'remove' lists, or None if nothing found."""
        def format_msg_line(msg):
            ts = msg.get('timestamp', '')
            if ts and '[' in ts and ']' in ts:
                try:
                    time_part = ts.split('[')[1].split(']')[0]
                    return f"[{time_part}] [{msg['sender']}]: {msg['text']}"
                except:
                    pass
            return f"[{msg['sender']}]: {msg['text']}"

        messages_text = "\n".join([format_msg_line(msg) for msg in messages])

        system_prompt = """You analyze recent WhatsApp golf group messages to find NEW signups or dropouts.
The original signup message is no longer visible - you are only seeing recent messages.

Look for:
- NEW SIGNUPS: Someone asking to play, be added, join Sunday, etc. (e.g. "Can I play?", "Add me please", "Count me in for Sunday")
- DROPOUTS: Someone pulling out, cancelling, can't make it (e.g. "I'm out", "Can't make it", "Pull me out")
- GUEST ADDITIONS: Someone asking for a guest spot (e.g. "Can I bring a mate?", "Can I have a guest?")
- GUEST REMOVALS: Someone cancelling a guest

IGNORE: Banter, questions about tee times, general chat, reactions.
Only include clear signup/dropout intent.

Return JSON with:
- "add": list of {"name": "SenderName", "guests": [], "preferences": null} for new signups
- "remove": list of player names dropping out
- "guest_add": list of {"host": "SenderName", "guest_name": "HostName-Guest"} for guest additions
- "guest_remove": list of {"host": "SenderName", "guest_name": "name"} for guest removals"""

        user_prompt = f"""RECENT MESSAGES:
{messages_text}

Return ONLY valid JSON:
{{"add": [], "remove": [], "guest_add": [], "guest_remove": []}}"""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            result_text = response.content[0].text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.rstrip("`")
            delta = json.loads(result_text)

            has_changes = (delta.get('add') or delta.get('remove') or
                          delta.get('guest_add') or delta.get('guest_remove'))

            if has_changes:
                print(f"📝 Delta analysis found changes: +{len(delta.get('add', []))} players, -{len(delta.get('remove', []))} players, +{len(delta.get('guest_add', []))} guests, -{len(delta.get('guest_remove', []))} guests")
                return {'delta': delta}
            else:
                print("📋 Delta analysis: no new signups or dropouts in recent messages")
                return None

        except Exception as e:
            print(f"⚠️  Delta analysis error: {e}")
            return None


# ==================== ADMIN COMMAND HANDLER ====================
class AdminCommandHandler:
    """Handles admin commands with AI-powered understanding"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def parse_command(self, message: str, sender: str) -> Dict:
        """
        Parse admin command and extract intent

        Returns:
        {
            "command": "show_list" | "show_tee_sheet" | "unknown",
            "params": {},
            "response_needed": true/false
        }
        """

        admin_system = """Parse golf admin commands into JSON. Extract exact names/values as written.

Commands: show_list, show_tee_sheet, add_player(player_name), remove_player(player_name), add_guest(guest_name,host_name), remove_guest(guest_name), set_partner_preference(player_name,target_name), remove_partner_preference(player_name), set_avoidance(player_name,target_name), remove_avoidance(player_name), show_constraints, set_tee_times(start_time,interval_minutes,num_slots), show_tee_times, set_time_preference(player_name,time_preference=early|late), remove_time_preference(player_name), add_tee_time(tee_time), remove_tee_time(tee_time), clear_tee_times, clear_time_preferences, clear_tee_sheet, clear_participants, swap_players(player_name,target_name), move_player(player_name,group_number), randomize, unknown

swap_players: "swap X with Y", "switch X and Y" - swaps two players between their groups on the tee sheet
move_player: "move X to group 3", "put X in group 2", "move X to the 3 ball" - moves a single player from their current group to a specified group number
randomize: "randomize", "shuffle", "reshuffle", "new tee sheet", "regenerate" - creates a completely new random tee sheet"""

        admin_user_prompt = f"""COMMAND: "{message}"

Return ONLY JSON: {{"command":"show_list|show_tee_sheet|add_player|remove_player|add_guest|remove_guest|set_partner_preference|remove_partner_preference|set_avoidance|remove_avoidance|show_constraints|set_tee_times|show_tee_times|set_time_preference|remove_time_preference|add_tee_time|remove_tee_time|clear_tee_times|clear_time_preferences|clear_tee_sheet|clear_participants|swap_players|move_player|randomize|unknown","confidence":"high|medium|low","params":{{}},"needs_response":true}}"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=300,
                temperature=0.1,
                system=admin_system,
                messages=[{"role": "user", "content": admin_user_prompt}]
            )

            result_text = response.content[0].text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            return json.loads(result_text)

        except Exception as e:
            print(f"⚠️  Admin command parse error: {e}")
            return {
                "command": "unknown",
                "confidence": "low",
                "params": {},
                "needs_response": False
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
        except:
            print("❌ Not logged in - QR code scan needed")
            return False

        # Health check - verify Chrome is responsive before proceeding
        try:
            self.driver.execute_script("return document.readyState")
            print("✅ Chrome health check passed")
            return True
        except Exception as e:
            print(f"❌ Chrome health check failed: {e}")
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
    def sanitize_message(self, message: str) -> str:
        """Remove characters outside BMP that Chrome can't handle"""
        # Keep only characters in the Basic Multilingual Plane (U+0000 to U+FFFF)
        return ''.join(char for char in message if ord(char) <= 0xFFFF)

    def send_to_group(self, group_name: str, message: str):
        """Send message to a group"""
        try:
            # Sanitize message to remove problematic Unicode characters
            message = self.sanitize_message(message)
            time.sleep(2)

            # Search for group
            search_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
            )

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

            search_box.send_keys(group_name)
            time.sleep(3)

            # Find and click group
            group_spans = self.driver.find_elements(By.XPATH, f'//span[@title="{group_name}"]')
            if not group_spans:
                print(f"❌ Group '{group_name}' not found")
                return

            group_span = group_spans[0]
            parent = group_span.find_element(By.XPATH, './ancestor::div[5]')
            parent.click()
            time.sleep(2)

            # Send message
            msg_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
            )

            lines = message.strip().split('\n')
            for i, line in enumerate(lines):
                msg_box.send_keys(line)
                if i < len(lines) - 1:
                    msg_box.send_keys(Keys.SHIFT + Keys.ENTER)

            time.sleep(1)
            send_button = self.driver.find_element(By.XPATH, '//button[@aria-label="Send"]')
            send_button.click()

            print(f"✅ Message sent to group: {group_name}")
            time.sleep(2)

            self.driver.get('https://web.whatsapp.com')
            time.sleep(2)

        except Exception as e:
            print(f"❌ Error sending to group: {e}")
            try:
                self.driver.get('https://web.whatsapp.com')
                time.sleep(2)
            except:
                pass

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
            time.sleep(5)

            # Wait for messages to fully load in the DOM before scraping
            for _ in range(10):
                msg_count = len(self.driver.find_elements(By.CSS_SELECTOR, '.message-in, .message-out'))
                if msg_count >= 20:
                    break
                time.sleep(1)

            # Scroll up and accumulate messages (WhatsApp Web virtualises — unloads messages as you scroll)
            # We scroll up in steps, extracting messages at each position, until we find "taking names"
            STOP_PHRASES = ['taking names for sunday', 'names for sunday']
            MAX_SCROLL_ATTEMPTS = 50
            SCROLL_PIXELS = 3000

            def extract_message_from_element(elem):
                """Extract a single message dict from a DOM element."""
                try:
                    is_outgoing = 'message-out' in elem.get_attribute('class')
                    sender = "Unknown"
                    timestamp = ""

                    # Try to get data-pre-plain-text (contains timestamp + sender)
                    # Format: [HH:MM, DD/MM/YYYY] Name:
                    try:
                        copyable = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
                        pre_text = copyable.get_attribute('data-pre-plain-text') if copyable else None
                        if pre_text:
                            timestamp = pre_text
                    except:
                        pass

                    if not is_outgoing:
                        try:
                            spans = elem.find_elements(By.XPATH, './/span[@dir="auto"]')
                            if spans and len(spans) > 0:
                                sender_text = spans[0].text.strip()
                                if sender_text and ':' not in sender_text and len(sender_text) > 0:
                                    sender = sender_text
                        except:
                            pass

                        if sender == "Unknown" and timestamp and ']:' in timestamp:
                            try:
                                sender = timestamp.split(']')[1].strip().rstrip(':').strip()
                            except:
                                pass
                    else:
                        for admin in self.config.ADMIN_USERS:
                            if not admin.isdigit():
                                sender = admin
                                break
                        if sender == "Unknown":
                            sender = "You"

                    if sender != "Unknown":
                        sender = sender.replace('Maybe ', '').replace('maybe ', '')
                        sender = sender.replace('+44 ', '+44').strip()
                        if len(sender.strip()) < 1:
                            sender = "Unknown"

                    message_elem = elem.find_element(By.CSS_SELECTOR, '.copyable-text')
                    text = message_elem.text if message_elem else ""

                    if sender == "Unknown" and not is_outgoing and text:
                        lines = text.split('\n')
                        if len(lines) > 1:
                            first_line = lines[0].strip()
                            if len(first_line) < 50 and not first_line.endswith('?'):
                                sender = first_line
                                text = '\n'.join(lines[1:]).strip()

                    if sender in self.config.NAME_MAPPING:
                        sender = self.config.NAME_MAPPING[sender]

                    if text and text.strip():
                        return {
                            'sender': sender,
                            'text': text,
                            'is_outgoing': is_outgoing,
                            'timestamp': timestamp
                        }
                except:
                    pass
                return None

            # Find scroll container
            scroll_container = None
            try:
                first_msg = self.driver.find_element(By.CSS_SELECTOR, '.message-in, .message-out')
                scroll_container = self.driver.execute_script("""
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
                if not scroll_container:
                    scroll_container = self.driver.execute_script("""
                        let el = arguments[0];
                        while (el) {
                            if (el.scrollHeight > el.clientHeight && el.clientHeight > 200) {
                                return el;
                            }
                            el = el.parentElement;
                        }
                        return null;
                    """, first_msg)
            except:
                pass

            # Accumulate messages across scroll positions
            accumulated = {}  # key: (sender, text_first_80) -> message dict

            # Collect initial messages from current position
            for elem in self.driver.find_elements(By.CSS_SELECTOR, '.message-in, .message-out'):
                msg = extract_message_from_element(elem)
                if msg:
                    key = (msg['sender'], msg['text'][:80])
                    accumulated[key] = msg

            # Scroll up and collect until we find "taking names" or exhaust scrolling
            found_stop = False
            if scroll_container:
                no_new_count = 0
                for scroll_i in range(MAX_SCROLL_ATTEMPTS):
                    self.driver.execute_script(f"arguments[0].scrollBy(0, -{SCROLL_PIXELS});", scroll_container)
                    time.sleep(1.5)

                    new_count = 0
                    for elem in self.driver.find_elements(By.CSS_SELECTOR, '.message-in, .message-out'):
                        msg = extract_message_from_element(elem)
                        if msg:
                            key = (msg['sender'], msg['text'][:80])
                            if key not in accumulated:
                                accumulated[key] = msg
                                new_count += 1

                    # Check for stop phrase
                    for key, msg in accumulated.items():
                        text_lower = msg['text'].lower()
                        if any(phrase in text_lower for phrase in STOP_PHRASES):
                            found_stop = True
                            break

                    if found_stop:
                        print(f"   Scrolled {scroll_i+1}x — found 'taking names' message, accumulated {len(accumulated)} messages")
                        break

                    if new_count == 0:
                        no_new_count += 1
                        if no_new_count >= 3:
                            print(f"   Scrolled {scroll_i+1}x — reached top of history, accumulated {len(accumulated)} messages")
                            break
                    else:
                        no_new_count = 0

                if not found_stop and no_new_count < 3:
                    print(f"   Scrolled {MAX_SCROLL_ATTEMPTS}x (max), accumulated {len(accumulated)} messages")
            else:
                print(f"   ⚠️ No scroll container found, using {len(accumulated)} initial messages")

            # Convert accumulated dict to list, sorted by timestamp
            # data-pre-plain-text format: [HH:MM, DD/MM/YYYY] Name:
            def parse_sort_key(msg):
                ts = msg.get('timestamp', '')
                if ts and '[' in ts and ']' in ts:
                    try:
                        bracket_content = ts.split('[')[1].split(']')[0]  # "HH:MM, DD/MM/YYYY"
                        parts = bracket_content.split(', ')
                        if len(parts) == 2:
                            time_str = parts[0].strip()  # "HH:MM"
                            date_str = parts[1].strip()  # "DD/MM/YYYY"
                            # Convert to sortable format: YYYY/MM/DD HH:MM
                            date_parts = date_str.split('/')
                            if len(date_parts) == 3:
                                return f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]} {time_str}"
                    except:
                        pass
                return "9999/99/99 99:99"  # No timestamp — sort to end

            messages = sorted(accumulated.values(), key=parse_sort_key)[-Config.MAX_MESSAGES:]
            print(f"   📨 Total messages to analyse: {len(messages)}")

            return messages

        except Exception as e:
            print(f"❌ Error getting messages: {e}")
            return None

    def send_message(self, phone_number: str, message: str):
        """Send message to a phone number"""
        try:
            # Sanitize message to remove problematic Unicode characters
            message = self.sanitize_message(message)

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

    def _format_date_lines(self):
        """Format date lines for tee sheet: swindle date + generated timestamp"""
        now = datetime.now()
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 12:
            days_until_sunday = 0  # It's Sunday afternoon, swindle is today
        elif days_until_sunday == 0:
            days_until_sunday = 0  # It's Sunday morning, swindle is today
        sunday = now + timedelta(days=days_until_sunday)
        swindle_line = f"📅 Sunday {sunday.strftime('%d/%m/%Y')}"
        generated_line = f"⏰ Generated: {now.strftime('%a %d/%m at %H:%M')}"
        return f"{swindle_line}\n{generated_line}"

    def generate(self, participants: List[Dict], partner_prefs: Dict[str, List[str]] = None, avoidances: Dict[str, List[str]] = None, available_tee_times: List[str] = None) -> tuple:
        """
        Generate tee sheet from participants

        Args:
            participants: List of player dicts with name, guests, preferences
            partner_prefs: Dict of {player_name: [preferred_partners]}
            avoidances: Dict of {player_name: [players_to_avoid]}
            available_tee_times: List of available tee time strings (e.g., ["08:00", "08:08", ...])

        Returns:
            Tuple of (formatted_tee_sheet_string, tee_groups_list, assigned_times_dict)
        """
        partner_prefs = partner_prefs or {}
        avoidances = avoidances or {}
        available_tee_times = available_tee_times or self.config.TEE_TIMES

        # Make partner preferences bidirectional
        # If Lloyd→Segan is set, also create Segan→Lloyd so it works regardless of processing order
        bidirectional_prefs = {}
        for player, partners in partner_prefs.items():
            if player not in bidirectional_prefs:
                bidirectional_prefs[player] = []
            for p in partners:
                if p not in bidirectional_prefs[player]:
                    bidirectional_prefs[player].append(p)
                if p not in bidirectional_prefs:
                    bidirectional_prefs[p] = []
                if player not in bidirectional_prefs[p]:
                    bidirectional_prefs[p].append(player)
        partner_prefs = bidirectional_prefs

        # Build time preference map early (needed during grouping, not just time assignment)
        player_prefs_map = {}
        for p in participants:
            if p.get('preferences'):
                pref_text = p['preferences'].lower()
                if 'early' in pref_text:
                    player_prefs_map[p['name']] = 'early'
                elif 'late' in pref_text:
                    player_prefs_map[p['name']] = 'late'

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

        # Sort player_groups: players with partner preferences first (so they pair up
        # before other players fill the groups), then by group size descending (larger
        # blocks like host+guest are harder to place, so they go first)
        player_groups.sort(key=lambda g: (
            0 if g[0]['name'] in partner_prefs else 1,  # preferences first
            -len(g)  # larger blocks first
        ))

        # Distribute into tee time groups with constraint awareness
        # PRIORITY: Fill groups to MAX_GROUP_SIZE to minimize tee times
        tee_groups = []
        used_players = set()

        # Helper functions
        def has_avoidance(name1, name2):
            return (name2 in avoidances.get(name1, []) or
                   name1 in avoidances.get(name2, []))

        def get_player_names(group):
            return [p['name'] for p in group if not p.get('is_guest')]

        def can_add_to_group(player_group, tee_group):
            """Check if player_group can be added to tee_group"""
            host_name = player_group[0]['name']
            if len(tee_group) + len(player_group) > self.config.MAX_GROUP_SIZE:
                return False
            group_names = get_player_names(tee_group)
            return not any(has_avoidance(host_name, name) for name in group_names)

        # First pass: Build groups ONLY for players with partner preferences
        # Everyone else goes to pass 2 where time-preference-aware filling happens
        for player_group in player_groups:
            host_name = player_group[0]['name']
            if host_name in used_players:
                continue
            if host_name not in partner_prefs:
                continue  # Leave for pass 2

            current_group = player_group.copy()
            used_players.add(host_name)

            # Add preferred partners
            if host_name in partner_prefs:
                for pref_partner in partner_prefs[host_name]:
                    if pref_partner in used_players:
                        continue
                    partner_group = next((g for g in player_groups
                                        if g[0]['name'] == pref_partner), None)
                    if partner_group and can_add_to_group(partner_group, current_group):
                        current_group.extend(partner_group)
                        used_players.add(pref_partner)
                        if len(current_group) >= self.config.MAX_GROUP_SIZE:
                            break

            tee_groups.append(current_group)

        # Second pass: Fill existing groups before creating new ones
        # Process players with time preferences first so they can find matching groups
        # Shuffle neutral players for randomization (time-pref players stay ordered)
        remaining = [g for g in player_groups if g[0]['name'] not in used_players]
        pref_remaining = [g for g in remaining if player_prefs_map.get(g[0]['name'])]
        neutral_remaining = [g for g in remaining if not player_prefs_map.get(g[0]['name'])]
        pref_remaining.sort(key=lambda g: -len(g))
        random.shuffle(neutral_remaining)
        remaining = pref_remaining + neutral_remaining

        for player_group in remaining:
            host_name = player_group[0]['name']
            placed = False
            host_time_pref = player_prefs_map.get(host_name)

            # Sort target groups: prefer matching time preference, then smallest
            # Random tiebreaker so equal-priority groups get shuffled
            def group_fill_priority(tee_group):
                group_hosts = get_player_names(tee_group)
                if host_time_pref:
                    # Late/early player: prefer groups with matching preference
                    has_match = any(player_prefs_map.get(n) == host_time_pref for n in group_hosts)
                    return (0 if has_match else 1, len(tee_group), random.random())
                else:
                    # Neutral player: prefer groups WITHOUT time preferences
                    # (don't fill up a group that late/early players want to join)
                    has_any_pref = any(player_prefs_map.get(n) for n in group_hosts)
                    return (1 if has_any_pref else 0, len(tee_group), random.random())

            for tee_group in sorted(tee_groups, key=group_fill_priority):
                if can_add_to_group(player_group, tee_group):
                    tee_group.extend(player_group)
                    used_players.add(host_name)
                    placed = True
                    break

            if not placed:
                tee_groups.append(player_group.copy())
                used_players.add(host_name)

        # Third pass: Consolidate small groups to minimize tee times
        consolidated = True
        while consolidated:
            consolidated = False
            tee_groups.sort(key=len)

            for i in range(len(tee_groups)):
                if len(tee_groups[i]) >= self.config.MAX_GROUP_SIZE:
                    continue
                for j in range(i + 1, len(tee_groups)):
                    if len(tee_groups[i]) + len(tee_groups[j]) <= self.config.MAX_GROUP_SIZE:
                        g1_names = get_player_names(tee_groups[i])
                        g2_names = get_player_names(tee_groups[j])
                        has_conflict = any(has_avoidance(n1, n2)
                                         for n1 in g1_names for n2 in g2_names)
                        if not has_conflict:
                            tee_groups[i].extend(tee_groups[j])
                            tee_groups.pop(j)
                            consolidated = True
                            break
                if consolidated:
                    break

        # Fourth pass: Balance groups (avoid very small groups like 2 when we could have 3,3)
        # If we have a group of 2 and a group of 4, try to move a solo player to make 3,3
        improved = True
        while improved:
            improved = False
            tee_groups.sort(key=len)

            for i in range(len(tee_groups)):
                if len(tee_groups[i]) >= 3:  # Small groups are acceptable at 3+
                    break
                # Found a very small group (1 or 2 players)
                for j in range(len(tee_groups) - 1, i, -1):  # Check largest groups
                    if len(tee_groups[j]) <= 3:  # Don't take from groups of 3 or less
                        continue

                    # Try to move solo players (no guests) from group j to group i
                    space_needed = 3 - len(tee_groups[i])
                    gi_names = get_player_names(tee_groups[i])

                    for k in range(len(tee_groups[j]) - 1, -1, -1):
                        if space_needed == 0:
                            break
                        player = tee_groups[j][k]
                        if not player.get('is_host') or player.get('is_guest'):
                            continue  # Skip guests
                        # Skip hosts that have guests in this group (can't split block)
                        host_name = player['name']
                        has_guests = any(p.get('brought_by') == host_name for p in tee_groups[j])
                        if has_guests:
                            continue
                        # Check source group stays at 3+ after removal
                        if len(tee_groups[j]) - 1 < 3:
                            continue
                        # Check avoidances
                        if not any(has_avoidance(host_name, name) for name in gi_names):
                            tee_groups[i].append(tee_groups[j].pop(k))
                            space_needed -= 1
                            improved = True

                if improved:
                    break

        # Fifth pass: Force fit within available tee times
        # Tee times are pre-booked - we MUST fit within available slots, never TBC
        max_slots = len(available_tee_times)
        if len(tee_groups) > max_slots:
            # Helper: extract host+guest blocks from groups, merging preference-linked blocks
            def extract_blocks(groups):
                blks = []
                for grp in groups:
                    seen = set()
                    for player in grp:
                        if player.get('is_host') and player['name'] not in seen:
                            h_name = player['name']
                            blk = [p for p in grp if p['name'] == h_name or p.get('brought_by') == h_name]
                            blks.append(blk)
                            seen.add(h_name)

                # Merge blocks whose players have partner preferences with each other
                # so they stay together during repacking (e.g. Lloyd + Segan+Guest = one block)
                merged = True
                while merged:
                    merged = False
                    for i in range(len(blks)):
                        if merged:
                            break
                        for j in range(i + 1, len(blks)):
                            hosts_i = [p['name'] for p in blks[i] if not p.get('is_guest')]
                            hosts_j = [p['name'] for p in blks[j] if not p.get('is_guest')]
                            linked = any(
                                hj in partner_prefs.get(hi, [])
                                for hi in hosts_i for hj in hosts_j
                            )
                            if linked and len(blks[i]) + len(blks[j]) <= self.config.MAX_GROUP_SIZE:
                                blks[i].extend(blks[j])
                                blks.pop(j)
                                merged = True
                                break
                return blks

            # Helper: score how constraint-free a group is (higher = better to break apart)
            def group_freedom_score(group):
                score = 0
                for player in group:
                    if player.get('is_guest'):
                        continue
                    name = player['name']
                    if name not in partner_prefs:
                        score += 2
                    if name not in avoidances:
                        score += 2
                    # Solo player (no guests) = easier to redistribute
                    if not any(p.get('brought_by') == name for p in group):
                        score += 1
                    # No tee time preference
                    pref = next((pp.get('preferences', '') for pp in participants if pp['name'] == name), '')
                    if not pref:
                        score += 1
                return score

            # Phase 1: Decompose non-full groups into blocks
            full_groups = [g for g in tee_groups if len(g) >= self.config.MAX_GROUP_SIZE]
            non_full = [g for g in tee_groups if len(g) < self.config.MAX_GROUP_SIZE]
            blocks = extract_blocks(non_full)

            # Phase 2: If blocks don't fit in remaining slots, break constraint-free full groups
            target_new = max(0, max_slots - len(full_groups))
            total_block_players = sum(len(b) for b in blocks)
            max_capacity = target_new * self.config.MAX_GROUP_SIZE

            while (target_new <= 0 or total_block_players > max_capacity) and full_groups:
                # Find the most constraint-free full group to break apart
                best_idx = max(range(len(full_groups)), key=lambda i: group_freedom_score(full_groups[i]))
                victim = full_groups.pop(best_idx)
                blocks.extend(extract_blocks([victim]))
                target_new = max(0, max_slots - len(full_groups))
                total_block_players = sum(len(b) for b in blocks)
                max_capacity = target_new * self.config.MAX_GROUP_SIZE
                print(f"   🔄 Broke apart a {len(victim)}-ball to redistribute players")

            # Phase 3: Pack all blocks into target_new groups using best-fit
            if target_new > 0 and blocks:
                blocks.sort(key=len, reverse=True)
                new_groups = [[] for _ in range(target_new)]

                for block in blocks:
                    block_names = [p['name'] for p in block if not p.get('is_guest')]

                    # Best-fit: find group with LEAST remaining space that still fits this block
                    best_idx = None
                    best_space = float('inf')
                    for idx, ng in enumerate(new_groups):
                        space = self.config.MAX_GROUP_SIZE - len(ng)
                        if space >= len(block):
                            group_names = get_player_names(ng)
                            conflict = any(has_avoidance(bn, gn) for bn in block_names for gn in group_names)
                            if not conflict and space < best_space:
                                best_idx = idx
                                best_space = space

                    if best_idx is not None:
                        new_groups[best_idx].extend(block)
                    else:
                        # Avoidance constraints blocking - place anyway (capacity takes priority)
                        for idx, ng in enumerate(new_groups):
                            space = self.config.MAX_GROUP_SIZE - len(ng)
                            if space >= len(block):
                                new_groups[idx].extend(block)
                                print(f"⚠️  Placed {block[0]['name']} ignoring avoidance (must fit within tee times)")
                                break

                tee_groups = full_groups + [g for g in new_groups if g]
            elif not blocks and len(full_groups) <= max_slots:
                tee_groups = full_groups
            else:
                print(f"⚠️  Cannot fit all players into {max_slots} tee times - capacity exceeded")

        # Assign tee times based on preferences (player_prefs_map built earlier)
        # Categorize groups by preference
        early_groups = []
        late_groups = []
        neutral_groups = []

        for group in tee_groups:
            # Check if any player in group has preference
            has_early = any(player_prefs_map.get(p['name']) == 'early' for p in group if not p.get('is_guest'))
            has_late = any(player_prefs_map.get(p['name']) == 'late' for p in group if not p.get('is_guest'))

            if has_early and not has_late:
                early_groups.append(group)
            elif has_late and not has_early:
                late_groups.append(group)
            else:
                neutral_groups.append(group)

        # Within each category, sort smaller groups first (3-balls before 4-balls)
        early_groups.sort(key=len)
        neutral_groups.sort(key=len)
        late_groups.sort(key=len)

        # Assign tee times: early groups first, then neutral, then late groups
        assigned_times = {}
        time_idx = 0

        # Assign early groups to first available times
        for group in early_groups:
            if time_idx < len(available_tee_times):
                assigned_times[id(group)] = available_tee_times[time_idx]
                time_idx += 1

        # Assign neutral groups
        for group in neutral_groups:
            if time_idx < len(available_tee_times):
                assigned_times[id(group)] = available_tee_times[time_idx]
                time_idx += 1

        # Assign late groups to later times
        for group in late_groups:
            if time_idx < len(available_tee_times):
                assigned_times[id(group)] = available_tee_times[time_idx]
                time_idx += 1

        # Format tee sheet
        lines = [f"🏌️ *{self.config.GROUP_NAME.upper()} TEE SHEET* 🏌️\n"]
        lines.append(f"{self._format_date_lines()}\n")
        lines.append(f"👥 {total_players} players, {len(tee_groups)} groups\n")

        # Show tee time utilization - list which times can be returned
        used_slots = len(tee_groups)
        total_slots = len(available_tee_times)
        available_slots = total_slots - used_slots
        if available_slots > 0:
            # The returned times are the ones after the last used slot
            returned_times = available_tee_times[used_slots:]
            returned_str = ', '.join(returned_times)
            lines.append(f"✅ {available_slots} tee time(s) can be returned: {returned_str}\n")

        all_groups = early_groups + neutral_groups + late_groups

        for group in all_groups:
            tee_time = assigned_times.get(id(group), "TBC")
            group_num = all_groups.index(group) + 1
            lines.append(f"\n⏰ *Group {group_num} - {tee_time}*")
            for player in group:
                if player.get('is_guest'):
                    lines.append(f"  • {player['name']} (guest of {player['brought_by']})")
                else:
                    lines.append(f"  • {player['name']}")

        return '\n'.join(lines), all_groups, assigned_times

    def adjust_tee_sheet(self, published_sheet: Dict, current_participants: List[Dict], avoidances: Dict) -> str:
        """
        Minimally adjust a published tee sheet when players drop out or are added.
        Keeps everyone else in their same group and tee time.
        """
        groups = published_sheet['groups']

        # Build set of current player names (including guests)
        current_names = set()
        for p in current_participants:
            current_names.add(p['name'])
            for g in p.get('guests', []):
                current_names.add(g)

        # Build set of players in the published sheet
        published_names = set()
        for group in groups:
            for player in group['players']:
                published_names.add(player['name'])

        # Find who dropped out and who's new
        dropped = published_names - current_names
        new_players = current_names - published_names

        if not dropped and not new_players:
            # No changes - return original sheet
            return published_sheet.get('tee_sheet_text', ''), False, None

        # Remove dropped players from their groups
        for group in groups:
            group['players'] = [p for p in group['players'] if p['name'] not in dropped]
            # Also remove guests of dropped hosts
            group['players'] = [p for p in group['players']
                               if not (p.get('is_guest') and p.get('brought_by') in dropped)]

        # Remove empty groups
        groups = [g for g in groups if len(g['players']) > 0]

        # Handle groups that are now too small (< 3 players)
        small_groups = [g for g in groups if len(g['players']) < 3]
        ok_groups = [g for g in groups if len(g['players']) >= 3]

        # Try to merge small groups into adjacent groups that have space
        for small_group in small_groups:
            merged = False
            # Try groups with space, preferring groups at nearby tee times
            for target in sorted(ok_groups, key=lambda g: len(g['players'])):
                if len(target['players']) + len(small_group['players']) <= self.config.MAX_GROUP_SIZE:
                    # Check avoidance constraints
                    small_names = [p['name'] for p in small_group['players']]
                    target_names = [p['name'] for p in target['players']]
                    has_conflict = False
                    for n1 in small_names:
                        for n2 in target_names:
                            if n1 in avoidances and n2 in avoidances[n1]:
                                has_conflict = True
                            if n2 in avoidances and n1 in avoidances[n2]:
                                has_conflict = True
                    if not has_conflict:
                        target['players'].extend(small_group['players'])
                        merged = True
                        break

            if not merged:
                # Keep the small group as-is (better than moving lots of people)
                ok_groups.append(small_group)

        groups = ok_groups

        # Add new players to groups with space
        new_player_data = []
        for p in current_participants:
            if p['name'] in new_players:
                new_player_data.append({'name': p['name'], 'is_guest': False, 'brought_by': None})
                for g in p.get('guests', []):
                    if g in new_players:
                        new_player_data.append({'name': g, 'is_guest': True, 'brought_by': p['name']})

        for new_p in new_player_data:
            if new_p.get('is_guest'):
                continue  # Guests get added with their host
            placed = False
            # Try existing groups with space
            for group in sorted(groups, key=lambda g: len(g['players'])):
                if len(group['players']) < self.config.MAX_GROUP_SIZE:
                    # Check avoidances
                    group_names = [p['name'] for p in group['players']]
                    has_conflict = any(
                        (new_p['name'] in avoidances and n in avoidances[new_p['name']]) or
                        (n in avoidances and new_p['name'] in avoidances[n])
                        for n in group_names
                    )
                    if not has_conflict:
                        group['players'].append(new_p)
                        # Add their guests too
                        for gp in new_player_data:
                            if gp.get('brought_by') == new_p['name']:
                                group['players'].append(gp)
                        placed = True
                        break
            if not placed:
                # Create a new group at the end
                groups.append({
                    'tee_time': 'TBC',
                    'players': [new_p] + [gp for gp in new_player_data if gp.get('brought_by') == new_p['name']]
                })

        # Remove empty groups again
        groups = [g for g in groups if len(g['players']) > 0]

        # Count total players
        total_players = sum(len(g['players']) for g in groups)

        # Format the adjusted tee sheet
        changes = []
        if dropped:
            changes.append(f"Removed: {', '.join(dropped)}")
        if new_players:
            changes.append(f"Added: {', '.join(new_players)}")

        lines = [f"🏌️ *{self.config.GROUP_NAME.upper()} TEE SHEET (UPDATED)* 🏌️\n"]
        lines.append(f"{self._format_date_lines()}\n")
        lines.append(f"👥 {total_players} players, {len(groups)} groups\n")
        if changes:
            lines.append(f"🔄 Changes: {'; '.join(changes)}\n")

        for i, group in enumerate(groups):
            tee_time = group.get('tee_time', 'TBC')
            lines.append(f"\n⏰ *Group {i + 1} - {tee_time}*")
            for player in group['players']:
                if player.get('is_guest'):
                    lines.append(f"  • {player['name']} (guest of {player['brought_by']})")
                else:
                    lines.append(f"  • {player['name']}")

        return '\n'.join(lines), True, groups


# ==================== MAIN BOT ====================
class SwindleBot:
    """Main bot controller - simplified AI-native version"""

    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.DB_PATH)
        self.ai = AIAnalyzer(self.config.ANTHROPIC_API_KEY)
        self.admin_handler = AdminCommandHandler(self.config.ANTHROPIC_API_KEY)
        self.whatsapp = WhatsAppBot(self.config)
        self.tee_generator = TeeSheetGenerator(self.config)
        self.running = True
        self._admin_anchor = []  # Last 3 admin messages as fingerprint for new message detection

        # Blocklist of known bot response prefixes (after emoji/markdown stripping)
        # These are how bot responses look when WhatsApp strips formatting
        # Admin commands never start with these phrases
        self._bot_response_prefixes = [
            # Status messages
            "shanks", "admin interface ready", "bot shutting down", "bot restarting",
            "weekly reset", "sunday swindle", "randomized tee sheet",
            # Success responses (past tense - commands use present tense)
            "added ", "removed ", "cleared ", "swapped:", "moved:",
            "set preference", "set avoidance", "partner preference saved",
            # Error responses
            "error:", "failed ",
            # Warning/info responses
            "preference already", "preference not found",
            "avoidance already", "avoidance not found",
            "already in the participants", "already in group", "already exists",
            "not found on tee sheet", "not found",
            "no published tee sheet", "no participants", "no constraints set",
            "no settings configured",
            "need both", "need player", "need guest", "need tee time",
            "need two player", "need a player",
            "invalid group", "invalid interval",
            # Tee time responses
            "tee times configured", "tee time ",
            "manual tee times", "remaining times", "will now use",
            # Reserve notifications
            "reserve promoted", "moved to reserves", "moved from reserves",
            # Dynamic content markers
            "constraints", "tee times", "participants",
            "player", "guest",
        ]

    def _clean_for_compare(self, text: str) -> str:
        """Strip emojis, markdown, and special chars for comparison"""
        import re
        # Remove emojis and non-ASCII unicode
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        # Remove markdown formatting
        text = text.replace('*', '').replace('_', '')
        # Normalize whitespace and lowercase
        text = ' '.join(text.split()).strip().lower()
        return text

    def _is_bot_response(self, text: str) -> bool:
        """Check if a message looks like a bot response rather than an admin command"""
        # Multi-line or long messages are always bot responses
        if '\n' in text.strip() or len(text.strip()) > 150:
            return True
        # Messages starting with bot emoji prefixes are always bot responses
        # Admin commands are plain text, bot responses use emoji indicators
        stripped = text.strip()
        bot_emojis = ['✅', '❌', '⚠️', '🏌', '📅', '⏰', '👥', '📋', '⚙️', '🔄']
        if any(stripped.startswith(e) for e in bot_emojis):
            return True
        # Check cleaned text against blocklist
        cleaned = self._clean_for_compare(text)
        for prefix in self._bot_response_prefixes:
            if cleaned.startswith(prefix):
                return True
        return False

    def send_to_me(self, message: str):
        """Send message to yourself"""
        self.whatsapp.send_message(self.config.MY_NUMBER, message)

    def send_to_admin_group(self, message: str):
        """Send message to admin group"""
        self.whatsapp.send_to_group(self.config.ADMIN_GROUP_NAME, message)

    def _restart_bot(self):
        """Restart the bot by re-executing the current script"""
        import sys
        print("🔄 Restarting bot process...")
        try:
            self.whatsapp.driver.quit()
        except:
            pass
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def auto_adjust_published_sheet(self):
        """Auto-adjust published tee sheet if participants changed"""
        published = self.db.get_published_tee_sheet()
        if not published:
            return
        participants = self.db.get_participants(status_filter='playing')
        avoidances = self.db.get_avoidances()
        tee_sheet, had_changes, adjusted_groups = self.tee_generator.adjust_tee_sheet(
            published, participants, avoidances
        )
        if had_changes:
            self.db.save_published_tee_sheet(adjusted_groups, {}, tee_sheet)
            self.send_to_admin_group(f"📢 *Tee sheet auto-updated:*\n\n{tee_sheet}")
            print(f"   📢 Auto-adjusted published tee sheet")

    def handle_admin_command(self, command_text: str, sender: str):
        """Process and respond to admin command"""
        print(f"📱 Processing: '{command_text[:50]}...'")

        # Direct commands (no AI needed, restricted to first admin user)
        cmd_lower = command_text.strip().lower()
        primary_admin = self.config.ADMIN_USERS[0] if self.config.ADMIN_USERS else None
        if cmd_lower in ('shutdown', 'stop bot', 'kill bot') and sender == primary_admin:
            print("🛑 Shutdown command received")
            self.send_to_admin_group("🛑 Bot shutting down...")
            self.running = False
            return
        if cmd_lower in ('restart', 'restart bot', 'reboot') and sender == primary_admin:
            print("🔄 Restart command received")
            self.send_to_admin_group("🔄 Bot restarting...")
            self._restart_bot()
            return

        # Parse command with AI
        result = self.admin_handler.parse_command(command_text, sender)
        command = result.get('command', 'unknown')
        confidence = result.get('confidence', 'low')

        print(f"   → Detected: {command} (confidence: {confidence})")

        if command == 'show_list':
            self.refresh_main_group()
            participant_list = self.generate_participant_list()
            self.send_to_admin_group(participant_list)
            print(f"   ✅ Sent participant list")

        elif command == 'show_tee_sheet':
            self.refresh_main_group()
            participants = self.db.get_participants(status_filter='playing')
            published = self.db.get_published_tee_sheet()

            if published:
                # Published sheet exists - minimally adjust it
                avoidances = self.db.get_avoidances()
                tee_sheet, had_changes, adjusted_groups = self.tee_generator.adjust_tee_sheet(
                    published, participants, avoidances
                )
                if had_changes:
                    self.db.save_published_tee_sheet(adjusted_groups, {}, tee_sheet)
                    self.send_to_admin_group(tee_sheet)
                    print(f"   ✅ Sent adjusted tee sheet (minimal changes from published, saved)")
                else:
                    self.send_to_admin_group(published.get('tee_sheet_text', tee_sheet))
                    print(f"   ✅ Sent published tee sheet (no changes)")
            else:
                # No published sheet - generate fresh and save as published
                partner_prefs = self.db.get_partner_preferences()
                avoidances = self.db.get_avoidances()
                available_times = self.db.generate_tee_times()
                tee_sheet, groups, assigned_times = self.tee_generator.generate(
                    participants, partner_prefs, avoidances, available_times
                )
                self.db.save_published_tee_sheet(groups, assigned_times, tee_sheet)
                self.send_to_admin_group(tee_sheet)
                print(f"   ✅ Sent fresh tee sheet (saved as published)")

        elif command == 'add_player':
            # Manually add a player
            params = result.get('params', {})
            player_name = params.get('player_name')

            if not player_name:
                self.send_to_admin_group("❌ Error: Could not extract player name from command")
                print(f"   ❌ No player name found")
                return

            status = self.db.add_player_manually(player_name)
            if status == 'playing':
                participant_list = self.generate_participant_list()
                self.send_to_admin_group(f"✅ Added {player_name} (playing)\n\n{participant_list}")
                print(f"   ✅ Added player: {player_name} (playing)")
                self.auto_adjust_published_sheet()
            elif status == 'reserve':
                reserves = self.db.get_participants(status_filter='reserve')
                position = next((i+1 for i, r in enumerate(reserves) if r['name'] == player_name), len(reserves))
                participant_list = self.generate_participant_list()
                self.send_to_admin_group(f"✅ Added {player_name} to reserves (position {position})\n\n{participant_list}")
                print(f"   ✅ Added player: {player_name} (reserve position {position})")
            elif status == 'exists':
                self.send_to_admin_group(f"⚠️ {player_name} is already in the participants list")
                print(f"   ⚠️ Player already exists: {player_name}")
            else:
                self.send_to_admin_group(f"❌ Failed to add {player_name}")
                print(f"   ❌ Failed to add player")

        elif command == 'remove_player':
            # Manually remove a player
            params = result.get('params', {})
            player_name = params.get('player_name')

            if not player_name:
                self.send_to_admin_group("❌ Error: Could not extract player name from command")
                print(f"   ❌ No player name found")
                return

            result_info = self.db.remove_player_manually(player_name)
            if result_info.get('removed'):
                participant_list = self.generate_participant_list()
                msg = f"✅ Removed {player_name}"
                if result_info.get('promoted'):
                    promoted_names = ', '.join(result_info['promoted'])
                    msg += f"\n\n📢 Reserve promoted to playing: {promoted_names}"
                msg += f"\n\n{participant_list}"
                self.send_to_admin_group(msg)
                print(f"   ✅ Removed player: {player_name}")
                if result_info.get('promoted'):
                    print(f"   📢 Promoted from reserves: {result_info['promoted']}")
                self.auto_adjust_published_sheet()
            else:
                self.send_to_admin_group(f"❌ Player '{player_name}' not found")
                print(f"   ⚠️  Player not found: {player_name}")

        elif command == 'add_guest':
            # Manually add a guest
            params = result.get('params', {})
            guest_name = params.get('guest_name')
            host_name = params.get('host_name')

            if not guest_name or not host_name:
                self.send_to_admin_group("❌ Error: Need both guest name and host name")
                print(f"   ❌ Missing guest or host name")
                return

            result_info = self.db.add_guest_manually(host_name, guest_name)
            if result_info.get('success'):
                participant_list = self.generate_participant_list()
                msg = f"✅ Added {guest_name} as guest of {host_name}"
                if result_info.get('demoted'):
                    demoted_names = ', '.join(result_info['demoted'])
                    msg += f"\n\n⚠️ Moved to reserves (no space): {demoted_names}"
                msg += f"\n\n{participant_list}"
                self.send_to_admin_group(msg)
                print(f"   ✅ Added guest: {guest_name} for {host_name}")
                if result_info.get('demoted'):
                    print(f"   ⚠️ Demoted to reserves: {result_info['demoted']}")
                self.auto_adjust_published_sheet()
            else:
                self.send_to_admin_group(f"❌ Failed to add guest. Host '{host_name}' not found?")
                print(f"   ❌ Failed to add guest")

        elif command == 'remove_guest':
            # Manually remove a guest
            params = result.get('params', {})
            guest_name = params.get('guest_name')
            host_name = params.get('host_name')  # Optional

            if not guest_name:
                self.send_to_admin_group("❌ Error: Could not extract guest name from command")
                print(f"   ❌ No guest name found")
                return

            result_info = self.db.remove_guest_manually(guest_name, host_name)
            if result_info.get('success'):
                participant_list = self.generate_participant_list()
                host_text = f" from {host_name}" if host_name else ""
                msg = f"✅ Removed guest {guest_name}{host_text}"
                if result_info.get('promoted'):
                    promoted_names = ', '.join(result_info['promoted'])
                    msg += f"\n\n📢 Reserve promoted to playing: {promoted_names}"
                msg += f"\n\n{participant_list}"
                self.send_to_admin_group(msg)
                print(f"   ✅ Removed guest: {guest_name}")
                if result_info.get('promoted'):
                    print(f"   📢 Promoted from reserves: {result_info['promoted']}")
                self.auto_adjust_published_sheet()
            else:
                self.send_to_admin_group(f"❌ Guest '{guest_name}' not found")
                print(f"   ⚠️  Guest not found: {guest_name}")

        elif command == 'set_partner_preference':
            # Set partner preference
            params = result.get('params', {})
            player_name = params.get('player_name')
            target_name = params.get('target_name')

            if not player_name or not target_name:
                self.send_to_admin_group("❌ Error: Need both player and partner names")
                print(f"   ❌ Missing player or partner name")
                return

            success = self.db.add_constraint('partner_preference', player_name, target_name)
            if success:
                self.send_to_admin_group(f"✅ Set preference: {player_name} plays with {target_name}")
                print(f"   ✅ Added partner preference: {player_name} -> {target_name}")
            else:
                self.send_to_admin_group(f"⚠️  Preference already exists")
                print(f"   ⚠️  Preference already exists")

        elif command == 'remove_partner_preference':
            # Remove partner preference
            params = result.get('params', {})
            player_name = params.get('player_name')
            target_name = params.get('target_name')

            if not player_name:
                self.send_to_admin_group("❌ Error: Need player name")
                print(f"   ❌ Missing player name")
                return

            # Try removing season-long preference first, then weekly pairing
            success = self.db.remove_constraint('partner_preference', player_name, target_name)
            if not success:
                success = self.db.remove_constraint('weekly_pairing', player_name, target_name)
            if success:
                target_text = f" with {target_name}" if target_name else ""
                self.send_to_admin_group(f"✅ Removed preference for {player_name}{target_text}")
                print(f"   ✅ Removed partner preference")
            else:
                self.send_to_admin_group(f"❌ Preference not found")
                print(f"   ⚠️  Preference not found")

        elif command == 'set_avoidance':
            # Set avoidance
            params = result.get('params', {})
            player_name = params.get('player_name')
            target_name = params.get('target_name')

            if not player_name or not target_name:
                self.send_to_admin_group("❌ Error: Need both player names")
                print(f"   �� Missing player or target name")
                return

            success = self.db.add_constraint('avoid', player_name, target_name)
            if success:
                self.send_to_admin_group(f"✅ Set avoidance: {player_name} avoids {target_name}")
                print(f"   ✅ Added avoidance: {player_name} -> {target_name}")
            else:
                self.send_to_admin_group(f"⚠️  Avoidance already exists")
                print(f"   ⚠️  Avoidance already exists")

        elif command == 'remove_avoidance':
            # Remove avoidance
            params = result.get('params', {})
            player_name = params.get('player_name')
            target_name = params.get('target_name')

            if not player_name:
                self.send_to_admin_group("❌ Error: Need player name")
                print(f"   ❌ Missing player name")
                return

            success = self.db.remove_constraint('avoid', player_name, target_name)
            if success:
                target_text = f" with {target_name}" if target_name else ""
                self.send_to_admin_group(f"✅ Removed avoidance for {player_name}{target_text}")
                print(f"   ✅ Removed avoidance")
            else:
                self.send_to_admin_group(f"❌ Avoidance not found")
                print(f"   ⚠️  Avoidance not found")

        elif command == 'show_constraints':
            # Show all constraints with active/inactive status
            constraints = self.db.get_constraints()

            # Get current participant names and time preferences
            participants = self.db.get_participants()
            signed_up = set()
            time_prefs = []
            for p in participants:
                signed_up.add(p['name'].lower())
                for g in p.get('guests', []):
                    signed_up.add(g.lower())
                if p.get('preferences'):
                    pref_text = p['preferences'].lower()
                    if 'early' in pref_text:
                        time_prefs.append((p['name'], 'early'))
                    elif 'late' in pref_text:
                        time_prefs.append((p['name'], 'late'))

            if not constraints and not time_prefs:
                self.send_to_admin_group("📋 *Constraints*\n\nNo constraints set")
                print(f"   ℹ️  No constraints")
                return

            def player_status(player, target):
                p_in = player.lower() in signed_up
                t_in = target.lower() in signed_up if target else False
                if p_in and t_in:
                    return "✅"
                elif p_in or t_in:
                    who = target if p_in else player
                    return f"⚠️ {who} not signed up"
                else:
                    return "💤 neither signed up"

            # Group by type
            partner_prefs = [c for c in constraints if c['type'] == 'partner_preference']
            weekly_pairings = [c for c in constraints if c['type'] == 'weekly_pairing']
            avoidances = [c for c in constraints if c['type'] == 'avoid']

            lines = ["📋 *Constraints*\n"]

            if partner_prefs:
                lines.append("🤝 *Partner Preferences (season-long):*")
                for c in partner_prefs:
                    status = player_status(c['player'], c['target'])
                    lines.append(f"  • {c['player']} plays with {c['target']}  {status}")
                lines.append("")

            if weekly_pairings:
                lines.append("🏌️ *MP Pairings (this week):*")
                for c in weekly_pairings:
                    status = player_status(c['player'], c['target'])
                    lines.append(f"  • {c['player']} ↔ {c['target']}  {status}")
                lines.append("")

            if avoidances:
                lines.append("⚠️  *Avoidances:*")
                for c in avoidances:
                    status = player_status(c['player'], c['target'])
                    lines.append(f"  • {c['player']} avoids {c['target']}  {status}")
                lines.append("")

            if time_prefs:
                lines.append("⏰ *Time Preferences:*")
                for name, pref in time_prefs:
                    lines.append(f"  • {name}: {pref}")

            self.send_to_admin_group('\n'.join(lines))
            print(f"   ✅ Sent constraints list ({len(constraints)} constraints, {len(time_prefs)} time prefs)")

        elif command == 'set_tee_times':
            # Configure tee time settings
            params = result.get('params', {})
            start_time = params.get('start_time')
            interval = params.get('interval_minutes')
            num_slots = params.get('num_slots')

            # Try to parse parameters or use defaults
            if not start_time:
                start_time = "08:00"  # Default
            if not interval:
                interval = 8  # Default 8 minutes
            if not num_slots:
                num_slots = 10  # Default 10 slots

            try:
                interval = int(interval)
                num_slots = int(num_slots)
            except:
                self.send_to_admin_group("❌ Error: Invalid interval or num_slots")
                print(f"   ❌ Invalid parameters")
                return

            success = self.db.set_tee_time_settings(start_time, interval, num_slots)
            if success:
                times = self.db.generate_tee_times()
                times_preview = ', '.join(times[:5]) + (f"... (+{len(times)-5} more)" if len(times) > 5 else "")
                # Capacity changed - recalculate statuses
                changes = self.db.recalculate_statuses()
                msg = (
                    f"✅ Tee times configured\n\n"
                    f"Start: {start_time}\n"
                    f"Interval: {interval} minutes\n"
                    f"Slots: {num_slots}\n\n"
                    f"Times: {times_preview}"
                )
                if changes.get('promoted'):
                    msg += f"\n\n📢 Reserve promoted to playing: {', '.join(changes['promoted'])}"
                if changes.get('demoted'):
                    msg += f"\n\n⚠️ Moved to reserves (no space): {', '.join(changes['demoted'])}"
                self.send_to_admin_group(msg)
                print(f"   ✅ Set tee times: {start_time}, {interval}min, {num_slots} slots")
            else:
                self.send_to_admin_group("❌ Failed to set tee times")
                print(f"   ❌ Failed to set tee times")

        elif command == 'show_tee_times':
            # Show current tee time settings with breakdown
            settings = self.db.get_tee_time_settings()
            if not settings:
                self.send_to_admin_group("📋 *Tee Times*\n\nNo settings configured")
                print(f"   ℹ️  No tee time settings")
                return

            # Get all times
            final_times = self.db.generate_tee_times()
            added_times = self.db.get_manual_tee_times()
            removed_times = self.db.get_removed_tee_times()

            # Build message
            message = f"📋 *Tee Time Settings*\n\n"
            message += f"⚙️ *Auto-Generation:*\n"
            message += f"  Start: {settings['start_time']}\n"
            message += f"  Interval: {settings['interval_minutes']} minutes\n"
            message += f"  Slots: {settings['num_slots']}\n\n"

            if added_times:
                added_list = ', '.join(added_times)
                message += f"➕ *Added:* {added_list}\n\n"

            if removed_times:
                removed_list = ', '.join(removed_times)
                message += f"➖ *Removed:* {removed_list}\n\n"

            times_list = '\n'.join(f"  • {t}" for t in final_times)
            message += f"✅ *Final Times ({len(final_times)}):*\n{times_list}\n\n"
            message += f"💡 'add/remove tee time HH:MM' or 'clear tee times'"

            self.send_to_admin_group(message)
            print(f"   ✅ Sent tee time breakdown")

        elif command == 'set_time_preference':
            # Set player time preference
            params = result.get('params', {})
            player_name = params.get('player_name')
            time_pref = params.get('time_preference', '').lower()

            if not player_name or not time_pref:
                self.send_to_admin_group("❌ Error: Need player name and preference (early/late)")
                print(f"   ❌ Missing parameters")
                return

            if time_pref not in ['early', 'late']:
                time_pref = 'early' if 'early' in time_pref or 'morning' in time_pref else 'late'

            # Update player's preferences
            participants = self.db.get_participants()
            player_found = False
            for p in participants:
                if p['name'] == player_name:
                    player_found = True
                    current_pref = p.get('preferences') or ''
                    # Remove old time preferences, add new one
                    new_pref = ' '.join([word for word in current_pref.split() if word.lower() not in ['early', 'late']])
                    new_pref = f"{new_pref} {time_pref}".strip()

                    # Save to database
                    conn = sqlite3.connect(self.db.db_path, timeout=10)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE participants SET preferences = ? WHERE name = ?", (new_pref, player_name))
                    conn.commit()
                    conn.close()

                    self.send_to_admin_group(f"✅ Set {player_name} preference to: {time_pref} tee time")
                    print(f"   ✅ Set {player_name} to {time_pref}")
                    break

            if not player_found:
                self.send_to_admin_group(f"❌ Player '{player_name}' not found")
                print(f"   ⚠️  Player not found")

        elif command == 'remove_time_preference':
            # Remove a single player's time preference (early/late)
            params = result.get('params', {})
            player_name = params.get('player_name')

            if not player_name:
                self.send_to_admin_group("❌ Error: Need player name")
                print(f"   ❌ Missing player name")
                return

            participants = self.db.get_participants()
            player_found = False
            for p in participants:
                if p['name'] == player_name:
                    player_found = True
                    current_pref = p.get('preferences') or ''
                    cleaned = ' '.join([w for w in current_pref.split() if w.lower() not in ['early', 'late']])

                    conn = sqlite3.connect(self.db.db_path, timeout=10)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE participants SET preferences = ? WHERE name = ?",
                                 (cleaned.strip() or None, player_name))
                    conn.commit()
                    conn.close()

                    self.send_to_admin_group(f"✅ Removed time preference for {player_name}")
                    print(f"   ✅ Removed time preference for {player_name}")
                    break

            if not player_found:
                self.send_to_admin_group(f"❌ Player '{player_name}' not found")
                print(f"   ⚠️  Player not found")

        elif command == 'add_tee_time':
            # Add a single tee time
            params = result.get('params', {})
            tee_time = params.get('tee_time')

            if not tee_time:
                self.send_to_admin_group("❌ Error: Need tee time in HH:MM format")
                print(f"   ❌ Missing tee time")
                return

            # Validate format (HH:MM)
            import re
            if not re.match(r'^\d{1,2}:\d{2}$', tee_time):
                self.send_to_admin_group("❌ Error: Tee time must be in HH:MM format (e.g., 08:24)")
                print(f"   ❌ Invalid format")
                return

            # Add to database
            success = self.db.add_manual_tee_time(tee_time)
            if success:
                manual_times = self.db.get_manual_tee_times()
                times_str = ', '.join(manual_times)
                # Capacity increased - recalculate (may promote reserves)
                changes = self.db.recalculate_statuses()
                msg = f"✅ Added tee time: {tee_time}\n\n📋 Manual tee times:\n{times_str}"
                if changes.get('promoted'):
                    msg += f"\n\n📢 Reserve promoted to playing: {', '.join(changes['promoted'])}"
                self.send_to_admin_group(msg)
                print(f"   ✅ Added tee time: {tee_time}")
            else:
                self.send_to_admin_group(f"⚠️  Tee time {tee_time} already exists")
                print(f"   ⚠️  Already exists")

        elif command == 'remove_tee_time':
            # Remove a single tee time
            params = result.get('params', {})
            tee_time = params.get('tee_time')

            if not tee_time:
                self.send_to_admin_group("❌ Error: Need tee time to remove")
                print(f"   ❌ Missing tee time")
                return

            # Remove from database
            success = self.db.remove_manual_tee_time(tee_time)
            if success:
                manual_times = self.db.get_manual_tee_times()
                # Capacity decreased - recalculate (may demote to reserves)
                changes = self.db.recalculate_statuses()
                if manual_times:
                    times_str = ', '.join(manual_times)
                    msg = f"✅ Removed tee time: {tee_time}\n\n📋 Remaining times:\n{times_str}"
                else:
                    msg = f"✅ Removed tee time: {tee_time}\n\n⏰ No manual times left - will use auto-generated times"
                if changes.get('demoted'):
                    msg += f"\n\n⚠️ Moved to reserves (no space): {', '.join(changes['demoted'])}"
                self.send_to_admin_group(msg)
                print(f"   ✅ Removed tee time: {tee_time}")
            else:
                self.send_to_admin_group(f"⚠️  Tee time {tee_time} not found")
                print(f"   ⚠️  Not found")

        elif command == 'clear_tee_times':
            # Clear all manual tee times
            self.db.clear_manual_tee_times()
            # Capacity changed - recalculate
            changes = self.db.recalculate_statuses()
            msg = "✅ Cleared all manual tee times\n\n⏰ Will now use auto-generated times from settings"
            if changes.get('promoted'):
                msg += f"\n\n📢 Reserve promoted to playing: {', '.join(changes['promoted'])}"
            if changes.get('demoted'):
                msg += f"\n\n⚠️ Moved to reserves (no space): {', '.join(changes['demoted'])}"
            self.send_to_admin_group(msg)
            print(f"   ✅ Cleared manual tee times")

        elif command == 'clear_time_preferences':
            # Clear time preferences for new week (keeps partner preferences)
            self.db.clear_time_preferences()
            participants = self.db.get_participants()
            self.send_to_admin_group(
                f"✅ Cleared time preferences for all players\n\n"
                f"📋 {len(participants)} participants still registered\n"
                f"🤝 Partner preferences remain active\n\n"
                f"💡 Time preferences reset for new week"
            )
            print(f"   ✅ Cleared time preferences (kept {len(participants)} participants)")

        elif command == 'clear_tee_sheet':
            # Clear the published tee sheet
            published = self.db.get_published_tee_sheet()
            if published:
                self.db.clear_published_tee_sheet()
                self.send_to_admin_group("✅ Published tee sheet cleared. Use 'Show tee sheet' or 'Randomize' to generate a new one.")
                print(f"   ✅ Cleared published tee sheet")
            else:
                self.send_to_admin_group("ℹ️ No published tee sheet to clear")
                print(f"   ℹ️ No published tee sheet to clear")

        elif command == 'clear_participants':
            # Clear all participants and snapshot - forces fresh re-scan from main group
            participants = self.db.get_participants()
            count = len(participants)
            self.db.clear_participants()
            self.send_to_admin_group(
                f"✅ Cleared {count} participants and message snapshot\n\n"
                f"The bot will re-scan the main group on the next check and rebuild the list from scratch."
            )
            print(f"   ✅ Cleared {count} participants and snapshot")

        elif command == 'swap_players':
            # Swap two players between groups on the published tee sheet
            params = result.get('params', {})
            player1 = params.get('player_name')
            player2 = params.get('target_name')

            if not player1 or not player2:
                self.send_to_admin_group("❌ Error: Need two player names to swap")
                print(f"   ❌ Missing player names")
                return

            published = self.db.get_published_tee_sheet()
            if not published:
                self.send_to_admin_group("❌ No published tee sheet to swap on. Use 'Show tee sheet' first to generate one.")
                print(f"   ❌ No published sheet")
                return

            groups = published['groups']
            p1_group = p2_group = p1_idx = p2_idx = None

            for gi, group in enumerate(groups):
                players = group.get('players', [])
                for pi, player in enumerate(players):
                    name = player.get('name', '')
                    if name.lower() == player1.lower():
                        p1_group, p1_idx = gi, pi
                    elif name.lower() == player2.lower():
                        p2_group, p2_idx = gi, pi

            if p1_group is None:
                self.send_to_admin_group(f"❌ {player1} not found on tee sheet")
                return
            if p2_group is None:
                self.send_to_admin_group(f"❌ {player2} not found on tee sheet")
                return
            if p1_group == p2_group:
                self.send_to_admin_group(f"⚠️ {player1} and {player2} are already in the same group")
                return

            # Swap them
            groups[p1_group]['players'][p1_idx], groups[p2_group]['players'][p2_idx] = \
                groups[p2_group]['players'][p2_idx], groups[p1_group]['players'][p1_idx]

            # Rebuild tee sheet text
            total_players = sum(len(g.get('players', [])) for g in groups)
            lines = [f"🏌️ *{self.config.GROUP_NAME.upper()} TEE SHEET (SWAPPED)* 🏌️\n"]
            lines.append(f"{self.tee_generator._format_date_lines()}\n")
            lines.append(f"👥 {total_players} players, {len(groups)} groups\n")
            lines.append(f"🔄 Swapped: {player1} ↔ {player2}\n")

            for i, group in enumerate(groups):
                tee_time = group.get('tee_time', 'TBC')
                lines.append(f"\n⏰ *Group {i + 1} - {tee_time}*")
                for player in group.get('players', []):
                    if player.get('is_guest'):
                        lines.append(f"  • {player['name']} (guest of {player.get('brought_by', '?')})")
                    else:
                        lines.append(f"  • {player['name']}")

            tee_sheet_text = '\n'.join(lines)
            # Save updated published sheet
            assigned_times = {i: g.get('tee_time', 'TBC') for i, g in enumerate(groups)}
            self.db.save_published_tee_sheet(groups, assigned_times, tee_sheet_text)
            self.send_to_admin_group(tee_sheet_text)
            print(f"   ✅ Swapped {player1} ↔ {player2}")

        elif command == 'move_player':
            # Move a single player to a different group on the published tee sheet
            params = result.get('params', {})
            player_name = params.get('player_name')
            target_group = params.get('group_number')

            if not player_name or target_group is None:
                self.send_to_admin_group("❌ Error: Need a player name and group number (e.g. 'Move Chris to group 3')")
                print(f"   ❌ Missing player name or group number")
                return

            try:
                target_group = int(target_group)
            except (ValueError, TypeError):
                self.send_to_admin_group(f"❌ Invalid group number: {target_group}")
                return

            published = self.db.get_published_tee_sheet()
            if not published:
                self.send_to_admin_group("❌ No published tee sheet. Use 'Show tee sheet' first to generate one.")
                print(f"   ❌ No published sheet")
                return

            groups = published['groups']

            if target_group < 1 or target_group > len(groups):
                self.send_to_admin_group(f"❌ Group {target_group} doesn't exist. There are {len(groups)} groups.")
                return

            # Find the player
            src_group = src_idx = None
            for gi, group in enumerate(groups):
                for pi, player in enumerate(group.get('players', [])):
                    if player.get('name', '').lower() == player_name.lower():
                        src_group, src_idx = gi, pi
                        break

            if src_group is None:
                self.send_to_admin_group(f"❌ {player_name} not found on tee sheet")
                return

            target_gi = target_group - 1  # Convert to 0-indexed
            if src_group == target_gi:
                self.send_to_admin_group(f"⚠️ {player_name} is already in group {target_group}")
                return

            # Move the player
            player_data = groups[src_group]['players'].pop(src_idx)
            groups[target_gi]['players'].append(player_data)

            src_size = len(groups[src_group]['players'])
            dst_size = len(groups[target_gi]['players'])

            # Rebuild tee sheet text
            total_players = sum(len(g.get('players', [])) for g in groups)
            lines = [f"🏌️ *{self.config.GROUP_NAME.upper()} TEE SHEET (UPDATED)* 🏌️\n"]
            lines.append(f"{self.tee_generator._format_date_lines()}\n")
            lines.append(f"👥 {total_players} players, {len(groups)} groups\n")
            lines.append(f"➡️ Moved: {player_name} → Group {target_group}\n")

            for i, group in enumerate(groups):
                tee_time = group.get('tee_time', 'TBC')
                lines.append(f"\n⏰ *Group {i + 1} - {tee_time}*")
                for player in group.get('players', []):
                    if player.get('is_guest'):
                        lines.append(f"  • {player['name']} (guest of {player.get('brought_by', '?')})")
                    else:
                        lines.append(f"  • {player['name']}")

            tee_sheet_text = '\n'.join(lines)
            assigned_times = {i: g.get('tee_time', 'TBC') for i, g in enumerate(groups)}
            self.db.save_published_tee_sheet(groups, assigned_times, tee_sheet_text)
            self.send_to_admin_group(tee_sheet_text)
            print(f"   ✅ Moved {player_name} to group {target_group} (group {src_group+1}: {src_size} players, group {target_group}: {dst_size} players)")

        elif command == 'randomize':
            # Randomize the tee sheet (full fresh generation) - playing only, no reserves
            participants = self.db.get_participants(status_filter='playing')
            if not participants:
                self.send_to_admin_group("❌ No participants to generate tee sheet for")
                return
            partner_prefs = self.db.get_partner_preferences()
            avoidances = self.db.get_avoidances()
            available_times = self.db.generate_tee_times()
            tee_sheet, groups, assigned_times = self.tee_generator.generate(
                participants, partner_prefs, avoidances, available_times
            )
            # Save as the new published sheet
            self.db.save_published_tee_sheet(groups, assigned_times, tee_sheet)
            self.send_to_admin_group(f"🔀 *RANDOMIZED TEE SHEET*\n\n{tee_sheet}")
            print(f"   ✅ Randomized and published new tee sheet")

        elif command == 'unknown':
            # Unknown command - just log it, don't respond
            print(f"   ⚠️  Not a recognized command, ignoring")

        else:
            # Command recognized but not implemented yet
            print(f"   ⚠️  Command '{command}' not implemented yet")

    def _format_player_line(self, p: Dict) -> str:
        """Format a single player line with guests and preferences"""
        guests = p.get('guests', [])
        guest_text = f" (bringing: {', '.join(guests)})" if guests else ""
        pref_text = f" - {p['preferences']}" if p.get('preferences') else ""
        return f"{p['name']}{guest_text}{pref_text}"

    def generate_participant_list(self) -> str:
        """Generate formatted participant list with capacity and reserves"""
        playing = self.db.get_participants(status_filter='playing')
        reserves = self.db.get_participants(status_filter='reserve')
        capacity = self.db.get_capacity()

        if not playing and not reserves:
            return f'🏌️ *Shanks Bot Update*\n\nNo names in yet - it\'s looking quiet out there!'

        playing_spots = sum(1 + len(p.get('guests', [])) for p in playing)
        reserve_spots = sum(1 + len(p.get('guests', [])) for p in reserves)

        lines = [f'🏌️ *Shanks Bot Update*\n']

        # Capacity line
        spaces_left = capacity - playing_spots
        if spaces_left > 0:
            lines.append(f'👥 {playing_spots}/{capacity} spots filled ({spaces_left} spaces left)\n')
        else:
            lines.append(f'👥 {playing_spots}/{capacity} spots filled - *FULL*\n')

        # Playing list
        for p in playing:
            lines.append(f"• {self._format_player_line(p)}")

        # Reserves section
        if reserves:
            lines.append(f"\n📋 *Reserves* ({len(reserves)}):")
            for i, p in enumerate(reserves, 1):
                lines.append(f"{i}. {self._format_player_line(p)}")
            lines.append(f"\nIf someone drops out, reserves move up automatically!")
        else:
            lines.append(f"\nIf you're playing and not on the list, give us a shout!")

        return '\n'.join(lines)

    def clear_weekly_data(self):
        """Clear data for new week (Monday 00:01)"""
        print("⏰ Clearing data for new week...")
        self.db.clear_participants()
        self.db.clear_time_preferences()
        self.db.clear_manual_tee_times()
        self.db.clear_published_tee_sheet()
        self.db.clear_weekly_pairings()
        print("✅ Weekly reset complete:")
        print("   - Participants cleared")
        print("   - Time preferences cleared (early/late)")
        print("   - Manual tee time modifications cleared")
        print("   - Published tee sheet cleared")
        print("   - MP/weekly pairings cleared")
        print("   - Partner preferences kept (season-long)")
        print("   - Tee time settings kept (season-long)")

        # Send notification to admin group
        message = "🏌️ *Shanks Bot - New Week!*\n\nSlate wiped clean, ready for a fresh one.\n\n✅ *Cleared:*\n- Participants\n- Time preferences\n- Tee time modifications\n- Published tee sheet\n- MP pairings\n\n🔒 *Kept:*\n- Partner preferences\n- Tee time settings"
        self.send_to_admin_group(message)

    def send_weekly_opening(self):
        """Send Monday morning message - ready to take tee times for Sunday"""
        print("⏰ Sending weekly opening message...")
        sunday = datetime.now() + timedelta(days=6)
        message = (
            f"🏌️ *Shanks Bot here!* Now taking names for Sunday {sunday.strftime('%d/%m/%Y')}. Drop your name in the group if you're playing!\n\n"
            f"Quick one - please make sure your WhatsApp display name is your *full name* so I can find you!\n"
            f"_Settings > tap your name > edit_"
        )
        self.send_to_admin_group(message)

    def send_health_check(self):
        """Send health check to admin group"""
        print("⏰ Sending health check...")
        now = datetime.now()
        message = f"🏌️ *Shanks Bot* is alive and well! Still on the job.\n_{now.strftime('%d/%m/%Y %H:%M')}_"
        self.send_to_admin_group(message)

    def send_startup_message(self):
        """Send startup message to admin group"""
        print("📤 Sending startup message...")
        now = datetime.now()

        # Also notify admin group
        commands = [
            "Show list",
            "Show tee sheet",
            "Show constraints",
            "Show tee times",
            "Add [Name]",
            "Remove [Name]",
            "[Name] plays with [Name]",
            "Remove [Name]'s preference",
            "Don't pair [Name] with [Name]",
            "[Name] prefers early/late",
            "Swap [Name] with [Name]",
            "Move [Name] to group [N]",
            "Set tee times from [HH:MM]",
            "Add tee time [HH:MM]",
            "Remove tee time [HH:MM]",
            "Clear tee times",
            "Clear tee sheet",
            "Clear time preferences",
            "Clear participants",
            "Randomize"
        ]
        admin_msg = f"🏌️ *Shanks Bot is online!* Ready to go at {now.strftime('%H:%M')}.\n\n*Commands:*\n" + "\n".join(f"  - {cmd}" for cmd in commands)
        self.send_to_admin_group(admin_msg)

    def _find_new_admin_messages(self, current_messages: list) -> list:
        """Find new admin messages by matching the anchor sequence (last 3 messages from previous check).
        Uses a sequence of messages as fingerprint so duplicate commands are handled correctly."""
        if not self._admin_anchor:
            return []  # First run after init, nothing is new

        anchor_len = len(self._admin_anchor)

        # Search backwards through current messages to find where the anchor sequence appears
        for i in range(len(current_messages) - anchor_len, -1, -1):
            window = [(m['sender'], m['text']) for m in current_messages[i:i + anchor_len]]
            if window == self._admin_anchor:
                # Found the anchor - everything after it is new
                return current_messages[i + anchor_len:]

        # Anchor not found (messages shifted too much) - skip this cycle to be safe
        print(f"   ⚠️  Admin anchor not found in {len(current_messages)} messages - resetting")
        return []

    def _snapshot_matches(self, messages, last_snapshot) -> bool:
        """Compare messages to snapshot, ignoring order (DOM order can vary between loads)"""
        if not last_snapshot:
            return False
        sorted_new = sorted(messages, key=lambda m: (m.get('sender', ''), m.get('text', '')))
        sorted_old = sorted(last_snapshot, key=lambda m: (m.get('sender', ''), m.get('text', '')))
        return json.dumps(sorted_new) == json.dumps(sorted_old)

    def _apply_delta(self, delta: Dict):
        """Apply delta changes (add/remove players/guests) on top of existing DB data - silently"""
        for player in delta.get('add', []):
            name = player.get('name')
            if name:
                status = self.db.add_player_manually(name, player.get('guests'), player.get('preferences'))
                if status in ('playing', 'reserve'):
                    print(f"   ➕ Delta: added {name} ({status})")

        for name in delta.get('remove', []):
            if name:
                result = self.db.remove_player_manually(name)
                if result.get('removed'):
                    print(f"   ➖ Delta: removed {name}")

        for guest_info in delta.get('guest_add', []):
            host = guest_info.get('host')
            guest_name = guest_info.get('guest_name')
            if host and guest_name:
                result = self.db.add_guest_manually(host, guest_name)
                if result.get('success'):
                    print(f"   ➕ Delta: added guest {guest_name} for {host}")

        for guest_info in delta.get('guest_remove', []):
            host = guest_info.get('host')
            guest_name = guest_info.get('guest_name')
            if guest_name:
                result = self.db.remove_guest_manually(guest_name, host)
                if result.get('success'):
                    print(f"   ➖ Delta: removed guest {guest_name}")

    def refresh_main_group(self):
        """Reload WhatsApp Web and do a fresh scan of the main group.
        This ensures a full message load (WhatsApp loads fewer messages on chat re-visits).
        Only used before scheduled messages - on-demand commands use DB data."""
        print(f"🔄 Refreshing main group before scheduled message...")
        try:
            # Reload page to reset WhatsApp's DOM - ensures full message load
            print("   Reloading WhatsApp Web for clean message load...")
            self.whatsapp.driver.get('https://web.whatsapp.com')
            time.sleep(8)
            # Wait for WhatsApp to be ready
            self.whatsapp.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
            )
            time.sleep(2)
            print("   ✅ WhatsApp reloaded")

            messages = self.whatsapp.get_all_messages(self.config.GROUP_NAME)
            if messages is None:
                print("⚠️  Failed to get main group messages - using existing data")
                return

            # Check if messages have changed since last analysis (order-independent)
            last_snapshot = self.db.get_last_snapshot()
            if self._snapshot_matches(messages, last_snapshot):
                print("📋 No new messages since last check - already up to date")
                return

            # Analyze with AI
            print(f"🤖 Analyzing {len(messages)} messages with AI...")
            result = self.ai.analyze_messages(messages)

            if result is not None and result.get('delta'):
                # Delta mode - apply changes on top of existing data
                self._apply_delta(result['delta'])
                self.db.save_snapshot(messages)
                return

            if result is None:
                # No result at all - keep existing data
                print("📋 Keeping existing player data")
                return

            if result['players'] or result.get('total_count', 0) > 0:
                # Safety check: don't overwrite a larger list with a significantly smaller one
                existing = self.db.get_participants()
                new_count = len(result['players'])
                existing_count = len(existing) if existing else 0
                if existing_count > 0 and new_count < existing_count * 0.7:
                    print(f"⚠️  AI returned {new_count} players but DB has {existing_count} - keeping existing data (possible scrape issue)")
                else:
                    changes = self.db.update_participants(result['players'])
                    self.db.save_snapshot(messages)
                    if result.get('pairings'):
                        self.db.save_weekly_pairings(result['pairings'])
                    print(f"✅ Refreshed: {result['total_count']} players")
                    # Notify admin group if reserves were promoted
                    if changes.get('promoted'):
                        promoted_names = ', '.join(changes['promoted'])
                        self.send_to_admin_group(f"📢 Reserve promoted to playing: {promoted_names}")
                        print(f"   📢 Promoted from reserves: {changes['promoted']}")
                    self.auto_adjust_published_sheet()
            else:
                existing = self.db.get_participants()
                if existing:
                    print(f"⚠️  AI returned 0 players but DB has {len(existing)} - keeping existing data")
                else:
                    self.db.save_snapshot(messages)
        except Exception as e:
            print(f"⚠️  Error refreshing main group: {e} - using existing data")

    def send_daily_update(self):
        """Send daily 8pm update to admin group"""
        print("⏰ Sending daily update...")
        self.refresh_main_group()
        participant_list = self.generate_participant_list()
        self.send_to_admin_group(participant_list)

    def generate_saturday_tee_sheet(self):
        """Generate Saturday 5pm tee sheet and publish it (locks in groups/times) - playing only, no reserves"""
        print("⏰ Generating Saturday tee sheet...")
        self.refresh_main_group()
        participants = self.db.get_participants(status_filter='playing')
        partner_prefs = self.db.get_partner_preferences()
        avoidances = self.db.get_avoidances()
        available_times = self.db.generate_tee_times()
        tee_sheet, groups, assigned_times = self.tee_generator.generate(
            participants, partner_prefs, avoidances, available_times
        )
        # Save as published sheet - future changes will only minimally adjust
        self.db.save_published_tee_sheet(groups, assigned_times, tee_sheet)
        self.send_to_admin_group(f"🏌️ *Shanks Bot has the final tee sheet!*\n\nThis is now locked in. Any changes from here will only tweak the affected groups.\n\n{tee_sheet}")
        print("✅ Tee sheet published - future changes will use minimal adjustments")

    def schedule_jobs(self):
        """Schedule recurring jobs"""
        schedule.every().day.at("12:00").do(self.send_health_check)
        schedule.every().monday.at("10:00").do(self.send_daily_update)
        schedule.every().monday.at("15:30").do(self.send_daily_update)
        schedule.every().monday.at("20:00").do(self.send_daily_update)
        schedule.every().tuesday.at("10:00").do(self.send_daily_update)
        schedule.every().tuesday.at("15:30").do(self.send_daily_update)
        schedule.every().tuesday.at("20:00").do(self.send_daily_update)
        schedule.every().wednesday.at("10:00").do(self.send_daily_update)
        schedule.every().wednesday.at("15:30").do(self.send_daily_update)
        schedule.every().wednesday.at("20:00").do(self.send_daily_update)
        schedule.every().thursday.at("10:00").do(self.send_daily_update)
        schedule.every().thursday.at("15:30").do(self.send_daily_update)
        schedule.every().thursday.at("20:00").do(self.send_daily_update)
        schedule.every().friday.at("10:00").do(self.send_daily_update)
        schedule.every().friday.at("15:30").do(self.send_daily_update)
        schedule.every().friday.at("20:00").do(self.send_daily_update)
        schedule.every().saturday.at("10:00").do(self.send_daily_update)
        schedule.every().saturday.at("17:00").do(self.generate_saturday_tee_sheet)
        schedule.every().monday.at("00:01").do(self.clear_weekly_data)
        schedule.every().monday.at("10:00").do(self.send_weekly_opening)
        print("✅ Scheduled jobs configured")

    def run_scheduler(self):
        """Run scheduled jobs in background"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)

    def monitor_messages(self):
        """Monitor and analyze messages with AI"""
        main_interval = self.config.MAIN_GROUP_CHECK_MINUTES * 60  # Convert to seconds
        admin_interval = self.config.ADMIN_GROUP_CHECK_SECONDS
        burst_duration = self.config.ADMIN_BURST_DURATION_SECONDS
        burst_interval = self.config.ADMIN_BURST_CHECK_SECONDS

        print(f"\n👀 Monitoring groups:")
        print(f"   📊 Main: {self.config.GROUP_NAME} (every {self.config.MAIN_GROUP_CHECK_MINUTES} min)")
        print(f"   ⚙️  Admin: {self.config.ADMIN_GROUP_NAME} (every {admin_interval}s, burst: {burst_interval}s for {burst_duration}s)")
        print(f"🤖 AI-powered analysis enabled")

        consecutive_failures = 0
        max_consecutive_failures = 3
        last_main_check = time.time() - main_interval  # Start by checking immediately

        # Clear snapshot so first main group check always does a fresh analysis
        self.db.save_snapshot([])
        print("🔄 Cleared message snapshot - will do fresh analysis on first check")
        burst_mode_until = 0  # Timestamp when burst mode expires (admin group)

        # Initialize admin anchor - save last 3 messages as fingerprint to detect new ones
        try:
            admin_messages = self.whatsapp.get_all_messages(self.config.ADMIN_GROUP_NAME)
            if admin_messages:
                self._admin_anchor = [(m['sender'], m['text']) for m in admin_messages[-3:]]
                print(f"📌 Initialized admin check - skipping {len(admin_messages)} existing messages")
            else:
                self._admin_anchor = []
                print(f"📌 Initialized admin check - no existing messages")
        except Exception as e:
            self._admin_anchor = []
            print(f"⚠️  Could not initialize admin check: {e}")

        while self.running:
            try:
                now = datetime.now()
                current_time = time.time()

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

                # === MONITOR MAIN GROUP ===
                time_since_last_check = current_time - last_main_check
                if time_since_last_check >= main_interval:
                    # Check if we should monitor main group (not after Sunday tee time)
                    should_monitor_main = True
                    if now.weekday() == 6:
                        first_tee_time = self.config.TEE_TIMES[0]
                        tee_hour, tee_minute = map(int, first_tee_time.split(':'))

                        if now.hour > tee_hour or (now.hour == tee_hour and now.minute >= tee_minute):
                            print(f"\n😴 Past tee time ({first_tee_time}) - skipping main group")
                            should_monitor_main = False

                    if should_monitor_main:
                        print(f"\n📥 Fetching messages from {self.config.GROUP_NAME}...")
                        messages = self.whatsapp.get_all_messages(self.config.GROUP_NAME)

                        if messages is None:
                            consecutive_failures += 1
                            print(f"⚠️  Failed to get main group messages ({consecutive_failures}/{max_consecutive_failures})")
                        else:
                            consecutive_failures = 0

                            # Check if messages have changed since last analysis (order-independent)
                            last_snapshot = self.db.get_last_snapshot()
                            if self._snapshot_matches(messages, last_snapshot):
                                print(f"📋 No new messages since last check - skipping AI analysis (saving tokens)")
                                last_main_check = current_time
                                continue

                            # Analyze with AI
                            print(f"🤖 Analyzing {len(messages)} messages with AI...")
                            result = self.ai.analyze_messages(messages)

                            if result is not None and result.get('delta'):
                                # Delta mode - apply changes on top of existing data
                                self._apply_delta(result['delta'])
                                self.db.save_snapshot(messages)
                                last_main_check = current_time
                                continue

                            if result is None:
                                # No result at all - keep existing data
                                print("📋 Keeping existing player data")
                                last_main_check = current_time
                                continue

                            # Only update database if AI returned valid results
                            # Prevents wiping participants on API errors
                            if result['players'] or result.get('total_count', 0) > 0:
                                # Safety check: don't overwrite a larger list with a significantly smaller one
                                existing = self.db.get_participants()
                                new_count = len(result['players'])
                                existing_count = len(existing) if existing else 0
                                if existing_count > 0 and new_count < existing_count * 0.7:
                                    print(f"⚠️  AI returned {new_count} players but DB has {existing_count} - keeping existing data (possible scrape issue)")
                                else:
                                    changes = self.db.update_participants(result['players'])
                                    self.db.save_snapshot(messages)
                                    # Save any AI-detected MP pairings as weekly constraints
                                    if result.get('pairings'):
                                        self.db.save_weekly_pairings(result['pairings'])
                                    # Notify admin group if reserves were promoted
                                    if changes.get('promoted'):
                                        promoted_names = ', '.join(changes['promoted'])
                                        self.send_to_admin_group(f"📢 Reserve promoted to playing: {promoted_names}")
                                        print(f"   📢 Promoted from reserves: {changes['promoted']}")
                            else:
                                existing = self.db.get_participants()
                                if existing:
                                    print(f"⚠️  AI returned 0 players but DB has {len(existing)} - keeping existing data")
                                else:
                                    self.db.save_snapshot(messages)

                            # Log results
                            print(f"✅ Analysis complete:")
                            print(f"   Players: {result['total_count']}")
                            print(f"   Summary: {result['summary']}")
                            if result.get('changes'):
                                print(f"   Changes: {', '.join(result['changes'])}")

                            # Change notifications disabled per user request
                            # If you want to re-enable, uncomment the lines below:
                            # if result.get('changes') and len(result['changes']) > 0:
                            #     change_msg = f"🔔 UPDATE\n\n{result['summary']}\n\nChanges:\n"
                            #     change_msg += '\n'.join(f"• {c}" for c in result['changes'])
                            #     self.send_to_me(change_msg)

                    last_main_check = current_time

                # === MONITOR ADMIN GROUP ===
                in_burst = current_time < burst_mode_until
                if in_burst:
                    remaining = int(burst_mode_until - current_time)
                    print(f"\n📥 Checking admin group (burst mode - {remaining}s remaining)...")
                else:
                    print(f"\n📥 Checking admin group for commands...")

                admin_messages = self.whatsapp.get_all_messages(self.config.ADMIN_GROUP_NAME)

                if admin_messages and len(admin_messages) > 0:
                    # Find new messages using anchor sequence (last 3 messages as fingerprint)
                    new_messages = self._find_new_admin_messages(admin_messages)

                    if not new_messages:
                        last_text = admin_messages[-1]['text']
                        print(f"   No new messages (last was: {last_text[:30]}...)")
                    else:
                        print(f"   Found {len(new_messages)} new message(s)")

                        for msg in new_messages:
                            sender = msg['sender']
                            text = msg['text']

                            # Skip bot responses using blocklist
                            if self._is_bot_response(text):
                                print(f"   Skipping bot response: '{text[:40]}...'")
                                continue

                            # Check if sender is an admin
                            sender_cleaned = sender.replace('+', '').replace(' ', '').replace('(', '').replace(')', '')
                            is_admin = sender in self.config.ADMIN_USERS or sender_cleaned in self.config.ADMIN_USERS

                            if is_admin:
                                print(f"✅ New admin message from: {sender}")
                                self.handle_admin_command(text, sender)
                                # Activate burst mode
                                burst_mode_until = time.time() + burst_duration
                                print(f"⚡ Burst mode activated - checking every {burst_interval}s for {burst_duration}s")
                            else:
                                print(f"⚠️  Message from non-admin: {sender}")

                    # Always update the anchor to the latest 3 messages
                    self._admin_anchor = [(m['sender'], m['text']) for m in admin_messages[-3:]]

                # Check for failures
                if consecutive_failures >= max_consecutive_failures:
                    print(f"❌ Too many failures. Stopping.")
                    self.running = False
                    break

                # Sleep - use burst interval if admin is active, otherwise normal interval
                in_burst = time.time() < burst_mode_until
                sleep_time = burst_interval if in_burst else admin_interval
                minutes_until_next_main = max(0, int((main_interval - (time.time() - last_main_check)) / 60))
                if in_burst:
                    print(f"⏰ Next admin check in {sleep_time}s (burst) | main group in {minutes_until_next_main} min...")
                else:
                    print(f"⏰ Next admin check in {sleep_time}s | main group in {minutes_until_next_main} min...")
                time.sleep(sleep_time)

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
