"""Unit tests for the ML / calculation layer (no web server or database needed)."""

import json
from datetime import date, timedelta

import pytest

from app.config import SEED_DIR
from ml import behavior_clustering
from ml.calculations import bmi_category, calculate_bmr, calculate_targets
from ml.chat_assistant import MEDICAL_PATTERN, ChatAssistant
from ml.meal_recommender import MealRecommender, is_compatible, slot_targets
from ml.progress_predictor import predict_weight
from ml.weekly_insights import analyse_week
from ml.workout_recommender import WorkoutRecommender, weekly_split


def _load(name):
    items = json.loads((SEED_DIR / name).read_text(encoding="utf-8"))
    for i, item in enumerate(items, start=1):
        item.setdefault("id", i)
    return items


MEALS = _load("meals.json")
EXERCISES = _load("exercises.json")


# ---------------------------------------------------------------- formulas
@pytest.mark.parametrize("bmi, expected", [(18.4, "Underweight"), (18.5, "Normal"), (24.9, "Normal"),
                                           (25.0, "Overweight"), (30.0, "Obese")])
def test_bmi_categories_follow_who_cutoffs(bmi, expected):
    assert bmi_category(bmi) == expected


def test_macros_add_up_to_daily_calories():
    t = calculate_targets(weight_kg=60, height_cm=165, age=21, gender="female",
                          activity_level="lightly_active", fitness_goal="muscle_gain")
    energy = t.protein_g * 4 + t.carbs_g * 4 + t.fat_g * 9
    assert abs(energy - t.daily_calories) <= 15  # only rounding differences
    assert calculate_bmr(60, 165, 21, "female") == 10 * 60 + 6.25 * 165 - 5 * 21 - 161


# ---------------------------------------------------------------- meal recommender
def test_diet_hierarchy():
    vegan, egg, chicken = {"diet_type": "vegan"}, {"diet_type": "eggetarian"}, {"diet_type": "non_vegetarian"}
    assert is_compatible(vegan, "vegetarian", [])
    assert not is_compatible(egg, "vegetarian", [])
    assert is_compatible(egg, "eggetarian", [])
    assert not is_compatible(chicken, "eggetarian", [])
    assert not is_compatible({"diet_type": "vegan", "allergens": ["Peanuts"]}, "vegan", ["peanuts"])


def test_remaining_calories_are_shared_across_uneaten_meals():
    targets = {"daily_calories": 2000, "protein_g": 120, "carbs_g": 250, "fat_g": 60}
    eaten = {"breakfast": {"calories": 500, "protein": 30}}
    slots = slot_targets(targets, eaten)
    open_total = sum(slots[s]["calories"] for s in ("lunch", "dinner", "snacks"))
    assert abs(open_total - 1500) <= 2
    assert slots["breakfast"]["already_eaten"] and not slots["lunch"]["already_eaten"]


def test_recommendations_are_ranked_scaled_and_respect_exclusions():
    targets = calculate_targets(weight_kg=70, height_cm=170, age=25, gender="male",
                                activity_level="moderately_active", fitness_goal="muscle_gain").to_dict()
    slot = slot_targets(targets, {})["lunch"]
    profile = {"dietary_preference": "vegetarian", "allergies": ["dairy"], "fitness_goal": "muscle_gain"}
    ranked = MealRecommender(MEALS).rank(profile=profile, targets=targets, meal_type="lunch", slot_target=slot)
    assert ranked, "expected at least one vegetarian, dairy-free lunch"
    scores = [m["match_score"] for m in ranked]
    assert scores == sorted(scores, reverse=True)
    assert all(0.75 <= m["portion"] <= 1.5 for m in ranked)
    again = MealRecommender(MEALS).rank(profile=profile, targets=targets, meal_type="lunch",
                                        slot_target=slot, exclude_ids={ranked[0]["id"]})
    assert ranked[0]["id"] not in {m["id"] for m in again}


# ---------------------------------------------------------------- workout recommender
@pytest.mark.parametrize("days", [2, 3, 4, 5, 6])
def test_weekly_split_has_one_session_per_day(days):
    assert len(weekly_split(days, "intermediate", "maintenance")) == days


def test_weight_loss_plan_adds_cardio_and_avoids_repeated_muscles():
    plan = WorkoutRecommender(EXERCISES).build_plan({
        "fitness_goal": "weight_loss", "workout_level": "beginner",
        "workout_days_per_week": 3, "preferred_workout_type": "bodyweight"})
    for session in plan["sessions"]:
        assert any(e["category"] == "cardio" for e in session["exercises"])
        assert all(e["equipment"] == "bodyweight" for e in session["exercises"])
        muscles = [e["target_muscle"] for e in session["exercises"]]
        assert len(set(muscles)) >= len(muscles) - 1  # MMR keeps sessions varied


@pytest.mark.parametrize("split,expected", [
    ("upper_lower", ["Upper body", "Lower body and core", "Upper body", "Lower body and core"]),
    ("bro_split", ["Chest day", "Back day", "Leg day", "Shoulder day"]),
    ("arnold", ["Chest and back", "Shoulders and arms", "Legs and core", "Chest and back"]),
])
def test_named_splits(split, expected):
    titles = [t["title"] for t in weekly_split(4, "intermediate", "muscle_gain", split)]
    assert sorted(titles) == sorted(expected) and len(titles) == 4


def test_custom_day_shares_exercises_between_groups():
    (day,) = weekly_split(3, "beginner", "maintenance", "custom", [{"name": "", "groups": ["chest", "arms"]}])
    assert day["focus"] == {"chest": 3, "arms": 3} and day["title"] == "Chest, Arms"


# ---------------------------------------------------------------- progress predictor
def test_regression_recovers_a_known_trend():
    start = date(2026, 1, 1)
    logs = [(start + timedelta(days=d), 80 - 0.5 * d / 7) for d in range(0, 42, 3)]  # -0.5 kg per week
    p = predict_weight(logs, target_weight=75)
    assert p["available"] and p["weekly_change_kg"] == pytest.approx(-0.5, abs=0.01)
    assert p["confidence"] == "high" and p["target_eta"] is not None


def test_prediction_needs_enough_data():
    assert not predict_weight([(date(2026, 1, 1), 70.0), (date(2026, 1, 2), 69.9)], 65)["available"]


# ---------------------------------------------------------------- clustering and weekly insights
def test_clusters_are_named_from_their_centres():
    good = behavior_clustering.classify({"calorie_adherence": 0.9, "protein_ratio": 1.0,
                                         "workout_ratio": 1.0, "logging_ratio": 1.0})
    new = behavior_clustering.classify({"calorie_adherence": 0.1, "protein_ratio": 0.4,
                                        "workout_ratio": 0.1, "logging_ratio": 0.2})
    assert good["label"] == "Consistent achiever"
    assert new["label"] == "Getting started"


def test_perfect_week_insights():
    targets = {"daily_calories": 2000, "protein_g": 120, "water_ml": 2500}
    days = [{"date": f"2026-01-0{i + 1}", "calories": 2000, "protein": 125, "water_ml": 2600,
             "workout_done": i < 4} for i in range(7)]
    result = analyse_week(days, targets, planned_workouts=4, weight_this_week=70.0, weight_last_week=70.5)
    texts = " ".join(i["text"] for i in result["insights"])
    assert "7 out of 7 days" in texts and "4 workouts" in texts and "down by 0.5 kg" in texts
    assert result["behaviour"]["label"] == "Consistent achiever"


# ---------------------------------------------------------------- assistant
@pytest.mark.parametrize("question, intent", [
    ("what shud i eat for dinr", "meal_suggestion"),
    ("protien target", "protein_query"),
    ("which exercise today", "workout_today"),
    ("i have 300 kcal left what to eat", "calories_remaining"),
    ("whats my bmi", "calorie_target"),
])
def test_intent_classifier_handles_typos(question, intent):
    assert ChatAssistant().classify(question)[0] == intent


def test_medical_questions_are_caught_by_the_safety_rule():
    assert MEDICAL_PATTERN.search("Can I eat rice if I have diabetes?")
    assert MEDICAL_PATTERN.search("my knee pain after squats")
    assert not MEDICAL_PATTERN.search("suggest a high protein breakfast")
