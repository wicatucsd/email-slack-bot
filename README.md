# WIC's Slack Gmail Bot

This bot provides a weekly summary of missed Gmails for WIC officers on Slack every **Monday at 8:00 AM**. Below is a short guide of this repository.

---
## Automating the Bot
This section covers how to automate `gmail_analyze.py` and `generate_digest.py` to run automatically every **Monday at 8:00 AM**, using Windows Task Scheduler.

### Overview

The automation has two pieces:

1. **A batch file** (`auto-script\run_digest.bat`) that runs both Python scripts in the correct order
2. **A Windows Task Scheduler task** that triggers the batch file weekly

**Important:** `gmail_analyze.py` must run first — it generates/refreshes `threads_summary.json`, which `generate_digest.py` then reads from. Running them out of order (or only running the second one) will fail or post stale data.

### Test it manually first

Before scheduling anything, double-click `run_digest.bat` (or run it from a terminal) to confirm both scripts execute cleanly and the digest posts to Slack successfully. Fix any errors here before moving to Task Scheduler — it's much easier to debug interactively than after it's hidden inside a scheduled task.

### Step 1: Open Task Scheduler

1. Press `Win + R`
2. Type `taskschd.msc` and hit Enter

### Step 2: Create the task

1. In the right-hand panel, click **Create Basic Task...**
2. **Name:** `WIC Weekly Inbox Digest` → **Next**
3. **Trigger:** select **Weekly** → **Next**
4. Set:
   - **Start date:** any upcoming Sunday
   - **Start time:** `11:59:00 PM`
   - Check the box for **Sunday** only
   → **Next**
5. **Action:** select **Start a program** → **Next**
6. **Program/script:** click **Browse...** and select `run_digest.bat`
7. Click **Next**, review the summary, then **Finish**

### Step 3: Recommended settings tweaks

Find your new task in the Task Scheduler Library, right-click it, and select **Properties**. Adjust the following:
- General tab
  - Check **"Run whether user is logged on or not"** if you want the digest to post even when you're not actively logged into Windows.
    - Note: you'll be prompted to enter your Windows account password once, so the task can run with saved credentials.
- Conditions tab
  - Uncheck **"Start the task only if the computer is on AC power"** — especially important if this runs on a laptop that might be on battery at 8:00 AM.
- Settings tab
  - Check **"Run task as soon as possible after a scheduled start is missed"** — this way, if the computer is asleep or off at the exact scheduled time, it'll still run once the computer wakes up/turns on.

---

## Security reminder

- Never commit `slack_api_key.json` or `token.json` to GitHub — both should be listed in your `.gitignore`.
- If a Slack webhook URL or Gmail token is ever exposed (e.g. pasted somewhere, committed accidentally), rotate/revoke it immediately:
  - **Slack:** App settings → Incoming Webhooks → revoke → generate new
  - **Gmail token:** revoke access via [Google Account → Security → Third-party access](https://myaccount.google.com/permissions), then re-run the OAuth flow to get a fresh `token.json`
 
---

## Block Formatting Tips

If you would like to change the format/layout of the bot's messages, use Slack's [Block Kit builder](https://api.slack.com/tools/block-kit-builder).
