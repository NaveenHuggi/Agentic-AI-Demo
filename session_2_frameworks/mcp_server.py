"""
╔══════════════════════════════════════════════════════════════╗
║  SESSION 2C (Part 1)  —  MCP Server                          ║
╠══════════════════════════════════════════════════════════════╣
║  This file IS the MCP Server — the "tool provider".          ║
║  Think of it as a USB-C port: it exposes standardised        ║
║  tools that ANY MCP-compatible agent can discover and use    ║
║  automatically, without writing custom integration code.     ║
║                                                              ║
║  DO NOT run this file directly.                              ║
║  The MCP client (demo_2c_mcp_client.py) starts it            ║
║  automatically as a subprocess.                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger().setLevel(logging.ERROR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ── Make imports work ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from mcp.server.fastmcp import FastMCP
from utils.gmail_utils import fetch_recent_emails
from utils.calendar_utils import create_calendar_event

# ═════════════════════════════════════════════════════════════
#  CREATE THE MCP SERVER
#  The FastMCP class handles all the protocol details.
#  We just register tools with the @mcp.tool() decorator.
# ═════════════════════════════════════════════════════════════

mcp = FastMCP(
    "Inbox Intelligence MCP Server",
    instructions=(
        "This server provides tools to interact with a user's Gmail inbox "
        "and Google Calendar. Use fetch_inbox to read emails and "
        "schedule_calendar_event to create meetings."
    ),
)


@mcp.tool()
def fetch_inbox(limit: int = 5) -> str:
    """Fetch the most recent emails from the user's Gmail inbox.

    Args:
        limit: Number of emails to fetch (default 5).

    Returns:
        A formatted string listing each email's sender, subject, and preview.
    """
    emails = fetch_recent_emails(limit=limit)
    if not emails:
        return "No emails found in the inbox."

    result = ""
    for i, email in enumerate(emails, 1):
        result += f"\nEmail {i}:\n"
        result += f"  From:    {email['from']}\n"
        result += f"  Subject: {email['subject']}\n"
        result += f"  Preview: {email['snippet']}\n"
        result += f"  Date:    {email['date']}\n"
    return result


@mcp.tool()
def schedule_calendar_event(time: str, attendees: str, title: str) -> str:
    """Schedule a meeting on Google Calendar and send invite emails with a Google Meet link.

    Args:
        time:      Meeting start time in 'YYYY-MM-DD HH:MM' format.
        attendees: Comma-separated email addresses of attendees.
        title:     Title/summary of the meeting.

    Returns:
        Confirmation message with the calendar event link.
    """
    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()]
    link = create_calendar_event(time, attendee_list, title)
    return f"✅ Meeting '{title}' scheduled at {time}. Link: {link}"


@mcp.tool()
def get_inbox_stats() -> str:
    """Get quick statistics about the user's inbox.

    Returns:
        A summary string with the count of emails and basic category breakdown.
    """
    emails = fetch_recent_emails(limit=10)
    total = len(emails)

    meeting_kw = ["meeting", "call", "sync", "schedule", "discuss"]
    urgent_kw = ["urgent", "asap", "critical", "important"]

    meetings = sum(
        1 for e in emails
        if any(k in f"{e.get('subject','')} {e.get('snippet','')}".lower() for k in meeting_kw)
    )
    urgents = sum(
        1 for e in emails
        if any(k in f"{e.get('subject','')} {e.get('snippet','')}".lower() for k in urgent_kw)
    )

    return (
        f"Inbox Stats: {total} recent emails, "
        f"{urgents} urgent, {meetings} meeting-related, "
        f"{total - urgents - meetings} informational."
    )


# ── Entry point — MCP handles the stdio transport ───────────
if __name__ == "__main__":
    mcp.run(transport="stdio")


