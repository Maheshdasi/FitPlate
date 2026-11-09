from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

GENDERS = ("male", "female", "other")
ACTIVITY_LEVELS = ("sedentary", "lightly_active", "moderately_active", "very_active")
GOALS = ("weight_loss", "weight_gain", "muscle_gain", "maintenance", "general_fitness")
DIETS = ("vegetarian", "non_vegetarian", "vegan", "eggetarian")
LEVELS = ("beginner", "intermediate", "advanced")
WORKOUT_TYPES = ("gym", "home", "bodyweight", "mixed", "cardio")
MEAL_TYPES = ("breakfast", "lunch", "dinner", "snacks")
CATEGORIES = ("chest", "back", "shoulders", "arms", "legs", "core", "full_body", "cardio")
SPLITS = ("auto", "full_body", "upper_lower", "push_pull_legs", "bro_split", "arnold", "custom")


def _in(column: str, values: tuple) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False,
                                                  cascade="all, delete-orphan")


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("age BETWEEN 13 AND 100", name="ck_profile_age"),
        CheckConstraint("height_cm BETWEEN 100 AND 250", name="ck_profile_height"),
        CheckConstraint("weight_kg BETWEEN 30 AND 300", name="ck_profile_weight"),
        CheckConstraint("target_weight_kg BETWEEN 30 AND 300", name="ck_profile_target"),
        CheckConstraint("workout_days_per_week BETWEEN 2 AND 6", name="ck_profile_days"),
        CheckConstraint(_in("gender", GENDERS), name="ck_profile_gender"),
        CheckConstraint(_in("activity_level", ACTIVITY_LEVELS), name="ck_profile_activity"),
        CheckConstraint(_in("fitness_goal", GOALS), name="ck_profile_goal"),
        CheckConstraint(_in("dietary_preference", DIETS), name="ck_profile_diet"),
        CheckConstraint(_in("workout_level", LEVELS), name="ck_profile_level"),
        CheckConstraint(_in("preferred_workout_type", WORKOUT_TYPES), name="ck_profile_wtype"),
        CheckConstraint(_in("workout_split", SPLITS), name="ck_profile_split"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(10))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    target_weight_kg: Mapped[float] = mapped_column(Float)
    activity_level: Mapped[str] = mapped_column(String(30))
    fitness_goal: Mapped[str] = mapped_column(String(30))
    dietary_preference: Mapped[str] = mapped_column(String(30))
    allergies: Mapped[list[str]] = mapped_column(ARRAY(String(30)), default=list)
    food_preferences: Mapped[str | None] = mapped_column(Text)
    workout_level: Mapped[str] = mapped_column(String(20))
    workout_days_per_week: Mapped[int] = mapped_column(Integer, default=3)
    preferred_workout_type: Mapped[str] = mapped_column(String(20), default="mixed")
    # Training split: "auto" lets the app choose; "custom" uses custom_split = [{name, groups}]
    workout_split: Mapped[str] = mapped_column(String(20), default="auto", server_default="auto")
    custom_split: Mapped[list | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="profile")


class FoodItem(TimestampMixin, Base):
    __tablename__ = "food_items"
    __table_args__ = (
        CheckConstraint("calories >= 0 AND protein >= 0 AND carbs >= 0 AND fat >= 0",
                        name="ck_food_nonnegative"),
        CheckConstraint(_in("diet_type", DIETS), name="ck_food_diet"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    serving_desc: Mapped[str] = mapped_column(String(60))
    serving_g: Mapped[float] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float)
    protein: Mapped[float] = mapped_column(Float)
    carbs: Mapped[float] = mapped_column(Float)
    fat: Mapped[float] = mapped_column(Float)
    fiber: Mapped[float] = mapped_column(Float, default=0)
    diet_type: Mapped[str] = mapped_column(String(30))
    allergens: Mapped[list[str]] = mapped_column(ARRAY(String(30)), default=list)


class Meal(TimestampMixin, Base):
    """Catalogue of meal templates used by the meal recommender."""
    __tablename__ = "meals"
    __table_args__ = (
        CheckConstraint(_in("meal_type", MEAL_TYPES), name="ck_meal_type"),
        CheckConstraint(_in("diet_type", DIETS), name="ck_meal_diet"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    diet_type: Mapped[str] = mapped_column(String(30))
    ingredients: Mapped[list[str]] = mapped_column(ARRAY(Text))
    instructions: Mapped[str] = mapped_column(Text)
    calories: Mapped[float] = mapped_column(Float)
    protein: Mapped[float] = mapped_column(Float)
    carbs: Mapped[float] = mapped_column(Float)
    fat: Mapped[float] = mapped_column(Float)
    allergens: Mapped[list[str]] = mapped_column(ARRAY(String(30)), default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(30)), default=list)
    prep_time_min: Mapped[int] = mapped_column(Integer, default=15)


class FoodLog(TimestampMixin, Base):
    __tablename__ = "food_logs"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND quantity <= 20", name="ck_foodlog_quantity"),
        CheckConstraint(_in("meal_type", MEAL_TYPES), name="ck_foodlog_meal_type"),
        Index("ix_food_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    food_item_id: Mapped[int | None] = mapped_column(ForeignKey("food_items.id", ondelete="SET NULL"))
    meal_id: Mapped[int | None] = mapped_column(ForeignKey("meals.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(150))
    serving_desc: Mapped[str] = mapped_column(String(60))
    meal_type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float)  # number of servings
    amount_text: Mapped[str | None] = mapped_column(String(60))  # what the user entered, e.g. "2 katori"
    log_date: Mapped[date] = mapped_column(Date)
    # Nutrient snapshot at logging time so history stays correct if the catalogue changes
    calories: Mapped[float] = mapped_column(Float)
    protein: Mapped[float] = mapped_column(Float)
    carbs: Mapped[float] = mapped_column(Float)
    fat: Mapped[float] = mapped_column(Float)


class MealRecommendation(TimestampMixin, Base):
    __tablename__ = "meal_recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "rec_date", "meal_type", name="uq_mealrec_user_date_type"),
        CheckConstraint(_in("meal_type", MEAL_TYPES), name="ck_mealrec_type"),
        CheckConstraint("status IN ('suggested', 'logged')", name="ck_mealrec_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"))
    rec_date: Mapped[date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(20))
    portion: Mapped[float] = mapped_column(Float, default=1.0)
    calories: Mapped[float] = mapped_column(Float)
    protein: Mapped[float] = mapped_column(Float)
    carbs: Mapped[float] = mapped_column(Float)
    fat: Mapped[float] = mapped_column(Float)
    match_score: Mapped[float] = mapped_column(Float)
    excluded_meal_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    status: Mapped[str] = mapped_column(String(20), default="suggested")

    meal: Mapped[Meal] = relationship()


class WorkoutExercise(TimestampMixin, Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (
        CheckConstraint(_in("category", CATEGORIES), name="ck_exercise_category"),
        CheckConstraint(_in("difficulty", LEVELS), name="ck_exercise_difficulty"),
        CheckConstraint("exercise_type IN ('strength', 'cardio')", name="ck_exercise_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    target_muscle: Mapped[str] = mapped_column(String(80))
    equipment: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(20))
    exercise_type: Mapped[str] = mapped_column(String(20))
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False)
    is_timed: Mapped[bool] = mapped_column(Boolean, default=False)
    default_duration: Mapped[str | None] = mapped_column(String(20))
    goal_tags: Mapped[list[str]] = mapped_column(ARRAY(String(20)), default=list)
    instructions: Mapped[str] = mapped_column(Text)


class WorkoutPlan(TimestampMixin, Base):
    __tablename__ = "workout_plans"
    __table_args__ = (Index("ix_workout_plans_user_active", "user_id", "is_active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    days_per_week: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    goal: Mapped[str] = mapped_column(String(30))
    schedule: Mapped[list[int]] = mapped_column(ARRAY(Integer))  # weekday numbers, Monday = 0
    plan: Mapped[dict] = mapped_column(JSONB)


class WorkoutLog(TimestampMixin, Base):
    __tablename__ = "workout_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "log_date", "exercise_id", name="uq_workoutlog_user_date_ex"),
        CheckConstraint("sets_completed BETWEEN 0 AND 20", name="ck_workoutlog_sets"),
        Index("ix_workout_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("workout_plans.id", ondelete="SET NULL"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("workout_exercises.id", ondelete="CASCADE"))
    log_date: Mapped[date] = mapped_column(Date)
    day_number: Mapped[int | None] = mapped_column(Integer)
    sets_completed: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    # Set-by-set log: [{"weight_kg": 40, "reps": 10, "seconds": null, "done": true}, ...]
    sets: Mapped[list | None] = mapped_column(JSONB)

    exercise: Mapped[WorkoutExercise] = relationship()


class WeightLog(TimestampMixin, Base):
    __tablename__ = "weight_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "log_date", name="uq_weightlog_user_date"),
        CheckConstraint("weight_kg BETWEEN 30 AND 300", name="ck_weightlog_weight"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    log_date: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    chest_cm: Mapped[float | None] = mapped_column(Float)
    hips_cm: Mapped[float | None] = mapped_column(Float)
    arms_cm: Mapped[float | None] = mapped_column(Float)


class WaterLog(TimestampMixin, Base):
    __tablename__ = "water_logs"
    __table_args__ = (
        CheckConstraint("amount_ml > 0 AND amount_ml <= 3000", name="ck_waterlog_amount"),
        Index("ix_water_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    log_date: Mapped[date] = mapped_column(Date)
    amount_ml: Mapped[int] = mapped_column(Integer)


class WeeklyInsight(TimestampMixin, Base):
    __tablename__ = "weekly_insights"
    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_insight_user_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    week_end: Mapped[date] = mapped_column(Date)
    metrics: Mapped[dict] = mapped_column(JSONB)
    insights: Mapped[list] = mapped_column(JSONB)
    suggestions: Mapped[list] = mapped_column(JSONB)
    behaviour: Mapped[dict] = mapped_column(JSONB)
    daily: Mapped[list] = mapped_column(JSONB)
