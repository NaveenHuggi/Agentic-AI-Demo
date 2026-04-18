"""
╔══════════════════════════════════════════════════════════════╗
║  SESSION 1A  —  The Passive LLM (The Baseline)             ║
╠══════════════════════════════════════════════════════════════╣
║  GOAL: Prove that a standard LLM is ONLY a text predictor. ║
║  It can read and summarize emails, but it CANNOT actually   ║
║  schedule a meeting or take any real-world action.          ║
╚══════════════════════════════════════════════════════════════╝

Run:   python session_1_vanilla/demo_1a_passive_llm.py
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
import google.generativeai as genai
from utils.gmail_utils import fetch_recent_emails

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def run_passive_llm():
    print("=" * 60)
    print("  SESSION 1A : The Passive LLM (Text Predictor)")
    print("=" * 60)

    # ── STEP 1: Fetch real emails from your Gmail ────────────
    print("\n📥 [Step 1] Fetching your 5 most recent emails …")
    emails = fetch_recent_emails(limit=5)

    if not emails:
        print("   ⚠  No emails found. Make sure credentials.json is set up.")
        return

    # ── STEP 2: Format emails as plain text for the LLM ─────
    email_text = ""
    for i, email in enumerate(emails, 1):
        email_text += f"\nEmail {i}:\n"
        email_text += f"  From:    {email['from']}\n"
        email_text += f"  Subject: {email['subject']}\n"
        email_text += f"  Preview: {email['snippet']}\n"

    # ── STEP 3: Ask the LLM to analyse AND schedule ─────────
    prompt = f"""Here are my recent emails:
{email_text}

Please do the following:
1. Categorize each email (urgent / meeting / task / informational).
2. Identify any meeting requests and extract the proposed time.
3. **Schedule the meeting on my Google Calendar right now.**
4. Give me a summary of what you did.
"""

    print("\n🧠 [Step 2] Sending emails to Gemini LLM …")
    model = genai.GenerativeModel("gemini-flash-latest")
    response = model.generate_content(prompt)

    print("\n💬 [Step 3] LLM Response:")
    print("-" * 50)
    print(response.text)
    print("-" * 50)

    # ── THE KEY LESSON ───────────────────────────────────────
    print()
    print("⚠️  IMPORTANT OBSERVATION:")
    print("   The LLM *says* it scheduled the meeting …")
    print("   But open your Google Calendar — NOTHING was created!")
    print()
    print("   WHY?  Because a standard LLM is a TEXT PREDICTOR.")
    print("   It has NO ability to call APIs or execute code.")
    print("   It can only generate text that *looks* like an answer.")
    print()
    print("   👉 THIS is why we need AGENTS (see Demo 1B).")
    print("=" * 60)


if __name__ == "__main__":
    run_passive_llm()


