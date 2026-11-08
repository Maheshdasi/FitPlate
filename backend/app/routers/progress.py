from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserProfile, WaterLog, WeightLog, WorkoutLog
from ..schemas import WaterIn, WeightIn, WeightOut
from ..security import get_current_profile, get_current_user
from ..services import progress as prog
from ..services import recommendations as recs
from ..services.nutrition import day_totals, profile_targets, remaining
from .common import resolve_date

router = APIRouter(tags=["Progress"])

ALLOWED_RANGES = {7, 30, 90, 180}


@router.post("/progress/weight", response_model=WeightOut, status_code=status.HTTP_201_CREATED)
def log_weight(data: WeightIn, user: User = Depends(get_current_user),
               profile: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    d = resolve_date(data.log_date)
    log = db.scalar(select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.log_date == d))
    if log is None:
        log = WeightLog(user_id=user.id, log_date=d)
        db.add(log)
    for field in ("weight_kg", "waist_cm", "chest_cm", "hips_cm", "arms_cm"):
        value = getattr(data, field)
        if value is not None or field == "weight_kg":
            setattr(log, field, value)

    # The newest entry becomes the profile's current weight (keeps calorie targets up to date)
    latest = db.scalar(select(WeightLog.log_date).where(WeightLog.user_id == user.id)
                       .order_by(WeightLog.log_date.desc()).limit(1))
    if latest is None or d >= latest:
        profile.weight_kg = data.weight_kg
    db.commit()
    db.refresh(log)
    return log


@router.get("/progress/weight", response_model=list[WeightOut])
def get_weights(days: int = Query(default=180, ge=7, le=730), user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return prog.weight_logs(db, user.id, date.today() - timedelta(days=days))


@router.delete("/progress/weight/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight(log_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log = db.get(WeightLog, log_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Weight entry not found.")
    db.delete(log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/progress/water", status_code=status.HTTP_201_CREATED)
def log_water(data: WaterIn, user: User = Depends(get_current_user),
              profile: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    d = resolve_date(data.log_date)
    db.add(WaterLog(user_id=user.id, log_date=d, amount_ml=data.amount_ml))
    db.commit()
    total = prog.water_by_day(db, user.id, d, d).get(d, 0)
    return {"date": d.isoformat(), "total_ml": total, "goal_ml": profile_targets(profile)["water_ml"]}


@router.delete("/progress/water/last", status_code=status.HTTP_200_OK)
def undo_water(date_: date | None = Query(default=None, alias="date"),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = resolve_date(date_)
    last = db.scalar(select(WaterLog).where(WaterLog.user_id == user.id, WaterLog.log_date == d)
                     .order_by(WaterLog.created_at.desc(), WaterLog.id.desc()).limit(1))
    if last is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No water logged for this day.")
    db.delete(last)
    db.commit()
    return {"date": d.isoformat(), "total_ml": prog.water_by_day(db, user.id, d, d).get(d, 0)}


@router.get("/progress/summary")
def progress_summary(days: int = Query(default=30), date_: date | None = Query(default=None, alias="date"),
                     user: User = Depends(get_current_user),
                     _: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    if days not in ALLOWED_RANGES:
        raise HTTPException(422, "days must be one of 7, 30, 90 or 180.")
    return prog.summary(db, user, resolve_date(date_), days)


@router.get("/dashboard")
def dashboard(date_: date | None = Query(default=None, alias="date"),
              user: User = Depends(get_current_user),
              profile: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    """Everything the dashboard needs in one request."""
    d = resolve_date(date_)
    targets = profile_targets(profile)
    consumed, by_slot = day_totals(db, user.id, d)
    plan = recs.active_plan(db, user)
    session = recs.session_for_date(plan, d)
    done_ids = set(db.scalars(select(WorkoutLog.exercise_id).where(
        WorkoutLog.user_id == user.id, WorkoutLog.log_date == d, WorkoutLog.completed.is_(True))))
    total_ex = len(session["exercises"]) if session else 0
    done_in_session = len([e for e in (session or {}).get("exercises", []) if e["exercise_id"] in done_ids])
    week = prog.summary(db, user, d, 7)
    weights = prog.weight_logs(db, user.id, d - timedelta(days=90))

    # Next meal suggestion for the current slot
    meal_plan = recs.daily_meal_plan(db, user, d)
    next_slot = next((m for m in ["breakfast", "lunch", "dinner", "snacks"]
                      if by_slot[m]["calories"] == 0), "snacks")

    return {
        "date": d.isoformat(),
        "name": profile.name,
        "targets": targets,
        "consumed": consumed,
        "by_meal": by_slot,
        "remaining": remaining(targets, consumed),
        "water": {"total_ml": prog.water_by_day(db, user.id, d, d).get(d, 0), "goal_ml": targets["water_ml"]},
        "weight": {"current": profile.weight_kg, "target": profile.target_weight_kg,
                   "start": weights[0].weight_kg if weights else profile.weight_kg,
                   "history": [{"date": w.log_date.isoformat(), "weight": w.weight_kg} for w in weights]},
        "workout": {
            "is_rest_day": session is None,
            "session": session,
            "completed": done_in_session,
            "total": total_ex,
            "status": "rest" if session is None else ("done" if total_ex and done_in_session == total_ex
                                                      else "in_progress" if done_in_session else "pending"),
        },
        "week": week["daily"],
        "week_totals": week["totals"],
        "next_meal": {"meal_type": next_slot, **(meal_plan["slots"][next_slot] or {})},
    }
