# Golf Swindle Bot - Technical Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Scheduled Jobs](#scheduled-jobs)
5. [Key Components](#key-components)
6. [AI Analysis System](#ai-analysis-system)
7. [Admin Commands](#admin-commands)
8. [Configuration](#configuration)
9. [Development & Maintenance](#development--maintenance)

---

## System Overview

The Golf Swindle Bot is an automated tee sheet management system that monitors a WhatsApp group, extracts player signups using AI, and generates optimized tee sheets with actual tee time assignments.

### Technology Stack
- **Language**: Python 3
- **Browser Automation**: Selenium WebDriver (Chrome)
- **AI**: Anthropic Claude API (Haiku 4.5 for analysis, Sonnet 4.5 for commands)
- **Database**: SQLite
- **Scheduling**: Python `schedule` library

### Key Features
- **Phase 1**: AI-powered message analysis & player extraction
- **Phase 2**: Manual player/guest management via admin commands
- **Phase 3**: Group constraints (partner preferences, avoidances) & optimized grouping
- **Phase 4**: Dynamic tee time management with preference-based assignment

---

## Architecture

### Main Components

```
┌─────────────────────────────────────────────────────────────┐
│                     WhatsApp Web                             │
│              (Chrome via Selenium)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  WhatsAppBot                                 │
│  - Message extraction                                        │
│  - Sender name identification (100% accuracy)                │
│  - Admin group monitoring (1-minute intervals)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   AIAnalyzer                                 │
│  - Claude Haiku for message analysis                         │
│  - Player extraction with natural language understanding     │
│  - Guest detection & duplicate handling                      │
│  - Timeline filtering (ignore pre-signup messages)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Database (SQLite)                         │
│  - participants, constraints, tee_time_settings              │
│  - Persistent storage across sessions                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              TeeSheetGenerator                               │
│  - Constraint-aware grouping                                 │
│  - Group optimization (fill to 4 players)                    │
│  - Tee time assignment based on preferences                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│            AdminCommandHandler                               │
│  - Claude Haiku for command parsing                          │
│  - Natural language command understanding                    │
│  - Action execution & response generation                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### `participants` Table
```sql
CREATE TABLE participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- Player name (exact from WhatsApp)
    guests TEXT,                         -- JSON array of guest names
    preferences TEXT,                    -- Time preferences (early/late) & other notes
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### `constraints` Table (Phase 3)
```sql
CREATE TABLE constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    constraint_type TEXT NOT NULL,      -- 'partner_preference' or 'avoid'
    player_name TEXT NOT NULL,          -- Player this applies to
    target_name TEXT,                    -- Other player (for preferences/avoidances)
    value TEXT,                          -- Additional data if needed
    active BOOLEAN DEFAULT 1,            -- Soft delete flag
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### `tee_time_settings` Table (Phase 4)
```sql
CREATE TABLE tee_time_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,           -- e.g., "08:00"
    interval_minutes INTEGER NOT NULL,   -- e.g., 8
    num_slots INTEGER NOT NULL,          -- e.g., 10
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### `last_snapshot` Table
```sql
CREATE TABLE last_snapshot (
    id INTEGER PRIMARY KEY,
    messages_json TEXT,                 -- JSON snapshot of last analyzed messages
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**Purpose**: Change detection - only notify when the player list actually changes.

---

## Scheduled Jobs

### Job Schedule Overview

| Time | Day | Job | Description |
|------|-----|-----|-------------|
| **Every 1 minute** | All | `check_admin_commands()` | Monitor admin group for commands |
| **Every 1 hour** | All | `check_main_group()` | Check main group for new signups (when active) |
| **12:00 PM** | Daily | `send_health_check()` | Health check message |
| **8:00 PM** | Mon, Tue, Wed, Thu, Fri, Sat | `send_daily_update()` | Daily participant list update |
| **5:00 PM** | Saturday | `generate_saturday_tee_sheet()` | Final tee sheet generation |

### Detailed Job Descriptions

#### 1. Admin Command Monitoring (Every 1 minute)
**Function**: `check_admin_commands()`
**Purpose**: Fast response to admin commands
**Process**:
- Fetches messages from admin group
- Checks only the LAST message (not last 5)
- Ignores bot's own messages
- Validates sender is in `ADMIN_USERS` list
- Parses command with AI
- Executes action and responds

**Deduplication**: Uses `last_admin_check` to track last processed message key

#### 2. Main Group Monitoring (Every 1 hour)
**Function**: `check_main_group()`
**Purpose**: Detect new signups/changes
**Process**:
- Fetches all messages from main group
- Pre-filters messages:
  - Finds "now taking names" organizer message
  - Only analyzes messages AFTER signup started
  - Filters out quoted organizer messages
- Sends to AI for analysis
- Compares with last snapshot
- Updates database if changes detected
- Sends notification ONLY if changes occur (not just "UPDATE" spam)

**Note**: Currently disabled (can re-enable by uncommenting notification code)

#### 3. Health Check (12:00 PM Daily)
**Function**: `send_health_check()`
**Purpose**: Verify bot is running
**Sends to**: Your personal number (first in `ADMIN_USERS`)
**Message**: "HEALTH CHECK\n\nBot is running normally\nTime: DD/MM/YYYY HH:MM"

#### 4. Daily Update (8:00 PM Mon-Sat)
**Function**: `send_daily_update()`
**Purpose**: Regular status update with current participant list
**Sends to**: Your personal number
**Message**: Formatted participant list with guests and preferences

#### 5. Saturday Tee Sheet (5:00 PM)
**Function**: `generate_saturday_tee_sheet()`
**Purpose**: Generate final tee sheet for Sunday game
**Sends to**: Your personal number
**Process**:
- Gets all participants
- Gets constraints (partner prefs, avoidances)
- Gets tee time settings
- Generates optimized groups (Phase 3)
- Assigns actual tee times (Phase 4)
- Sends formatted tee sheet

---

## Key Components

### 1. WhatsAppBot Class

**Responsibilities**:
- Chrome/Selenium session management
- Message extraction from WhatsApp Web
- Sender name identification (critical!)
- Message sending

**Critical Methods**:

#### `get_all_messages(group_name)`
Extracts messages with 100% accurate sender identification.

**Sender Extraction Logic**:
```python
# For incoming messages: Use span[dir="auto"] (most reliable)
spans = elem.find_elements(By.XPATH, './/span[@dir="auto"]')
sender = spans[0].text.strip()  # First span is sender name

# Fallback: data-pre-plain-text attribute
# Format: "[HH:MM, DD/MM/YYYY] Name:"

# For outgoing messages: Use admin name from config
```

**Name Mapping** (for unusual contact names):
```python
NAME_MAPPING = {
    ".": "Segan",    # Contact name is literally "."
    "L": "Lloyd",    # Contact name is "L"
}
```

#### Session Management
- Chrome session restarts every 24 hours (configurable)
- Prevents memory leaks and stale sessions
- `CHROME_RESTART_HOURS = 24` in Config

---

### 2. AIAnalyzer Class

**Model**: Claude Haiku 4.5 (fast and cost-effective)

**Pre-Filtering** (Python-side before AI):
1. Find "now taking names" organizer message
2. Only send messages AFTER that point
3. Filter out messages quoting the organizer

**AI Prompt Key Rules**:
- Use exact sender names from [brackets]
- Identify organizer (don't include unless explicit signup)
- Handle guest duplicates (if guest also signs up separately)
- Understand natural language ("I'm in", "can't make it", etc.)
- Track latest message per person (people change minds)

**Output Format**:
```json
{
    "players": [
        {
            "name": "John Smith",
            "guests": ["Guest1"],
            "preferences": "early tee time"
        }
    ],
    "total_count": 10,
    "summary": "10 players confirmed...",
    "changes": ["John added", "Mike removed"]
}
```

---

### 3. TeeSheetGenerator Class

**Phase 3: Group Optimization**

**Algorithm** (4 passes):

1. **Partner Preferences Pass**
   - Groups players with partner preferences together
   - Fills to MAX_GROUP_SIZE (4) when possible

2. **Fill Groups Pass**
   - Adds remaining players to existing groups
   - Sorts by smallest groups first (balances sizes)
   - Checks avoidances before adding

3. **Consolidation Pass**
   - Merges small groups when possible
   - Respects MAX_GROUP_SIZE and avoidances

4. **Balancing Pass**
   - Redistributes players to avoid very small groups (1-2)
   - Goal: All groups have 3+ players
   - Example: [2,4,4,4] → [3,3,4,4]

**Result**: Optimal groups (e.g., 14 players → 2×4 + 2×3 = 4 tee times)

**Phase 4: Tee Time Assignment**

**Algorithm**:
1. Categorize groups by preference:
   - Early groups (any player with "early" preference)
   - Late groups (any player with "late" preference)
   - Neutral groups (no preferences)

2. Assign times:
   - Early groups → First available times
   - Neutral groups → Middle times
   - Late groups → Later times

3. Calculate unused slots:
   - Total slots - Used slots = Slots to return to course

---

### 4. AdminCommandHandler Class

**Model**: Claude Haiku 4.5

**Supported Commands**:
- **Phase 1**: `show_list`, `show_tee_sheet`
- **Phase 2**: `add_player`, `remove_player`, `add_guest`, `remove_guest`
- **Phase 3**: `set_partner_preference`, `set_avoidance`, `show_constraints`
- **Phase 4**: `set_tee_times`, `show_tee_times`, `set_time_preference`

**Natural Language Examples**:
- "Show list" → `show_list`
- "Add John Smith" → `add_player` (extracts name)
- "Mike plays with John" → `set_partner_preference` (extracts both names)
- "Don't pair Alex with Tom" → `set_avoidance`
- "Set tee times from 8:00" → `set_tee_times` (extracts start time)

---

## Configuration

### Environment Variables
```bash
ANTHROPIC_API_KEY=your_api_key_here
```

### Config Class (`swindle_bot_v5_admin.py`)

```python
class Config:
    # WhatsApp Groups
    GROUP_NAME = "Sunday Swindle"          # Main group to monitor
    ADMIN_GROUP_NAME = "Sunday Swindle - Admin"  # Admin commands group

    # Admin Users (phone numbers or names)
    ADMIN_USERS = [
        "Your Phone Number",   # Example: "+447123456789"
        "Your WhatsApp Name"   # Example: "John Smith"
    ]

    # Name Mapping (for unusual contact names)
    NAME_MAPPING = {
        ".": "Segan",
        "L": "Lloyd"
    }

    # Golf Settings
    MAX_GROUP_SIZE = 4
    TEE_TIMES = ["8:24", "8:32", "8:40", "8:48", "8:56", "9:04", "9:12", "9:20"]

    # Database
    DB_PATH = "golf_swindle.db"

    # Chrome Settings
    CHROME_RESTART_HOURS = 24

    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

---

## Development & Maintenance

### Running the Bot

```bash
# Set API key
export ANTHROPIC_API_KEY="your_key_here"

# Run bot
python3 swindle_bot_v5_admin.py
```

**First Run**:
- Opens Chrome with WhatsApp Web
- Scan QR code to login
- Session persists (cookies saved)
- Subsequent runs use saved session

### Adding New Admin Commands

1. **Update AdminCommandHandler prompt** (line ~795):
```python
12. "your_command" - Description
    Triggers: "trigger phrases", etc.
    Extract: param1, param2
```

2. **Add to OUTPUT command list**:
```python
"command": "... | your_command | ...",
```

3. **Add command handler** (line ~1669):
```python
elif command == 'your_command':
    params = result.get('params', {})
    # Your logic here
    self.send_to_admin_group("Response message")
```

4. **Update startup message** (line ~1817):
```python
commands = [
    # ...existing commands...
    "Your command example"
]
```

### Modifying Scheduled Jobs

Edit `schedule_jobs()` method (line ~1744):

```python
def schedule_jobs(self):
    # Add new job
    schedule.every().wednesday.at("14:00").do(self.your_function)

    # Modify existing job time
    schedule.every().saturday.at("17:00").do(self.generate_saturday_tee_sheet)  # Changed from 5pm
```

### Debugging

**Debug Scripts**:
- `debug_messages.py` - Check message extraction & sender names
- `debug_ai_analysis.py` - See AI analysis decisions
- `debug_admin.py` - Test admin command parsing
- `test_phase2_commands.py` - Test Phase 2 commands
- `test_phase3_constraints.py` - Test Phase 3 constraints
- `test_phase4_tee_times.py` - Test Phase 4 tee times

**Common Issues**:

1. **"Unknown" sender names**
   - Check `debug_messages.py` output
   - Add to `NAME_MAPPING` if needed
   - Verify span extraction logic

2. **AI including wrong players**
   - Check `debug_ai_analysis.py`
   - Verify pre-filtering logic (organizer message detection)
   - Update AI prompt if needed

3. **Chrome session stale**
   - Bot auto-restarts every 24 hours
   - Manually restart: `bot.restart_session()`

4. **Commands not responding**
   - Check admin group monitoring (1-minute interval)
   - Verify sender is in `ADMIN_USERS`
   - Check bot message pattern filter (line ~1965)

### Database Maintenance

**Backup**:
```bash
cp golf_swindle.db golf_swindle_backup_$(date +%Y%m%d).db
```

**Clear for new week**:
```python
db.clear_participants()  # Removes all participants and snapshots
```

**Query participants**:
```python
participants = db.get_participants()
for p in participants:
    print(f"{p['name']}: {p['guests']}")
```

---

## Performance & Costs

### AI API Usage

**Messages Analyzed** (per week):
- Main group check: 1/hour × 168 hours = 168 calls
- Admin commands: ~10-20 calls
- **Total**: ~180-190 API calls/week

**Cost Estimate** (Claude Haiku 4.5):
- Input: ~500 tokens/call × 190 calls = 95,000 tokens
- Output: ~200 tokens/call × 190 calls = 38,000 tokens
- **Cost**: ~$0.10-0.20 per week (very low!)

### Chrome Memory Usage
- Typical: 200-400 MB
- Restarts every 24 hours to prevent leaks
- Headless mode (no GUI) saves resources

---

## Security Considerations

1. **API Key**: Store in environment variable, never commit to git
2. **Phone Numbers**: Consider hashing or encrypting in production
3. **WhatsApp Session**: Cookie file should be secured
4. **Admin Access**: Only users in `ADMIN_USERS` can execute commands
5. **Message Deduplication**: Prevents duplicate processing and loops

---

## Future Enhancement Ideas

### Phase 5: Handicap & Competition Management
- Track player handicaps
- Calculate match play pairings
- Generate competition draws

### Phase 6: Notifications & Reminders
- Send tee time confirmations to individual players
- 24-hour reminders
- Weather alerts

### Phase 7: Historical Analytics
- Attendance tracking
- Popular playing partners analysis
- Performance stats

### Phase 8: Multi-Week Planning
- Recurring events
- Season scheduling
- Waiting list management

---

## Support & Troubleshooting

### Logs
Bot prints detailed logs to console:
- `📱 Processing: 'command'...` - Admin command received
- `✅ Sent participant list` - Successful action
- `❌ Error: ...` - Error details

### Getting Help
1. Check debug scripts for specific issues
2. Review logs for error messages
3. Verify configuration settings
4. Test with debug scripts before modifying production code

---

**Last Updated**: February 2026
**Version**: 5.0 (Phases 1-4 Complete)
**Author**: Golf Swindle Bot Development Team
