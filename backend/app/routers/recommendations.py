from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ml import progression as prog

from ..database import get_db
from ..models import FoodLog, MealRecommendation, User, UserProfile, WorkoutExercise, WorkoutLog
from ..schemas import LogMealIn, ReplaceMealIn, SplitIn, WorkoutLogIn
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


def _plan_response(db, user, plan, d: date) -> dict:
    today = recs.session_for_date(plan, d)
    done = _completed_ids(db, user.id, d)
    meta = plan.plan.get("profile", {})
    return {
        "plan_id": plan.id,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "days_per_week": plan.days_per_week,
        "level": plan.level,
        "goal": plan.goal,
        "split": meta.get("workout_split", "auto"),
        "custom_split": meta.get("custom_split"),
        "schedule": [recs.WEEKDAYS[i] for i in plan.schedule],
        "sessions": plan.plan["sessions"],
        "method": plan.plan.get("method"),
        "today": {"date": d.isoformat(), "weekday": recs.WEEKDAYS[d.weekday()],
                  "session": today, "is_rest_day": today is None,
                  "completed_exercise_ids": sorted(done)},
    }


@router.get("/recommendations/workouts")
def workout_recommendations(date_: date | None = Query(default=None, alias="date"),
                            regenerate: bool = False,
                            user: User = Depends(get_current_user),
                            _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    plan = recs.active_plan(db, user, regenerate=regenerate)
    return _plan_response(db, user, plan, resolve_date(date_))


@router.put("/recommendations/workouts/split")
def set_workout_split(data: SplitIn, date_: date | None = Query(default=None, alias="date"),
                      user: User = Depends(get_current_user),
                      profile: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    """Choose a training split (or define your own days) and rebuild the plan around it."""
    profile.workout_split = data.workout_split
    profile.custom_split = [d.model_dump() for d in data.custom_split] if data.custom_split else None
    if data.custom_split:
        profile.workout_days_per_week = len(data.custom_split)
    elif data.workout_days_per_week:
        profile.workout_days_per_week = data.workout_days_per_week
    db.commit()
    db.refresh(user)
    plan = recs.active_plan(db, user)
    return _plan_response(db, user, plan, resolve_date(date_))


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
    if data.sets is not None:
        log.sets = [st.model_dump() for st in data.sets]
        log.sets_completed = min(20, sum(1 for st in data.sets if st.done))
    else:
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
             "category": log.exercise.category, "sets_completed": log.sets_completed,
             "volume_kg": prog.volume(log.sets)})
    return [{"date": d, "exercises": ex, "sets": sum(e["sets_completed"] for e in ex),
             "volume_kg": round(sum(e["volume_kg"] for e in ex), 1)} for d, ex in grouped.items()]


@router.get("/workout-log/day")
def workout_day(date_: date | None = Query(default=None, alias="date"),
                user: User = Depends(get_current_user),
                _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    """Everything the set-by-set tracker needs for one day: the sets logged so far, what was lifted last
    time, the best so far, a progressive-overload target for each exercise and today's personal records."""
    d = resolve_date(date_)
    plan = recs.active_plan(db, user)
    plan_ex = {}
    for session in plan.plan["sessions"]:
        for e in session["exercises"]:
            plan_ex.setdefault(e["exercise_id"], e)

    today_logs = {log.exercise_id: log for log in db.scalars(select(WorkoutLog).where(
        WorkoutLog.user_id == user.id, WorkoutLog.log_date == d))}
    ids = set(plan_ex) | set(today_logs)
    past = db.scalars(select(WorkoutLog).where(
        WorkoutLog.user_id == user.id, WorkoutLog.log_date < d, WorkoutLog.exercise_id.in_(ids),
        WorkoutLog.sets.is_not(None)).order_by(WorkoutLog.log_date.desc())).all()

    exercises, logs, volume, sets_done, pr_count = {}, {}, 0.0, 0, 0
    for ex_id in ids:
        meta = plan_ex.get(ex_id)
        if meta is None:
            log = today_logs[ex_id]
            meta = {"category": log.exercise.category, "equipment": log.exercise.equipment, "reps": "8-12", "sets": 3}
        kind = prog.exercise_kind(meta)
        history = [p for p in past if p.exercise_id == ex_id and prog.done_sets(p.sets)]
        previous = history[0] if history else None
        best, best_at = 0.0, None
        for p in history:
            for st in prog.done_sets(p.sets):
                score = prog.set_score(kind, st)
                if score > best:
                    best, best_at = score, {"date": p.log_date.isoformat(), **st}
        today = today_logs.get(ex_id)
        records = prog.mark_records(kind, today.sets, best) if today and today.sets else []
        exercises[ex_id] = {
            "kind": kind,
            "previous": ({"date": previous.log_date.isoformat(), "sets": prog.done_sets(previous.sets)}
                         if previous else None),
            "best": {"score": best, "set": best_at} if best_at else None,
            "suggestion": prog.suggest(meta, previous.sets if previous else None),
            "records": records,
        }
        if today:
            logs[ex_id] = {"sets": today.sets or [], "completed": today.completed}
            volume += prog.volume(today.sets)
            sets_done += len(prog.done_sets(today.sets)) if today.sets else today.sets_completed
            pr_count += len(records)
    return {"date": d.isoformat(), "logs": logs, "exercises": exercises,
            "summary": {"volume_kg": round(volume, 1), "sets_done": sets_done, "records": pr_count}}
