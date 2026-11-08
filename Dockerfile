# One container for the whole platform: React website + FastAPI API + ML layer.
# Used for online hosting (Render). The database is provided by the host.

# ---- 1. Build the React website ----
FROM node:22-slim AS website
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Python backend that also serves the website ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY ml/ ml/
COPY database/ database/
COPY --from=website /web/dist frontend/dist
WORKDIR /app/backend
EXPOSE 8000
# Load foods, meals, exercises and refresh the demo account, then start the server
CMD python seed.py && uvicorn app.server:site --host 0.0.0.0 --port ${PORT}
