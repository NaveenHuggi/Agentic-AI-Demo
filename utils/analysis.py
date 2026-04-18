"""
Rule-based inbox analysis — the BASELINE intelligence.
This is the keyword-matching logic from the original main.py.
Sessions 1-4 progressively replace this with LLM-powered intelligence.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

# ── Keyword banks ────────────────────────────────────────────
MEETING_KEYWORDS = [
    "meeting", "discuss", "call", "sync", "schedule",
    "agenda", "catch up", "standup", "stand-up",
    "huddle", "conference", "meet",
]
URGENT_KEYWORDS = [
    "urgent", "asap", "immediately", "critical", "important", "priority",
]
TASK_KEYWORDS = [
    "deadline", "submit", "complete", "action required",
    "task", "please do", "finish",
]

# ── Regex patterns for time extraction ───────────────────────
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOMORROW_PATTERN = re.compile(
    r"\btomorrow(?:\s+at)?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
    re.IGNORECASE,
)
DAY_TIME_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"(?:\s+at)?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
    re.IGNORECASE,
)
DAY_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


# ── Helpers ──────────────────────────────────────────────────
def _normalize_hour(hour: int, ampm: str | None) -> int:
    if not ampm:
        return hour
    ampm = ampm.lower()
    if ampm == "pm" and hour != 12:
        return hour + 12
    if ampm == "am" and hour == 12:
        return 0
    return hour


def summarize_email(email: dict[str, str]) -> str:
    subject = (email.get("subject") or "").strip() or "(no subject)"
    snippet = re.sub(r"\s+", " ", email.get("snippet", "") or "").strip()
    snippet = snippet[:120].rstrip() + "..." if len(snippet) > 120 else snippet
    return f"{subject} — {snippet}" if snippet else subject


def categorize_email(email: dict[str, str]) -> str:
    text = f"{email.get('subject', '')} {email.get('snippet', '')}".lower()
    if any(k in text for k in URGENT_KEYWORDS):
        return "urgent"
    if any(k in text for k in MEETING_KEYWORDS):
        return "meeting"
    if any(k in text for k in TASK_KEYWORDS):
        return "task"
    return "info"


def detect_meeting_emails(emails: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        e for e in emails
        if any(k in f"{e.get('subject','')} {e.get('snippet','')}".lower()
               for k in MEETING_KEYWORDS)
    ]


def extract_time_from_text(text: str) -> str:
    now = datetime.now()

    m = TOMORROW_PATTERN.search(text)
    if m:
        hour = _normalize_hour(int(m.group(1)), m.group(3))
        minute = int(m.group(2) or 0)
        dt = (now + timedelta(days=1)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return dt.strftime("%Y-%m-%d %H:%M")

    m = DAY_TIME_PATTERN.search(text)
    if m:
        day_name = m.group(1).lower()
        hour = _normalize_hour(int(m.group(2)), m.group(4))
        minute = int(m.group(3) or 0)
        target_day = DAY_INDEX[day_name]
        days_ahead = (target_day - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        dt = (now + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return dt.strftime("%Y-%m-%d %H:%M")

    m = TIME_PATTERN.search(text)
    if m:
        hour = _normalize_hour(int(m.group(1)), m.group(3))
        minute = int(m.group(2) or 0)
        dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt < now:
            dt = dt + timedelta(days=1)
        return dt.strftime("%Y-%m-%d %H:%M")

    return "NONE"


def extract_meeting_time(emails: list[dict[str, str]]) -> str:
    for email in emails:
        text = f"{email.get('subject', '')} {email.get('snippet', '')}"
        found = extract_time_from_text(text)
        if found != "NONE":
            return found
    return "NONE"


def extract_participants(emails: list[dict[str, str]]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for email in emails:
        text = " ".join([
            email.get("from", ""),
            email.get("subject", ""),
            email.get("snippet", ""),
            email.get("from_email", ""),
        ])
        for addr in EMAIL_REGEX.findall(text):
            addr = addr.strip().lower()
            if addr and addr not in seen:
                seen.add(addr)
                found.append(addr)
    return found


def generate_overall_summary(
    emails: list[dict[str, str]],
    categories: dict[str, int],
    urgent_subjects: list[str],
    meeting_time: str,
) -> str:
    total = len(emails)
    parts = [f"You have {total} recent emails in your inbox."]
    if categories["urgent"] > 0:
        parts.append(f"{categories['urgent']} appear urgent.")
    if categories["meeting"] > 0:
        parts.append(f"{categories['meeting']} are meeting-related.")
    if categories["task"] > 0:
        parts.append(f"{categories['task']} look task-oriented.")
    if categories["info"] > 0:
        parts.append(f"{categories['info']} are mostly informational.")
    if urgent_subjects:
        parts.append(f"Most urgent thread: {urgent_subjects[0]}.")
    if meeting_time != "NONE":
        parts.append(f"A meeting request appears to target {meeting_time}.")
    return " ".join(parts)


def analyze_inbox(emails: list[dict[str, str]]) -> dict[str, Any]:
    """Full rule-based analysis — used by the baseline web dashboard."""
    categories = {"meeting": 0, "urgent": 0, "info": 0, "task": 0}
    urgent_subjects: list[str] = []
    email_summaries: list[dict[str, str]] = []

    for email in emails:
        category = categorize_email(email)
        categories[category] += 1
        if category == "urgent":
            urgent_subjects.append(email.get("subject", "No Subject"))
        email_summaries.append({
            "subject": email.get("subject", "No Subject"),
            "summary": summarize_email(email),
            "category": category,
            "from_email": email.get("from_email", ""),
        })

    meeting_emails = detect_meeting_emails(emails)
    meeting_time = extract_meeting_time(meeting_emails) if meeting_emails else "NONE"
    meeting_attendees = extract_participants(meeting_emails) if meeting_emails else []

    overall = generate_overall_summary(emails, categories, urgent_subjects, meeting_time)

    if urgent_subjects:
        suggested_action = "Handle urgent emails first, then review meeting-related threads."
    elif meeting_time != "NONE":
        suggested_action = "Review the detected meeting and schedule it if the time looks right."
    elif categories["task"] > 0:
        suggested_action = "Review task-related emails and respond in priority order."
    else:
        suggested_action = "No critical urgency detected. Triage informational emails at your convenience."

    return {
        "inbox_summary": overall,
        "urgent_emails": urgent_subjects,
        "categories": categories,
        "suggested_action": suggested_action,
        "meeting_time": meeting_time,
        "meeting_subject": "AI Scheduled Meeting",
        "meeting_attendees": meeting_attendees,
        "email_summaries": email_summaries,
        "used_fallback": False,
    }


