@echo off
REM Quick start script for LiveKit Voice Agent (Windows PowerShell)

echo.
echo ========================================
echo  LiveKit Voice Agent - Quick Start
echo ========================================
echo.

REM Check if we're on Windows
if not exist "%ProgramFiles%\Python*" (
    echo Warning: Python not found in PATH. Make sure Python is installed.
)

setlocal enabledelayedexpansion

echo Step 1: Setting up backend...
if not exist .venv (
    echo Creating virtualenv...
    python -m venv .venv
)

echo Activating virtualenv...
call .venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install --upgrade pip > nul 2>&1
pip install -r requirements.txt > nul 2>&1

if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo ⚠️  IMPORTANT: Edit .env and fill in your API keys!
    echo    • DEEPGRAM_API_KEY
    echo    • ELEVENLABS_API_KEY
    echo    • GEMINI_API_KEY
    echo    • LIVEKIT_API_KEY
    echo    • LIVEKIT_API_SECRET
    echo    • LIVEKIT_URL
    pause
)

echo.
echo Step 2: Setting up token server...
cd token-server
npm install > nul 2>&1

if not exist .env (
    echo Creating token-server/.env from .env.example...
    copy .env.example .env
    echo ⚠️  Fill in the same LiveKit credentials as the main .env
    pause
)

cd ..

echo.
echo Step 3: Setting up frontend...
cd frontend
npm install > nul 2>&1
cd ..

echo.
echo ========================================
echo  Ready to start!
echo ========================================
echo.
echo Open 3 PowerShell windows and run:
echo.
echo  Terminal 1 (Backend):
echo    cd "d:/LiveKit Voice Agent"
echo    .venv\Scripts\activate
echo    python src/main.py
echo.
echo  Terminal 2 (Token Server):
echo    cd "d:/LiveKit Voice Agent/token-server"
echo    node index.js
echo.
echo  Terminal 3 (Frontend):
echo    cd "d:/LiveKit Voice Agent/frontend"
echo    npm run dev
echo.
echo Then open: http://localhost:5173
echo.
pause
