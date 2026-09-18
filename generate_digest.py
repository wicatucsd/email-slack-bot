"""
Reads threads_summary.json (produced by gmail_analyze.py), formats a
weekly digest directly (no LLM involved), and posts it to Slack via an
Incoming Webhook.

Run this LOCALLY, after running gmail_analyze.py.

Setup (if not already installed):
    pip install requests

Environment variables required:
    SLACK_WEBHOOK_URL   - the webhook URL from Slack's Incoming Webhooks setup

Usage:
    py generate_digest.py
"""

import json
import os
from datetime import datetime, timedelta
from collections import Counter

import requests

SUMMARY_FILE = "threads_summary.json"

CATEGORY_HEADERS = {
    "needs_label": ":label: *Missing Label*",
    "needs_first_reply": ":envelope: *Unread*",
    "awaiting_reply": ":hourglass_flowing_sand: *Awaiting Reply*",
}
CATEGORY_ORDER = ["needs_label", "needs_first_reply", "awaiting_reply"]
SLACK_WEBHOOK_FILE = "slack_api_key.json"
DAYS_BACK = 7

def load_threads():
    with open(SUMMARY_FILE) as f:
        data = json.load(f)
    return data["threads"], data["days_back"]

def format_thread_line(t, num):
    days = t["days_waiting"]
    day_str = "today" if days == 0 else f"{days}d"
    labels = ", ".join(t["labels"]) if t["labels"] else "no label"
    sender = t["last_from"].split("<")[0].strip() or t["last_from"]
    return f"{num}. *{t['subject']}* — from {sender} ({day_str}, {labels})"

def count_labels(threads):
    counter = Counter()
    for t in threads:
        for label in t["labels"]:
            counter[label] += 1
    if not counter:
        return {}
    return dict(counter.most_common())

def get_date_range_str(days_back=DAYS_BACK):
    end = datetime.now()
    start = end - timedelta(days=days_back)
    return f"{start.strftime('%b %d')} to {end.strftime('%b %d')}"

def build_digest_text(threads, days_back):
    # Handled threads are noise for a "who needs to act" digest
    actionable = [t for t in threads if t["category"] != "handled"]

    if not actionable:
        return "No action-needed emails this week — inbox is fully caught up! :tada:"

    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for t in actionable:
        grouped.setdefault(t["category"], []).append(t)

    date_range = get_date_range_str(days_back)
    lines = [f":email: *WIC's Weekly Inbox Summary* — ({date_range})\nNEEDS REVIEW: {len(actionable)} email(s)\n"]

    for cat in CATEGORY_ORDER:
        items = grouped.get(cat, [])
        if not items:
            continue
        lines.append(f"{CATEGORY_HEADERS[cat]}: {len(items)} Item(s)")
        for i, t in enumerate(items, start=1):
            lines.append(format_thread_line(t, i))
        lines.append("")  # blank line between sections

    return "\n".join(lines).strip()


def post_to_slack(text):
    with open(SLACK_WEBHOOK_FILE) as f:
        config = json.load(f)
    webhook_url = config["url"]

    payload = {"text": text}
    resp = requests.post(webhook_url, json=payload)
    resp.raise_for_status()
    print("Posted to Slack successfully.")


def main():
    threads, days_back = load_threads()
    digest = build_digest_text(threads, days_back)

    print("----- Generated digest -----")
    print(digest)
    print("-----------------------------")

    post_to_slack(digest)


if __name__ == "__main__":
    main()