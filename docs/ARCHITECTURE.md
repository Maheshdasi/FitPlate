# Architecture

FitPlate has three layers (React website, FastAPI backend, PostgreSQL database) and a separate ML layer that the
backend calls as plain Python functions. The diagrams below are drawn by GitHub from the text in this file.

## System overview

```mermaid
flowchart LR
    U([User's browser]) -->|pages, charts, forms| FE[React website<br/>Vite + Tailwind + Recharts]
    FE -->|REST API, JSON + JWT| BE[FastAPI backend<br/>validation, auth, business logic]
    BE -->|SQLAlchemy ORM| DB[(PostgreSQL<br/>12 tables)]
    BE -->|Python calls| ML
    subgraph ML [ML layer: ml/]
        direction TB
        F[Formulas<br/>BMI, BMR, TDEE, macros]
        R[Rules<br/>diet and allergy filter,<br/>weekly split, sets and reps]
        M[Models<br/>content-based meals, exercise similarity,<br/>linear regression, K-Means, intent classifier]
    end
```

## How a meal recommendation is made

```mermaid
sequenceDiagram
    actor User
    participant Web as React website
    participant API as FastAPI
    participant DB as PostgreSQL
    participant ML as Meal recommender

    User->>Web: Opens "Meal plan"
    Web->>API: GET /recommendations/meals (JWT)
    API->>DB: Profile, today's food log, foods logged most often
    API->>ML: Daily targets (formulas)
    ML-->>API: Calories and protein left, split across uneaten meals
    API->>ML: Rank meals for each slot
    Note over ML: 1. Remove meals outside the diet type or with allergens (rule)<br/>2. Score: macro cosine similarity, calorie fit,<br/>TF-IDF similarity to liked foods, protein density<br/>3. Scale the portion to 0.75x to 1.5x
    ML-->>API: Ranked meals with reasons
    API->>DB: Save today's pick (stays stable, "Show another" skips it)
    API-->>Web: Recommended meal and 3 alternatives per slot
    Web-->>User: Meal cards with macros, ingredients and reasons
```

## User journey

```mermaid
flowchart LR
    A[Register] --> B[5-step profile] --> C[Calorie and macro targets]
    C --> D[Log food] --> E[Meal suggestions]
    C --> F[Weekly workout plan] --> G[Log sets, reps and weight]
    D --> H[Progress charts]
    G --> H
    H --> I[Weekly insights]
    D -.-> J[Ask the assistant]
    F -.-> J
```

## Database

```mermaid
erDiagram
    users ||--|| user_profiles : has
    users ||--o{ food_logs : logs
    users ||--o{ meal_recommendations : receives
    users ||--o{ workout_plans : follows
    users ||--o{ workout_logs : completes
    users ||--o{ weight_logs : records
    users ||--o{ water_logs : records
    users ||--o{ weekly_insights : gets
    food_items |o--o{ food_logs : "logged as"
    meals |o--o{ food_logs : "logged as"
    meals ||--o{ meal_recommendations : "recommended as"
    workout_exercises ||--o{ workout_logs : "done as"
    workout_plans |o--o{ workout_logs : "part of"

    users {
        int id PK
        string email UK
        string password_hash
    }
    user_profiles {
        int user_id FK
        int age
        float height_cm
        float weight_kg
        float target_weight_kg
        string fitness_goal
        string dietary_preference
        text allergies
        string workout_level
    }
    food_items {
        int id PK
        string name UK
        float calories
        float protein
        float carbs
        float fat
        string diet_type
        text allergens
    }
    meals {
        int id PK
        string name UK
        string meal_type
        text ingredients
        text instructions
        float calories
    }
    food_logs {
        int id PK
        int user_id FK
        date log_date
        string meal_type
        float quantity
        float calories
    }
    meal_recommendations {
        int user_id FK
        int meal_id FK
        date rec_date
        string meal_type
        float match_score
    }
    workout_exercises {
        int id PK
        string name UK
        string category
        string target_muscle
        string difficulty
    }
    workout_plans {
        int id PK
        int user_id FK
        jsonb plan
        text schedule
    }
    workout_logs {
        int user_id FK
        int exercise_id FK
        date log_date
        bool completed
    }
    weight_logs {
        int user_id FK
        date log_date
        float weight_kg
        float waist_cm
    }
    water_logs {
        int user_id FK
        date log_date
        int amount_ml
    }
    weekly_insights {
        int user_id FK
        date week_start
        jsonb insights
        jsonb behaviour
    }
```

Every table has a `created_at` timestamp, every user-owned row is deleted with its user, and CHECK constraints
guard every range and allowed value. Full DDL: [database/schema.sql](../database/schema.sql).

## Code layout

| Folder | What it contains |
|---|---|
| `frontend/src/pages` | The 14 pages (landing, login, registration, profile setup, dashboard, calculator, food tracker, meal plan, workout plan, workout tracker, progress, weekly insights, assistant, settings) |
| `frontend/src/components` | Sidebar layout, calorie ring, profile form, shared UI pieces |
| `backend/app/routers` | REST endpoints grouped by feature |
| `backend/app/services` | Business logic shared by the endpoints |
| `backend/app/models.py`, `schemas.py` | Database tables and input validation |
| `ml/` | Formulas, rules and models, independent of the web code |
| `backend/tests` | 110 automated tests (API, security and ML) |
