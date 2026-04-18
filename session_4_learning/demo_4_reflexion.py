"""
╔══════════════════════════════════════════════════════════════╗
║  SESSION 4  —  Learning Agent (Reflexion Paradigm)          ║
╠══════════════════════════════════════════════════════════════╣
║  GOAL: Build an agent that grades its own homework and      ║
║  improves over time WITHOUT retraining the model.           ║
║                                                             ║
║  The Reflexion Loop:                                        ║
║                                                             ║
║    ┌──────────┐        ┌─────────────┐                      ║
║    │  DRAFTER │───────▶│  EVALUATOR  │                      ║
║    │  (Actor) │        │  (Critic)   │                      ║
║    └──────────┘        └─────────────┘                      ║
║         ▲                    │                              ║
║         │     ❌ FAIL        │  ✅ PASS                     ║
║         │  (critique +       │                              ║
║         │   retry)           ▼                              ║
║         │              ┌─────────────┐                      ║
║         └──────────────│  EPISODIC   │                      ║
║                        │  MEMORY     │                      ║
║                        │ (JSON logs) │                      ║
║                        └─────────────┘                      ║
║                                                             ║
║  Key Concepts:                                              ║
║    • Actor-Evaluator pattern                                ║
║    • Self-critique (plain-language "report cards")          ║
║    • Episodic Memory (learning from past successes)         ║
║    • No model retraining — prompt-based learning            ║
╚══════════════════════════════════════════════════════════════╝

Run:   python session_4_learning/demo_4_reflexion.py
"""

import os
import sys
import json
from datetime import datetime
from typing import Literal
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
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from utils.gmail_utils import fetch_recent_emails


# ═════════════════════════════════════════════════════════════
#  EPISODIC MEMORY (The "Diary")
#  Stores past successes and failures as JSON entries.
#  The agent reads these before attempting a task to learn
#  from its own history.
# ═════════════════════════════════════════════════════════════

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "episodic_memory.json")


def load_episodic_memory() -> list[dict]:
    """Load past experiences from the episodic memory file."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_to_episodic_memory(entry: dict):
    """Append a new experience to the episodic memory file."""
    memories = load_episodic_memory()
    entry["timestamp"] = datetime.now().isoformat()
    memories.append(entry)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)
    print(f"   💾 Saved to episodic memory ({len(memories)} total entries)")


def format_episodic_memories() -> str:
    """Format past memories into a prompt-injectable string."""
    memories = load_episodic_memory()
    if not memories:
        return "No past experiences found. This is the first attempt."

    result = "📖 PAST EXPERIENCES (learn from these):\n"
    # Show only the last 5 entries to avoid context overflow
    for i, mem in enumerate(memories[-5:], 1):
        result += f"\n--- Experience {i} (from {mem.get('timestamp', 'unknown')}) ---\n"
        result += f"  Task:     {mem.get('task', 'N/A')}\n"
        result += f"  Outcome:  {mem.get('outcome', 'N/A')}\n"
        if mem.get("critique"):
            result += f"  Critique: {mem['critique']}\n"
        if mem.get("successful_reply"):
            result += f"  Good Reply: {mem['successful_reply'][:200]}\n"
    return result


# ═════════════════════════════════════════════════════════════
#  SHARED LLM (WITH FALLBACK ROUTER)
# ═════════════════════════════════════════════════════════════
from utils.llm_router import get_routed_llm
llm = get_routed_llm(role="worker_model")


# ═════════════════════════════════════════════════════════════
#  TOOLS
# ═════════════════════════════════════════════════════════════

@tool
def fetch_emails(limit: int = 5) -> str:
    """Fetch recent emails from Gmail inbox.

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
    return result


# ═════════════════════════════════════════════════════════════
#  GRAPH STATE — extends MessagesState with extra fields
# ═════════════════════════════════════════════════════════════

class ReflexionState(MessagesState):
    draft: str           # Current draft reply
    critique: str        # Evaluator's critique
    attempt: int         # Attempt number
    task_description: str  # What we're trying to accomplish
    passed: bool         # Whether the evaluator approved


# ═════════════════════════════════════════════════════════════
#  GRAPH NODES
# ═════════════════════════════════════════════════════════════

def fetch_and_select_node(state: ReflexionState):
    """Fetch emails and select an email to reply to."""
    print("\n📥 [FETCH] Getting emails and selecting one to reply to …")

    agent = create_react_agent(
        llm,
        tools=[fetch_emails],
        prompt=SystemMessage(content=(
            "Fetch the user's recent emails. Pick the most important one "
            "that requires a reply (prioritize urgent or task emails). "
            "Output the selected email's details clearly."
        )),
    )

    result = agent.invoke({"messages": state["messages"]})

    # Extract the task description from the last message
    last_content = result["messages"][-1].content if result["messages"] else ""

    return {
        "messages": result["messages"],
        "task_description": f"Reply to the most important email found in inbox",
        "attempt": 0,
        "draft": "",
        "critique": "",
        "passed": False,
    }


def drafter_node(state: ReflexionState):
    """
    The ACTOR — drafts a reply to the selected email.
    On retry, it receives the evaluator's critique and past memories.
    """
    attempt = state.get("attempt", 0) + 1
    print(f"\n✍️  [DRAFTER] Writing reply (Attempt {attempt}) …")

    # Build the prompt with context
    memories = format_episodic_memories()
    critique = state.get("critique", "")

    draft_prompt = (
        "You are a professional email assistant. Draft a reply to the "
        "email discussed above.\n\n"
        "STRICT RULES:\n"
        "1. The reply MUST be professional and polite.\n"
        "2. The reply MUST be under 80 words.\n"
        "3. The reply MUST address the specific request in the email.\n"
        "4. Include a proper greeting and sign-off.\n"
        "5. If the email mentions a deadline, acknowledge it.\n\n"
    )

    if memories:
        draft_prompt += f"\n{memories}\n"

    if critique:
        draft_prompt += (
            f"\n⚠️ YOUR PREVIOUS ATTEMPT WAS REJECTED.\n"
            f"The evaluator said: {critique}\n"
            f"Fix these issues in your new draft.\n"
        )

    draft_prompt += "\nOutput ONLY the email reply text. Nothing else."

    response = llm.invoke(
        state["messages"] + [HumanMessage(content=draft_prompt)]
    )

    draft = response.content.strip()
    print(f"   📝 Draft: {draft[:200]}…")

    return {
        "messages": state["messages"] + [
            AIMessage(content=f"[DRAFT Attempt {attempt}]:\n{draft}")
        ],
        "draft": draft,
        "attempt": attempt,
    }


def evaluator_node(state: ReflexionState):
    """
    The EVALUATOR — critiques the draft against a rubric.
    Does NOT change the draft; writes a plain-language "report card".
    """
    print("\n🔍 [EVALUATOR] Grading the draft …")

    draft = state.get("draft", "")

    eval_prompt = (
        "You are a strict email quality evaluator. Grade this draft reply:\n\n"
        f'"""\n{draft}\n"""\n\n'
        "RUBRIC (ALL must pass):\n"
        "1. PROFESSIONAL TONE: Is it polite and professional? (no slang, no emojis)\n"
        "2. CONCISENESS: Is it under 80 words?\n"
        "3. RELEVANCE: Does it address the original email's request?\n"
        "4. STRUCTURE: Does it have a greeting and sign-off?\n"
        "5. ACTIONABLE: Does it provide a clear next step or confirmation?\n\n"
        "OUTPUT FORMAT (respond with EXACTLY this JSON):\n"
        '{"passed": true/false, "score": "X/5", '
        '"critique": "Detailed feedback on what to fix (if failed)"}\n\n'
        "Be strict. Only pass drafts that meet ALL 5 criteria."
    )

    response = llm.invoke([HumanMessage(content=eval_prompt)])
    raw = response.content.strip()

    # Parse the evaluation
    try:
        # Clean markdown fences
        clean = raw
        if clean.startswith("```"):
            clean = "\n".join(l for l in clean.split("\n") if not l.strip().startswith("```"))
        evaluation = json.loads(clean.strip())
    except (json.JSONDecodeError, ValueError):
        # Default to pass if we can't parse (edge case)
        evaluation = {"passed": True, "score": "3/5", "critique": "Unable to parse evaluation."}

    passed = evaluation.get("passed", False)
    critique = evaluation.get("critique", "")
    score = evaluation.get("score", "?/5")

    if passed:
        print(f"   ✅ PASSED ({score}) — Draft approved!")
    else:
        print(f"   ❌ FAILED ({score}) — Critique: {critique}")

    return {
        "messages": state["messages"] + [
            AIMessage(content=f"[EVALUATION] Score: {score}, Passed: {passed}. {critique}")
        ],
        "passed": passed,
        "critique": critique,
    }


def memory_node(state: ReflexionState):
    """Save the experience to episodic memory for future learning."""
    print("\n💾 [MEMORY] Storing experience …")

    entry = {
        "task": state.get("task_description", "Reply to email"),
        "attempts": state.get("attempt", 1),
        "outcome": "success" if state.get("passed") else "failed_max_attempts",
        "critique": state.get("critique", ""),
        "successful_reply": state.get("draft", "") if state.get("passed") else "",
    }

    save_to_episodic_memory(entry)

    summary = (
        f"Task completed in {entry['attempts']} attempt(s). "
        f"Outcome: {entry['outcome']}. "
        f"This experience has been saved to episodic memory for future learning."
    )

    return {
        "messages": state["messages"] + [AIMessage(content=summary)]
    }


# ═════════════════════════════════════════════════════════════
#  ROUTING LOGIC
# ═════════════════════════════════════════════════════════════

def should_retry_or_finalize(state: ReflexionState) -> Literal["drafter_node", "memory_node"]:
    """After evaluation: retry if failed (max 3 attempts), else save and end."""
    passed = state.get("passed", False)
    attempt = state.get("attempt", 0)

    if passed:
        print("   → Routing to MEMORY (draft approved)")
        return "memory_node"
    elif attempt >= 3:
        print(f"   → Routing to MEMORY (max retries reached: {attempt})")
        return "memory_node"
    else:
        print(f"   → Routing back to DRAFTER (attempt {attempt + 1})")
        return "drafter_node"


# ═════════════════════════════════════════════════════════════
#  BUILD THE GRAPH
# ═════════════════════════════════════════════════════════════

def build_reflexion_graph():
    graph = StateGraph(ReflexionState)

    # Add nodes
    graph.add_node("fetch_and_select", fetch_and_select_node)
    graph.add_node("drafter_node", drafter_node)
    graph.add_node("evaluator_node", evaluator_node)
    graph.add_node("memory_node", memory_node)

    # Add edges
    graph.add_edge(START, "fetch_and_select")
    graph.add_edge("fetch_and_select", "drafter_node")
    graph.add_edge("drafter_node", "evaluator_node")

    # Conditional: retry or finalize based on evaluation
    graph.add_conditional_edges(
        "evaluator_node",
        should_retry_or_finalize,
    )

    graph.add_edge("memory_node", END)

    # Compile with checkpointing
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ═════════════════════════════════════════════════════════════
#  RUN
# ═════════════════════════════════════════════════════════════

def run_reflexion_agent():
    print("=" * 60)
    print("  SESSION 4 : Learning Agent (Reflexion Paradigm)")
    print("=" * 60)

    app = build_reflexion_graph()
    config = {"configurable": {"thread_id": "reflexion-demo-1"}}

    print("\n🚀 [System] Starting the Reflexion loop …")
    print("   Flow: Fetch → Draft → Evaluate → (Retry?) → Save to Memory")
    print()

    result = app.invoke(
        {
            "messages": [
                HumanMessage(content=(
                    "Fetch my recent emails, pick the most important one "
                    "that needs a reply, and draft a professional response."
                ))
            ],
            "draft": "",
            "critique": "",
            "attempt": 0,
            "task_description": "",
            "passed": False,
        },
        config=config,
    )

    # ── Print the conversation ───────────────────────────────
    print("\n" + "─" * 50)
    print("📜 FULL REFLEXION CONVERSATION:")
    print("─" * 50)
    for msg in result["messages"]:
        role = msg.type.upper()
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            content = "\n".join(c.get("text", "") if isinstance(c, dict) and "text" in c else str(c) for c in content)
        if content:
            # Highlight drafts and evaluations
            if "[DRAFT" in content:
                print(f"\n✍️  {content}")
            elif "[EVALUATION]" in content:
                print(f"\n🔍 {content}")
            else:
                print(f"\n[{role}]: {content}")

    # ── Show episodic memory ─────────────────────────────────
    print("\n" + "─" * 50)
    print("📖 EPISODIC MEMORY (accumulated experiences):")
    print("─" * 50)
    memories = load_episodic_memory()
    for i, mem in enumerate(memories, 1):
        print(f"\n  Experience {i}:")
        print(f"    Task:     {mem.get('task', 'N/A')}")
        print(f"    Attempts: {mem.get('attempts', '?')}")
        print(f"    Outcome:  {mem.get('outcome', '?')}")
        if mem.get("critique"):
            print(f"    Lesson:   {mem['critique'][:200]}")

    print()
    print("─" * 50)
    print("🎓 KEY TAKEAWAYS:")
    print("   1. SELF-CRITIQUE — The Evaluator graded the Drafter's work")
    print("      against a rubric, writing a plain-language 'report card'.")
    print("   2. RETRY LOOP — Failed drafts get sent back with the critique,")
    print("      so the Drafter learns from its mistakes mid-task.")
    print("   3. EPISODIC MEMORY — Successful experiences are saved to a JSON")
    print("      file. NEXT TIME the agent runs, it reads these memories")
    print("      BEFORE drafting, so it improves over time!")
    print("   4. NO RETRAINING — The model weights never change. All 'learning'")
    print("      happens through better prompts + memory injection.")
    print()
    print("   💡 Run this demo again — the agent will read its past")
    print("      experiences and draft a BETTER reply on the first try!")
    print("=" * 60)


if __name__ == "__main__":
    run_reflexion_agent()


