#!/usr/bin/env pwsh
# Quick start script for LiveKit Voice Agent (Windows PowerShell)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LiveKit Voice Agent - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Setting up backend..." -ForegroundColor Green

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtualenv..."
    python -m venv .venv
}

Write-Host "Activating virtualenv..."
& ".venv\Scripts\Activate.ps1"

Write-Host "Installing Python dependencies (this may take a minute)..."
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item .env.example .env
    Write-Host "⚠️  IMPORTANT: Edit .env and fill in your API keys!" -ForegroundColor Yellow
    Write-Host "   • DEEPGRAM_API_KEY"
    Write-Host "   • ELEVENLABS_API_KEY"
    Write-Host "   • GEMINI_API_KEY"
    Write-Host "   • LIVEKIT_API_KEY"
    Write-Host "   • LIVEKIT_API_SECRET"
    Write-Host "   • LIVEKIT_URL"
    Read-Host "Press Enter once you've updated .env"
}

Write-Host ""
Write-Host "Step 2: Setting up token server..." -ForegroundColor Green

Push-Location "token-server"
Write-Host "Installing Node dependencies..."
npm install --quiet

if (-not (Test-Path ".env")) {
    Write-Host "Creating token-server/.env..."
    Copy-Item .env.example .env
    Write-Host "⚠️  Fill in the same LiveKit credentials as the main .env" -ForegroundColor Yellow
    Read-Host "Press Enter once you've updated token-server/.env"
}

Pop-Location

Write-Host ""
Write-Host "Step 3: Setting up frontend..." -ForegroundColor Green

Push-Location "frontend"
Write-Host "Installing Node dependencies..."
npm install --quiet
Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ready to start!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Open 3 PowerShell windows and run each of these commands:" -ForegroundColor Magenta
Write-Host ""

Write-Host "  Terminal 1 (Backend):" -ForegroundColor Yellow
Write-Host "    cd ""d:/LiveKit Voice Agent"""
Write-Host "    .venv\Scripts\activate"
Write-Host "    python src/main.py"
Write-Host ""

Write-Host "  Terminal 2 (Token Server):" -ForegroundColor Yellow
Write-Host "    cd ""d:/LiveKit Voice Agent/token-server"""
Write-Host "    node index.js"
Write-Host ""

Write-Host "  Terminal 3 (Frontend):" -ForegroundColor Yellow
Write-Host "    cd ""d:/LiveKit Voice Agent/frontend"""
Write-Host "    npm run dev"
Write-Host ""

Write-Host "Then open in your browser: " -ForegroundColor Cyan -NoNewline
Write-Host "http://localhost:5173" -ForegroundColor White

Write-Host ""
Read-Host "Press Enter to exit"
