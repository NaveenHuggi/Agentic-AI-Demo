#!/usr/bin/env bash
set -e

echo "============================================================"
echo " Inbox Intelligence Agent -- Environment Setup (Mac/Linux)"
echo "============================================================"
echo ""

# Check Python is installed
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 is not installed."
    echo "Install it via: sudo apt install python3 python3-venv  (Ubuntu)"
    echo "            or: brew install python                     (macOS)"
    exit 1
fi

echo "[1/4] Creating virtual environment in ./venv ..."
python3 -m venv venv

echo "[2/4] Activating virtual environment ..."
source venv/bin/activate

echo "[3/4] Upgrading pip ..."
pip install --upgrade pip --quiet

echo "[4/4] Installing dependencies from requirements.txt ..."
pip install -r requirements.txt

echo ""
echo "============================================================"
echo " Setup complete!"
echo ""
echo " To activate the environment in future sessions, run:"
echo "     source venv/bin/activate"
echo ""
echo " Next Steps:"
echo "  1. Copy .env.example to .env and add your API keys"
echo "  2. Place your credentials.json in the project root"
echo "  3. Run: python -c \"from utils.auth import get_credentials; get_credentials()\""
echo "  4. Run a demo: python session_1_vanilla/demo_1a_passive_llm.py"
echo "============================================================"
