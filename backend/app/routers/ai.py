import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ml.chat_assistant import QUICK_REPLIES, SAFETY_REPLY, ChatAssistant

from ..database import get_db
from ..models import FoodItem, FoodLog, User, UserProfile
from ..schemas import ChatIn
from ..security import get_current_profile, get_current_user
from ..services import llm
from ..services import progress as prog
from ..services import recommendations as recs
from ..services.nutrition import DIET_ORDER, day_totals, profile_targets, remaining
from .common import resolve_date

router = APIRouter(prefix="/ai", tags=["AI assistant"])
logger = logging.getLogger("fitness.ai")

# With an LLM, general health questions get careful general answers; asking for medicines, doses or a
# diagnosis is still always declined before anything is sent to the model.
HARD_MEDICAL = re.compile(
    r"\b(medicine|medication|tablet|pill|insulin|steroid|dose|dosage|diagnos\w*|prescri\w*|antibiotic\w*|"
    r"painkiller\w*|supplement dose|cure)\b", re.IGNORECASE)
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
    hour = data.local_hour if data.local_hour is not None else datetime.now().hour
    prediction = prog.weight_prediction(db, user)

    llm_error = None
    if llm.configured():
        if HARD_MEDICAL.search(data.message):
            return {"reply": SAFETY_REPLY, "intent": "medical_safety", "confidence": 1.0, "source": "safety",
                    "quick_replies": QUICK_REPLIES, "context": {}}
        facts = _llm_facts(db, user, profile, d, hour, targets, consumed, left, plan, weights, prediction)
        history = [{"role": t.role, "content": t.text} for t in (data.history or [])[-12:]]
        try:
            answer = llm.ask(llm.build_system_prompt(facts), [*history, {"role": "user", "content": data.message}])
            return {"reply": answer.text, "intent": "llm", "confidence": 1.0, "source": answer.provider,
                    "source_name": llm.provider_name(answer.provider), "model": answer.model,
                    "sources": answer.sources, "quick_replies": QUICK_REPLIES, "context": {}}
        except llm.LLMError as e:
            logger.warning("LLM unavailable, using the offline assistant: %s", e)
            llm_error = llm.short_reason(e)

    ctx = {
        "profile": recs.profile_dict(profile),
        "targets": targets,
        "consumed": consumed,
        "remaining": left,
        "hour": hour,
        "recommend_meals": lambda slot, overrides: recs.rank_meals(db, user, d, slot, overrides),
        "foods_within": foods_within,
        "today_workout": recs.session_for_date(plan, d),
        "water_today": prog.water_by_day(db, user.id, d, d).get(d, 0),
        "weight": {"latest": weights[-1].weight_kg if weights else profile.weight_kg,
                   "start": weights[0].weight_kg if weights else None,
                   "target": profile.target_weight_kg},
        "prediction": prediction,
        "context": data.context.model_dump() if data.context else {},
    }
    out = {**assistant().reply(data.message, ctx), "source": "offline"}
    if llm_error:
        out["llm_error"] = llm_error
    return out


@router.get("/status")
def ai_status(_: User = Depends(get_current_user)):
    """Which engine answers chat messages: a hosted LLM or the offline assistant."""
    cfg = llm.configured()
    if cfg is None:
        return {"mode": "offline", "name": "Offline assistant"}
    return {"mode": "llm", "provider": cfg[0], "name": llm.provider_name(cfg[0]), "model": cfg[2]}


def _llm_facts(db, user, profile, d, hour, targets, consumed, left, plan, weights, prediction) -> dict:
    """Everything the LLM should know about the user today, kept small and factual."""
    slot = "breakfast" if hour < 11 else "lunch" if hour < 15 else "snacks" if hour < 18 else "dinner"
    picks = recs.rank_meals(db, user, d, slot)[:5]
    entries = db.scalars(select(FoodLog).where(FoodLog.user_id == user.id, FoodLog.log_date == d)
                         .order_by(FoodLog.created_at)).all()
    workout = recs.session_for_date(plan, d)
    return {
        "date": d.isoformat(), "local_time": f"{hour:02d}:00", "next_meal": slot,
        "profile": {
            "name": profile.name, "age": profile.age, "gender": profile.gender,
            "height_cm": profile.height_cm, "weight_kg": profile.weight_kg,
            "target_weight_kg": profile.target_weight_kg, "goal": profile.fitness_goal,
            "activity_level": profile.activity_level, "diet": profile.dietary_preference,
            "allergies": list(profile.allergies or []), "food_preferences": profile.food_preferences,
            "workout_level": profile.workout_level, "workout_days_per_week": profile.workout_days_per_week,
            "workout_type": profile.preferred_workout_type, "split": profile.workout_split or "auto",
        },
        "daily_targets": {k: targets[k] for k in ("daily_calories", "protein_g", "carbs_g", "fat_g", "water_ml",
                                                  "bmi", "bmi_category", "bmr", "tdee") if k in targets},
        "eaten_today": consumed, "left_today": left,
        "food_log_today": [{"meal": e.meal_type, "food": e.name,
                            "amount": e.amount_text or f"{e.quantity:g} x {e.serving_desc}",
                            "kcal": round(e.calories), "protein_g": e.protein} for e in entries],
        "water_today_ml": prog.water_by_day(db, user.id, d, d).get(d, 0),
        "todays_workout": None if workout is None else {
            "title": workout["title"], "minutes": workout["estimated_minutes"],
            "exercises": [f"{e['name']}: {e['sets']} x {e['reps']}" for e in workout["exercises"]]},
        "weekly_plan": [f"{s['weekday_name']}: {s['title']}" for s in plan.plan["sessions"]],
        "weight": {"latest_kg": weights[-1].weight_kg if weights else profile.weight_kg,
                   "first_logged_kg": weights[0].weight_kg if weights else None,
                   "trend_kg_per_week": prediction.get("weekly_change_kg") if prediction.get("available") else None,
                   "target_eta": prediction.get("target_eta")},
        "app_meal_suggestions_for_" + slot: [
            {"name": m["name"], "kcal": m["calories"], "protein_g": m["protein"], "portion": m["portion"],
             "ingredients": m["ingredients"]} for m in picks],
    }
