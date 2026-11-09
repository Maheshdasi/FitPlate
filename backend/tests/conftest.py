import os

# Use a separate database so tests never touch real data
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg2://fitness:fitness@localhost:5432/fitness_test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from seed import load_catalogue  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

PROFILE = {
    "name": "Test User", "age": 25, "gender": "male", "height_cm": 175, "weight_kg": 80,
    "target_weight_kg": 72, "activity_level": "moderately_active", "fitness_goal": "weight_loss",
    "dietary_preference": "vegetarian", "allergies": ["peanuts"], "food_preferences": "paneer dal",
    "workout_level": "beginner", "workout_days_per_week": 3, "preferred_workout_type": "home",
}


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        load_catalogue(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


_counter = {"n": 0}


def make_user(client, profile=None):
    _counter["n"] += 1
    r = client.post("/auth/register", json={"email": f"user{_counter['n']}@test.com", "password": "Passw0rd!"})
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if profile is not False:
        r = client.put("/profile", json=profile or PROFILE, headers=headers)
        assert r.status_code == 200, r.text
    return headers


@pytest.fixture
def auth(client):
    return make_user(client)


@pytest.fixture(autouse=True)
def offline_assistant_by_default(monkeypatch):
    """Tests never call a real LLM, even if a key is set in backend/.env."""
    for key in ("GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(key, raising=False)
