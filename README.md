# 🏌️ Golf Swindle Bot

An intelligent WhatsApp bot that automates weekly golf tee sheet management. The bot monitors your golf group, extracts player signups using AI, and generates optimized tee sheets with automatic partner pairing and tee time assignment.

**No more manual spreadsheets!** ⛳

---

## ✨ Features

### 🤖 Automated Player Tracking
- Monitors WhatsApp group messages hourly
- Uses Claude AI to understand natural language signups ("I'm in", "Yes please", "Can't make it")
- Tracks guests and handles duplicates intelligently
- Sends daily updates on participant list

### 👥 Smart Group Management
- **Constraint-based grouping**: Partner preferences and avoidances
- **Optimal group sizes**: Fills groups to 4 players when possible
- **Guest handling**: Keeps guests with their hosts
- **Persistent preferences**: Set partner preferences once, applied every week

### ⏰ Dynamic Tee Time Assignment
- **Additive tee time management**: Start with auto-generated times, then add/remove specific times
- Configurable start times and intervals
- Preference-based assignment (early birds vs late starters)
- Calculates unused slots to return to the course
- Actual tee times in tee sheet (e.g., 8:00am, 8:08am, 8:16am)
- **Weekly time preferences**: Reset each week (partner preferences persist)

### 📱 Admin Control via WhatsApp
- Fast 1-minute response time for admin commands
- Add/remove players and guests manually
- Set partner preferences and avoidances
- Configure tee times
- View constraints and settings

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Chrome browser
- Anthropic API key ([get one here](https://console.anthropic.com/))
- WhatsApp Web access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/golf-swindle-bot.git
   cd golf-swindle-bot
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up configuration**
   ```bash
   # Copy example files
   cp config.example.py config.py
   cp .env.example .env

   # Edit config.py with your details
   nano config.py  # or your preferred editor

   # Edit .env with your API key
   nano .env
   ```

5. **Configure your settings in `config.py`:**
   ```python
   GROUP_NAME = "Your Golf Group Name"
   ADMIN_GROUP_NAME = "Your Admin Group Name"
   MY_NUMBER = "447123456789"  # Your phone number
   ADMIN_USERS = ["447123456789", "Your Name"]
   NAME_MAPPING = {}  # Optional: map unusual contact names
   ```

6. **Add your Anthropic API key to `.env`:**
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
   ```

7. **Run the bot**
   ```bash
   python3 src/swindle_bot_v5_admin.py
   ```

8. **First run setup:**
   - Chrome will open with WhatsApp Web
   - Scan the QR code with your phone
   - Session will be saved for future runs
   - Bot will send a startup message to your admin group

---

## 📋 Usage

### Automatic Operation

The bot runs scheduled tasks automatically:

| When | What | Why |
|------|------|-----|
| **Every hour** | Check main group | Detect new signups |
| **Every minute** | Check admin group | Respond to commands |
| **12:00 PM daily** | Health check | Confirm bot is running |
| **8:00 PM Mon-Sat** | Daily update | Current participant list |
| **5:00 PM Saturday** | Final tee sheet | Complete tee sheet for Sunday |

### Admin Commands

Send these in your admin WhatsApp group:

**View information:**
```
Show list              # Current participants
Show tee sheet         # Complete tee sheet with groups
Show constraints       # Partner preferences and avoidances
Show tee times         # Tee time configuration
```

**Manage players:**
```
Add John Smith         # Add a player
Remove Mike Jones      # Remove a player
Add guest Tom for Alex # Add a guest
Remove guest Tom       # Remove a guest
```

**Set preferences:**
```
Mike plays with John          # Set partner preference
Don't pair Alex with Tom      # Set avoidance
Mike prefers early            # Early tee time preference
Dave wants late tee time      # Late tee time preference
```

**Configure tee times:**
```
Set tee times from 8:00                        # Use defaults
Configure tee times starting at 8am with 8 minute intervals
```

**Manage individual tee times (additive):**
```
Add tee time 09:00           # Add specific time to auto-generated list
Remove tee time 08:32        # Remove specific time from list
Clear tee times              # Reset to pure auto-generation
```

**Weekly time preferences:**
```
Clear time preferences       # Clear early/late for new week (keeps partner prefs)
```

**Remove preferences:**
```
Remove Mike's partner preference
Remove avoidance for Alex
```

---

## 📁 Project Structure

```
golf-swindle-bot/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── .env.example                 # Example environment variables
├── config.example.py            # Example configuration
│
├── src/
│   └── swindle_bot_v5_admin.py # Main bot application
│
├── tests/
│   ├── test_phase2_commands.py  # Test admin commands
│   ├── test_phase3_constraints.py # Test constraint system
│   ├── test_phase4_tee_times.py   # Test tee time assignment
│   └── ...                      # More test files
│
├── scripts/
│   ├── add_constraints.py       # Add partner preferences
│   ├── add_test_participants.py # Add test data
│   └── debug_*.py               # Debug utilities
│
├── docs/
│   ├── TECHNICAL_DOCUMENTATION.md  # Detailed technical docs
│   └── USER_GUIDE.md               # Simple user guide
│
├── data/                        # Database files (gitignored)
│   └── .gitkeep
│
└── logs/                        # Log files (gitignored)
    └── .gitkeep
```

---

## 🔧 Configuration Details

### WhatsApp Groups

You need **two WhatsApp groups**:

1. **Main Group** (`GROUP_NAME`): Where players sign up
   - Bot monitors this every hour
   - Extracts participants using AI
   - Does not send messages here

2. **Admin Group** (`ADMIN_GROUP_NAME`): For admin commands
   - Bot monitors this every minute
   - Responds to commands
   - Sends notifications and updates

### Name Mapping (Optional)

If some contacts have unusual display names in WhatsApp:

```python
NAME_MAPPING = {
    ".": "John",   # Contact name is literally "."
    "L": "Lloyd",  # Contact name is just "L"
}
```

### Database

- SQLite database stored in `data/` directory
- Tables: `participants`, `constraints`, `tee_time_settings`, `manual_tee_times`, `removed_tee_times`, `last_snapshot`
- Automatically created on first run
- Backs up Chrome profile every session
- **Additive tee times**: Combines auto-generated times with manual additions/removals

---

## 🧪 Testing

### Run Test Suite

```bash
# Test admin commands
python3 tests/test_phase2_commands.py

# Test constraints
python3 tests/test_phase3_constraints.py

# Test tee time assignment
python3 tests/test_phase4_tee_times.py

# Test with sample data
python3 scripts/add_test_participants.py
```

### Add Test Data

```bash
# Add sample participants to test the system
python3 scripts/add_test_participants.py

# Add partner preferences
python3 scripts/add_constraints.py

# View the generated tee sheet
python3 tests/test_show_tee_sheet.py
```

---

## 🔒 Security & Privacy

### What's Protected

- ✅ **API Keys**: Stored in `.env` (gitignored)
- ✅ **Config File**: `config.py` (gitignored)
- ✅ **Database**: `*.db` files (gitignored)
- ✅ **Chrome Session**: `chrome_profile/` (gitignored)
- ✅ **Logs**: `*.log` files (gitignored)

### What's Public

- ✅ Source code (no sensitive data)
- ✅ Example configuration files
- ✅ Documentation
- ✅ Test scripts

### Before Pushing to GitHub

```bash
# Verify no sensitive data
grep -r "ANTHROPIC_API_KEY.*sk-" .  # Should find nothing
grep -r "+44[0-9]\{10\}" .          # Should find nothing in tracked files

# Check what will be committed
git status

# Make sure config.py and .env are not tracked
git check-ignore config.py .env     # Should show both files
```

---

## 📚 Documentation

- **[USER_GUIDE.md](docs/USER_GUIDE.md)**: Simple guide for golf group organizers
- **[TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md)**: Detailed technical documentation for developers

---

## 🐛 Troubleshooting

### "config.py not found" warning
- Copy `config.example.py` to `config.py`
- Update with your WhatsApp group names and phone numbers

### "ANTHROPIC_API_KEY not set"
- Copy `.env.example` to `.env`
- Add your API key from https://console.anthropic.com/

### Bot doesn't respond to commands
- Check you're in the correct admin group
- Verify your name/number is in `ADMIN_USERS`
- Wait 1 minute (admin group checks every minute)

### Chrome session expired
- Delete `chrome_profile/` directory
- Restart bot and scan QR code again

### Player names incorrect
- Use `scripts/debug_messages.py` to check extracted names
- Add mappings to `NAME_MAPPING` in `config.py`

---

## 🎯 Phases & Features

### ✅ Phase 1: AI Analysis
- WhatsApp message extraction
- Claude AI-powered participant detection
- Guest handling
- Change detection

### ✅ Phase 2: Manual Management
- Admin commands for player management
- Add/remove players and guests
- Show participant list
- Generate basic tee sheet

### ✅ Phase 3: Constraints
- Partner preferences (persistent across weeks)
- Avoidance rules
- Constraint-aware grouping
- Group optimization (fill to 4 players)

### ✅ Phase 4: Dynamic Tee Times
- Configurable tee time settings
- Preference-based time assignment
- Unused slot tracking
- Admin commands for configuration

---

## 📅 Preference Types: Season-Long vs Weekly

### Season-Long (Persist Forever)
These are set once and automatically applied every week:
- ✅ **Partner preferences**: "Lloyd plays with Segan"
- ✅ **Avoidances**: "Don't pair Mike with John"
- ✅ **Tee time settings**: Auto-generation configuration

### Weekly (Reset Each Week)
These must be set fresh each week:
- 🔄 **Time preferences**: "Mike prefers early"
- 🔄 **Tee time modifications**: Added/removed specific times

**Why?** Players' time preferences change week-to-week, but playing partnerships are consistent all season!

**Admin commands:**
```
Clear time preferences    # Reset early/late for new week
Clear tee times          # Reset tee time modifications
```

---

## 💡 Tips & Best Practices

1. **Set partner preferences at season start** - They persist all season!
2. **Use test scripts** - Verify changes before live use
3. **Check daily updates** - Stay informed without manual work
4. **Trust the AI** - Very accurate at detecting signups
5. **Backup database** - `cp data/golf_swindle.db data/backup_$(date +%Y%m%d).db`

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test your changes thoroughly
4. Commit with clear messages
5. Push and open a Pull Request

---

## 📄 License

This project is open source and available under the MIT License.

---

## 🙏 Acknowledgments

- **Anthropic Claude AI** - Powers the intelligent message analysis
- **Selenium WebDriver** - Enables WhatsApp Web automation
- **Python Schedule** - Handles automated tasks

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/golf-swindle-bot/issues)
- **Documentation**: See `docs/` directory
- **Debug Scripts**: See `scripts/debug_*.py`

---

**Built with ❤️ for golf enthusiasts who want to spend more time playing and less time organizing!** ⛳

---

**Last Updated**: February 2026
**Version**: 5.0 (All 4 Phases Complete)
