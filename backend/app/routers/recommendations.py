from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FoodLog, MealRecommendation, User, UserProfile, WorkoutExercise, WorkoutLog
from ..schemas import LogMealIn, ReplaceMealIn, WorkoutLogIn
from ..security import get_current_profile, get_current_user
from ..services import recommendations as recs
from .common import resolve_date

router = APIRouter(tags=["Recommendations & Workouts"])


# ---------------------------------------------------------------- meals
@router.get("/recommendations/meals")
def meal_recommendations(date_: date | None = Query(default=None, alias="date"),
                         user: User = Depends(get_current_user),
                         _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    return recs.daily_meal_plan(db, user, resolve_date(date_))


@router.post("/recommendations/meals/replace")
def replace_meal(data: ReplaceMealIn, user: User = Depends(get_current_user),
                 _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    meal = recs.replace_meal(db, user, resolve_date(data.rec_date), data.meal_type)
    if meal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "No other meals match your diet and allergy settings for this slot.")
    return meal


@router.post("/recommendations/meals/log", status_code=status.HTTP_201_CREATED)
def log_recommended_meal(data: LogMealIn, user: User = Depends(get_current_user),
                         _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    d = resolve_date(data.rec_date)
    rec = db.scalar(select(MealRecommendation).where(
        MealRecommendation.user_id == user.id, MealRecommendation.rec_date == d,
        MealRecommendation.meal_type == data.meal_type))
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Load recommendations for this day first.")
    db.add(FoodLog(user_id=user.id, meal_id=rec.meal_id, name=rec.meal.name,
                   serving_desc="recipe portion", meal_type=data.meal_type,
                   quantity=rec.portion, log_date=d, calories=rec.calories, protein=rec.protein,
                   carbs=rec.carbs, fat=rec.fat))
    rec.status = "logged"
    db.commit()
    return {"detail": f"{rec.meal.name} added to your {data.meal_type}."}


# ---------------------------------------------------------------- workouts
def _completed_ids(db, user_id, d) -> set[int]:
    return set(db.scalars(select(WorkoutLog.exercise_id).where(
        WorkoutLog.user_id == user_id, WorkoutLog.log_date == d, WorkoutLog.completed.is_(True))))


@router.get("/recommendations/workouts")
def workout_recommendations(date_: date | None = Query(default=None, alias="date"),
                            regenerate: bool = False,
                            user: User = Depends(get_current_user),
                            _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    d = resolve_date(date_)
    plan = recs.active_plan(db, user, regenerate=regenerate)
    today = recs.session_for_date(plan, d)
    done = _completed_ids(db, user.id, d)
    return {
        "plan_id": plan.id,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "days_per_week": plan.days_per_week,
        "level": plan.level,
        "goal": plan.goal,
        "schedule": [recs.WEEKDAYS[i] for i in plan.schedule],
        "sessions": plan.plan["sessions"],
        "method": plan.plan.get("method"),
        "today": {"date": d.isoformat(), "weekday": recs.WEEKDAYS[d.weekday()],
                  "session": today, "is_rest_day": today is None,
                  "completed_exercise_ids": sorted(done)},
    }


@router.post("/workout-log", status_code=status.HTTP_201_CREATED)
def log_workout(data: WorkoutLogIn, user: User = Depends(get_current_user),
                _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    if db.get(WorkoutExercise, data.exercise_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercise not found.")
    d = resolve_date(data.log_date)
    plan = recs.active_plan(db, user)
    log = db.scalar(select(WorkoutLog).where(WorkoutLog.user_id == user.id, WorkoutLog.log_date == d,
                                             WorkoutLog.exercise_id == data.exercise_id))
    if log is None:
        log = WorkoutLog(user_id=user.id, exercise_id=data.exercise_id, log_date=d, plan_id=plan.id)
        db.add(log)
    log.completed = data.completed
    log.sets_completed = data.sets_completed
    log.day_number = data.day_number
    db.commit()
    return {"exercise_id": data.exercise_id, "completed": log.completed, "log_date": d.isoformat(),
            "completed_exercise_ids": sorted(_completed_ids(db, user.id, d))}


@router.get("/workout-log/history")
def workout_history(days: int = Query(default=30, ge=7, le=180),
                    date_: date | None = Query(default=None, alias="date"),
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    end = resolve_date(date_)
    start = end - timedelta(days=days - 1)
    logs = db.scalars(select(WorkoutLog).where(
        WorkoutLog.user_id == user.id, WorkoutLog.completed.is_(True),
        WorkoutLog.log_date.between(start, end)).order_by(WorkoutLog.log_date.desc())).all()
    grouped: dict[str, list] = {}
    for log in logs:
        grouped.setdefault(log.log_date.isoformat(), []).append(
            {"exercise_id": log.exercise_id, "name": log.exercise.name,
             "category": log.exercise.category, "sets_completed": log.sets_completed})
    return [{"date": d, "exercises": ex} for d, ex in grouped.items()]
