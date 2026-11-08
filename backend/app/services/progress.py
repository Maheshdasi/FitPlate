from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ml.progress_predictor import predict_weight

from ..models import User, WaterLog, WeightLog, WorkoutLog
from .nutrition import daily_series, profile_targets
from .recommendations import active_plan


def water_by_day(db: Session, user_id: int, start: date, end: date) -> dict[date, int]:
    rows = db.execute(
        select(WaterLog.log_date, func.sum(WaterLog.amount_ml))
        .where(WaterLog.user_id == user_id, WaterLog.log_date.between(start, end))
        .group_by(WaterLog.log_date)
    ).all()
    return {d: int(v) for d, v in rows}


def workouts_by_day(db: Session, user_id: int, start: date, end: date) -> dict[date, int]:
    rows = db.execute(
        select(WorkoutLog.log_date, func.count())
        .where(WorkoutLog.user_id == user_id, WorkoutLog.completed.is_(True),
               WorkoutLog.log_date.between(start, end))
        .group_by(WorkoutLog.log_date)
    ).all()
    return {d: int(c) for d, c in rows}


def weight_logs(db: Session, user_id: int, start: date | None = None) -> list[WeightLog]:
    q = select(WeightLog).where(WeightLog.user_id == user_id)
    if start:
        q = q.where(WeightLog.log_date >= start)
    return list(db.scalars(q.order_by(WeightLog.log_date)))


def weight_prediction(db: Session, user: User) -> dict:
    logs = weight_logs(db, user.id)
    return predict_weight([(w.log_date, w.weight_kg) for w in logs], user.profile.target_weight_kg)


def summary(db: Session, user: User, end: date, days: int) -> dict:
    start = end - timedelta(days=days - 1)
    targets = profile_targets(user.profile)
    food = daily_series(db, user.id, start, end)
    water = water_by_day(db, user.id, start, end)
    workouts = workouts_by_day(db, user.id, start, end)
    plan = active_plan(db, user)
    # Days before the account existed are not "missed" workouts
    joined = user.created_at.date() if user.created_at else start

    daily = []
    for i in range(days):
        d = start + timedelta(days=i)
        f = food.get(d, {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
        daily.append({
            "date": d.isoformat(),
            "calories": f["calories"], "protein": f["protein"], "carbs": f["carbs"], "fat": f["fat"],
            "calorie_goal": targets["daily_calories"], "protein_goal": targets["protein_g"],
            "water_ml": water.get(d, 0),
            "exercises_completed": workouts.get(d, 0),
            "workout_done": workouts.get(d, 0) > 0,
            "workout_planned": d.weekday() in plan.schedule and d >= joined,
        })

    weights = weight_logs(db, user.id, start)
    logged = [x for x in daily if x["calories"] > 0]
    planned = sum(1 for x in daily if x["workout_planned"])
    done = sum(1 for x in daily if x["workout_done"])

    first_weight = weights[0].weight_kg if weights else None
    last_weight = weights[-1].weight_kg if weights else None
    return {
        "range_days": days,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "targets": targets,
        "daily": daily,
        "weights": [{"date": w.log_date.isoformat(), "weight": w.weight_kg, "waist": w.waist_cm,
                     "chest": w.chest_cm, "hips": w.hips_cm, "arms": w.arms_cm} for w in weights],
        "totals": {
            "days_logged": len(logged),
            "avg_calories": round(sum(x["calories"] for x in logged) / len(logged)) if logged else 0,
            "avg_protein": round(sum(x["protein"] for x in logged) / len(logged), 1) if logged else 0,
            "workouts_done": done,
            "workouts_planned": planned,
            "consistency_pct": round(done / planned * 100) if planned else 0,
            "weight_change": round(last_weight - first_weight, 1) if weights else None,
        },
        "prediction": weight_prediction(db, user),
    }
