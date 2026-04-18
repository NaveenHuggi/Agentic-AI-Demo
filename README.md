# 🤖 Inbox Intelligence: Agentic AI Framework

Welcome to the **Agentic AI Hackathon** repository! This project serves as a comprehensive, hands-on masterclass in building advanced AI agents. 

Unlike standard text-generation bots, **Agentic AI** systems have the ability to *reason*, *use tools*, *interact with external APIs*, and *self-correct*. This repository takes you step-by-step from a traditional LLM script all the way to a Multi-Agent, self-learning Reflection loop, using a practical **Inbox Intelligence** scenario: an agent that reads your emails, categorizes them, drafts replies, and schedules calendar events autonomously.

---

## 🎯 What You Will Learn

This repository is split into progressive sessions. By running each demo, you will understand how AI architectures evolve:

- **Session 1: The Vanilla Agent** — Understand the core ReAct (Reason + Act) loop from scratch.
- **Session 2: Frameworks & RAG** — Scale up with LangChain, inject personal knowledge via ChromaDB (RAG), and magically discover tools using the Model Context Protocol (MCP).
- **Session 3: Distributed Multi-Agent Systems** — Use LangGraph to build a team of specialized agents (Triage, Drafter, Scheduler) that collaborate and pause for Human-in-the-Loop approval.
- **Session 4: Learning Agents** — Implement the Reflexion paradigm, where the agent critiques its own work and saves successful strategies to an Episodic Memory JSON file, improving over time without model retraining.

---

## 📁 Repository Structure

```text
├── .env.example                          # Template for API keys
├── requirements.txt                      # Python dependencies
├── main.py                               # Web Dashboard (FastAPI baseline UI)
│
├── utils/                                # Shared utilities
│   ├── auth.py                           #   Google OAuth Flow
│   ├── gmail_utils.py                    #   Fetch inbox messages
│   ├── calendar_utils.py                 #   Schedule meetings
│   ├── dns_patch.py                      #   Network stability patch
│   └── llm_router.py                     #   Multi-provider LLM Load Balancer
│
├── session_1_vanilla/                    # Session 1: No frameworks
│   ├── demo_1a_passive_llm.py            #   Demo: LLM can only talk
│   └── demo_1b_vanilla_agent.py          #   Demo: Agent can ACT (while loop)
│
├── session_2_frameworks/                 # Session 2: LangChain + RAG + MCP
│   ├── demo_2a_langchain_agent.py        #   Demo: Clean agent with LangChain
│   ├── demo_2b_rag_agent.py              #   Demo: Agent with personal knowledge
│   ├── user_preferences.txt              #   Private data for RAG DB
│   ├── mcp_server.py                     #   MCP tool provider
│   └── demo_2c_mcp_client.py             #   Demo: Auto-discovered tools
│
├── session_3_distributed/                # Session 3: Multi-agent
│   └── demo_3_multi_agent.py             #   Demo: Team of agents + Human-approval
│
├── session_4_learning/                   # Session 4: Reflexion
│   └── demo_4_reflexion.py               #   Demo: Self-correcting & learning agent
│
└── resources/                            # Presentation slides and context docs
```

---

## 🔧 Setup & Execution: Getting Started

Follow these steps carefully to configure your environment before running the demos.

### Step 1: Install Dependencies
Open a terminal in the project directory and run:
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables (.env)
This repository uses a high-throughput multiplexing router that load-balances across different AI providers. You don't need all of them, but you need at least one API key.

1. **Copy the `.env.example` file** and rename it to `.env`.
   ```bash
   copy .env.example .env
   ```
2. **Add your API Keys** inside the `.env` file. You can generate free API keys from:
   - [Google AI Studio (Gemini)](https://aistudio.google.com/)
   - [Groq Console (Llama 3)](https://console.groq.com/keys)
   - [GitHub Models](https://github.com/marketplace/models)

If you hit a rate limit on one provider, the system will seamlessly failover to the next!

### Step 3: Google Workspace API Setup (credentials.json)
This project actually reads your Gmail and can insert events into your Google Calendar. 
*Note: Your data stays entirely local to your machine. The `.gitignore` ensures secrets are never pushed to GitHub.*

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Enable the **Gmail API** and **Google Calendar API**.
3. Go to **OAuth consent screen**, set up an **External** app, and add your email to the **Test Users** section.
4. Go to **Credentials**, click **Create Credentials → OAuth client ID** (Choose "Desktop app").
5. Click **Download JSON**, rename the downloaded file to exactly `credentials.json`, and place it in the root of this project folder.

### Step 4: First-Time Authentication
Run this one-liner to securely authenticate. A browser window will pop up asking you to sign in to your Google Account.
```bash
python -c "from utils.auth import get_credentials; get_credentials()"
```
*This will generate a local `token.json` file so you don't have to log in every time.*

---

## 🚀 Execution Guide: Running the Demos

Once setup is complete, execute the demos progressively. All outputs have been optimized for clean, structured console displays.

### Session 1: The Paradigm Shift
*Prove that an LLM alone cannot take actions, then build the ReAct agent loop manually.*
```bash
python session_1_vanilla/demo_1a_passive_llm.py
python session_1_vanilla/demo_1b_vanilla_agent.py
```

### Session 2: Frameworks, Memory & Tools
*Inject private rules via Vector Databases (RAG) and dynamically load tool definitions (MCP).*
```bash
python session_2_frameworks/demo_2a_langchain_agent.py
python session_2_frameworks/demo_2b_rag_agent.py
python session_2_frameworks/demo_2c_mcp_client.py
```

### Session 3: Distributed Agent Teams
*Watch a LangGraph system route tasks between a Triage Agent, a Drafter, and a Scheduler, pausing for your manual approval.*
```bash
python session_3_distributed/demo_3_multi_agent.py
```

### Session 4: Experiential Learning
*Run this twice! The agent drafts an email, an Evaluator agent critiques it (Fail/Pass), and the final result is saved format to Episodic Memory. On the second run, watch the agent recall its past mistakes to draft a better email instantly.*
```bash
python session_4_learning/demo_4_reflexion.py
```

### Optional: Start the Web UI
There is a baseline FastAPI Web Dashboard included to visualize the inbox flow.
```bash
uvicorn main:app --reload
```
---

## 🤝 Contribution & License
Feel free to fork this project to experiment with your own `@tool` injections or LangGraph routing node architectures! Make sure to NEVER commit your `.env` or `.json` secrets to source control. Happy Hacking!
