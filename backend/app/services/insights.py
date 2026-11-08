from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ml.weekly_insights import analyse_week

from ..models import User, WeeklyInsight
from .nutrition import daily_series, profile_targets
from .progress import water_by_day, weight_logs, workouts_by_day


def week_start_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _avg_weight(logs, start: date, end: date):
    values = [w.weight_kg for w in logs if start <= w.log_date <= end]
    return round(sum(values) / len(values), 2) if values else None


def build_week(db: Session, user: User, week_start: date, today: date) -> WeeklyInsight:
    week_end = week_start + timedelta(days=6)
    last_day = min(week_end, today)
    targets = profile_targets(user.profile)
    food = daily_series(db, user.id, week_start, week_end)
    water = water_by_day(db, user.id, week_start, week_end)
    workouts = workouts_by_day(db, user.id, week_start, week_end)

    days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        f = food.get(d, {"calories": 0, "protein": 0})
        days.append({"date": d.isoformat(), "calories": f["calories"], "protein": f["protein"],
                     "water_ml": water.get(d, 0), "workout_done": workouts.get(d, 0) > 0})

    logs = weight_logs(db, user.id, week_start - timedelta(days=7))
    this_week = _avg_weight(logs, week_start, last_day)
    prev_week = _avg_weight(logs, week_start - timedelta(days=7), week_start - timedelta(days=1))

    result = analyse_week(days, targets, user.profile.workout_days_per_week, this_week, prev_week)

    row = db.scalar(select(WeeklyInsight).where(WeeklyInsight.user_id == user.id,
                                                WeeklyInsight.week_start == week_start))
    if row is None:
        row = WeeklyInsight(user_id=user.id, week_start=week_start, week_end=week_end)
        db.add(row)
    row.metrics = result["metrics"]
    row.insights = result["insights"]
    row.suggestions = result["suggestions"]
    row.behaviour = result["behaviour"]
    row.daily = result["daily"]
    db.commit()
    db.refresh(row)
    return row


def insight_out(row: WeeklyInsight, today: date) -> dict:
    return {
        "week_start": row.week_start.isoformat(),
        "week_end": row.week_end.isoformat(),
        "is_complete": row.week_end < today,
        "metrics": row.metrics,
        "insights": row.insights,
        "suggestions": row.suggestions,
        "behaviour": row.behaviour,
        "daily": row.daily,
        "generated_at": row.created_at.isoformat() if row.created_at else None,
        "method": "Pandas weekly aggregation + rule-based suggestions + K-Means behaviour cluster",
    }
