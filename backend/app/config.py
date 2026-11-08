import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://fitness:fitness@localhost:5432/fitness_db"
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    cors_origins: list[str] = [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if o.strip()
    ]

    def __init__(self):
        if not self.jwt_secret:
            # Development fallback so the project runs out of the box.
            # Always set JWT_SECRET in .env for anything beyond local use.
            self.jwt_secret = "dev-only-secret-change-me"


settings = Settings()

PROJECT_ROOT = BACKEND_DIR.parent
SEED_DIR = PROJECT_ROOT / "database" / "seed_data"
