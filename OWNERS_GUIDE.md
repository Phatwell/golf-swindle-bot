# Shanks Bot - Owner's Guide

## What is Shanks Bot?

Shanks Bot is a WhatsApp assistant that helps manage the Sunday Swindle. It monitors the main group chat, keeps track of who's playing, handles reserves, and generates tee sheets with groups and times — all automatically.

It uses AI to read the WhatsApp messages and work out who's in, who's out, who's bringing a guest, and who wants to play with who.

---

## Proof of Concept — What This Means For You

Right now, Shanks Bot is in **proof of concept** mode. This means:

- **Carry on doing what you're normally doing** — manage the swindle as you always have
- The bot posts everything into the **admin channel only** (not the main group)
- You can check what the bot is doing in the admin channel and see if it's getting things right
- **Forward messages from the admin channel into the main chat** when you're happy with what it's produced (e.g., the tee sheet, the player list)
- Once we're confident everything is working properly, we can move the bot to post directly into the main group

---

## Your Workflow This Week

Starting this Monday, here's what to do:

1. **Carry on as normal** — create your player list and tee sheet manually like you always do
2. **Keep an eye on the admin channel** — the bot will post its own player lists and tee sheet there throughout the week
3. **Compare** — when the bot posts a player list or tee sheet, check it against your own. Does it match?
4. **If it matches, just forward it** — instead of typing it out yourself, forward the bot's message from the admin channel into the main group. Saves you the job.
5. **If it doesn't match, use your own** — post your manual version as normal and let Chris know what the bot got wrong so we can fix it

Over time, the idea is that you'll be forwarding the bot's messages more and more until you're confident enough to let it post directly. No rush — take as many weeks as you need.

**In short:** The bot does the work, you check it, and forward it if it's right. You're always in control.

---

## What Does The Bot Do Automatically?

### Weekly Schedule

| When | What happens |
|------|-------------|
| **Monday 00:01** | Wipes the slate clean for the new week (clears players, tee sheet, time preferences). Partner preferences are kept. |
| **Monday 10:00** | Posts a "taking names for Sunday" message in the admin channel |
| **Mon-Fri 10:00, 15:30, 20:00** | Posts an updated player list to the admin channel |
| **Saturday 10:00** | Posts the player list one last time before the tee sheet |
| **Saturday 17:00** | Generates the **final tee sheet** and locks it in |
| **Every day 12:00** | Health check — just lets you know the bot is still running |

### Between Scheduled Messages

- Every **10 minutes**, the bot checks the main group for new messages
- If someone signs up or drops out, it updates the player list automatically
- If there's already a published tee sheet (after Saturday 5pm), it **auto-updates** the tee sheet when players change and posts the updated version

---

## Admin Commands

You can send these commands in the **admin group chat** and the bot will respond:

### Player Management
- **"Show list"** — See all current players and reserves
- **"Add Chris"** — Manually add a player
- **"Remove Chris"** — Remove a player (reserves get promoted automatically)
- **"Add guest for Chris"** — Add a guest for a player
- **"Remove guest from Chris"** — Remove a guest

### Tee Sheet
- **"Show tee sheet"** — See the current tee sheet
- **"Randomize"** — Generate a completely new random tee sheet
- **"Swap Chris with Kenny"** — Swap two players between groups
- **"Move Chris to group 3"** — Move a player to a specific group
- **"Clear tee sheet"** — Remove the published tee sheet entirely

### Preferences & Constraints
- **"Chris plays with Kenny"** — Set a partner preference (they'll be grouped together)
- **"Remove Chris's preference"** — Remove a partner preference
- **"Don't pair Chris with Kenny"** — Set an avoidance (keep them apart)
- **"Chris prefers late"** — Set a late tee time preference
- **"Chris prefers early"** — Set an early tee time preference
- **"Remove late tee time preference for Chris"** — Remove a player's time preference
- **"Show constraints"** — See all partner preferences, avoidances, and time preferences

### Tee Time Settings
- **"Show tee times"** — See the current tee time slots
- **"Set tee times from 08:24"** — Configure the starting tee time
- **"Add tee time 09:20"** — Add an extra tee time slot
- **"Remove tee time 09:12"** — Remove a tee time slot
- **"Clear tee times"** — Reset back to default tee times
- **"Clear time preferences"** — Clear ALL players' early/late preferences

---

## How Do Reserves Work?

The bot calculates capacity based on the number of tee time slots:

> **Total spots = Number of tee times x 4**
>
> With 7 tee times: 7 x 4 = **28 playing spots**

- Players 1-28 are **playing**
- Player 29 onwards are on the **reserve list** (first come, first served)
- If someone drops out, the next reserve is **automatically promoted** and the bot lets you know
- If you add an extra tee time, that creates 4 more spots and reserves may get promoted

---

## FAQ

### When does the tee sheet get created?

The bot automatically generates the final tee sheet at **Saturday 5pm**. You can also generate one at any time by sending **"Show tee sheet"** or **"Randomize"** in the admin group.

### What's the difference between "Show tee sheet" and "Randomize"?

- **"Show tee sheet"** — If a tee sheet has already been published, it shows the same one (with minor adjustments if players changed). If no tee sheet exists yet, it generates a fresh one.
- **"Randomize"** — Always generates a completely new tee sheet from scratch with different group assignments.

### What happens if someone drops out after the tee sheet is published?

The bot automatically detects the change and updates the tee sheet. It removes the player, merges any small groups, and posts the updated sheet to the admin channel. You don't need to do anything.

### What happens if someone new signs up after the tee sheet is published?

Same as above — the bot detects the new player, adds them to a group with space, and posts the updated sheet.

### Can I change groups after the tee sheet is published?

Yes! Use **"Swap Chris with Kenny"** to swap two players between groups, or **"Move Chris to group 3"** to move someone to a specific group. The bot updates and re-posts the sheet.

### How do partner preferences work?

If you set **"Chris plays with Kenny"**, the bot will always try to put them in the same group when generating the tee sheet. These preferences are **season-long** — they persist week to week until you remove them.

### How do time preferences work?

If you set **"Chris prefers late"**, the bot will try to put Chris in one of the later tee time groups. You can also set **"early"**. These are **cleared each week** on Monday with the weekly reset.

### What gets wiped each Monday?

**Cleared:**
- Player list (everyone needs to sign up again)
- Time preferences (early/late)
- Published tee sheet
- Any manual tee time changes

**Kept (season-long):**
- Partner preferences (e.g., "Chris plays with Kenny")
- Tee time settings (start time, interval, number of slots)

### What if the bot gets something wrong?

That's exactly what the proof of concept phase is for! Since everything goes to the admin channel first, you can check it before forwarding to the main group. If something looks off, you can use the admin commands to fix it (swap players, move players, add/remove people, etc.) or just do it manually as you normally would.

### How does the bot know who's playing?

The bot uses AI to read the messages in the main group. It picks up phrases like:

**Signing up:**
- "I'm in", "yes please", "count me in", "me", "please", "yes"

**Signing up others:**
- "Me and John please" — signs up both the sender AND John as separate players
- "Me, Mitch and Ken please" — signs up all three as separate players

**Dropping out:**
- "I'm out", "can't make it", mentioning illness

**Guests:**
- "Me +1" or "can I have a guest" — adds an anonymous guest (named "YourName-Guest")
- "Bringing Dave" — adds Dave as a named guest (if Dave isn't already a group member)

**Match Play pairings:**
- "Me and John for MP please" — signs up both AND pairs them together for match play

**Things the bot ignores:**
- Questions, banter, emoji reactions, organisational chat
- Messages from before the "taking names" post

It checks for new messages every 10 minutes, so there may be a short delay between someone signing up and the bot picking it up.

### What about Match Play (MP) pairings?

When someone says something like "me and John for MP", the bot picks up that both players want to be **paired together** for match play. These pairings:

- Are detected automatically from the chat messages
- Last for the current week only (cleared on Monday with the weekly reset)
- Mean the two players will be put in the **same group** on the tee sheet
- Show up under "Show constraints" as MP Pairings

You can also manually set or remove pairings using the partner preference commands.

### How are guests handled?

Guests are **always kept with their host** — they'll never be split into different groups.

- If someone says "+1" or "can I have a guest", the bot creates an anonymous guest called "YourName-Guest"
- If someone says "bringing Dave", Dave is added as a named guest
- The host and their guest(s) are treated as one block when building groups
- If a host is moved or swapped, their guest(s) move with them
- Guests count towards the group size (max 4 per group) and the overall capacity

**Example:** If Scotty brings a guest, they take up 2 spots. They'll always be in the same group, and there's room for 2 more players in that group.

### What about recap messages?

If the organiser posts a numbered or bulleted list of names (a recap/roll call), the bot treats **every name on that list** as a confirmed player — even if that person never sent a message themselves. This is useful for confirming the final list.

The bot also uses the names from the recap as the "official" player names, so if someone's WhatsApp name is "KennyD" but the recap says "Kenny Davis", the bot will use "Kenny Davis".

### What if someone's name is wrong?

The bot uses WhatsApp display names. If someone's display name is just their first name or a nickname, the bot might not recognise them correctly. The best fix is for players to set their WhatsApp display name to their **full name** (Settings > tap your name > edit).

For persistent issues, we can add name mappings behind the scenes (e.g., telling the bot that "KennyD" is actually "Kenny Davis").

---

## Need Help?

If something isn't working or you have questions, get in touch with Chris and we'll sort it out.