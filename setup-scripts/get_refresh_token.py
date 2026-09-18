"""
One-time script to authorize this app against a Gmail account and obtain
a refresh token. Run this LOCALLY on your machine (it opens a browser).

Setup:
    pip install google-auth-oauthlib google-api-python-client

Usage:
    1. Put your downloaded client_secret_*.json in the same folder as this
       script, and update CLIENT_SECRET_FILE below to match its filename.
    2. Run: python get_refresh_token.py
    3. A browser window opens. Log into the WIC INBOX ACCOUNT (not your
       personal account) and approve access.
    4. The script prints your refresh token and also saves it to
       token.json in this folder.

Keep token.json and the client secret file private (don't commit to git,
don't share in chat, etc.) — anyone with the refresh token can read the
WIC inbox until it's revoked.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

# Update this to match your downloaded file's exact name
CLIENT_SECRET_FILE = "client_secret_694867578479-hare0iifa2kso17iloeotei36f0vg7db.apps.googleusercontent.com.json"

# Read-only Gmail access — matches what you enabled in Cloud Console
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    # Opens a local browser window for the OAuth consent flow
    creds = flow.run_local_server(port=0)

    print("\nAuthorization successful!")
    print(f"Refresh token: {creds.refresh_token}")

    with open("token.json", "w") as f:
        f.write(creds.to_json())
    print("\nFull credentials saved to token.json")
    print("Keep this file private — it grants read access to the WIC inbox.")

if __name__ == "__main__":
    main()