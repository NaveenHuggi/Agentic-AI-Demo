"""
╔══════════════════════════════════════════════════════════════╗
║  SESSION 2B  —  RAG-Powered Agent (Semantic Memory)         ║
╠══════════════════════════════════════════════════════════════╣
║  GOAL: Give the agent knowledge it was NEVER trained on.    ║
║  We ingest a "user_preferences.txt" file into a vector DB   ║
║  so the agent can look up YOUR personal rules before acting.║
║                                                             ║
║  Example: The preferences say "No meetings before 10 AM".   ║
║  If an email requests a 9 AM meeting, the agent will REFUSE ║
║  and suggest an alternative — because it checked the RAG!   ║
╚══════════════════════════════════════════════════════════════╝

Run:   python session_2_frameworks/demo_2b_rag_agent.py
"""

import sys
import os
import socket
import warnings

warnings.filterwarnings("ignore")
import logging
logging.getLogger().setLevel(logging.ERROR)

# Set stdout to utf-8 to prevent charmap UnicodeEncodeErrors in Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import time
# Highly resilient DNS retry monkeypatch for flaky network drops
_orig_getaddrinfo = socket.getaddrinfo
def _resilient_getaddrinfo(*args, **kwargs):
    for attempt in range(5):
        try:
            return _orig_getaddrinfo(*args, **kwargs)
        except socket.gaierror as e:
            if attempt == 4:
                raise e
            time.sleep(1)
socket.getaddrinfo = _resilient_getaddrinfo

# ── Make imports work from any sub-folder ────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.dns_patch
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from langgraph.prebuilt import create_react_agent

from utils.gmail_utils import fetch_recent_emails
from utils.calendar_utils import create_calendar_event

# ═════════════════════════════════════════════════════════════
#  STEP 1 : BUILD THE VECTOR STORE (one-time ingestion)
#  This is the "Data Ingestion Pipeline" from the framework:
#     Load → Chunk → Embed → Store
# ═════════════════════════════════════════════════════════════

PREFS_FILE = os.path.join(os.path.dirname(__file__), "user_preferences.txt")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), ".chroma_db")


def build_vector_store():
    """
    Ingest user_preferences.txt into a ChromaDB vector store.
    This runs once; subsequent calls reuse the stored embeddings.
    """
    print("📚 [RAG] Building vector store from user_preferences.txt …")

    # LOAD: Read the raw text file
    loader = TextLoader(PREFS_FILE, encoding="utf-8")
    documents = loader.load()

    # CHUNK: Split into overlapping sections (512 chars, 20% overlap)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=100,        # ~20% of 512
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"   → Split into {len(chunks)} chunks")

    # EMBED + STORE: Convert chunks to vectors and persist
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )
    print(f"   → Stored in ChromaDB at {CHROMA_DIR}")
    return vectorstore


def load_vector_store():
    """Load an existing ChromaDB store (or build if missing)."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    if os.path.exists(CHROMA_DIR):
        return Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
        )
    return build_vector_store()


# ═════════════════════════════════════════════════════════════
#  STEP 2 : DEFINE TOOLS  (including the RAG retriever tool)
# ═════════════════════════════════════════════════════════════

# Global reference — initialised in main
_vectorstore = None


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
def search_user_preferences(query: str) -> str:
    """Search the user's personal preferences and rules.

    Use this tool BEFORE scheduling meetings or drafting replies to check
    if the user has any relevant rules (e.g., time restrictions, priority
    settings, communication style preferences).

    Args:
        query: A natural language question about the user's preferences.
               Examples: "meeting time restrictions", "priority rules",
                         "how should I reply to emails"

    Returns:
        Relevant preference rules found in the user's personal knowledge base.
    """
    if _vectorstore is None:
        return "No preference database available."

    # Top-k retrieval with k=3 (as recommended in the framework)
    docs = _vectorstore.similarity_search(query, k=3)

    if not docs:
        return "No relevant preferences found for this query."

    result = "📋 USER PREFERENCES FOUND:\n"
    for i, doc in enumerate(docs, 1):
        result += f"\n--- Rule Set {i} ---\n"
        result += doc.page_content.strip()
        result += "\n"
    return result


@tool
def schedule_meeting(time: str, attendees: str, title: str) -> str:
    """Schedule a meeting on Google Calendar and send invite emails.

    IMPORTANT: Always call search_user_preferences first to check for
    scheduling restrictions before calling this tool!

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
#  STEP 3 : BUILD AND RUN THE RAG-POWERED AGENT
# ═════════════════════════════════════════════════════════════

def run_rag_agent():
    global _vectorstore

    print("=" * 60)
    print("  SESSION 2B : RAG-Powered Agent (Semantic Memory)")
    print("=" * 60)

    # Build / load the vector store
    _vectorstore = load_vector_store()

    # Create the LLM
    from utils.llm_router import get_routed_llm
    llm = get_routed_llm(role="worker_model")

    # Tools — now includes the RAG retriever!
    tools = [fetch_emails, search_user_preferences, schedule_meeting]

    # System message instructing the agent to check preferences
    system_msg = SystemMessage(content=(
        "You are an intelligent email assistant with access to the user's "
        "personal preferences database. "
        "ALWAYS search the user's preferences BEFORE scheduling any meeting "
        "or drafting any reply. If a requested action violates a preference "
        "(e.g., a meeting before 10 AM), you MUST refuse and explain why, "
        "then suggest an alternative that complies with the rules."
    ))

    # Create the agent
    agent = create_react_agent(llm, tools)

    print("\n🤖 [Agent] Running RAG-powered agent …\n")

    result = agent.invoke({
        "messages": [
            system_msg,
            HumanMessage(content=(
                "Fetch my recent emails. For any meeting requests found, "
                "check my personal preferences first, then schedule the "
                "meetings ONLY if they comply with my rules. "
                "If they don't comply, explain the conflict and suggest "
                "an alternative. Give me a complete summary at the end."
            )),
        ]
    })

    # Print the conversation
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

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"  🔧 Tool Call: {tc['name']}({tc['args']})")

    print()
    print("─" * 50)
    print("🎓 KEY TAKEAWAY:")
    print("   The agent now has SEMANTIC MEMORY — knowledge it was")
    print("   never trained on (your personal rules in user_preferences.txt).")
    print()
    print("   RAG Pipeline:  Load → Chunk → Embed → Store → Retrieve")
    print()
    print("   The agent searched the vector DB BEFORE scheduling,")
    print("   ensuring it respects YOUR rules — not just generic logic.")
    print("=" * 60)


if __name__ == "__main__":
    run_rag_agent()


