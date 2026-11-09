from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after the first release. create_all() only creates missing tables, so existing
# databases get these columns here (safe to run on every start).
UPGRADES = [
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS workout_split VARCHAR(20) NOT NULL DEFAULT 'auto'",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS custom_split JSONB",
    "ALTER TABLE food_logs ADD COLUMN IF NOT EXISTS amount_text VARCHAR(60)",
    "ALTER TABLE workout_logs ADD COLUMN IF NOT EXISTS sets JSONB",
]


def init_db():
    """Create missing tables, then add any newer columns to existing tables."""
    from sqlalchemy import text

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for sql in UPGRADES:
            conn.execute(text(sql))
