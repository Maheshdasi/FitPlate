from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ml.meal_recommender import MEAL_TYPES, MealRecommender, slot_targets
from ml.workout_recommender import WorkoutRecommender

from ..models import Meal, MealRecommendation, User, UserProfile, WorkoutExercise, WorkoutPlan
from .nutrition import day_totals, favourite_foods, profile_targets

# Workout days spread across the week (Monday = 0)
SCHEDULES = {2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 3, 4], 6: [0, 1, 2, 3, 4, 5]}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_meal_model: MealRecommender | None = None
_workout_model: WorkoutRecommender | None = None


def meal_model(db: Session) -> MealRecommender:
    global _meal_model
    if _meal_model is None:
        meals = db.scalars(select(Meal)).all()
        _meal_model = MealRecommender([meal_to_dict(m) for m in meals])
    return _meal_model


def workout_model(db: Session) -> WorkoutRecommender:
    global _workout_model
    if _workout_model is None:
        exercises = db.scalars(select(WorkoutExercise).order_by(WorkoutExercise.id)).all()
        _workout_model = WorkoutRecommender([exercise_to_dict(e) for e in exercises])
    return _workout_model


def reset_models():
    global _meal_model, _workout_model
    _meal_model = _workout_model = None


def meal_to_dict(m: Meal) -> dict:
    return {"id": m.id, "name": m.name, "meal_type": m.meal_type, "diet_type": m.diet_type,
            "ingredients": list(m.ingredients), "instructions": m.instructions,
            "calories": m.calories, "protein": m.protein, "carbs": m.carbs, "fat": m.fat,
            "allergens": list(m.allergens or []), "tags": list(m.tags or []),
            "prep_time_min": m.prep_time_min}


def exercise_to_dict(e: WorkoutExercise) -> dict:
    return {"id": e.id, "name": e.name, "category": e.category, "target_muscle": e.target_muscle,
            "equipment": e.equipment, "difficulty": e.difficulty, "exercise_type": e.exercise_type,
            "is_compound": e.is_compound, "is_timed": e.is_timed,
            "default_duration": e.default_duration, "goal_tags": list(e.goal_tags or []),
            "instructions": e.instructions}


def profile_dict(p: UserProfile) -> dict:
    return {"name": p.name, "fitness_goal": p.fitness_goal, "dietary_preference": p.dietary_preference,
            "allergies": list(p.allergies or []), "food_preferences": p.food_preferences or "",
            "workout_level": p.workout_level, "workout_days_per_week": p.workout_days_per_week,
            "preferred_workout_type": p.preferred_workout_type,
            "workout_split": p.workout_split or "auto", "custom_split": p.custom_split}


# ---------------------------------------------------------------- meals
def rank_meals(db: Session, user: User, d: date, meal_type: str, overrides: dict | None = None,
               exclude_ids=None) -> list[dict]:
    profile = profile_dict(user.profile)
    profile.update({k: v for k, v in (overrides or {}).items() if k == "dietary_preference"})
    targets = profile_targets(user.profile)
    _, by_slot = day_totals(db, user.id, d)
    slots = slot_targets(targets, by_slot)
    return meal_model(db).rank(
        profile=profile, targets=targets, meal_type=meal_type, slot_target=slots[meal_type],
        favourite_foods=favourite_foods(db, user.id), exclude_ids=exclude_ids,
    )


def daily_meal_plan(db: Session, user: User, d: date) -> dict:
    """Recommend one meal per slot, keeping earlier choices for the same day stable."""
    targets = profile_targets(user.profile)
    consumed, by_slot = day_totals(db, user.id, d)
    slots = slot_targets(targets, by_slot)
    existing = {r.meal_type: r for r in db.scalars(
        select(MealRecommendation).where(MealRecommendation.user_id == user.id,
                                         MealRecommendation.rec_date == d))}
    result = {}
    for meal_type in MEAL_TYPES:
        ranked = rank_meals(db, user, d, meal_type)
        rec = existing.get(meal_type)
        chosen = None
        if rec:
            # Keep today's earlier pick unless it no longer fits (e.g. profile changed)
            chosen = next((m for m in ranked if m["id"] == rec.meal_id), None)
        if chosen is None:
            excluded = set(rec.excluded_meal_ids or []) if rec else set()
            pool = [m for m in ranked if m["id"] not in excluded] or ranked
            chosen = pool[0] if pool else None
            if chosen:
                rec = _save_rec(db, user.id, d, meal_type, chosen, rec)
        alternatives = [m for m in ranked if chosen and m["id"] != chosen["id"]][:3]
        result[meal_type] = {
            "target": slots[meal_type],
            "recommended": chosen,
            "alternatives": alternatives,
            "status": rec.status if rec else None,
        }
    db.commit()
    return {"date": d.isoformat(), "targets": targets, "consumed": consumed, "slots": result,
            "method": "Content-based filtering: diet & allergy rules, then TF-IDF + cosine similarity "
                      "on ingredients and macro balance, with portion scaling."}


def _save_rec(db, user_id, d, meal_type, meal: dict, rec: MealRecommendation | None):
    if rec is None:
        rec = MealRecommendation(user_id=user_id, rec_date=d, meal_type=meal_type, excluded_meal_ids=[])
        db.add(rec)
    rec.meal_id = meal["id"]
    rec.portion = meal["portion"]
    rec.calories, rec.protein, rec.carbs, rec.fat = (meal["calories"], meal["protein"],
                                                      meal["carbs"], meal["fat"])
    rec.match_score = meal["match_score"]
    rec.status = "suggested"
    return rec


def replace_meal(db: Session, user: User, d: date, meal_type: str) -> dict | None:
    rec = db.scalar(select(MealRecommendation).where(
        MealRecommendation.user_id == user.id, MealRecommendation.rec_date == d,
        MealRecommendation.meal_type == meal_type))
    excluded = set(rec.excluded_meal_ids or []) if rec else set()
    if rec:
        excluded.add(rec.meal_id)
    ranked = rank_meals(db, user, d, meal_type, exclude_ids=excluded)
    if not ranked:
        # Every suitable meal has been shown once, so start the cycle again
        excluded = {rec.meal_id} if rec else set()
        ranked = rank_meals(db, user, d, meal_type, exclude_ids=excluded)
    if not ranked:
        return None
    chosen = ranked[0]
    rec = _save_rec(db, user.id, d, meal_type, chosen, rec)
    rec.excluded_meal_ids = sorted(excluded)
    db.commit()
    return chosen


# ---------------------------------------------------------------- workouts
def _plan_matches(plan: WorkoutPlan, p: UserProfile) -> bool:
    meta = plan.plan.get("profile", {})
    days = len(p.custom_split) if p.workout_split == "custom" and p.custom_split else p.workout_days_per_week
    return (plan.days_per_week == days and plan.level == p.workout_level
            and plan.goal == p.fitness_goal
            and meta.get("preferred_workout_type") == p.preferred_workout_type
            and meta.get("workout_split", "auto") == (p.workout_split or "auto")
            and meta.get("custom_split") == p.custom_split)


def active_plan(db: Session, user: User, regenerate: bool = False) -> WorkoutPlan:
    profile = user.profile
    plan = db.scalar(select(WorkoutPlan).where(WorkoutPlan.user_id == user.id,
                                               WorkoutPlan.is_active.is_(True)))
    if plan and not regenerate and _plan_matches(plan, profile):
        return plan

    variation, avoid_ids = 0, []
    if plan and regenerate:
        # A manual rebuild: give a different variation instead of the same plan again
        variation = (plan.plan.get("variation", 0) or 0) + 1
        avoid_ids = [e["exercise_id"] for s in plan.plan["sessions"] for e in s["exercises"]]

    db.execute(update(WorkoutPlan).where(WorkoutPlan.user_id == user.id).values(is_active=False))
    built = workout_model(db).build_plan(profile_dict(profile), variation=variation, avoid_ids=avoid_ids)
    built["variation"] = variation
    built["profile"] = {"preferred_workout_type": profile.preferred_workout_type,
                        "workout_split": profile.workout_split or "auto",
                        "custom_split": profile.custom_split}
    schedule = SCHEDULES[len(built["sessions"])]
    for session, weekday in zip(built["sessions"], schedule, strict=True):
        session["weekday"] = weekday
        session["weekday_name"] = WEEKDAYS[weekday]
    plan = WorkoutPlan(user_id=user.id, is_active=True, days_per_week=len(built["sessions"]),
                       level=profile.workout_level, goal=profile.fitness_goal,
                       schedule=schedule, plan=built)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def session_for_date(plan: WorkoutPlan, d: date) -> dict | None:
    weekday = d.weekday()
    for s in plan.plan["sessions"]:
        if s.get("weekday") == weekday:
            return s
    return None
