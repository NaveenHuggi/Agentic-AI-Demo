"""
╔══════════════════════════════════════════════════════════════╗
║  SESSION 2C (Part 2)  —  MCP Client Agent                   ║
╠══════════════════════════════════════════════════════════════╣
║  GOAL: Show the "USB-C for AI" concept.                     ║
║                                                              ║
║  Instead of writing @tool decorators like in Demo 2A,        ║
║  we connect to an MCP Server and the agent AUTO-DISCOVERS    ║
║  all available tools at runtime.                             ║
║                                                              ║
║  Zero tool code in this file — the tools come from the       ║
║  MCP server automatically!                                   ║
╚══════════════════════════════════════════════════════════════╝

Run:   python session_2_frameworks/demo_2c_mcp_client.py
"""

import os
import sys
import asyncio
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
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Path to the MCP server script
MCP_SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "mcp_server.py")


async def run_mcp_agent():
    print("=" * 60)
    print("  SESSION 2C : MCP Client — Auto-Discovered Tools")
    print("=" * 60)

    # ── STEP 1: Connect to the MCP Server ────────────────────
    #   The client starts the MCP server as a subprocess and
    #   communicates over stdio. No HTTP, no REST — just a
    #   standardised protocol pipe.
    print("\n🔌 [MCP] Connecting to the Inbox Intelligence MCP Server …")

    client = MultiServerMCPClient(
        {
            "inbox_server": {
                "command": sys.executable,       # python interpreter
                "args": [MCP_SERVER_SCRIPT],     # our MCP server
                "transport": "stdio",
            }
        }
    )
    
    # ── STEP 2: Auto-discover tools ──────────────────────
    #   THIS is the magic of MCP. We wrote ZERO @tool code
    #   in this file. The tools come from the server.
    tools = await client.get_tools()

    print(f"\n🔍 [MCP] Auto-discovered {len(tools)} tools:")
    for t in tools:
        print(f"   • {t.name}: {t.description[:80]}…")

    # ── STEP 3: Create the agent with discovered tools ───
    from utils.llm_router import get_routed_llm
    llm = get_routed_llm(role="worker_model")
    agent = create_react_agent(llm, tools)

    print("\n🤖 [Agent] Running with MCP-discovered tools …\n")

    result = await agent.ainvoke({
        "messages": [
            HumanMessage(content=(
                "First get my inbox statistics, then fetch my recent "
                "emails and analyze them. If you find any meeting "
                "requests, schedule them on my calendar. "
                "Give me a complete summary at the end."
            ))
        ]
    })

    # ── Print the conversation ───────────────────────────
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
    print("   We wrote ZERO tool definitions in this file!")
    print("   The MCP server exposed tools, and the agent")
    print("   auto-discovered them at runtime via the protocol.")
    print()
    print("   MCP = 'USB-C for AI'")
    print("   • Traditional: Write a custom adapter per tool (days)")
    print("   • MCP:         Connect to a server (minutes)")
    print()
    print("   Imagine connecting to Slack, GitHub, or Database MCP")
    print("   servers — your agent gains new abilities instantly.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_mcp_agent())


