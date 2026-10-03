@echo off
rem Starts the LedgerLens API (port 8000) and web app (port 3000), then opens the browser.
cd /d "%~dp0"
start "LedgerLens API" cmd /k "backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --port 8000"
start "LedgerLens web" cmd /k "pnpm --dir frontend start"
timeout /t 8 >nul
start http://localhost:3000
