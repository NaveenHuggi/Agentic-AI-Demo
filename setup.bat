@echo off
echo ============================================================
echo  Inbox Intelligence Agent -- Environment Setup (Windows)
echo ============================================================
echo.

REM Check Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment in .\venv ...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment ...
call venv\Scripts\activate.bat

echo [3/4] Upgrading pip ...
python -m pip install --upgrade pip --quiet

echo [4/4] Installing dependencies from requirements.txt ...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed. Check the output above for details.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  To activate the environment in future sessions, run:
echo      venv\Scripts\activate
echo.
echo  Next Steps:
echo   1. Copy .env.example to .env and add your API keys
echo   2. Place your credentials.json in the project root
echo   3. Run: python -c "from utils.auth import get_credentials; get_credentials()"
echo   4. Run a demo: python session_1_vanilla/demo_1a_passive_llm.py
echo ============================================================
pause
