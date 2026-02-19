"""
Configuration file for Golf Swindle Bot
Copy this file to 'config.py' and update with your personal details
"""

# WhatsApp Group Names
GROUP_NAME = "Your Main Golf Group Name"  # The group where players sign up
ADMIN_GROUP_NAME = "Your Admin Group Name"  # The group for admin commands

# Admin Users (people who can send commands to the bot)
# You can use phone numbers (format: "447123456789") or WhatsApp display names
ADMIN_USERS = [
    "Your Phone Number",  # Example: "447123456789"
    "Your WhatsApp Name",  # Example: "John Smith"
]

# Your phone number (for receiving notifications)
MY_NUMBER = "Your Phone Number"  # Example: "447123456789"

# Name Mapping (optional)
# If some contacts have unusual display names in WhatsApp, map them here
NAME_MAPPING = {
    # Example: ".": "John",  # If someone's contact name is literally "."
    # Example: "L": "Dave",   # If someone's contact name is just "L"
}

# Golf Settings
MAX_GROUP_SIZE = 4  # Maximum players per group
DEFAULT_START_TIME = "08:00"  # Default tee time start
DEFAULT_INTERVAL_MINUTES = 8  # Minutes between tee times
DEFAULT_NUM_SLOTS = 10  # Number of tee time slots booked

# Database
DB_PATH = "data/golf_swindle.db"

# WhatsApp Settings
MAX_MESSAGES = 200  # Number of recent messages to check in WhatsApp group
MAIN_GROUP_CHECK_MINUTES = 10  # How often to check the main swindle group (minutes) - snapshot comparison makes idle checks free
ADMIN_GROUP_CHECK_SECONDS = 60  # How often to check the admin group (seconds)
ADMIN_BURST_DURATION_SECONDS = 180  # After a command, check admin group rapidly for this long (seconds)
ADMIN_BURST_CHECK_SECONDS = 5  # During burst mode, check every N seconds

# Chrome Settings
CHROME_RESTART_HOURS = 24  # Restart Chrome session every N hours
