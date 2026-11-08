# FitPlate: AI Fitness & Nutrition Platform

[![Tests](https://github.com/Maheshdasi/FitPlate/actions/workflows/tests.yml/badge.svg)](https://github.com/Maheshdasi/FitPlate/actions/workflows/tests.yml)

FitPlate is a full-stack web application that brings fitness, nutrition, workouts and progress tracking into one place.
It turns a user's profile into daily calorie and protein targets, suggests meals and workouts that fit those targets,
tracks what they eat and how they train, and explains each week back to them in plain language.

Most fitness apps either give numbers without explaining them or label everything as "AI". FitPlate clearly separates
**formula-based calculations**, **rule-based decisions** and **machine-learning recommendations**, and shows the user
which is which. It also covers everyday Indian meals such as dal, roti, idli, paneer and curd.

Built as a final-year B.Tech capstone project.

![FitPlate dashboard](docs/screenshots/dashboard.png)

---

## The problem

People who want to lose weight, build muscle or simply stay fit usually juggle several separate tools: a calorie calculator,
a food-logging app, a workout app and a notebook for their weight. These tools don't share data, so the user has to work out
for themselves what to eat next, whether today's workout fits their goal, and whether their habits are working.
Popular food databases also focus on packaged Western foods, and many "smart" apps never explain where their numbers come from.

## What FitPlate does

A user's journey through the app:

1. **Create an account and a profile**: age, gender, height, weight, target weight, activity level, fitness goal, diet type
   (vegetarian, non-vegetarian, vegan, eggetarian), food allergies, workout level, available workout days and where they train.
2. **Get their daily targets**: BMI, BMR, TDEE, daily calories, protein, carbohydrates, fat and water, with every step of
   the calculation shown.
3. **Log food**: search 79 foods, choose servings and meal type, and see daily totals, what's left and progress bars update instantly.
4. **Get meal suggestions** for breakfast, lunch, dinner and snacks that respect their diet and allergies and fit the calories
   and protein still left today. Each meal has ingredients, macros, preparation steps and the reasons it was chosen.
5. **Follow a weekly workout plan** built for their goal, level, equipment and free days, and tick off exercises as they go.
6. **Track progress**: weight, body measurements, calories, protein, water and workout consistency over 7 days to 6 months,
   with a trend line that predicts where their weight is heading.
7. **Read a weekly review** in plain sentences, such as "You stayed close to your calorie target on 5 out of 7 days",
   followed by practical suggestions.
8. **Ask the fitness assistant** questions like "What should I eat for dinner?" or "I have 500 calories left, what can I eat?",
   answered from their own profile and today's food log.

## Screenshots

| | |
|---|---|
| ![Landing page](docs/screenshots/landing.png) | ![Calorie calculator](docs/screenshots/calculator.png) |
| Landing page | Calorie and macro calculator, with every step shown |
| ![Food tracker](docs/screenshots/food-tracker.png) | ![Meal plan](docs/screenshots/meal-plan.png) |
| Food tracker with daily totals | Meal recommendations with match score and reasons |
| ![Workout plan](docs/screenshots/workout-plan.png) | ![Progress](docs/screenshots/progress.png) |
| Weekly workout plan | Progress charts with a weight trend forecast |
| ![Weekly insights](docs/screenshots/weekly-insights.png) | ![Fitness assistant](docs/screenshots/assistant.png) |
| Weekly insights and habit pattern | Fitness assistant using the user's own data |

<p align="center"><img src="docs/screenshots/mobile-dashboard.png" alt="Dashboard on a phone" width="300"><br>The layout adapts to phones and tablets</p>

---

## How it works

### Architecture

```
React website  ──HTTP / JSON──▶  FastAPI backend  ──SQLAlchemy ORM──▶  PostgreSQL
                                       │
                                       ▼
                               ML / AI layer (/ml)
```

- The **React website** shows the pages, charts and forms, and talks to the backend through a REST API.
- The **FastAPI backend** checks who the user is (JWT login), validates every input, reads and writes the database,
  and calls the ML layer.
- The **ML layer** is plain Python (scikit-learn, Pandas, NumPy) with no web code, so each model can be tested on its own.
- **PostgreSQL** stores users, profiles, foods, meals, exercises and every log, in 12 related tables.

### Formulas, rules and machine learning

| Part of the app | Type | Technique |
|---|---|---|
| BMI, BMR, TDEE, calories, protein, carbs, fat, water | Formula | WHO BMI, Mifflin-St Jeor equation, activity factors, goal adjustment |
| Removing meals that break the diet type or contain allergens | Rule | Hard safety filter, applied before any ML |
| Weekly workout split; sets, reps and rest | Rule | Common strength-training guidelines by goal and level |
| Ranking meals | Machine learning | Content-based filtering: TF-IDF and cosine similarity |
| Choosing exercises | Machine learning | Cosine similarity with Maximal Marginal Relevance (MMR) |
| Weight trend and target date | Machine learning | Linear regression |
| Habit pattern in the weekly review | Machine learning | K-Means clustering |
| Weekly statistics and suggestions | Analysis and rules | Pandas aggregation with threshold rules |
| Understanding assistant questions | Machine learning | TF-IDF (character n-grams) and logistic regression |

### Calorie and macro targets (formula-based)

```
BMI      = weight (kg) / height (m)²
BMR      = 10 × weight + 6.25 × height (cm) - 5 × age + 5   (men; -161 for women)
TDEE     = BMR × activity factor (1.2 to 1.725)
Calories = TDEE adjusted for the goal (-20% weight loss, +15% weight gain, +10% muscle gain)
Protein  = 1.4 to 2.0 g per kg of body weight, depending on the goal
Fat      = 25% of calories;  Carbohydrates = the remaining calories
```

The calculator page shows every one of these steps with the user's own numbers and a medical disclaimer.

### Meal recommendations (content-based filtering)

1. **Filter**: meals outside the user's diet type or containing their allergens are removed.
2. **Target**: the calories and protein left today are shared out across the meals not yet eaten.
3. **Score** each remaining meal on four things: how closely its protein/carbs/fat split matches the target (cosine similarity),
   how close its calories are to the target, how similar its ingredients are to foods the user likes and logs often
   (TF-IDF), and its protein per calorie.
4. **Portion**: the serving is scaled between 0.75× and 1.5× to land near the target.

"Show another" gives the next-best meal that hasn't been shown yet. The more a user logs, the more personal the suggestions become.

### Workout recommendations (rules + similarity)

The number of free days decides the weekly split (for example, 4 days gives upper body and lower body sessions twice),
and the goal and level decide sets, reps and rest. Every exercise is described as a set of features (difficulty, equipment,
strength or cardio, compound movement, goals it suits). The user is described the same way, and exercises are ranked by
cosine similarity. Maximal Marginal Relevance then picks a varied session, so the same muscle isn't trained twice in a row.

### Progress, weekly insights and the assistant

- **Weight trend**: linear regression on recent weight entries gives the weekly change, a 4-week forecast and an estimated
  date to reach the target weight.
- **Weekly insights**: Pandas summarises the week (days on calorie target, average protein, workouts, water, weight change),
  rules turn it into plain sentences and suggestions, and K-Means places the week into a habit pattern such as
  "Consistent achiever" or "Getting started".
- **Fitness assistant**: a safety rule first declines questions about medical conditions, medicines or injuries.
  A classifier then works out what the user is asking (meal idea, calories left, protein, workout, progress, water),
  and the answer is built from their own targets, today's log, the meal recommender and their workout plan.
  It runs fully offline with no paid API.

Full details: [docs/ML_AND_ALGORITHMS.md](docs/ML_AND_ALGORITHMS.md)

---

## Data

- **79 foods**, mostly Indian staples (rice, roti, dal, idli, paneer, curd, chicken, eggs, fruits, nuts and more),
  with calories, protein, carbs, fat, fibre, diet type and allergens per serving.
- **49 meals** with ingredients, preparation steps and macros, across breakfast, lunch, dinner and snacks.
- **72 exercises** across chest, back, shoulders, arms, legs, core, full body and cardio, with target muscle,
  equipment and difficulty.
- **A demo account** with four months of food, water, weight, measurement and workout history, so every chart
  and insight has data from the first login (`demo@fitness.app` / `Demo@1234`).

## Security

- Passwords are hashed with bcrypt and never stored as plain text.
- Login uses JWT tokens that expire; every page of user data requires a valid token.
- Users can only see and change their own records.
- Every input is validated (ranges, allowed values, email format, password strength, no future dates).
- All database access goes through the SQLAlchemy ORM, which prevents SQL injection.
- Secrets are kept in environment variables, never in the code.

## Testing

26 automated tests cover the formulas, login and security, input validation, food logging, the diet and allergy rules,
the meal and workout recommenders, progress tracking, weekly insights and the assistant's safety rule. They run
automatically on every update (see the **Tests** badge above). In an evaluation of 384 combinations of diet, allergies,
goal and meal, the meal recommender never suggested a meal that broke the user's diet or allergy settings.

## Technology

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, React Router |
| Backend | Python, FastAPI, SQLAlchemy 2, Pydantic |
| Database | PostgreSQL |
| Authentication | JWT and bcrypt |
| AI / ML | scikit-learn, Pandas, NumPy |

## Project structure

```
FitPlate/
├── frontend/      React website: 14 pages, charts and the API client
├── backend/       FastAPI application: routes, database models, validation, security, tests
├── ml/            Machine-learning and calculation modules
├── database/      PostgreSQL schema and the food, meal and exercise datasets
└── docs/          Project report, API reference, algorithm details and screenshots
```

## Try it yourself

There are three ways to run FitPlate. The first two need only a browser and a GitHub account.

**1. Deploy it online (live link)**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Maheshdasi/FitPlate)

1. Click the button above and sign in to Render with GitHub (the free plan is enough).
2. Click **Deploy Blueprint**. Render reads [`render.yaml`](render.yaml) and creates the website, the API and a PostgreSQL database.
3. After about 5 to 10 minutes the service shows **Live**. Open its `onrender.com` link.

On the free plan the site sleeps after 15 minutes without visitors and takes about a minute to wake up.

**2. Run it in GitHub Codespaces (in the browser)**

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Maheshdasi/FitPlate?quickstart=1)

1. Click the button above, then **Create codespace**.
2. Wait about 3 to 5 minutes while it installs everything and loads the demo data.
3. The website opens in a new tab. If it doesn't, open the **PORTS** tab and click the globe icon next to port **5173**.

**3. Run it on your own computer**

Install Python 3.12 or 3.13, Node.js and PostgreSQL. On Windows, double-click `setup-windows.bat` once and then
`start-windows.bat`. On macOS or Linux, follow the manual steps in [docs/SETUP.md](docs/SETUP.md).

**Log in** with the demo account **`demo@fitness.app`** / **`Demo@1234`**, which has four months of sample history,
or click "Get started" to create a new account. The API documentation is at `/api/docs` on the live site,
or `/docs` on port 8000 in Codespaces and locally.

## Documentation

- [Project report](docs/PROJECT_REPORT.md): problem statement, literature survey, objectives, design, methodology, testing and results
- [Algorithms](docs/ML_AND_ALGORITHMS.md): every formula, rule and model in detail
- [API reference](docs/API.md): all REST endpoints
- [Database schema](database/schema.sql)
- [Setup and deployment](docs/SETUP.md)

## Disclaimer

Calorie and nutrition values are estimates, and the assistant gives general guidance only.
FitPlate does not provide medical advice, diagnosis or treatment.
