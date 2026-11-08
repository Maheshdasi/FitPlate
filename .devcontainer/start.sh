#!/usr/bin/env bash
# Runs when the Codespace opens: refreshes the demo data and starts FitPlate.
# It stays running in this terminal. The app opens on port 8000 (see the PORTS tab).
set -e
cd "$(dirname "$0")/.."

python .devcontainer/wait-for-db.py
(cd backend && python seed.py)
[ -f frontend/dist/index.html ] || (cd frontend && npm run build)

echo ""
echo "============================================================"
echo "  FitPlate is running."
echo "  Open it: PORTS tab -> port 8000 -> globe icon"
echo "  Demo login: demo@fitness.app / Demo@1234"
echo "  Keep this terminal open while you use the app."
echo "============================================================"
echo ""
cd backend
exec python -m uvicorn app.server:site --host 0.0.0.0 --port 8000
