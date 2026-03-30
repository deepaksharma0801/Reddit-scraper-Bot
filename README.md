# Waymo Reddit Code Scanner — Setup Guide for automated codes

## Step 1: Get Reddit API Credentials (takes ~2 minutes)

1. Go to **https://www.reddit.com/prefs/apps**
2. Scroll down and click **"Create another app..."**
3. Fill in the form:
   - **Name:** `waymo-code-scanner` (anything you like)
   - **Type:** Select **"script"**
   - **Description:** optional
   - **Redirect URI:** `http://localhost:8080` (required but not actually used)
4. Click **"Create app"**
5. You'll see your new app listed. Note down:
   - **Client ID** — the short string just under the app name (looks like: `aBcD1234efGH`)
   - **Client Secret** — labeled "secret" (looks like: `xYz_AbCdEf1234567890`)

---

## Step 2: Add Your Credentials to the Script

Open `waymo_code_scanner.py` and replace the placeholder values near the top: 

```python
CLIENT_ID     = "YOUR_CLIENT_ID_HERE"       # ← paste your Client ID
CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"   # ← paste your Client Secret
USER_AGENT    = "waymo-code-scanner/1.0 (by u/YOUR_REDDIT_USERNAME)"  # ← your Reddit username
```

---

## Step 3: Install the Required Library

Open a terminal and run:

```bash
pip install praw
```

---

## Step 4: Run the Bot

```bash
python waymo_code_scanner.py
```

The bot will scan the Waymo mega referral thread for codes posted in the last 5 hours
and save a `.txt` file in the same folder.

---

## Output Example

```
============================================================
  WAYMO REFERRAL / INVITE CODES — LAST 5 HOURS
  Scanned at : 2026-03-24 09:00
  Source     : https://reddit.com/r/waymo/comments/1qw8cgh/
============================================================

[1] Posted by : u/SomeRedditUser
    Time      : 2026-03-24 06:42 UTC
    Code(s)   : WAYM0XYZ123
    Comment   : Here's my code, feel free to use it!
    Link      : https://reddit.com/r/waymo/comments/1qw8cgh/...
------------------------------------------------------------

Total comments with codes found: 1
```

---

## Automated Daily Runs

This bot is configured to run automatically every day via Cowork's scheduler.
Results will be saved as a new `.txt` file each time it runs.
