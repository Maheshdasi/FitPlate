"""
Load the food, meal and exercise catalogues and create a demo user with
~4 months of realistic history, so every chart and insight works right
after setup.

    python seed.py            # add catalogue + demo user (safe to re-run)
    python seed.py --reset    # drop all tables first
"""

import csv
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.config import SEED_DIR
from app.database import Base, SessionLocal, engine, init_db
from app.models import (
    FoodItem,
    FoodLog,
    Meal,
    MealRecommendation,
    User,
    UserProfile,
    WaterLog,
    WeeklyInsight,
    WeightLog,
    WorkoutExercise,
    WorkoutLog,
)
from app.security import hash_password
from app.services.nutrition import DIET_ORDER, profile_targets
from app.services.recommendations import active_plan, reset_models, session_for_date

DEMO_EMAIL = "demo@fitness.app"
DEMO_PASSWORD = "Demo@1234"
HISTORY_DAYS = 120


def load_catalogue(db):
    with open(SEED_DIR / "foods.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if db.scalar(select(FoodItem).where(FoodItem.name == row["name"])):
                continue
            db.add(FoodItem(
                name=row["name"], category=row["category"], serving_desc=row["serving_desc"],
                serving_g=float(row["serving_g"]), calories=float(row["calories"]),
                protein=float(row["protein"]), carbs=float(row["carbs"]), fat=float(row["fat"]),
                fiber=float(row["fiber"]), diet_type=row["diet_type"],
                allergens=[a for a in row["allergens"].split(";") if a],
            ))
    for m in json.loads((SEED_DIR / "meals.json").read_text(encoding="utf-8")):
        if not db.scalar(select(Meal).where(Meal.name == m["name"])):
            db.add(Meal(**m))
    for e in json.loads((SEED_DIR / "exercises.json").read_text(encoding="utf-8")):
        if not db.scalar(select(WorkoutExercise).where(WorkoutExercise.name == e["name"])):
            db.add(WorkoutExercise(**{"is_timed": False, "default_duration": None, **e}))
    db.commit()
    reset_models()
    print(f"Catalogue: {db.query(FoodItem).count()} foods, {db.query(Meal).count()} meals, "
          f"{db.query(WorkoutExercise).count()} exercises")


def create_demo_user(db):
    rng = random.Random(7)
    today = date.today()
    start = today - timedelta(days=HISTORY_DAYS)

    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user:
        for model in (FoodLog, WaterLog, WeightLog, WorkoutLog, MealRecommendation, WeeklyInsight):
            db.execute(delete(model).where(model.user_id == user.id))
    else:
        user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        db.add(user)
        db.flush()

    start_weight, end_weight = 82.0, 78.2
    profile = user.profile or UserProfile(user_id=user.id)
    profile.name = "Arjun Mehta"
    profile.age = 24
    profile.gender = "male"
    profile.height_cm = 175
    profile.weight_kg = end_weight
    profile.target_weight_kg = 72
    profile.activity_level = "moderately_active"
    profile.fitness_goal = "weight_loss"
    profile.dietary_preference = "eggetarian"
    profile.allergies = ["peanuts"]
    profile.food_preferences = "paneer, dal, eggs, oats, curd, roti"
    profile.workout_level = "intermediate"
    profile.workout_days_per_week = 4
    profile.preferred_workout_type = "mixed"
    db.add(profile)
    # Backdate the account so the history counts as "since joining"
    user.created_at = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    db.commit()
    db.refresh(user)

    targets = profile_targets(profile)
    plan = active_plan(db, user, regenerate=True)
    split = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.30, "snacks": 0.10}
    meals = [m for m in db.scalars(select(Meal))
             if m.diet_type in DIET_ORDER[profile.dietary_preference] and "peanuts" not in m.allergens]
    by_type = {t: [m for m in meals if m.meal_type == t] for t in split}
    extras = [db.scalar(select(FoodItem).where(FoodItem.name == n))
              for n in ("Masala chai (with sugar)", "Banana", "Apple", "Almonds", "Buttermilk (chaas)")]

    for i in range(HISTORY_DAYS + 1):
        d = start + timedelta(days=i)
        is_today = d == today
        # Habits improve over time: more consistent logging in recent weeks
        log_prob = 0.75 + 0.2 * (i / HISTORY_DAYS)

        # ---- food
        if is_today or rng.random() < log_prob:
            day_factor = rng.uniform(0.86, 1.12)
            slots = ["breakfast", "lunch"] if is_today else list(split)
            for slot in slots:
                meal = rng.choice(by_type[slot])
                kcal_goal = targets["daily_calories"] * split[slot] * day_factor
                portion = min(max(round(kcal_goal / meal.calories * 4) / 4, 0.5), 2.0)
                db.add(FoodLog(user_id=user.id, meal_id=meal.id, name=meal.name,
                               serving_desc="recipe portion", meal_type=slot, quantity=portion,
                               log_date=d, calories=round(meal.calories * portion, 1),
                               protein=round(meal.protein * portion, 1),
                               carbs=round(meal.carbs * portion, 1), fat=round(meal.fat * portion, 1)))
            if not is_today and rng.random() < 0.5:
                food = rng.choice(extras)
                db.add(FoodLog(user_id=user.id, food_item_id=food.id, name=food.name,
                               serving_desc=food.serving_desc, meal_type="snacks", quantity=1,
                               log_date=d, calories=food.calories, protein=food.protein,
                               carbs=food.carbs, fat=food.fat))

        # ---- water (250 ml glasses)
        glasses = 5 if is_today else rng.randint(7, 13)
        for _ in range(glasses):
            db.add(WaterLog(user_id=user.id, log_date=d, amount_ml=250))

        # ---- weight every 2-3 days, gentle downward trend with daily noise
        if is_today or i % rng.choice([2, 3]) == 0:
            trend = start_weight + (end_weight - start_weight) * (i / HISTORY_DAYS)
            weight = end_weight if is_today else round(trend + rng.uniform(-0.35, 0.35), 1)
            measures = {}
            if i % 14 == 0 or is_today:
                progress = i / HISTORY_DAYS
                measures = {"waist_cm": round(94 - 5 * progress, 1), "chest_cm": round(101 - 1.5 * progress, 1),
                            "hips_cm": round(100 - 3 * progress, 1), "arms_cm": round(33 + 0.6 * progress, 1)}
            db.add(WeightLog(user_id=user.id, log_date=d, weight_kg=weight, **measures))

        # ---- workouts on scheduled days, ~80% attendance
        session = session_for_date(plan, d)
        if session and not is_today and rng.random() < 0.65 + 0.25 * (i / HISTORY_DAYS):
            for ex in session["exercises"]:
                if rng.random() < 0.9:
                    db.add(WorkoutLog(user_id=user.id, plan_id=plan.id, exercise_id=ex["exercise_id"],
                                      log_date=d, day_number=session["day_number"],
                                      sets_completed=ex["sets"], completed=True))
    db.commit()
    print(f"Demo user ready: {DEMO_EMAIL} / {DEMO_PASSWORD} ({HISTORY_DAYS} days of history)")


def main():
    if "--reset" in sys.argv:
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables")
    init_db()
    with SessionLocal() as db:
        load_catalogue(db)
        if "--no-demo" not in sys.argv:
            create_demo_user(db)


if __name__ == "__main__":
    main()
