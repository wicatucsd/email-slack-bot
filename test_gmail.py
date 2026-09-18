"""
Quick test to confirm Gmail API access is working end-to-end.
Run this LOCALLY, in the same folder as token.json.

Setup (if not already installed):
    pip install google-auth google-api-python-client

Usage:
    python test_gmail.py
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = "token.json"


def main():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    service = build("gmail", "v1", credentials=creds)

    # Pull unread messages from the last 7 days
    results = service.users().messages().list(
        userId="me",
        q="is:unread newer_than:7d",
        maxResults=10
    ).execute()

    messages = results.get("messages", [])
    print(f"Found {len(messages)} unread message(s) from the last 7 days.\n")

    for msg_meta in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_meta["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        print(f"From:    {headers.get('From', '(unknown)')}")
        print(f"Subject: {headers.get('Subject', '(no subject)')}")
        print(f"Date:    {headers.get('Date', '(unknown)')}")
        print(f"Labels:  {msg.get('labelIds', [])}")
        print("-" * 50)


if __name__ == "__main__":
    main()