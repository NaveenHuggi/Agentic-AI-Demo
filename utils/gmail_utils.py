"""
Gmail helpers — fetch and parse inbox messages.
Extracted from the original main.py.
"""

from __future__ import annotations

import re
from email.utils import parseaddr

from googleapiclient.discovery import build

from utils.auth import get_credentials


def _get_gmail_service():
    return build("gmail", "v1", credentials=get_credentials())


def header_value(headers: list[dict[str, str]], name: str, default: str = "") -> str:
    """Return the value of a specific email header (case-insensitive)."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", default)
    return default


def truncate_text(text: str, limit: int = 120) -> str:
    """Collapse whitespace and truncate with ellipsis."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def fetch_recent_emails(limit: int = 10) -> list[dict[str, str]]:
    """
    Fetch the *limit* most recent INBOX messages.
    Returns a list of dicts with keys:
        id, subject, snippet, from, from_name, from_email, date
    """
    gmail = _get_gmail_service()

    response = (
        gmail.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=limit)
        .execute()
    )

    messages = response.get("messages", [])
    results: list[dict[str, str]] = []

    for msg in messages:
        try:
            data = (
                gmail.users()
                .messages()
                .get(userId="me", id=msg["id"], format="metadata")
                .execute()
            )

            payload = data.get("payload", {})
            headers = payload.get("headers", [])

            subject = header_value(headers, "Subject", "No Subject")
            from_raw = header_value(headers, "From", "")
            date_raw = header_value(headers, "Date", "")
            snippet = data.get("snippet", "")

            from_name, from_email = parseaddr(from_raw)

            results.append(
                {
                    "id": msg["id"],
                    "subject": subject,
                    "snippet": snippet,
                    "from": from_raw,
                    "from_name": from_name or "",
                    "from_email": from_email or "",
                    "date": date_raw or "",
                }
            )
        except Exception as e:
            print("[gmail] skipped one message:", e)

    print(f"[gmail] fetched {len(results)} emails")
    return results


