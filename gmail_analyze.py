"""
Pulls recent WIC inbox threads, maps label IDs to readable names, and
classifies each thread by what action (if any) it needs.

Run this LOCALLY, in the same folder as token.json.

Setup (if not already installed):
    pip install google-auth google-api-python-client

Usage:
    py gmail_analyze.py
"""

import json
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = "token.json"
DAYS_BACK = 7

# Gmail's built-in system labels we don't want to treat as "committee" labels
SYSTEM_LABEL_PREFIXES = ("CATEGORY_", "CHAT")
SYSTEM_LABEL_NAMES = {
    "INBOX", "UNREAD", "IMPORTANT", "STARRED", "SENT", "DRAFT",
    "SPAM", "TRASH", "SNOOZED",
}


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    return build("gmail", "v1", credentials=creds)


def get_label_map(service):
    """Returns {label_id: label_name} for every label in the mailbox."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    return {label["id"]: label["name"] for label in labels}


def get_own_email(service):
    """The inbox's own address, used to tell 'we replied' from 'they wrote in'."""
    profile = service.users().getProfile(userId="me").execute()
    return profile["emailAddress"].lower()


def list_recent_thread_ids(service, days=DAYS_BACK):
    query = f"newer_than:{days}d"
    thread_ids = []
    page_token = None
    while True:
        resp = service.users().threads().list(
            userId="me", q=query, pageToken=page_token
        ).execute()
        thread_ids.extend(t["id"] for t in resp.get("threads", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return thread_ids


def get_thread(service, thread_id):
    return service.users().threads().get(
        userId="me", id=thread_id, format="metadata",
        metadataHeaders=["From", "To", "Subject", "Date"]
    ).execute()


def committee_labels_for_thread(thread, label_map):
    """Non-system label names attached to any message in the thread."""
    label_ids = set()
    for msg in thread["messages"]:
        label_ids.update(msg.get("labelIds", []))

    names = set()
    for lid in label_ids:
        name = label_map.get(lid)
        if not name:
            continue
        if name in SYSTEM_LABEL_NAMES:
            continue
        if any(name.startswith(p) for p in SYSTEM_LABEL_PREFIXES):
            continue
        names.add(name)
    return sorted(names)


def classify_thread(thread, own_email):
    """
    Classifies a thread into one of:
      - 'needs_first_reply': last message is from someone else and unread
      - 'awaiting_reply': last message is from someone else (read, but no
         reply sent yet)
      - 'handled': last message in the thread was sent by us
    Also returns how many days it's been sitting since that last message.
    """
    messages = thread["messages"]
    last_msg = messages[-1]

    headers = {h["name"]: h["value"] for h in last_msg["payload"]["headers"]}
    from_addr = headers.get("From", "").lower()
    subject = headers.get("Subject", "(no subject)")

    is_from_us = own_email in from_addr
    is_unread = "UNREAD" in last_msg.get("labelIds", [])

    last_ts = int(last_msg["internalDate"]) / 1000
    last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
    days_waiting = (datetime.now(timezone.utc) - last_dt).days

    if is_from_us:
        category = "handled"
    elif is_unread:
        category = "needs_first_reply"
    else:
        category = "awaiting_reply"

    return {
        "thread_id": thread["id"],
        "subject": subject,
        "last_from": headers.get("From", ""),
        "category": category,
        "days_waiting": days_waiting,
        "message_count": len(messages),
    }


def needs_triage(labels):
    """True if a thread has no committee label attached — unclear owner.
    Used to promote a thread's category to 'needs_label' below."""
    return len(labels) == 0


def main():
    service = get_service()
    own_email = get_own_email(service)
    label_map = get_label_map(service)

    thread_ids = list_recent_thread_ids(service)
    print(f"Found {len(thread_ids)} thread(s) active in the last {DAYS_BACK} days.\n")

    results = []
    for tid in thread_ids:
        thread = get_thread(service, tid)
        classification = classify_thread(thread, own_email)
        labels = committee_labels_for_thread(thread, label_map)
        classification["labels"] = labels
        classification["reply_status"] = classification["category"]  # keep original detail

        # An unlabeled thread's real blocker is "nobody's claimed this" —
        # that supersedes reply status for anything still actionable.
        if classification["category"] != "handled" and needs_triage(labels):
            classification["category"] = "needs_label"

        results.append(classification)

    # needs_label first (unclear owner blocks everything else), then by
    # reply urgency, then handled last
    priority = {"needs_label": 0, "needs_first_reply": 1, "awaiting_reply": 2, "handled": 3}
    results.sort(key=lambda r: (priority[r["category"]], -r["days_waiting"]))

    # 'handled' threads don't need anyone's attention, so leave them out of
    # what officers actually see week to week
    actionable = [r for r in results if r["category"] != "handled"]

    for r in actionable:
        reply_note = f" (reply status: {r['reply_status']})" if r["category"] == "needs_label" else ""
        print(f"[{r['category']:>17}] ({r['days_waiting']}d) {r['subject']}{reply_note}")
        print(f"    From: {r['last_from']}")
        print(f"    Labels: {', '.join(r['labels']) or '(none)'}")
        print("-" * 60)

    handled_count = len(results) - len(actionable)
    print(f"\n({handled_count} handled thread(s) omitted from the list above)")

    output = {
        "days_back": DAYS_BACK,
        "threads": results,
    }
    # Full results (including handled) still saved for the digest step
    with open("threads_summary.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved full results to threads_summary.json")


if __name__ == "__main__":
    main()