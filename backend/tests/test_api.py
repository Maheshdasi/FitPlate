from datetime import date, timedelta

from conftest import PROFILE, make_user

from ml.calculations import calculate_bmr, calculate_targets


# ---------------------------------------------------------------- formulas
def test_mifflin_st_jeor_matches_published_formula():
    # 10*80 + 6.25*175 - 5*25 + 5 = 1773.75
    assert calculate_bmr(80, 175, 25, "male") == 1773.75
    assert calculate_bmr(60, 165, 30, "female") == 10 * 60 + 6.25 * 165 - 150 - 161


def test_targets_apply_goal_and_floor():
    t = calculate_targets(weight_kg=80, height_cm=175, age=25, gender="male",
                          activity_level="moderately_active", fitness_goal="weight_loss")
    assert t.tdee == round(1773.75 * 1.55)
    assert t.daily_calories == round(1773.75 * 1.55 * 0.8)
    assert t.protein_g == 144  # 1.8 g/kg
    low = calculate_targets(weight_kg=40, height_cm=150, age=60, gender="female",
                            activity_level="sedentary", fitness_goal="weight_loss")
    assert low.daily_calories == 1200  # safe minimum


# ---------------------------------------------------------------- auth
def test_register_validates_password(client):
    r = client.post("/auth/register", json={"email": "weak@test.com", "password": "abcdefgh"})
    assert r.status_code == 422
    assert "letter and one number" in r.json()["detail"]


def test_duplicate_email_conflict(client):
    client.post("/auth/register", json={"email": "dup@test.com", "password": "Passw0rd!"})
    r = client.post("/auth/register", json={"email": "DUP@test.com", "password": "Passw0rd!"})
    assert r.status_code == 409


def test_login_and_wrong_password(client):
    client.post("/auth/register", json={"email": "login@test.com", "password": "Passw0rd!"})
    assert client.post("/auth/login", json={"email": "login@test.com", "password": "Passw0rd!"}).status_code == 200
    assert client.post("/auth/login", json={"email": "login@test.com", "password": "wrong123"}).status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/profile").status_code == 401
    assert client.get("/profile", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_password_is_hashed(client):
    from app.database import SessionLocal
    from app.models import User
    make_user(client, profile=False)
    with SessionLocal() as db:
        user = db.query(User).order_by(User.id.desc()).first()
        assert user.password_hash.startswith("$2") and "Passw0rd" not in user.password_hash


# ---------------------------------------------------------------- profile
def test_profile_required_before_features(client):
    headers = make_user(client, profile=False)
    assert client.get("/profile", headers=headers).status_code == 404
    assert client.get("/nutrition/calories", headers=headers).status_code == 409


def test_profile_validation(client, auth):
    bad = {**PROFILE, "target_weight_kg": 90}  # weight loss but target above current
    r = client.put("/profile", json=bad, headers=auth)
    assert r.status_code == 422
    r = client.put("/profile", json={**PROFILE, "age": 8}, headers=auth)
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "age"


def test_calorie_endpoint_has_message_and_disclaimer(client, auth):
    r = client.get("/nutrition/calories", headers=auth).json()
    assert r["message"].startswith("Your estimated daily calorie requirement is")
    assert "not medical advice" in r["disclaimer"]
    assert len(r["explanation"]) >= 7


# ---------------------------------------------------------------- food log
def test_food_log_totals_and_delete(client, auth):
    foods = client.get("/foods", params={"search": "paneer"}, headers=auth).json()
    paneer = foods[0]
    r = client.post("/food-log", json={"food_item_id": paneer["id"], "quantity": 2, "meal_type": "lunch"}, headers=auth)
    assert r.status_code == 201
    log = client.get("/food-log/today", headers=auth).json()
    assert log["consumed"]["calories"] == round(paneer["calories"] * 2)
    assert log["remaining"]["calories"] == log["goal"]["calories"] - log["consumed"]["calories"]
    assert client.delete(f"/food-log/{r.json()['id']}", headers=auth).status_code == 204
    assert client.get("/food-log/today", headers=auth).json()["consumed"]["calories"] == 0


def test_food_log_rejects_bad_quantity(client, auth):
    r = client.post("/food-log", json={"food_item_id": 1, "quantity": 0, "meal_type": "lunch"}, headers=auth)
    assert r.status_code == 422


def test_cannot_delete_other_users_log(client, auth):
    other = make_user(client)
    r = client.post("/food-log", json={"food_item_id": 1, "quantity": 1, "meal_type": "dinner"}, headers=other)
    assert client.delete(f"/food-log/{r.json()['id']}", headers=auth).status_code == 404


def test_search_is_injection_safe(client, auth):
    r = client.get("/foods", params={"search": "'; DROP TABLE food_items; --"}, headers=auth)
    assert r.status_code == 200 and r.json() == []
    assert len(client.get("/foods", headers=auth).json()) > 50


# ---------------------------------------------------------------- recommendations
def test_meal_recommendations_respect_diet_and_allergies(client):
    headers = make_user(client, {**PROFILE, "dietary_preference": "vegan", "allergies": ["soy", "peanuts"]})
    plan = client.get("/recommendations/meals", headers=headers).json()
    for slot in plan["slots"].values():
        meal = slot["recommended"]
        assert meal["diet_type"] == "vegan"
        ingredients = " ".join(meal["ingredients"]).lower()
        assert "tofu" not in ingredients and "peanut" not in ingredients


def test_replace_meal_returns_a_different_meal(client, auth):
    plan = client.get("/recommendations/meals", headers=auth).json()
    before = plan["slots"]["dinner"]["recommended"]["id"]
    after = client.post("/recommendations/meals/replace", json={"meal_type": "dinner"}, headers=auth).json()
    assert after["id"] != before


def test_log_recommended_meal(client, auth):
    client.get("/recommendations/meals", headers=auth)
    assert client.post("/recommendations/meals/log", json={"meal_type": "breakfast"}, headers=auth).status_code == 201
    assert client.get("/food-log/today", headers=auth).json()["by_meal"]["breakfast"]["calories"] > 0


def test_workout_plan_matches_profile(client, auth):
    plan = client.get("/recommendations/workouts", headers=auth).json()
    assert plan["days_per_week"] == 3
    exercises = [e for s in plan["sessions"] for e in s["exercises"]]
    assert all(e["difficulty"] != "advanced" for e in exercises)
    assert all(e["equipment"] in ("bodyweight", "dumbbell") for e in exercises)  # home training


def test_workout_log_toggle(client, auth):
    plan = client.get("/recommendations/workouts", headers=auth).json()
    ex = plan["sessions"][0]["exercises"][0]["exercise_id"]
    r = client.post("/workout-log", json={"exercise_id": ex, "completed": True, "sets_completed": 3}, headers=auth)
    assert r.status_code == 201 and ex in r.json()["completed_exercise_ids"]
    r = client.post("/workout-log", json={"exercise_id": ex, "completed": False}, headers=auth)
    assert ex not in r.json()["completed_exercise_ids"]


# ---------------------------------------------------------------- progress & insights
def test_weight_logging_updates_profile_and_prediction(client, auth):
    today = date.today()
    for i, w in enumerate([80, 79.7, 79.5, 79.1, 78.8]):
        d = (today - timedelta(days=28 - i * 7)).isoformat()
        assert client.post("/progress/weight", json={"weight_kg": w, "log_date": d}, headers=auth).status_code == 201
    assert client.get("/profile", headers=auth).json()["weight_kg"] == 78.8
    summary = client.get("/progress/summary", params={"days": 30}, headers=auth).json()
    assert summary["prediction"]["available"] and summary["prediction"]["weekly_change_kg"] < 0


def test_future_weight_rejected(client, auth):
    d = (date.today() + timedelta(days=5)).isoformat()
    assert client.post("/progress/weight", json={"weight_kg": 70, "log_date": d}, headers=auth).status_code == 422


def test_summary_range_validation(client, auth):
    assert client.get("/progress/summary", params={"days": 12}, headers=auth).status_code == 422


def test_weekly_insights(client, auth):
    client.post("/progress/water", json={"amount_ml": 500}, headers=auth)
    r = client.get("/insights/weekly", params={"current": True}, headers=auth).json()
    assert r["insights"] and r["suggestions"]
    assert r["behaviour"]["label"] in {"Consistent achiever", "Nutrition-focused", "Workout-focused", "Getting started"}


# ---------------------------------------------------------------- AI assistant
def test_chat_uses_user_data(client, auth):
    r = client.post("/ai/chat", json={"message": "How much protein do I need today?"}, headers=auth).json()
    assert r["intent"] == "protein_query" and "144 g" in r["reply"]


def test_chat_refuses_medical_questions(client, auth):
    r = client.post("/ai/chat", json={"message": "What medicine should I take for my thyroid?"}, headers=auth).json()
    assert r["intent"] == "medical_safety"


def test_chat_meal_suggestion_respects_diet(client, auth):
    r = client.post("/ai/chat", json={"message": "What should I eat for dinner?"}, headers=auth).json()
    assert r["intent"] == "meal_suggestion"
    assert "chicken" not in r["reply"].lower() and "fish" not in r["reply"].lower()
