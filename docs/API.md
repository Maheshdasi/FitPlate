# API reference

Base URL: `http://localhost:8000` · Interactive docs: `/docs` (Swagger) and `/redoc`.

All routes except `/auth/register`, `/auth/login` and `/` need the header:

```
Authorization: Bearer <access_token>
```

Dates are `YYYY-MM-DD`. Most "today" routes accept `?date=` so the client can send its **local** date
(avoids UTC/IST mismatches). Dates more than one day in the future are rejected.

## Status codes

| Code | Meaning |
|---|---|
| 200 | OK |
| 201 | Created |
| 204 | Deleted (no body) |
| 401 | Missing, invalid or expired token; wrong email/password |
| 404 | Not found (or belongs to another user) |
| 409 | Conflict: email already registered, or profile not set up yet |
| 422 | Validation failed |

Error body:

```json
{ "detail": "age: Input should be greater than or equal to 13",
  "errors": [{ "field": "age", "message": "Input should be greater than or equal to 13" }] }
```

---

## Authentication

### `POST /auth/register` → 201

```json
{ "email": "priya@example.com", "password": "Fitness2026" }
```

Password: 8–72 characters with at least one letter and one number.

Response (also returned by login):

```json
{ "access_token": "eyJ...", "token_type": "bearer", "user_id": 7, "email": "priya@example.com", "has_profile": false }
```

### `POST /auth/login` → 200

Same body as register. `401` on wrong email or password.

### `GET /auth/me`

`{ "id": 7, "email": "...", "has_profile": true, "name": "Priya Reddy" }`

---

## Profile

### `GET /profile`

`404` if the profile has not been created yet.

### `PUT /profile` (create or update)

```json
{
  "name": "Priya Reddy", "age": 21, "gender": "female",
  "height_cm": 160, "weight_kg": 52, "target_weight_kg": 56,
  "activity_level": "moderately_active", "fitness_goal": "muscle_gain",
  "dietary_preference": "vegetarian", "allergies": ["nuts"],
  "food_preferences": "paneer, dosa, curd",
  "workout_level": "beginner", "workout_days_per_week": 3, "preferred_workout_type": "home"
}
```

| Field | Allowed values |
|---|---|
| gender | `male`, `female`, `other` |
| activity_level | `sedentary`, `lightly_active`, `moderately_active`, `very_active` |
| fitness_goal | `weight_loss`, `weight_gain`, `muscle_gain`, `maintenance`, `general_fitness` |
| dietary_preference | `vegetarian`, `non_vegetarian`, `vegan`, `eggetarian` |
| allergies | `dairy`, `eggs`, `gluten`, `nuts`, `peanuts`, `soy`, `fish`, `shellfish`, `sesame` |
| workout_level | `beginner`, `intermediate`, `advanced` |
| workout_days_per_week | 2–6 |
| preferred_workout_type | `gym`, `home`, `bodyweight`, `mixed`, `cardio` |

Ranges: age 13–100, height 100–250 cm, weights 30–300 kg. Target weight must match the goal
(at or below current weight for weight loss; not below current for gain). Saving also logs the weight
and rebuilds the workout plan if goal, level, days or type changed.

---

## Nutrition

### `GET /foods?search=&category=&limit=`

List of foods with nutrients **per serving**:

```json
[{ "id": 26, "name": "Paneer", "category": "Dairy", "serving_desc": "100 g", "serving_g": 100,
   "calories": 265, "protein": 18, "carbs": 3.5, "fat": 20, "fiber": 0,
   "diet_type": "vegetarian", "allergens": ["dairy"] }]
```

### `GET /foods/categories`

### `POST /food-log` → 201

```json
{ "food_item_id": 26, "quantity": 1.5, "meal_type": "lunch", "log_date": "2026-10-20" }
```

Exactly one of `food_item_id` / `meal_id`. `quantity` is servings (0 < q ≤ 20).
`meal_type`: `breakfast`, `lunch`, `dinner`, `snacks`. Nutrients are stored as a snapshot.

### `GET /food-log/today?date=`

```json
{ "date": "2026-10-20",
  "entries": { "breakfast": [ ... ], "lunch": [ ... ], "dinner": [], "snacks": [] },
  "by_meal": { "breakfast": { "calories": 548, "protein": 18, "carbs": 81, "fat": 18 }, ... },
  "goal":      { "calories": 2181, "protein": 140, "carbs": 269, "fat": 61 },
  "consumed":  { "calories": 1366, "protein": 61.5, "carbs": 157.5, "fat": 55.5 },
  "remaining": { "calories": 815,  "protein": 78.5, "carbs": 111.5, "fat": 5.5 } }
```

### `DELETE /food-log/{id}` → 204

### `GET /nutrition/calories`

```json
{ "bmi": 25.5, "bmi_category": "Overweight", "bmr": 1759, "tdee": 2726, "daily_calories": 2181,
  "protein_g": 140, "carbs_g": 269, "fat_g": 61, "water_ml": 2750,
  "current_weight": 78.0, "target_weight": 72.0,
  "message": "Your estimated daily calorie requirement is 2181 kcal.",
  "explanation": ["BMI = 78.0 kg / (1.75 m)² = 25.5 (Overweight).", "..."],
  "disclaimer": "Calorie and nutrition values are estimates ... not medical advice ...",
  "inputs": { ... } }
```

### `POST /nutrition/calculate`

"What if" calculation without saving: `age, gender, height_cm, weight_kg, activity_level, fitness_goal, target_weight_kg?`.

---

## Recommendations

### `GET /recommendations/meals?date=`

One recommendation per meal slot plus three alternatives. Picks are stored in `meal_recommendations`
so they stay stable for the day.

```json
{ "slots": { "dinner": {
    "target": { "calories": 611, "protein": 59, "carbs": 81, "fat": 18, "already_eaten": false },
    "recommended": { "id": 30, "name": "Egg bhurji with 2 rotis", "portion": 1.25,
      "calories": 644, "protein": 33.8, "carbs": 62.5, "fat": 27.5, "match_score": 74,
      "ingredients": ["3 eggs", "..."], "instructions": "...",
      "reasons": ["Close to your 611 kcal target for this meal", "Matches foods you like or log often"] },
    "alternatives": [ ... ], "status": "suggested" } },
  "targets": { ... }, "consumed": { ... }, "method": "Content-based filtering: ..." }
```

### `POST /recommendations/meals/replace`

`{ "meal_type": "dinner", "rec_date": "2026-10-20" }` → the next-best meal not shown yet.
`404` when nothing else fits the user's diet and allergies.

### `POST /recommendations/meals/log` → 201

`{ "meal_type": "dinner" }` adds today's recommended meal (with its portion) to the food log.

### `GET /recommendations/workouts?date=&regenerate=false`

```json
{ "plan_id": 1, "days_per_week": 4, "level": "intermediate", "goal": "weight_loss",
  "schedule": ["Monday", "Tuesday", "Thursday", "Friday"],
  "sessions": [{ "day_number": 1, "weekday": 0, "weekday_name": "Monday", "title": "Upper body",
     "estimated_minutes": 50,
     "exercises": [{ "exercise_id": 3, "name": "Incline push-ups", "category": "chest",
        "target_muscle": "Lower chest", "equipment": "bodyweight", "difficulty": "beginner",
        "sets": 3, "reps": "12-15", "rest_seconds": 45, "similarity": 0.83, "instructions": "..." }] }],
  "today": { "date": "2026-10-20", "weekday": "Tuesday", "is_rest_day": false,
             "session": { ... }, "completed_exercise_ids": [] } }
```

### `POST /workout-log` → 201

`{ "exercise_id": 3, "completed": true, "sets_completed": 3, "day_number": 1, "log_date": "2026-10-20" }`
One row per user, date and exercise (sending `completed: false` un-ticks it).

### `GET /workout-log/history?days=30&date=`

Completed exercises grouped by day, newest first.

---

## Progress

### `POST /progress/weight` → 201

`{ "weight_kg": 78.0, "waist_cm": 89, "chest_cm": 99.5, "hips_cm": 97, "arms_cm": 33.6, "log_date": "2026-10-20" }`
One entry per day (updates if it exists). The latest entry becomes the profile weight.

### `GET /progress/weight?days=180` · `DELETE /progress/weight/{id}`

### `POST /progress/water` → 201 · `DELETE /progress/water/last?date=`

`{ "amount_ml": 250 }` → `{ "date": "...", "total_ml": 1500, "goal_ml": 2750 }`

### `GET /progress/summary?days=7|30|90|180&date=`

Daily series (`calories`, `protein`, goals, `water_ml`, `workout_done`, `workout_planned`), weight and
measurement series, totals (averages, consistency %, weight change) and the regression `prediction`.

### `GET /dashboard?date=`

Everything the dashboard shows in one call.

---

## Insights

### `GET /insights/weekly?week_start=&current=false&date=`

Default: the last completed Monday–Sunday week. `current=true`: this week so far.

```json
{ "week_start": "2026-10-12", "week_end": "2026-10-18", "is_complete": true,
  "metrics": { "days_logged": 7, "days_on_calorie_target": 7, "avg_protein": 103.7,
               "workouts_completed": 4, "workouts_planned": 4, "weight_change_kg": -0.1, ... },
  "insights": [{ "tone": "good", "text": "You stayed close to your calorie target on 7 out of 7 days." }],
  "suggestions": ["Try adding a protein-rich snack in the afternoon ..."],
  "behaviour": { "label": "Consistent achiever", "description": "...", "features": { ... } },
  "daily": [ ... ] }
```

### `GET /insights/history`

Up to 12 stored weeks.

---

## AI assistant

### `POST /ai/chat`

```json
{ "message": "I have 500 calories remaining. What can I eat?", "local_date": "2026-10-20", "local_hour": 19 }
```

```json
{ "reply": "Today you've eaten 1366 of 2181 kcal ...", "intent": "calories_remaining",
  "confidence": 0.88, "quick_replies": ["What should I eat for dinner?", "..."] }
```

Intents: `meal_suggestion`, `calories_remaining`, `protein_query`, `workout_today`, `calorie_target`,
`progress`, `water`, `greeting`, `unknown`, and `medical_safety` (health-condition questions are declined).
