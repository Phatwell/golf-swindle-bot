# Golf Swindle — Admin Guide

## Weekly Workflow

### 1. Create the Event
- Go to **Dashboard** → **+ New Event**
- Click **Saturday Swindle** or **Sunday Swindle** template (auto-fills everything including date and WhatsApp group)
- Check the details look right → **Create Event**

### 2. Share the Signup Link
- On the event page, use **Copy** to get the link or **Share** to send directly to WhatsApp
- The message includes the event name, current player count, and signup link

### 3. Monitor Signups
- The event page shows who's signed up, their tee time preference (early/late/any), and any guests
- Capacity = tee times × group size (e.g. 7 slots × 4-ball = 28 spots)
- Once full, new players go on the **waitlist** automatically
- If someone drops out, the first waitlisted player is promoted automatically

### 4. Add/Remove Players (if needed)
- Use the **Add Player** form on the right side of the event page
- To remove someone, click **Remove** next to their name

### 5. Lock the Event
- Click **Lock Event** when signups close — this generates the tee sheet automatically
- Or let **auto-lock** do it (default: 5pm the day before)
- When auto-lock fires, the tee sheet is also sent to WhatsApp automatically

### 6. Review & Share the Tee Sheet
- After locking, the tee sheet appears on the event page
- Click **Edit** to drag-and-drop players between groups if needed
- Click **Regenerate Tee Sheet** if you want a fresh one
- Use the WhatsApp section to send the tee sheet or player list to the group

---

## Key Things to Know

**Tee sheet logic:**
- Pairs match play partners together
- Respects early/late preferences (won't mix early + late in same group)
- Returns unused tee times if there are fewer groups than slots

**WhatsApp messages:**
- Daily updates are sent automatically at **10am** and **5pm** for all open events
- You can also manually send a player list or tee sheet from the event page
- Messages queue up and send one at a time (takes a few seconds each)

**Match play partners:**
- When a player picks a match play partner, the partner is auto-signed up too
- They'll be grouped together on the tee sheet

**Guests:**
- Players can add guests when signing up
- Guests count toward capacity and are shown on the tee sheet

**Returning players:**
- The site remembers players by cookie — returning visitors can edit or remove their signup without re-entering their name

---

## Restarting the App

If the site goes down, check:
```
sudo systemctl status golf-swindle
sudo systemctl status cloudflared
```

To restart:
```
sudo systemctl restart golf-swindle
```

Both services auto-start on boot and auto-restart if they crash.

---

## Backups

The database is backed up daily at 3am to `data/backups/`. Last 30 days are kept.

---

## Scheduled WhatsApp Messages

These messages are sent automatically — no action needed from you.

| When | What | Condition |
|------|------|-----------|
| **10:00 AM daily** | Player list + signup link | Event is **open** and has a WhatsApp group set |
| **5:00 PM daily** | Player list + signup link | Event is **open** and has a WhatsApp group set |
| **At auto-lock time** | Tee sheet | Event auto-locks (default: 5pm day before) and has a WhatsApp group set |

**What the daily update includes:**
- Event name and date
- Current player count (e.g. "17/28 spots filled")
- Numbered player list with guests labelled
- Waitlist (if any)
- Signup link

**What the auto-lock tee sheet includes:**
- Event name and date
- Each tee time with the players in that group
- Guests labelled with who brought them

Messages queue up and are sent one at a time. If multiple events are open, each gets its own message.

---

## Field Reference

### Create Event Page

| Field | What it does |
|-------|-------------|
| **Saturday / Sunday Swindle** (template buttons) | Auto-fills all fields below with your standard setup. Calculates the next matching Saturday or Sunday for the date. |
| **Event Name** | Display name shown everywhere (signup page, WhatsApp messages, tee sheet). |
| **Date** | The event date. Templates auto-calculate this. |
| **First Tee** | Time of the first tee slot (e.g. 08:24). |
| **Interval (min)** | Minutes between tee times (e.g. 8 = 08:24, 08:32, 08:40...). |
| **Tee Times** | Number of tee time slots. Capacity = tee times x group size. |
| **Max Group Size** | 3-ball or 4-ball. Determines how many players per tee time. |
| **Auto-lock signups** | When checked, signups close automatically at the configured time. Untick to lock manually. |
| **Days before event** | How many days before the event date to auto-lock (1 = day before, 0 = same day). |
| **Lock at** | Time of day to auto-lock (e.g. 17:00). |
| **WhatsApp Group** | Exact name of the WhatsApp group (must match exactly). Leave blank to disable WhatsApp messages for this event. Templates auto-fill this. |

### Event Manage Page

**Share link section:**

| Button | What it does |
|--------|-------------|
| **Copy** | Copies the signup URL to your clipboard. |
| **Share** | Opens WhatsApp with a pre-filled message containing the event name, player count, and signup link. |

**Playing list:**
- Shows all signed-up players numbered, with badges for tee preference (early/late), match play partner (purple), and play-with partners (teal).
- **Remove** — drops that player from the event. If the event is full, the first waitlisted player is automatically promoted.

**Waitlist:**
- Shows players who signed up after capacity was reached, in order.
- **Remove** — drops them from the waitlist.

**Tee Sheet** (appears after locking):
- Preview of all groups and their tee times.
- **Edit** — opens the drag-and-drop tee sheet editor where you can move players between groups.

**Add Player form (right side):**

| Field | What it does |
|-------|-------------|
| **First name / Surname** | The player's name. Required. |
| **Tee preference** (Any / Early / Late) | Tells the tee sheet generator where to place them. "Any" = no preference. |
| **Guests** (+ Add) | Add one or more guests who are playing with this person. Guests count toward capacity. |
| **Match play partner** (expandable) | Their match play opponent. Partner is auto-signed up and they'll be grouped together on the tee sheet. |
| **Play with (up to 3)** (expandable) | Players they want to be grouped with (not match play — just social grouping). Partners are auto-signed up. Up to 3 allowed. |

**Event Controls:**

| Button | What it does |
|--------|-------------|
| **Lock Event** | Closes signups and generates the tee sheet. Players see "Event locked" on the signup page. |
| **Unlock Event** | Re-opens signups. Tee sheet is kept but can be regenerated. |
| **Regenerate Tee Sheet** | Creates a fresh tee sheet from the current player list, replacing the existing one. |

**Tee Times section:**
- Shows all tee time slots for this event.
- **x** — removes a tee time (reduces capacity).
- **Add** — adds a new tee time (increases capacity). Use this if you get an extra slot from the club.

**WhatsApp section** (only shows if a WhatsApp group is set):

| Button | What it does |
|--------|-------------|
| **Send to WhatsApp** (dropdown: Player List / Tee Sheet) | Queues the selected message to be sent via the WhatsApp bot. Takes a few seconds to send. |
| **Copy Player List** | Opens a preview of the player list message — copy it manually if the bot is down. |
| **Copy Tee Sheet** | Opens a preview of the tee sheet message — copy it manually if the bot is down. |

### Public Signup Page (what players see)

| Field | What it does |
|-------|-------------|
| **First name / Surname** | Their name. Required. Remembered by cookie for next time. |
| **Tee time preference** (Any / Early / Late) | Preference for early or late tee time. Defaults to "Any". |
| **Guests** (+ Add a guest) | Add guests they're bringing. Each guest needs a first name and surname. Guests count toward capacity. |
| **Match play partner** (expandable) | Pick an existing player from the dropdown or type a name manually. Partner is auto-signed up. |
| **Play with** (expandable) | Pick up to 3 existing players from the dropdown or type names manually. Partners are auto-signed up and grouped together on the tee sheet. |
| **Edit Signup** | Returning players (recognised by cookie) can change their preferences, guests, or partners. |
| **Remove Signup** | Returning players can remove themselves from the event. |

### Dashboard

| Element | What it does |
|---------|-------------|
| **+ New Event** | Goes to the create event page. |
| **Upcoming events** | Lists open/locked events with player counts. Click to manage. |
| **Completed events** | Lists past events (greyed out). Click to view. |
| **Trash icon** | Deletes an event. Past events delete immediately; upcoming events require the admin PIN. |
| **Logout** | Logs out of the admin panel. |