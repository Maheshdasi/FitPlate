import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Gender = Literal["male", "female", "other"]
Activity = Literal["sedentary", "lightly_active", "moderately_active", "very_active"]
Goal = Literal["weight_loss", "weight_gain", "muscle_gain", "maintenance", "general_fitness"]
Diet = Literal["vegetarian", "non_vegetarian", "vegan", "eggetarian"]
Level = Literal["beginner", "intermediate", "advanced"]
WorkoutType = Literal["gym", "home", "bodyweight", "mixed", "cardio"]
Split = Literal["auto", "full_body", "upper_lower", "push_pull_legs", "bro_split", "arnold", "custom"]
MuscleGroup = Literal["chest", "back", "shoulders", "arms", "legs", "core", "full_body", "cardio"]
MealType = Literal["breakfast", "lunch", "dinner", "snacks"]
Allergen = Literal["dairy", "eggs", "gluten", "nuts", "peanuts", "soy", "fish", "shellfish", "sesame"]


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one number")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    has_profile: bool


# ---------- Profile ----------
class CustomDay(BaseModel):
    """One day of a user-defined split, e.g. {"name": "Chest and triceps", "groups": ["chest", "arms"]}."""
    name: str = Field(default="", max_length=40)
    groups: list[MuscleGroup] = Field(min_length=1, max_length=4)

    @field_validator("name")
    @classmethod
    def clean_day_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if v and not re.fullmatch(r"[A-Za-z0-9 ,.&()'/+-]+", v):
            raise ValueError("Day names can only contain letters, numbers and simple punctuation")
        return v

    @field_validator("groups")
    @classmethod
    def unique_groups(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class SplitFields(BaseModel):
    workout_split: Split = "auto"
    custom_split: list[CustomDay] | None = Field(default=None, max_length=6)

    @model_validator(mode="after")
    def custom_needs_days(self):
        if self.workout_split == "custom":
            if not self.custom_split or len(self.custom_split) < 2:
                raise ValueError("A custom split needs between 2 and 6 workout days")
        else:
            self.custom_split = None
        return self


class SplitIn(SplitFields):
    workout_days_per_week: int | None = Field(default=None, ge=2, le=6)


class ProfileIn(SplitFields):
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=13, le=100)
    gender: Gender
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    target_weight_kg: float = Field(ge=30, le=300)
    activity_level: Activity
    fitness_goal: Goal
    dietary_preference: Diet
    allergies: list[Allergen] = []
    food_preferences: str | None = Field(default=None, max_length=500)
    workout_level: Level
    workout_days_per_week: int = Field(default=3, ge=2, le=6)
    preferred_workout_type: WorkoutType = "mixed"

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", v):
            raise ValueError("Name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v

    @model_validator(mode="after")
    def days_match_custom_split(self):
        if self.workout_split == "custom" and self.custom_split:
            self.workout_days_per_week = len(self.custom_split)
        return self

    @model_validator(mode="after")
    def target_matches_goal(self):
        diff = self.target_weight_kg - self.weight_kg
        if self.fitness_goal == "weight_loss" and diff > 0:
            raise ValueError("For weight loss, target weight should be less than or equal to current weight")
        if self.fitness_goal in ("weight_gain", "muscle_gain") and diff < -2:
            raise ValueError("For weight or muscle gain, target weight should not be below current weight")
        return self


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    email: str | None = None


# ---------- Calculator ----------
class CalculatorIn(BaseModel):
    age: int = Field(ge=13, le=100)
    gender: Gender
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    target_weight_kg: float | None = Field(default=None, ge=30, le=300)
    activity_level: Activity
    fitness_goal: Goal


# ---------- Food ----------
class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    serving_desc: str
    serving_g: float
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    diet_type: str
    allergens: list[str]


class FoodLogIn(BaseModel):
    food_item_id: int | None = None
    meal_id: int | None = None
    quantity: float = Field(gt=0, le=20)
    meal_type: MealType
    log_date: date | None = None

    @model_validator(mode="after")
    def exactly_one_source(self):
        if (self.food_item_id is None) == (self.meal_id is None):
            raise ValueError("Provide either food_item_id or meal_id")
        return self


class FoodLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    food_item_id: int | None
    meal_id: int | None
    name: str
    serving_desc: str
    meal_type: str
    quantity: float
    log_date: date
    calories: float
    protein: float
    carbs: float
    fat: float


# ---------- Workouts ----------
class WorkoutLogIn(BaseModel):
    exercise_id: int
    completed: bool = True
    sets_completed: int = Field(default=0, ge=0, le=20)
    day_number: int | None = Field(default=None, ge=1, le=7)
    log_date: date | None = None


# ---------- Progress ----------
class WeightIn(BaseModel):
    weight_kg: float = Field(ge=30, le=300)
    waist_cm: float | None = Field(default=None, ge=40, le=200)
    chest_cm: float | None = Field(default=None, ge=50, le=200)
    hips_cm: float | None = Field(default=None, ge=50, le=200)
    arms_cm: float | None = Field(default=None, ge=15, le=80)
    log_date: date | None = None

    @field_validator("log_date")
    @classmethod
    def not_future(cls, v):
        if v and v > date.today():
            raise ValueError("Date cannot be in the future")
        return v


class WeightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    log_date: date
    weight_kg: float
    waist_cm: float | None
    chest_cm: float | None
    hips_cm: float | None
    arms_cm: float | None


class WaterIn(BaseModel):
    amount_ml: int = Field(gt=0, le=3000)
    log_date: date | None = None


# ---------- Meals ----------
class ReplaceMealIn(BaseModel):
    meal_type: MealType
    rec_date: date | None = None


class LogMealIn(BaseModel):
    meal_type: MealType
    rec_date: date | None = None


# ---------- AI ----------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    local_date: date | None = None
    local_hour: int | None = Field(default=None, ge=0, le=23)
