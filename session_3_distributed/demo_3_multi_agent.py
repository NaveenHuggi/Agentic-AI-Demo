"""
╔══════════════════════════════════════════════════════════════╗
║  SESSION 3  —  Multi-Agent System (LangGraph)               ║
╠══════════════════════════════════════════════════════════════╣
║  GOAL: Break the single monolithic agent into a TEAM of     ║
║  specialised agents that route work to each other.          ║
║                                                             ║
║  The Graph:                                                 ║
║                                                             ║
║    ┌──────────┐    meeting    ┌────────────┐                ║
║    │  TRIAGE  │──────────────▶│ SCHEDULER  │                ║
║    │  AGENT   │               └────────────┘                ║
║    │          │    task       ┌────────────┐  ┌──────────┐  ║
║    │          │──────────────▶│  DRAFTER   │─▶│  HUMAN   │  ║
║    │          │               │   AGENT    │  │  REVIEW  │  ║
║    └──────────┘               └────────────┘  └──────────┘  ║
║         │ info                                              ║
║         ▼                                                   ║
║    ┌──────────┐                                             ║
║    │   END    │                                             ║
║    └──────────┘                                             ║
║                                                             ║
║  Features demonstrated:                                     ║
║    • Conditional routing  (edges based on email category)   ║
║    • Specialised agents   (each node has its own tools)     ║
║    • State management     (TypedDict flows through graph)   ║
║    • Human-in-the-loop    (graph pauses for human approval) ║
║    • Checkpointing        (crash recovery with MemorySaver) ║
╚══════════════════════════════════════════════════════════════╝

Run:   python session_3_distributed/demo_3_multi_agent.py
"""

import os
import sys
import json
from typing import Annotated, Literal
import warnings

warnings.filterwarnings("ignore")
import logging
logging.getLogger().setLevel(logging.ERROR)

# Set stdout to utf-8 to prevent charmap UnicodeEncodeErrors in Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ── Make imports work from any sub-folder ────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.dns_patch
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from utils.gmail_utils import fetch_recent_emails
from utils.calendar_utils import create_calendar_event


# ═════════════════════════════════════════════════════════════
#  SHARED LLM (WITH FALLBACK ROUTER)
# ═════════════════════════════════════════════════════════════
from utils.llm_router import get_routed_llm
llm = get_routed_llm(role="master_model")


# ═════════════════════════════════════════════════════════════
#  TOOLS — each agent gets ONLY the tools it needs
# ═════════════════════════════════════════════════════════════

@tool
def fetch_emails(limit: int = 5) -> str:
    """Fetch the most recent emails from Gmail inbox.

    Args:
        limit: Number of emails to fetch.

    Returns:
        Formatted string of emails.
    """
    emails = fetch_recent_emails(limit=limit)
    if not emails:
        return "No emails found."
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
    """Schedule a meeting on Google Calendar.

    Args:
        time: Start time in 'YYYY-MM-DD HH:MM' format.
        attendees: Comma-separated email addresses.
        title: Meeting title.

    Returns:
        Confirmation with calendar link.
    """
    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()]
    link = create_calendar_event(time, attendee_list, title)
    return f"✅ Meeting '{title}' scheduled at {time}. Link: {link}"


@tool
def draft_email_reply(original_subject: str, reply_body: str) -> str:
    """Draft an email reply (simulation — prints the draft).

    Args:
        original_subject: Subject of the email being replied to.
        reply_body: Body text of the reply.

    Returns:
        The formatted draft ready for review.
    """
    draft = (
        f"📧 DRAFT REPLY\n"
        f"Re: {original_subject}\n"
        f"{'─' * 40}\n"
        f"{reply_body}\n"
        f"{'─' * 40}"
    )
    return draft


# ═════════════════════════════════════════════════════════════
#  SPECIALISED SUB-AGENTS
# ═════════════════════════════════════════════════════════════

triage_agent = create_react_agent(
    llm,
    tools=[fetch_emails],
    prompt=SystemMessage(content=(
        "You are the TRIAGE AGENT. Your ONLY job is to:\n"
        "1. Fetch the user's recent emails.\n"
        "2. Categorize EACH email as exactly one of: 'meeting', 'task', or 'info'.\n"
        "3. After analyzing, respond with a JSON summary like:\n"
        '   {"emails": [{"subject": "...", "category": "meeting|task|info", '
        '"from": "...", "snippet": "...", "time_mentioned": "..." }]}\n'
        "Be precise. Include any time mentioned in meeting emails."
    )),
)

scheduler_agent = create_react_agent(
    llm,
    tools=[schedule_meeting],
    prompt=SystemMessage(content=(
        "You are the SCHEDULER AGENT. You receive meeting-related emails.\n"
        "Your job is to extract the meeting time and attendees, then\n"
        "call the schedule_meeting tool to create the calendar event.\n"
        "If no clear time is found, suggest a reasonable time."
    )),
)

drafter_agent = create_react_agent(
    llm,
    tools=[draft_email_reply],
    prompt=SystemMessage(content=(
        "You are the DRAFTER AGENT. You receive task-related emails.\n"
        "Your job is to draft professional, concise replies (under 100 words).\n"
        "Use the draft_email_reply tool to create each draft."
    )),
)


# ═════════════════════════════════════════════════════════════
#  GRAPH NODES
# ═════════════════════════════════════════════════════════════

def triage_node(state: MessagesState):
    """The Triage Agent reads emails and categorises them."""
    print("\n🔀 [TRIAGE AGENT] Analyzing inbox …")
    result = triage_agent.invoke(state)
    return {"messages": result["messages"]}


def router(state: MessagesState) -> Command[Literal["scheduler_node", "drafter_node", "__end__"]]:
    """Route based on what the triage agent found."""
    last_msg = state["messages"][-1]
    content = last_msg.content.lower() if hasattr(last_msg, "content") else ""

    has_meetings = "meeting" in content
    has_tasks = "task" in content

    if has_meetings:
        print("   📌 Route → SCHEDULER (meeting emails found)")
        return Command(goto="scheduler_node")
    elif has_tasks:
        print("   📌 Route → DRAFTER (task emails found)")
        return Command(goto="drafter_node")
    else:
        print("   📌 Route → END (only informational emails)")
        return Command(goto="__end__")


def scheduler_node(state: MessagesState):
    """The Scheduler Agent handles meeting requests."""
    print("\n📅 [SCHEDULER AGENT] Processing meeting requests …")
    result = scheduler_agent.invoke({
        "messages": state["messages"] + [
            HumanMessage(content=(
                "Based on the triage analysis above, schedule all "
                "detected meetings on Google Calendar."
            ))
        ]
    })
    return {"messages": result["messages"]}


def drafter_node(state: MessagesState):
    """The Drafter Agent creates reply drafts."""
    print("\n✍️  [DRAFTER AGENT] Drafting replies …")
    result = drafter_agent.invoke({
        "messages": state["messages"] + [
            HumanMessage(content=(
                "Based on the triage analysis above, draft professional "
                "replies for all task-related emails."
            ))
        ]
    })
    return {"messages": result["messages"]}


def human_review_node(state: MessagesState):
    """HUMAN-IN-THE-LOOP: Pause and ask for approval before finalizing."""
    print("\n🛑 [HUMAN REVIEW] The agent wants to send the following:")

    last_msg = state["messages"][-1]
    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    print(content[:800])

    # This PAUSES the graph and waits for human input
    human_decision = interrupt(
        "Do you approve this action? (yes/no): "
    )

    if human_decision.lower().strip() in ("yes", "y"):
        return {
            "messages": state["messages"] + [
                AIMessage(content="✅ Human approved. Action finalized.")
            ]
        }
    else:
        return {
            "messages": state["messages"] + [
                AIMessage(content="❌ Human rejected this action. Discarding.")
            ]
        }


# ═════════════════════════════════════════════════════════════
#  BUILD THE GRAPH
# ═════════════════════════════════════════════════════════════

def build_graph():
    graph = StateGraph(MessagesState)

    # Add nodes
    graph.add_node("triage_node", triage_node)
    graph.add_node("router", router)
    graph.add_node("scheduler_node", scheduler_node)
    graph.add_node("drafter_node", drafter_node)
    graph.add_node("human_review_node", human_review_node)

    # Add edges
    graph.add_edge(START, "triage_node")
    graph.add_edge("triage_node", "router")

    # After scheduler/drafter → human review
    graph.add_edge("scheduler_node", "human_review_node")
    graph.add_edge("drafter_node", "human_review_node")
    graph.add_edge("human_review_node", END)

    # Compile with checkpointing (crash recovery!)
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ═════════════════════════════════════════════════════════════
#  RUN
# ═════════════════════════════════════════════════════════════

def run_multi_agent():
    print("=" * 60)
    print("  SESSION 3 : Multi-Agent System (LangGraph)")
    print("=" * 60)

    app = build_graph()
    config = {"configurable": {"thread_id": "hackathon-demo-1"}}

    print("\n🚀 [System] Starting the multi-agent graph …")
    print("   Nodes: Triage → Router → Scheduler/Drafter → Human Review")
    print()

    # First invocation — runs until the human_review interrupt
    result = app.invoke(
        {
            "messages": [
                HumanMessage(content="Analyze my inbox and handle everything appropriately.")
            ]
        },
        config=config,
    )

    # Print results so far
    print("\n" + "─" * 50)
    print("📜 AGENT CONVERSATION (before human review):")
    print("─" * 50)
    for msg in result["messages"]:
        role = msg.type.upper()
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            content = "\n".join(c.get("text", "") if isinstance(c, dict) and "text" in c else str(c) for c in content)
        if content:
            print(f"\n[{role}]: {content}")

    # Resume with human approval
    print("\n" + "─" * 50)
    human_input = input("🛑 HUMAN-IN-THE-LOOP: Do you approve? (yes/no): ").strip()

    # Resume the graph from the checkpoint
    result = app.invoke(Command(resume=human_input), config=config)

    # Print final results
    print("\n" + "─" * 50)
    print("📜 FINAL RESULT:")
    print("─" * 50)
    last_msg = result["messages"][-1]
    print(f"  {last_msg.content if hasattr(last_msg, 'content') else last_msg}")

    print()
    print("─" * 50)
    print("🎓 KEY TAKEAWAYS:")
    print("   1. SPECIALISATION — Each agent has its own tools and prompt.")
    print("      The triage agent CANNOT schedule; the scheduler CANNOT draft.")
    print("   2. ROUTING — The graph decides which agent handles what.")
    print("   3. HUMAN-IN-THE-LOOP — The graph PAUSED and waited for you!")
    print("   4. CHECKPOINTING — If the server crashed after triage,")
    print("      it would resume from the checkpoint, not start over.")
    print("=" * 60)


if __name__ == "__main__":
    run_multi_agent()


