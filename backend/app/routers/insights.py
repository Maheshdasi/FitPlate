from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserProfile, WeeklyInsight
from ..security import get_current_profile, get_current_user
from ..services.insights import build_week, insight_out, week_start_of
from .common import resolve_date

router = APIRouter(prefix="/insights", tags=["Weekly insights"])


@router.get("/weekly")
def weekly_insights(
    week_start: date | None = Query(default=None, description="Monday of the week. Default: last completed week."),
    current: bool = Query(default=False, description="Analyse the current week so far"),
    date_: date | None = Query(default=None, alias="date"),
    user: User = Depends(get_current_user),
    _: UserProfile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    today = resolve_date(date_)
    this_monday = week_start_of(today)
    if week_start is not None:
        start = week_start_of(week_start)
    elif current:
        start = this_monday
    else:
        start = this_monday - timedelta(days=7)

    # Completed weeks are cached; the running week is always recalculated
    row = db.scalar(select(WeeklyInsight).where(WeeklyInsight.user_id == user.id,
                                                WeeklyInsight.week_start == start))
    if row is None or row.week_end >= today or start >= this_monday:
        row = build_week(db, user, start, today)
    return insight_out(row, today)


@router.get("/history")
def insight_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(WeeklyInsight).where(WeeklyInsight.user_id == user.id)
                      .order_by(WeeklyInsight.week_start.desc()).limit(12)).all()
    return [{"week_start": r.week_start.isoformat(), "week_end": r.week_end.isoformat(),
             "behaviour": r.behaviour.get("label"),
             "days_on_calorie_target": r.metrics.get("days_on_calorie_target"),
             "workouts_completed": r.metrics.get("workouts_completed")} for r in rows]
