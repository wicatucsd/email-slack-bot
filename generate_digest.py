"""
Reads threads_summary.json (produced by gmail_analyze.py), formats a
weekly digest as Slack Block Kit, and posts it via an Incoming Webhook.
"""

import json
from datetime import datetime, timedelta

import requests

SUMMARY_FILE = "threads_summary.json"
SLACK_WEBHOOK_FILE = "keys/slack_api_key.json"
DAYS_BACK = 7

CATEGORY_META = {
    "needs_first_reply": {"emoji": "incoming_envelope", "title": "Unread", "desc": "Make sure that the following Gmail(s) are read and responded to:"},
    "needs_label": {"emoji": "label", "title": "Missing Label", "desc": "Make sure that the following Gmail(s) are labeled correctly:"},
    "awaiting_reply": {"emoji": "hourglass_flowing_sand", "title": "Awaiting Reply", "desc": "Make sure that the following Gmail(s) are replied to:"},
}
CATEGORY_ORDER = ["needs_first_reply", "needs_label", "awaiting_reply"]


def load_threads():
    with open(SUMMARY_FILE) as f:
        data = json.load(f)
    return data["threads"], data["days_back"]


def get_date_range_str(days_back=DAYS_BACK):
    end = datetime.now()
    start = end - timedelta(days=days_back)
    return f"{start.strftime('%b %d')} to {end.strftime('%b %d')}"


def format_thread_line(t):
    days = t["days_waiting"]
    day_str = "today" if days == 0 else f"{days}d"
    labels = ", ".join(t["labels"]) if t["labels"] else "no label"
    sender = t["last_from"].split("<")[0].strip() or t["last_from"]
    return f"{t['subject']} — from {sender} ({day_str}, {labels})"


def category_rich_text_block(cat, items):
    meta = CATEGORY_META[cat]
    return {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_section",
                "elements": [
                    {"type": "emoji", "name": meta["emoji"], "style": {"bold": True}},
                    {"type": "text", "text": f" {meta['title']} ({len(items)})", "style": {"bold": True}},
                    {"type": "text", "text": "\n"},
                ]
            },
            {
                "type": "rich_text_section",
                "elements": [{"type": "text", "text": meta["desc"]}]
            },
            {
                "type": "rich_text_list",
                "style": "bullet",
                "indent": 0,
                "border": 0,
                "elements": [
                    {"type": "rich_text_section", "elements": [{"type": "text", "text": format_thread_line(t)}]}
                    for t in items
                ]
            }
        ]
    }


def build_digest_blocks(threads, days_back):
    actionable = [t for t in threads if t["category"] != "handled"]
    date_range = get_date_range_str(days_back)

    if not actionable:
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"˖.✦💜 WIC's Weekly Inbox Summary ({date_range}) 💜✦.˖", "emoji": True}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "No action-needed emails this week — inbox is fully caught up! :tada:"}
            }
        ]

    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for t in actionable:
        grouped.setdefault(t["category"], []).append(t)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"˖.✦💜 WIC's Weekly Inbox Summary ({date_range}) 💜✦.˖", "emoji": True}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Hi there! This is a weekly reminder to organize and catch up on our Gmails."}]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"There are currently :exclamation: *{len(actionable)} Gmail(s)* :exclamation: that need to be reviewed. Below are each of the unreviewed Gmail(s) sorted by issue!\n\nPlease ensure that these are reviewed by the *end of the week*."
            },
            "accessory": {
                "type": "image",
                "image_url": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOWlmZ3cxZ2dqZjIwbm9ydzBsZHk1NHZxbDE2dWVpdXg0dGl4cW4waCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/NTur7XlVDUdqM/giphy.gif",
                "alt_text": "This is fine"
            }
        },
        {"type": "divider"},
    ]

    for cat in CATEGORY_ORDER:
        items = grouped.get(cat, [])
        if not items:
            continue
        blocks.append(category_rich_text_block(cat, items))
        blocks.append({"type": "divider"})

    return blocks


def post_to_slack(blocks):
    with open(SLACK_WEBHOOK_FILE) as f:
        config = json.load(f)
    webhook_url = config["url"]

    payload = {"blocks": blocks}
    resp = requests.post(webhook_url, json=payload)
    resp.raise_for_status()
    print("Posted to Slack successfully.")


def main():
    threads, days_back = load_threads()
    blocks = build_digest_blocks(threads, days_back)

    print("----- Generated digest -----")
    print(json.dumps(blocks, indent=2))
    print("-----------------------------")

    post_to_slack(blocks)


if __name__ == "__main__":
    main()