from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ml.chat_assistant import ChatAssistant

from ..database import get_db
from ..models import FoodItem, User, UserProfile
from ..schemas import ChatIn
from ..security import get_current_profile, get_current_user
from ..services import progress as prog
from ..services import recommendations as recs
from ..services.nutrition import DIET_ORDER, day_totals, profile_targets, remaining
from .common import resolve_date

router = APIRouter(prefix="/ai", tags=["AI assistant"])
_assistant: ChatAssistant | None = None


def assistant() -> ChatAssistant:
    global _assistant
    if _assistant is None:
        _assistant = ChatAssistant()
    return _assistant


@router.post("/chat")
def chat(data: ChatIn, user: User = Depends(get_current_user),
         profile: UserProfile = Depends(get_current_profile), db: Session = Depends(get_db)):
    d = resolve_date(data.local_date)
    targets = profile_targets(profile)
    consumed, _ = day_totals(db, user.id, d)
    left = remaining(targets, consumed)

    allowed_diets = DIET_ORDER[profile.dietary_preference]
    allergies = set(profile.allergies or [])

    def foods_within(budget: int) -> list[dict]:
        foods = db.scalars(select(FoodItem).where(FoodItem.calories <= budget,
                                                  FoodItem.diet_type.in_(allowed_diets))).all()
        foods = [f for f in foods if not (set(f.allergens or []) & allergies) and f.calories >= 60]
        foods.sort(key=lambda f: f.protein / max(f.calories, 1), reverse=True)
        return [{"name": f.name, "serving": f.serving_desc, "calories": round(f.calories),
                 "protein": f.protein} for f in foods]

    plan = recs.active_plan(db, user)
    weights = prog.weight_logs(db, user.id)
    ctx = {
        "profile": recs.profile_dict(profile),
        "targets": targets,
        "consumed": consumed,
        "remaining": left,
        "hour": data.local_hour if data.local_hour is not None else datetime.now().hour,
        "recommend_meals": lambda slot, overrides: recs.rank_meals(db, user, d, slot, overrides),
        "foods_within": foods_within,
        "today_workout": recs.session_for_date(plan, d),
        "water_today": prog.water_by_day(db, user.id, d, d).get(d, 0),
        "weight": {"latest": weights[-1].weight_kg if weights else profile.weight_kg,
                   "start": weights[0].weight_kg if weights else None,
                   "target": profile.target_weight_kg},
        "prediction": prog.weight_prediction(db, user),
    }
    return assistant().reply(data.message, ctx)
