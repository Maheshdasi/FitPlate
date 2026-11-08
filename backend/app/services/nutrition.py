from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ml.calculations import calculate_targets

from ..models import FoodLog, UserProfile

DISCLAIMER = ("Calorie and nutrition values are estimates based on standard formulas and average "
              "food data. They are not medical advice. Consult a doctor or registered dietitian "
              "for personal medical or dietary needs.")

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snacks"]

# Food diet types each diet preference can eat
DIET_ORDER = {
    "vegan": ["vegan"],
    "vegetarian": ["vegan", "vegetarian"],
    "eggetarian": ["vegan", "vegetarian", "eggetarian"],
    "non_vegetarian": ["vegan", "vegetarian", "eggetarian", "non_vegetarian"],
}
EMPTY = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}


def profile_targets(profile: UserProfile) -> dict:
    return calculate_targets(
        weight_kg=profile.weight_kg, height_cm=profile.height_cm, age=profile.age,
        gender=profile.gender, activity_level=profile.activity_level,
        fitness_goal=profile.fitness_goal, target_weight_kg=profile.target_weight_kg,
    ).to_dict()


def _round(t: dict) -> dict:
    return {"calories": round(t["calories"]), "protein": round(t["protein"], 1),
            "carbs": round(t["carbs"], 1), "fat": round(t["fat"], 1)}


def day_totals(db: Session, user_id: int, d: date) -> tuple[dict, dict]:
    """Return (total, by_meal_type) for one day."""
    rows = db.execute(
        select(FoodLog.meal_type, func.sum(FoodLog.calories), func.sum(FoodLog.protein),
               func.sum(FoodLog.carbs), func.sum(FoodLog.fat))
        .where(FoodLog.user_id == user_id, FoodLog.log_date == d)
        .group_by(FoodLog.meal_type)
    ).all()
    by_slot = {m: dict(EMPTY) for m in MEAL_TYPES}
    for meal_type, kcal, p, c, f in rows:
        by_slot[meal_type] = _round({"calories": kcal, "protein": p, "carbs": c, "fat": f})
    total = _round({k: sum(v[k] for v in by_slot.values()) for k in EMPTY})
    return total, by_slot


def remaining(targets: dict, consumed: dict) -> dict:
    return {
        "calories": round(targets["daily_calories"] - consumed["calories"]),
        "protein": round(targets["protein_g"] - consumed["protein"], 1),
        "carbs": round(targets["carbs_g"] - consumed["carbs"], 1),
        "fat": round(targets["fat_g"] - consumed["fat"], 1),
    }


def daily_series(db: Session, user_id: int, start: date, end: date) -> dict[date, dict]:
    rows = db.execute(
        select(FoodLog.log_date, func.sum(FoodLog.calories), func.sum(FoodLog.protein),
               func.sum(FoodLog.carbs), func.sum(FoodLog.fat))
        .where(FoodLog.user_id == user_id, FoodLog.log_date.between(start, end))
        .group_by(FoodLog.log_date)
    ).all()
    return {d: _round({"calories": k, "protein": p, "carbs": c, "fat": f}) for d, k, p, c, f in rows}


def favourite_foods(db: Session, user_id: int, limit: int = 10) -> list[str]:
    rows = db.execute(
        select(FoodLog.name, func.count()).where(FoodLog.user_id == user_id)
        .group_by(FoodLog.name).order_by(func.count().desc()).limit(limit)
    ).all()
    return [r[0] for r in rows]
