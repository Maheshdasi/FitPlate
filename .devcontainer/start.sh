#!/usr/bin/env bash
# Runs every time the Codespace starts: refreshes the demo data and starts the app.
cd "$(dirname "$0")/.."
mkdir -p /tmp/fitplate

python .devcontainer/wait-for-db.py
# Regenerate the demo account's history so it always ends today
(cd backend && python seed.py) > /tmp/fitplate/seed.log 2>&1

pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

(cd backend && setsid nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/fitplate/backend.log 2>&1 &)
(cd frontend && setsid nohup npm run dev -- --host 0.0.0.0 --port 5173 > /tmp/fitplate/frontend.log 2>&1 &)

echo "FitPlate is starting. Open the PORTS tab and click the globe icon next to port 5173."
echo "Demo login: demo@fitness.app / Demo@1234"
echo "Logs: /tmp/fitplate/backend.log and /tmp/fitplate/frontend.log"
