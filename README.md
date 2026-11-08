# AI Fitness & Nutrition Platform (FitPlate)

A full-stack web application that helps users manage fitness, nutrition, workouts and progress in one place.
Users set up a profile, get explainable calorie and macro targets, log food (with an Indian food dataset),
receive machine-learning meal and workout recommendations, track progress with charts, read weekly insights,
and ask an AI assistant questions about their day.

Built as a final-year B.Tech capstone project.

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, React Router |
| Backend | Python, FastAPI, SQLAlchemy 2 |
| Database | PostgreSQL |
| Auth | JWT (HS256) + bcrypt password hashing |
| AI / ML | scikit-learn, Pandas, NumPy |

```
Frontend (React) ──HTTP/JSON──▶ FastAPI backend ──SQLAlchemy ORM──▶ PostgreSQL
                                     │
                                     ▼
                                ML / AI layer (/ml)
```

---

## Features

- **Registration, login and profile setup**: 5-step profile wizard (body, activity, goal, diet, allergies, training); editable later.
- **Calorie & macro calculator**: BMI, BMR (Mifflin-St Jeor), TDEE, goal-adjusted calories, protein/carbs/fat, with every step shown and a medical disclaimer. "Try different values" mode.
- **Food tracker**: search 79 foods, choose servings and meal type, daily goal / consumed / remaining with progress bars and charts, day-by-day navigation.
- **Meal recommendations (ML)**: content-based recommender filtered by diet type and allergies, ranked for the calories and protein left today, with portion scaling, reasons, ingredients, preparation steps, "Show another" and "Add to food log".
- **Workout recommendations (rules + ML)**: weekly split from available days; exercises ranked by cosine similarity with MMR diversity; sets, reps, rest and difficulty.
- **Workout tracker**: tick off exercises, 14-day calendar, recent workouts.
- **Dashboard**: calories, remaining, protein, water (+250 ml), weight vs target, workout status, today's workout, suggested meal, and charts for calories, macros, weight and workout consistency.
- **Progress**: log weight and body measurements; charts for weight (with regression trend forecast), calories vs goal, protein vs goal, workout consistency and water over 7 days / 30 days / 3 months / 6 months.
- **Weekly insights**: Pandas analysis of the week, plain-language insights, practical suggestions, and a K-Means behaviour cluster.
- **AI fitness assistant**: offline intent classifier (TF-IDF + logistic regression) that answers using the user's profile and today's log; refuses medical questions.

---

## Project structure

```
ai-fitness-platform/
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── main.py          app, CORS, error handlers
│   │   ├── config.py        settings from .env
│   │   ├── database.py      engine and session
│   │   ├── models.py        SQLAlchemy tables (12)
│   │   ├── schemas.py       Pydantic request validation
│   │   ├── security.py      bcrypt, JWT, current-user dependency
│   │   ├── routers/         auth, profile, nutrition, recommendations, progress, insights, ai
│   │   └── services/        business logic shared by routers
│   ├── tests/               pytest suite (26 tests)
│   ├── seed.py              loads catalogue + demo user
│   ├── requirements.txt
│   └── .env.example
├── frontend/                React + Vite + Tailwind
│   ├── src/pages/           14 pages
│   ├── src/components/      layout, UI kit, calorie ring, profile form
│   ├── src/api/client.js    fetch wrapper with JWT
│   ├── package.json
│   └── .env.example
├── ml/                      ML / AI layer (pure Python, no web code)
├── database/
│   ├── schema.sql           PostgreSQL schema
│   └── seed_data/           foods.csv, meals.json, exercises.json
└── docs/
    ├── API.md               endpoint reference
    ├── ML_AND_ALGORITHMS.md formula vs rules vs ML
    └── PROJECT_REPORT.md    capstone report sections
```

---

## Quick start on Windows (easiest)

1. Install **Python 3.12** (tick "Add python.exe to PATH"), **Node.js LTS**, and **PostgreSQL** (remember the `postgres` password).
2. Double-click **`setup-windows.bat`** once and type your `postgres` password when asked.
3. Double-click **`start-windows.bat`** whenever you want to run the app. It opens http://localhost:5173.
4. Log in with `demo@fitness.app` / `Demo@1234`.

Other scripts: **`refresh-demo-data-windows.bat`** (run on the morning of a demo so the sample history ends today)
and **`run-tests-windows.bat`** (runs the 26 automated tests).

The manual steps below do the same thing by hand, and work on macOS and Linux too.

## Setup

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
cp .env.example .env              # VITE_API_URL=http://localhost:8000
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

## Main user workflow

Register → profile setup → calorie calculator → food tracker → meal plan → workout plan → workout tracker → progress → weekly insights → assistant.

## Running the tests

```bash
sudo -u postgres createdb -O fitness fitness_test   # once
cd backend
pytest -q
```

The tests use the separate `fitness_test` database (override with `TEST_DATABASE_URL`).

## Security

- Passwords hashed with bcrypt (12 rounds); never stored in plain text.
- JWT bearer tokens with expiry; every data route depends on `get_current_user`.
- Users can only read or delete their own records (checked on every ID-based route).
- Pydantic validation on every input (ranges, enums, email, password strength, no future dates).
- SQLAlchemy ORM with bound parameters, never string-built SQL.
- CORS restricted to the origins in `CORS_ORIGINS`.
- Secrets read from environment variables (`.env`, excluded from git).

## Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot reach the server` in the app | Check the backend is running on port 8000 and `VITE_API_URL` matches. |
| `password authentication failed` | Check `DATABASE_URL` in `backend/.env` matches your PostgreSQL user. |
| CORS error in the browser console | Add your frontend URL to `CORS_ORIGINS` in `backend/.env` and restart. |
| Charts empty for a new user | Expected. Log food, weight and workouts for a few days, or use the demo account. |

## Disclaimer

Calorie and nutrition values are estimates, and the assistant gives general guidance only.
This application does not provide medical advice, diagnosis or treatment.
