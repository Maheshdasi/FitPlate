#!/usr/bin/env bash
# Runs once, when the Codespace is created: installs everything and loads the demo data.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Installing backend packages"
python -m pip install -r backend/requirements.txt

echo "==> Creating backend/.env with a random secret key"
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  secret=$(python -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s/change-me-to-a-long-random-string/${secret}/" backend/.env
  # The database address comes from the Codespace (docker-compose.yml), not from .env
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" backend/.env
fi

echo "==> Waiting for PostgreSQL"
python .devcontainer/wait-for-db.py

echo "==> Loading foods, meals, exercises and the demo account"
(cd backend && python seed.py)

echo "==> Installing frontend packages"
(cd frontend && [ -f .env ] || cp .env.example .env; npm install --no-audit --no-fund)

echo "==> Setup complete"
