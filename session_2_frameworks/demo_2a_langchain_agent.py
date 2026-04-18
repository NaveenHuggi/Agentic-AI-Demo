"""
╔══════════════════════════════════════════════════════════════╗
║  SESSION 2A  —  LangChain Agent                             ║
╠══════════════════════════════════════════════════════════════╣
║  GOAL: Replace the messy while-loop from Session 1B with    ║
║  LangChain's clean agent framework.                         ║
║                                                             ║
║  Compare:  ~120 lines of manual JSON parsing in 1B          ║
║            → ~40 lines of clean LangChain code here         ║
╚══════════════════════════════════════════════════════════════╝

Run:   python session_2_frameworks/demo_2a_langchain_agent.py
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore")
import logging
logging.getLogger().setLevel(logging.ERROR)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ── Make imports work from any sub-folder ────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.dns_patch
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

# LangChain's prebuilt ReAct agent — it handles the loop for us!
from langgraph.prebuilt import create_react_agent

from utils.gmail_utils import fetch_recent_emails
from utils.calendar_utils import create_calendar_event


# ═════════════════════════════════════════════════════════════
#  TOOLS  —  Just decorate normal functions with @tool
#  LangChain reads the docstrings to tell the LLM what each
#  tool does.  Compare this to the manual TOOLS dict in 1B!
# ═════════════════════════════════════════════════════════════

@tool
def fetch_emails(limit: int = 5) -> str:
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


@tool
def schedule_meeting(time: str, attendees: str, title: str) -> str:
    """Schedule a meeting on Google Calendar and send invite emails.

    Args:
        time:      Meeting start time in 'YYYY-MM-DD HH:MM' format.
        attendees: Comma-separated email addresses of attendees.
        title:     Title of the meeting.

    Returns:
        Confirmation message with the calendar event link.
    """
    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()]
    link = create_calendar_event(time, attendee_list, title)
    return f"✅ Meeting '{title}' scheduled at {time}. Link: {link}"


# ═════════════════════════════════════════════════════════════
#  AGENT SETUP  —  Compare this to the 120-line while-loop!
# ═════════════════════════════════════════════════════════════

def run_langchain_agent():
    print("=" * 60)
    print("  SESSION 2A : LangChain Agent")
    print("=" * 60)

    # 1. Create the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0,
    )

    # 2. List all tools
    tools = [fetch_emails, schedule_meeting]

    # 3. Create the agent — ONE LINE replaces the entire while-loop!
    agent = create_react_agent(llm, tools)

    # 4. Run the agent
    print("\n🤖 [Agent] Running LangChain ReAct agent …\n")

    result = agent.invoke({
        "messages": [
            HumanMessage(content=(
                "Fetch my recent emails, analyze them, categorize each as "
                "urgent/meeting/task/info, and if you find any meeting "
                "requests, schedule them on my Google Calendar. "
                "Give me a full summary at the end."
            ))
        ]
    })

    # 5. Print the conversation
    print("─" * 50)
    print("📜 FULL AGENT CONVERSATION:")
    print("─" * 50)
    for msg in result["messages"]:
        role = msg.type.upper()
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            content = "\n".join(c.get("text", "") if isinstance(c, dict) and "text" in c else str(c) for c in content)
        if content:
            print(f"\n[{role}]:")
            print(f"  {content}")

        # Show tool calls if any
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"  🔧 Tool Call: {tc['name']}({tc['args']})")

    print()
    print("─" * 50)
    print("🎓 KEY TAKEAWAY:")
    print("   We got the SAME result as Session 1B's manual agent,")
    print("   but LangChain handled ALL the complexity:")
    print("   • JSON parsing")
    print("   • Tool routing")
    print("   • Conversation management")
    print("   • Error handling")
    print()
    print("   The @tool decorator + create_react_agent() = Production-ready agent.")
    print("=" * 60)


if __name__ == "__main__":
    run_langchain_agent()


