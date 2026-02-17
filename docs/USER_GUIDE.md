# Sunday Swindle Bot - User Guide

## What is This?

The Sunday Swindle Bot automatically manages your weekly golf tee sheet! It watches your WhatsApp group, figures out who's playing, and creates an organized tee sheet with actual tee times.

**No more manual spreadsheets or confusion!** ⛳

---

## What The Bot Does Automatically

### 1. **Watches Your WhatsApp Group** 👀
The bot reads messages in the "Sunday Swindle" group and figures out who's playing.

### 2. **Understands Natural Language** 🧠
It understands when people say:
- "I'm in"
- "Yes please"
- "Count me in"
- "I'm out" / "Can't make it"
- "Bringing Tom as my guest"

### 3. **Creates Groups** 👥
- Automatically groups players together (4 per group)
- Keeps hosts with their guests
- Respects playing partner preferences
- Avoids pairing people who don't want to play together

### 4. **Assigns Tee Times** ⏰
- Gives actual tee times (e.g., 8:00am, 8:08am, 8:16am)
- Respects time preferences (early birds vs late starters)
- Shows how many tee time slots can be returned to the course

---

## Scheduled Messages You'll Receive

The bot sends messages to the **configured admin** at these times:

| When | What | Why |
|------|------|-----|
| **12:00 PM Every Day** | Health Check | Confirms bot is running |
| **8:00 PM Mon-Sat** | Daily Update | Current player list |
| **5:00 PM Saturday** | Final Tee Sheet | Complete tee sheet for Sunday |

**Note**: The bot won't spam you with constant "UPDATE" messages - it only notifies when the player list actually changes.

---

## Admin Commands

Send these commands in the **"Sunday Swindle - Admin"** WhatsApp group. The bot checks this group **every minute** for fast responses.

### 📋 Viewing Information

**Show the current list:**
```
Show list
```
Shows all signed-up players with their guests.

**Show the tee sheet:**
```
Show tee sheet
```
Shows the complete tee sheet with groups and tee times.

**Show constraints:**
```
Show constraints
```
Shows partner preferences and avoidances.

**Show tee time settings:**
```
Show tee times
```
Shows current tee time configuration.

---

### 👥 Managing Players

**Add a player:**
```
Add John Smith
```

**Remove a player:**
```
Remove Mike Jones
```

**Add a guest:**
```
Add guest Tom for Alex
```

**Remove a guest:**
```
Remove guest Tom
```

---

### 🤝 Setting Preferences

**Set playing partners:**
```
Mike plays with John
```
The bot will try to put them in the same group.

**⭐ Important**: Partner preferences are **remembered forever** and applied automatically every week until you remove them. You only need to set them once!

**What if only one partner plays?** No problem! The bot simply groups the available player with others. The preference remains active for future weeks when both are playing.

**Set avoidances:**
```
Don't pair David with Steve
```
The bot will keep them in separate groups.

**Set time preferences:**
```
Mike prefers early
Dave wants late tee time
```
The bot will assign early/late tee times accordingly.

**Remove preferences:**
```
Remove Mike's partner preference
Remove avoidance for Alex
```

---

### ⏰ Configure Tee Times

**Set tee time settings (auto-generation):**
```
Set tee times from 8:00
```
(The bot will use default 8-minute intervals and 10 slots)

You can be more specific:
```
Configure tee times starting at 8am with 8 minute intervals
```

**Manage individual tee times (additive):**

The bot starts with auto-generated times, then you can add or remove specific times:

```
Add tee time 09:00           # Add specific time to the list
Remove tee time 08:32        # Remove specific time from the list
Clear tee times              # Reset to pure auto-generation
```

**Example:**
- Auto-generated: 08:24, 08:32, 08:40, 08:48, 08:56, 09:04, 09:12
- `Add tee time 09:20` → 08:24, 08:32, 08:40, 08:48, 08:56, 09:04, 09:12, 09:20
- `Remove tee time 08:40` → 08:24, 08:32, 08:48, 08:56, 09:04, 09:12, 09:20

---

## How It All Works Together

### Sunday Swindle Typical Week:

**Monday Morning**
- Organizer posts: "Morning all, now taking names for Sunday"

**Monday-Saturday**
- People sign up in WhatsApp: "I'm in", "Yes please", etc.
- Bot watches the group (checks every hour)
- You receive daily updates at 8pm showing current list

**Saturday 5:00 PM**
- Bot generates final tee sheet
- Sends to Chris with:
  - All groups (optimally filled to 4 players each)
  - Actual tee times assigned
  - How many tee time slots can be returned to course

**If You Need to Make Changes**
- Use admin commands in admin group
- "Add John Smith" if someone signs up outside WhatsApp
- "Remove Mike Jones" if someone cancels
- "Mike plays with John" if partners request to play together
- "Show tee sheet" to see updated groups

---

## Real Examples

### Example 1: Viewing the List

**You send:**
```
Show list
```

**Bot responds:**
```
📋 Sunday Swindle Update

👥 17 signed up (19 total with guests)

• Alex (bringing: John balls) - MP
• Dave Walker - Later tee time
• Mike
• John
• Paul
• Danny Raf
• Adam
[... etc]
```

---

### Example 2: Managing Players

**You send:**
```
Add Tom Smith
```

**Bot responds:**
```
✅ Added Tom Smith

📋 Sunday Swindle Update
👥 18 signed up (20 total with guests)
[Updated list]
```

---

### Example 3: The Tee Sheet

**You send:**
```
Show tee sheet
```

**Bot responds:**
```
🏌️ SUNDAY SWINDLE TEE SHEET 🏌️

📅 16/02/2026

👥 16 players, 4 groups

✅ 6 tee time(s) can be returned


⏰ Group 1 - 08:00
  • Mike
  • John
  • Paul
  • Chris

⏰ Group 2 - 08:08
  • Alex
  • Tom (guest of Alex)
  • Dave Walker
  • Steve

⏰ Group 3 - 08:16
  • Danny Raf
  • Adam
  • Lloyd
  • David Murphy

⏰ Group 4 - 08:24
  • Sam Healy
  • Jordan Thorne
  • Goochie
  • Liam Sewell
```

**What this tells you:**
- 16 players total
- Perfectly grouped into 4 groups of 4
- Tee times start at 8:00am (8-minute intervals)
- 6 tee time slots can be returned (out of 10 available)

---

## Understanding Constraints (Important!)

### 🔄 Constraints Are Permanent

When you set constraints like partner preferences or avoidances, they are **stored permanently** and automatically applied every week.

**You only set them once!**

### Example Timeline:

**Week 1 (Setup)**
```
Lloyd plays with Segan
```
✅ Constraint saved to database

**Week 2 (Both Playing)**
- Lloyd ✅ and Segan ✅ sign up
- Bot automatically pairs them together
- You didn't need to do anything!

**Week 3 (Only One Playing)**
- Only Segan ✅ signs up
- Lloyd ❌ doesn't play this week
- Bot groups Segan with other available players
- Constraint remains active (not deleted)

**Week 4 (Both Back)**
- Lloyd ✅ and Segan ✅ both sign up again
- Bot automatically pairs them together again
- Constraint still working!

### 🎯 Best Practice for Season Start

**At the beginning of the season**, set up all your regular partnerships:
```
Lloyd plays with Segan
Mike plays with John
Alex plays with Tom
Dave wants late tee time
```

Then **forget about them!** The bot applies these automatically every week for the entire season. You never need to re-enter them.

### 🗑️ Removing Constraints

Only remove constraints if preferences change:
```
Remove Lloyd's partner preference
Remove avoidance for David
```

Otherwise, leave them active all season!

---

## 📅 Season-Long vs Weekly Preferences

### What Persists All Season? (Set Once, Use Forever)

**Partner Preferences:**
```
Lloyd plays with Segan
Mike plays with John
```
✅ Set at the start of the season
✅ Automatically applied every week
✅ Never need to re-enter
✅ Only remove if partnerships change

**Avoidances:**
```
Don't pair Mike with John
```
✅ Set once, persist forever
✅ Only remove if situation changes

**Tee Time Settings (Auto-Generation):**
```
Start: 08:24, Interval: 8min, Slots: 7
```
✅ Set once, used every week
✅ Only change if booking changes

### What Resets Each Week? (Must Set Fresh)

**Time Preferences:**
```
Mike prefers early
Dave wants late tee time
```
🔄 Reset automatically each week
🔄 Must be set again if needed
🔄 Why? Players' availability changes week-to-week

**Tee Time Modifications:**
```
Add tee time 09:00
Remove tee time 08:32
```
🔄 Reset each week to start fresh
🔄 Why? Available times change week-to-week

**To Start a New Week:**
```
Clear time preferences    # Clears early/late (keeps partner prefs!)
Clear tee times          # Resets to auto-generation
```

---

## Tips & Best Practices

### ✅ Do's
- **Trust the AI** - It's very accurate at detecting signups
- **Use natural language** - "Mike plays with John" works just as well as formal commands
- **Check the daily updates** - Stay informed without manually counting
- **Use the admin group** - Fast 1-minute response time for commands

### ❌ Don'ts
- **Don't manually edit the main group** - Let people sign up naturally
- **Don't worry about duplicates** - The bot handles guest duplicates automatically
- **Don't spam commands** - One command at a time, wait for response

### 💡 Pro Tips
- Set partner preferences early in the week (they'll be applied when the final sheet is generated)
- Use time preferences for players who consistently want early/late times
- Check "Show tee times" to see how many slots are available
- The bot ignores messages before the organizer posts "now taking names"

---

## Troubleshooting

### "The bot didn't respond to my command"
- Make sure you're in the **admin group** ("Sunday Swindle - Admin")
- Wait 1 minute (bot checks every minute)
- Check your command spelling

### "A player is missing from the list"
- Check if they signed up before the organizer posted "now taking names"
- Use "Add [Name]" to manually add them
- The AI might have thought they were asking a question rather than signing up

### "Groups look wrong"
- Check "Show constraints" to see if there are preferences affecting grouping
- Manually adjust with "Add" and "Remove" commands if needed
- Remember: The bot optimizes for full groups (4 players each)

### "Who do I contact for help?"
Contact your bot administrator - the person who receives all bot messages

---

## Quick Command Reference

| What You Want | Command Example |
|---------------|-----------------|
| See the list | `Show list` |
| See tee sheet | `Show tee sheet` |
| Add someone | `Add John Smith` |
| Remove someone | `Remove Mike Jones` |
| Add a guest | `Add guest Tom for Alex` |
| Set partners | `Mike plays with John` |
| Set avoidance | `Don't pair Alex with Tom` |
| Set time pref | `Mike prefers early` |
| Show settings | `Show tee times` |
| Show constraints | `Show constraints` |
| Add tee time | `Add tee time 09:00` |
| Remove tee time | `Remove tee time 08:32` |
| Clear tee times | `Clear tee times` |
| Clear time prefs | `Clear time preferences` |
| Add tee time | `Add tee time 09:00` |
| Remove tee time | `Remove tee time 08:32` |
| Clear tee times | `Clear tee times` |
| Clear time prefs | `Clear time preferences` |

---

## Summary

**The bot handles everything automatically:**
1. ✅ Monitors WhatsApp for signups
2. ✅ Understands natural language ("I'm in", "Yes please")
3. ✅ Creates optimized groups (4 players each when possible)
4. ✅ Assigns actual tee times
5. ✅ Sends you the final tee sheet Saturday at 5pm

**You only need to:**
- Let players sign up in WhatsApp naturally
- Use admin commands if manual adjustments are needed
- Check the Saturday 5pm tee sheet

**No more spreadsheets. No more manual counting. Just golf! ⛳**

---

**Questions?** Ask your bot administrator

**Last Updated**: February 2026
