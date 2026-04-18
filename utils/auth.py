"""
Authentication helpers for Google Workspace APIs.
Extracted from the original main.py so every session demo can reuse them.
"""

from __future__ import annotations

import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# ── Scopes required by the Inbox Intelligence Agent ──────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]
TIMEZONE = "Asia/Kolkata"

# Path helpers — always resolve relative to the PROJECT ROOT
# so that session scripts in sub-folders find the right files.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, "credentials.json")
TOKEN_PATH = os.path.join(PROJECT_ROOT, "token.json")


def get_credentials() -> Credentials:
    """Return valid Google OAuth2 credentials, refreshing or prompting as needed."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


