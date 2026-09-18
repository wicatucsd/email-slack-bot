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

import requests

SUMMARY_FILE = "threads_summary.json"

CATEGORY_HEADERS = {
    "needs_label": ":label: *Needs an owner assigned* (no committee label)",
    "needs_first_reply": ":envelope: *Needs a first reply* (unread)",
    "awaiting_reply": ":hourglass_flowing_sand: *Awaiting reply* (read, not answered)",
}
CATEGORY_ORDER = ["needs_label", "needs_first_reply", "awaiting_reply"]
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"


def load_threads():
    with open(SUMMARY_FILE) as f:
        return json.load(f)


def format_thread_line(t):
    days = t["days_waiting"]
    day_str = "today" if days == 0 else f"{days}d"
    labels = ", ".join(t["labels"]) if t["labels"] else "no label"
    # Trim a full "Name <email@domain>" sender down to just the name/email
    sender = t["last_from"].split("<")[0].strip() or t["last_from"]
    return f"- *{t['subject']}* — from {sender} ({day_str}, {labels})"


def build_digest_text(threads):
    # Handled threads are noise for a "who needs to act" digest
    actionable = [t for t in threads if t["category"] != "handled"]

    if not actionable:
        return "No action-needed emails this week — inbox is fully caught up! :tada:"

    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for t in actionable:
        grouped.setdefault(t["category"], []).append(t)

    lines = [f":email: *WIC Inbox Digest* — {len(actionable)} thread(s) need attention\n"]

    for cat in CATEGORY_ORDER:
        items = grouped.get(cat, [])
        if not items:
            continue
        lines.append(CATEGORY_HEADERS[cat])
        for t in items:
            lines.append(format_thread_line(t))
        lines.append("")  # blank line between sections

    return "\n".join(lines).strip()


def post_to_slack(text):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    payload = {"text": text}
    resp = requests.post(webhook_url, json=payload)
    resp.raise_for_status()
    print("Posted to Slack successfully.")


def main():
    threads = load_threads()
    digest = build_digest_text(threads)

    print("----- Generated digest -----")
    print(digest)
    print("-----------------------------")

    post_to_slack(digest)


if __name__ == "__main__":
    main()