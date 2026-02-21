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