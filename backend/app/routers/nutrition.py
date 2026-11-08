from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ml.calculations import calculate_targets

from ..database import get_db
from ..models import FoodItem, FoodLog, Meal, User, UserProfile
from ..schemas import CalculatorIn, FoodLogIn, FoodLogOut, FoodOut
from ..security import get_current_profile, get_current_user
from ..services.nutrition import DISCLAIMER, MEAL_TYPES, day_totals, profile_targets, remaining
from .common import resolve_date

router = APIRouter(tags=["Nutrition"])


# ---------------------------------------------------------------- foods
@router.get("/foods", response_model=list[FoodOut])
def list_foods(
    search: str | None = Query(default=None, max_length=60),
    category: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(FoodItem)
    if search:
        q = q.where(FoodItem.name.ilike(f"%{search.strip()}%"))  # bound parameter, safe from injection
    if category:
        q = q.where(FoodItem.category == category)
    return db.scalars(q.order_by(FoodItem.category, FoodItem.name).limit(limit)).all()


@router.get("/foods/categories", response_model=list[str])
def food_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(FoodItem.category).distinct().order_by(FoodItem.category)).all()


# ---------------------------------------------------------------- food log
@router.post("/food-log", response_model=FoodLogOut, status_code=status.HTTP_201_CREATED)
def add_food_log(data: FoodLogIn, user: User = Depends(get_current_user),
                 _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    source = db.get(FoodItem, data.food_item_id) if data.food_item_id else db.get(Meal, data.meal_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Food not found.")
    q = data.quantity
    log = FoodLog(
        user_id=user.id, food_item_id=data.food_item_id, meal_id=data.meal_id, name=source.name,
        serving_desc=getattr(source, "serving_desc", "1 serving"), meal_type=data.meal_type,
        quantity=q, log_date=resolve_date(data.log_date),
        calories=round(source.calories * q, 1), protein=round(source.protein * q, 1),
        carbs=round(source.carbs * q, 1), fat=round(source.fat * q, 1),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/food-log/today")
def food_log_today(date_: date | None = Query(default=None, alias="date"),
                   user: User = Depends(get_current_user),
                   profile: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    d = resolve_date(date_)
    entries = db.scalars(select(FoodLog).where(FoodLog.user_id == user.id, FoodLog.log_date == d)
                         .order_by(FoodLog.created_at)).all()
    targets = profile_targets(profile)
    total, by_slot = day_totals(db, user.id, d)
    return {
        "date": d.isoformat(),
        "entries": {m: [FoodLogOut.model_validate(e).model_dump() for e in entries if e.meal_type == m]
                    for m in MEAL_TYPES},
        "by_meal": by_slot,
        "consumed": total,
        "goal": {"calories": targets["daily_calories"], "protein": targets["protein_g"],
                 "carbs": targets["carbs_g"], "fat": targets["fat_g"]},
        "remaining": remaining(targets, total),
    }


@router.delete("/food-log/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food_log(log_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log = db.get(FoodLog, log_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Food log entry not found.")
    db.delete(log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- calculations
@router.get("/nutrition/calories")
def my_calories(profile: UserProfile = Depends(get_current_profile)):
    targets = profile_targets(profile)
    return {
        **targets,
        "message": f"Your estimated daily calorie requirement is {targets['daily_calories']} kcal.",
        "method": "Mifflin-St Jeor BMR × activity factor, adjusted for your goal",
        "disclaimer": DISCLAIMER,
        "inputs": {"age": profile.age, "gender": profile.gender, "height_cm": profile.height_cm,
                   "weight_kg": profile.weight_kg, "activity_level": profile.activity_level,
                   "fitness_goal": profile.fitness_goal},
    }


@router.post("/nutrition/calculate")
def calculate(data: CalculatorIn, _: User = Depends(get_current_user)):
    """Try 'what if' values without changing the saved profile."""
    t = calculate_targets(**{k: v for k, v in data.model_dump().items() if k != "target_weight_kg"},
                          target_weight_kg=data.target_weight_kg).to_dict()
    return {**t, "message": f"Your estimated daily calorie requirement is {t['daily_calories']} kcal.",
            "disclaimer": DISCLAIMER}
