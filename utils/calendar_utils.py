"""
Google Calendar helpers — create events with Meet links.
Extracted from the original main.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from utils.auth import TIMEZONE, get_credentials


def _get_calendar_service():
    return build("calendar", "v3", credentials=get_credentials())


def create_calendar_event(time_str: str, attendees: list[str], title: str) -> str:
    """
    Create a 30-minute Google Calendar event with a Meet link.

    Args:
        time_str:   Start time as "YYYY-MM-DD HH:MM"
        attendees:  List of email addresses to invite
        title:      Event title / summary

    Returns:
        The HTML link to the newly created event.
    """
    if not time_str or time_str == "NONE":
        raise ValueError("No meeting time found")

    calendar = _get_calendar_service()

    start = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=30)

    # Deduplicate and validate attendees
    unique_attendees = []
    seen: set[str] = set()
    for a in attendees:
        a = a.strip().lower()
        if a and "@" in a and a not in seen:
            seen.add(a)
            unique_attendees.append({"email": a})

    event = {
        "summary": title or "AI Scheduled Meeting",
        "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
        "attendees": unique_attendees,
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    created = (
        calendar.events()
        .insert(
            calendarId="primary",
            body=event,
            conferenceDataVersion=1,
            sendUpdates="all",
        )
        .execute()
    )

    return created.get("htmlLink", "")


