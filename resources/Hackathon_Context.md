# Agentic AI Hackathon — Project Context & Summary

> **Auto-generated Context Save State**
> Date: April 17, 2026
> Project: Inbox Intelligence Agent (4-Session Curriculum)

## 📌 Overall Architecture

We refactored an existing monolithic rule-based script into a modular **4-Session Agentic AI Curriculum**. The core philosophy is to demonstrate the evolution from a passive LLM text predictor to a fully autonomous, self-correcting agent.

*   **`utils/`**: Contains pure API integration logic (Gmail fetch, Calendar scheduling, Google Auth). This keeps the demos focused strictly on agent logic rather than API boilerplate.
*   **`.env`**: Contains `GOOGLE_API_KEY` and LanguageSmith tracing vars. Extracted from the `API-keys.txt` file.

## 🎓 The 4-Session Evolution

1.  **Session 1: Vanilla Agents (No Frameworks)**
    *   **Goal**: Break the illusion of "magic" by showing an agent is just a `while` loop that parses JSON to trigger functions.
    *   *Demo 1A*: Passive LLM (fails to schedule).
    *   *Demo 1B*: Manual ReAct loop (succeeds).
2.  **Session 2: Frameworks, Knowledge & Tools (LangChain, RAG, MCP)**
    *   **Goal**: Introduce frameworks to scale complexity.
    *   *Demo 2A*: LangChain `create_react_agent` implementation.
    *   *Demo 2B*: RAG (ChromaDB) to query `user_preferences.txt` before scheduling meetings.
    *   *Demo 2C*: MCP Server/Client showing auto-discovery of tools ("USB-C for AI").
3.  **Session 3: Distributed Multi-Agent Systems (LangGraph)**
    *   **Goal**: Show specialization, routing, and Human-in-the-loop.
    *   *Demo 3*: Triage node routes to Scheduler or Drafter nodes, pausing for user execution approval.
4.  **Session 4: Learning Agents (Reflexion Paradigm)**
    *   **Goal**: Demonstrate prompt-based learning without model retraining.
    *   *Demo 4*: Actor/Evaluator pattern saving successful attempts to `episodic_memory.json` to improve future drafts.

## 🛠️ Key Technical Hurdles Solved

1.  **Google OAuth Setup**: We navigated the "Unverified App" 403 blocks and successfully persisted a `token.json` using the local development callback port paradigm.
2.  **API Free Tier Quotas**: We successfully mapped and replaced deprecated models. Because `gemini-2.0-flash` threw a `limit: 0` error on the free tier, we migrated the entire codebase to **`gemini-flash-latest`** which executed flawlessly and scheduled the calendar event.
3.  **Cross-Platform UI Integration**: Refactored the baseline `main.py` FastAPI dashboard to natively import from the newly extracted `utils` architecture without breaking HTML mappings.

## 🚀 Next Steps (For Tomorrow)

*   All code is fully tested and functioning.
*   Next steps will likely involve running through Sessions 2, 3, and 4 to ensure the LangChain/LangGraph flows run as smoothly as Session 1 did tonight.
*   You can reference `Hackathon_Walkthrough.md` for teaching materials and CLI commands.
