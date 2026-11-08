# Setup and deployment

How to run FitPlate on your own computer, on GitHub Codespaces, or online on Render.

## Online on Render (live link)

The repository includes a [`render.yaml`](render.yaml) blueprint and a [`Dockerfile`](Dockerfile), so it can be deployed straight from GitHub to [Render](https://render.com) on the free plan, with no code editor:

1. Click **[Deploy to Render](https://render.com/deploy?repo=https://github.com/Maheshdasi/FitPlate)** and sign in to Render with GitHub.
2. Click **Deploy Blueprint**. Render creates the web service (website + API) and a free PostgreSQL database.
3. The first build takes about 5 to 10 minutes. When it shows **Live**, open the service's `onrender.com` link.
4. Log in with **`demo@fitness.app`** / **`Demo@1234`**. The API documentation is at `/api/docs`.

Every new push to `main` redeploys automatically. On the free plan the site sleeps after 15 minutes without visitors and takes about a minute to wake up, and the free database expires after 30 days (it can be recreated from the same blueprint).

## On GitHub Codespaces (no installation)

The whole app (website, API and PostgreSQL database) runs inside GitHub Codespaces in your browser.

1. Click **[Open in GitHub Codespaces](https://codespaces.new/Maheshdasi/FitPlate?quickstart=1)** and then **Create codespace** (you need to be signed in to GitHub).
2. Wait about 3 to 5 minutes the first time while it installs everything and loads the demo data. You can watch the progress in the terminal.
3. The website opens in a new browser tab. If it doesn't, open the **PORTS** tab at the bottom and click the globe icon next to port **5173**.
4. Log in with the demo account: **`demo@fitness.app`** / **`Demo@1234`** (4 months of sample history), or click "Get started" to create your own account.

The API documentation (Swagger) is on port **8000** at `/docs`. Every push also runs the 26 automated tests on GitHub Actions; see the **Tests** badge in the README.

## On Windows (easiest)

1. Install **Python 3.12** (tick "Add python.exe to PATH"), **Node.js LTS**, and **PostgreSQL** (remember the `postgres` password).
2. Double-click **`setup-windows.bat`** once and type your `postgres` password when asked.
3. Double-click **`start-windows.bat`** whenever you want to run the app. It opens http://localhost:5173.
4. Log in with `demo@fitness.app` / `Demo@1234`.

Other scripts: **`refresh-demo-data-windows.bat`** (run on the morning of a demo so the sample history ends today)
and **`run-tests-windows.bat`** (runs the 26 automated tests).

The manual steps below do the same thing by hand, and work on macOS and Linux too.

## On your own computer (manual setup)

### Prerequisites

- Python 3.10+ (tested on 3.13)
- Node.js 18+ (tested on 22)
- PostgreSQL 13+ (tested on 16)

### 1. Create the database

```bash
# Linux / macOS
sudo -u postgres psql -c "CREATE USER fitness WITH PASSWORD 'fitness' CREATEDB;"
sudo -u postgres createdb -O fitness fitness_db
```

On Windows, open **SQL Shell (psql)** as the `postgres` user and run:

```sql
CREATE USER fitness WITH PASSWORD 'fitness' CREATEDB;
CREATE DATABASE fitness_db OWNER fitness;
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
```

Edit `.env` and set `JWT_SECRET` to a long random string:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Load the food, meal and exercise data and the demo user, then start the API:

```bash
python seed.py
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI): http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env              # leave VITE_API_URL empty: /api is forwarded to port 8000
npm run dev
```

Open http://localhost:5173

### Demo account

| Email | Password |
|---|---|
| `demo@fitness.app` | `Demo@1234` |

The demo user (Arjun, 24, weight loss, eggetarian, peanut allergy, 4 workout days) has 120 days of
food, water, weight, measurement and workout history, so every chart and insight works immediately.
Run `python seed.py` again at any time to regenerate the history relative to today.
`python seed.py --reset` drops and recreates all tables.

---

## Running the tests

```bash
sudo -u postgres createdb -O fitness fitness_test   # once
cd backend
pytest -q
```

The tests use the separate `fitness_test` database (override with `TEST_DATABASE_URL`).

## Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot reach the server` in the app | Check the backend is running on port 8000. Leave `VITE_API_URL` in `frontend/.env` empty, or set it to `http://localhost:8000`. |
| `password authentication failed` | Check `DATABASE_URL` in `backend/.env` matches your PostgreSQL user. |
| CORS error in the browser console | Add your frontend URL to `CORS_ORIGINS` in `backend/.env` and restart. |
| Charts empty for a new user | Expected. Log food, weight and workouts for a few days, or use the demo account. |
