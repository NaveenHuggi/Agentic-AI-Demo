# 📧 Inbox Intelligence Agent — Hackathon Walkthrough

> Complete hands-on guide for the Agentic AI Hackathon.
> Follow this from top to bottom. Every step is explained for beginners.

---

## 📁 Project Structure

```
Agentic AI Demos/
├── .env.example                          # Template for API keys
├── .env                                  # Your actual API keys (you create this)
├── credentials.json                      # Google OAuth file (you download this)
├── requirements.txt                      # All Python dependencies
├── main.py                               # Web Dashboard (baseline)
│
├── utils/                                # Shared helpers
│   ├── auth.py                           #   Google OAuth
│   ├── gmail_utils.py                    #   Gmail fetch
│   ├── calendar_utils.py                 #   Calendar scheduling
│   └── analysis.py                       #   Rule-based analysis (baseline)
│
├── session_1_vanilla/                    # Session 1: No frameworks
│   ├── demo_1a_passive_llm.py            #   Demo: LLM can only talk
│   └── demo_1b_vanilla_agent.py          #   Demo: Agent can ACT
│
├── session_2_frameworks/                 # Session 2: LangChain + RAG + MCP
│   ├── demo_2a_langchain_agent.py        #   Demo: Clean agent with LangChain
│   ├── demo_2b_rag_agent.py              #   Demo: Agent with personal knowledge
│   ├── user_preferences.txt              #   Private data for RAG
│   ├── mcp_server.py                     #   MCP tool provider
│   └── demo_2c_mcp_client.py             #   Demo: Auto-discovered tools
│
├── session_3_distributed/                # Session 3: Multi-agent
│   └── demo_3_multi_agent.py             #   Demo: Team of agents + Human-in-the-loop
│
└── session_4_learning/                   # Session 4: Reflexion
    ├── demo_4_reflexion.py               #   Demo: Self-correcting agent
    └── episodic_memory.json              #   Auto-generated learning log
```

---

## 🔧 PHASE 0: One-Time Setup (Do this BEFORE the hackathon)

### Step 0.1 — Get Google Cloud `credentials.json`

This file lets the code read your Gmail and create Calendar events.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → Sign in.
2. Click the project dropdown (top-left) → **New Project** → Name: `Agentic AI Hackathon` → Create.
3. Make sure your new project is selected in the dropdown.
4. **Enable APIs:**
   - Sidebar → **APIs & Services → Library**
   - Search `Gmail API` → click → **Enable**
   - Go back → search `Google Calendar API` → click → **Enable**
5. **OAuth Consent Screen:**
   - Sidebar → **APIs & Services → OAuth consent screen**
   - Select **External** → Create
   - Fill: App name = `Inbox Intelligence Agent`, email fields = your email → Save
   - Skip "Scopes" → Save and Continue
   - **Test Users** → Add Users → type YOUR Gmail address → Save and Continue
6. **Download Credentials:**
   - Sidebar → **APIs & Services → Credentials**
   - Click **+ CREATE CREDENTIALS → OAuth client ID**
   - Type: **Desktop app** → Name: anything → Create
   - Click **DOWNLOAD JSON** on the popup
   - Move the file to your project folder and rename to **`credentials.json`**

### Step 0.2 — Get API Keys (Multi-Provider Support)

To avoid rate limits during the hackathon (a common issue!), the framework is built with a **failover router**. You can use API keys from multiple free-tier providers:

1. **Google AI Studio (Gemini)**: [Get Key Here](https://aistudio.google.com/)
2. **Groq (Free Llama 3)**: [Get Key Here](https://console.groq.com/keys)
3. **GitHub Models**: [Get Key Here](https://github.com/marketplace/models)

If one provider hits a limit, the agent seamlessly falls back to another!

### Step 0.3 — Create your `.env` file

Open a terminal in the project folder and copy the template:
```bash
copy .env.example .env
```
Open `.env` in a text editor and paste any keys you gathered. The router will magically load-balance any key prefixed with the provider name!
```
# Add as many fallbacks as you want:
GEMINI_API_KEY_1=paste-your-gemini-key-here
GROQ_API_KEY_1=paste-your-groq-key-here
# LANGCHAIN_TRACING_V2=true  (Optional visual dashboard)
```

### Step 0.5 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 0.6 — First-Time Google Auth

Run this once to create `token.json` (a browser window will pop up asking you to authorize):
```bash
python -c "from utils.auth import get_credentials; get_credentials()"
```
A browser will open → sign in with your Gmail → click "Allow" → done!

---

## 🟢 SESSION 1: The Paradigm Shift

> **Teaching Point:** An AI Agent is just a Python while-loop that lets an LLM call functions. No magic.

### Demo 1A — The Passive LLM

```bash
python session_1_vanilla/demo_1a_passive_llm.py
```

**What you'll see:**
1. The script fetches your real Gmail emails
2. It sends them to Gemini and asks it to "schedule a meeting"
3. Gemini responds with text saying it scheduled it
4. **But your Google Calendar is EMPTY** — nothing happened!

**The Lesson:** An LLM is a TEXT PREDICTOR. It cannot take real-world actions. It can only generate text that *looks* like an answer.

---

### Demo 1B — The Vanilla Agent (ReAct Loop)

```bash
python session_1_vanilla/demo_1b_vanilla_agent.py
```

**What you'll see:**
1. The script runs a `while` loop
2. It asks the LLM what to do → LLM outputs JSON like `{"tool": "fetch_emails"}`
3. Python intercepts the JSON and actually calls the Gmail API
4. It feeds the result back to the LLM → LLM decides what to do next
5. If a meeting is found, it **actually schedules it on your Calendar!**

**The Lesson:** The exact same LLM, but wrapped in a loop that lets it call functions. THAT is what makes it an agent. The pattern is: **Reason → Act → Observe → Repeat** (ReAct).

---

## 🔵 SESSION 2: Frameworks, Knowledge, and Interfaces

> **Teaching Point:** Writing manual while-loops doesn't scale. Frameworks handle the complexity.

### Demo 2A — LangChain Agent

```bash
python session_2_frameworks/demo_2a_langchain_agent.py
```

**What you'll see:**
Same result as Demo 1B, but the code is ~40 lines instead of ~120. LangChain's `create_react_agent()` handles all the JSON parsing, tool routing, and conversation management automatically.

**The Lesson:** `@tool` decorator + `create_react_agent()` = production-ready agent in minutes.

---

### Demo 2B — RAG Agent (Semantic Memory)

```bash
python session_2_frameworks/demo_2b_rag_agent.py
```

**What you'll see:**
1. The script ingests `user_preferences.txt` into a vector database (ChromaDB)
2. When a meeting request is found, the agent calls `search_user_preferences` **before** scheduling
3. If the proposed time violates a rule (e.g., "no meetings before 10 AM"), the agent **refuses and suggests an alternative**

**The Lesson:** RAG gives the agent knowledge it was NEVER trained on. The LLM has never seen your preferences file, but it can now reason with it.

> [!TIP]
> Try editing `user_preferences.txt` to add new rules, then re-run to see the agent follow them!

---

### Demo 2C — MCP Client (Auto-Discovered Tools)

```bash
python session_2_frameworks/demo_2c_mcp_client.py
```

**What you'll see:**
1. The script starts an MCP server as a subprocess
2. The agent client connects and **auto-discovers** 3 tools without any `@tool` code in the client file
3. The agent uses these discovered tools to analyze your inbox

**The Lesson:** MCP = "USB-C for AI". Instead of writing custom adapters for every tool, you connect to a standardized server and the tools are available instantly.

---

## 🟣 SESSION 3: Distributed Agents

> **Teaching Point:** One agent doing everything gets confused. A team of specialists works better.

### Demo 3 — Multi-Agent System

```bash
python session_3_distributed/demo_3_multi_agent.py
```

**What you'll see:**
1. **Triage Agent** reads emails and categorizes them
2. **Router** sends meeting emails to the Scheduler, task emails to the Drafter
3. **Scheduler/Drafter Agent** handles its specialization
4. **Human-in-the-Loop** — the graph PAUSES and asks YOU to approve before finalizing
5. You type "yes" or "no" to approve/reject the action

**The Lesson:**
- **Specialization** — each agent only has the tools it needs
- **Routing** — the graph decides who handles what
- **Human-in-the-Loop** — safety gate for high-stakes actions
- **Checkpointing** — if the server crashes, it resumes from exactly where it stopped

---

## 🟡 SESSION 4: Learning Agents

> **Teaching Point:** The agent grades its own work and improves over time — without retraining.

### Demo 4 — Reflexion Agent

```bash
python session_4_learning/demo_4_reflexion.py
```

**What you'll see:**
1. The agent fetches emails and picks one to reply to
2. **Drafter Agent** writes a reply
3. **Evaluator Agent** grades it against a rubric (tone, length, relevance, structure, actionability)
4. If it FAILS → the critique is fed back and the Drafter tries again (up to 3 times)
5. Once approved, the experience is saved to `episodic_memory.json`

**Run it AGAIN** and watch:
6. The agent reads its past experiences BEFORE drafting
7. It produces a BETTER draft on the first try!

**The Lesson:**
- **Self-Critique** — the Evaluator writes plain-language "report cards"
- **Retry Loop** — failed attempts learn from their own critique
- **Episodic Memory** — successful experiences are saved and injected into future prompts
- **No Retraining** — the model weights NEVER change. All learning is prompt-based.

---

## 🏁 Quick Reference — All Commands

| Session | Demo | Command |
|---------|------|---------|
| Dashboard | Web UI | `uvicorn main:app --reload` |
| 1A | Passive LLM | `python session_1_vanilla/demo_1a_passive_llm.py` |
| 1B | Vanilla Agent | `python session_1_vanilla/demo_1b_vanilla_agent.py` |
| 2A | LangChain Agent | `python session_2_frameworks/demo_2a_langchain_agent.py` |
| 2B | RAG Agent | `python session_2_frameworks/demo_2b_rag_agent.py` |
| 2C | MCP Client | `python session_2_frameworks/demo_2c_mcp_client.py` |
| 3 | Multi-Agent | `python session_3_distributed/demo_3_multi_agent.py` |
| 4 | Reflexion | `python session_4_learning/demo_4_reflexion.py` |
