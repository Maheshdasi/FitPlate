"""
MEAL RECOMMENDATION — content-based recommender (machine learning)

Pipeline
  1. Rule-based filter   : remove meals that clash with the user's diet
                           type or allergies (hard safety constraints).
  2. Slot targets        : split the remaining calories / protein for the
                           day across the meal slots not yet eaten.
  3. Content features    :
       a) Nutrition vector  [protein kcal, carb kcal, fat kcal]
       b) Text vector       TF-IDF over name + ingredients + tags
  4. User profile vector :
       a) Target macro split for the slot
       b) TF-IDF of the user's stated food preferences, goal keywords and
          the foods they log most often (implicit feedback)
  5. Score = cosine(nutrition) * 0.40 + calorie fit * 0.30
             + cosine(text) * 0.20 + protein density bonus * 0.10
  6. Portion scaling     : servings are scaled (0.75x – 1.5x) so the
                           meal lands close to the slot's calorie target.

The result is a ranked list per meal slot, so "replace" simply returns the
next-best item that is not excluded.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .calculations import MEAL_SPLIT

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snacks"]

# Which meal diet types each user diet preference may eat
DIET_ALLOWED = {
    "vegan": {"vegan"},
    "vegetarian": {"vegan", "vegetarian"},
    "eggetarian": {"vegan", "vegetarian", "eggetarian"},
    "non_vegetarian": {"vegan", "vegetarian", "eggetarian", "non_vegetarian"},
}

GOAL_KEYWORDS = {
    "weight_loss": "light high-protein high-fiber low-calorie vegetables salad",
    "weight_gain": "calorie-dense hearty nuts rice milk banana",
    "muscle_gain": "high-protein eggs chicken paneer dal recovery",
    "maintenance": "balanced wholesome",
    "general_fitness": "balanced wholesome fiber",
}

WEIGHTS = {"macro": 0.40, "calorie": 0.30, "text": 0.20, "protein": 0.10}


def is_compatible(meal: dict, diet: str, allergies: list[str]) -> bool:
    if meal["diet_type"] not in DIET_ALLOWED.get(diet, DIET_ALLOWED["non_vegetarian"]):
        return False
    meal_allergens = {a.lower() for a in (meal.get("allergens") or [])}
    return not (meal_allergens & {a.lower() for a in allergies})


def slot_targets(targets: dict, consumed_by_slot: dict) -> dict:
    """Spread what is left of today's targets over the meal slots not yet eaten."""
    eaten_slots = {s for s, v in consumed_by_slot.items() if v.get("calories", 0) > 0}
    open_slots = [s for s in MEAL_TYPES if s not in eaten_slots]
    total_consumed_kcal = sum(v.get("calories", 0) for v in consumed_by_slot.values())
    total_consumed_protein = sum(v.get("protein", 0) for v in consumed_by_slot.values())

    remaining_kcal = max(targets["daily_calories"] - total_consumed_kcal, 0)
    remaining_protein = max(targets["protein_g"] - total_consumed_protein, 0)
    open_share = sum(MEAL_SPLIT[s] for s in open_slots) or 1

    result = {}
    for slot in MEAL_TYPES:
        if slot in open_slots:
            share = MEAL_SPLIT[slot] / open_share
            kcal = remaining_kcal * share
            protein = remaining_protein * share
        else:
            # Already eaten: still recommend a typical-size option for next time
            kcal = targets["daily_calories"] * MEAL_SPLIT[slot]
            protein = targets["protein_g"] * MEAL_SPLIT[slot]
        kcal = max(kcal, 120)  # never recommend an empty plate
        result[slot] = {
            "calories": round(kcal),
            "protein": round(protein),
            "carbs": round(targets["carbs_g"] * MEAL_SPLIT[slot]),
            "fat": round(targets["fat_g"] * MEAL_SPLIT[slot]),
            "already_eaten": slot not in open_slots,
        }
    return result


def _portion(target_kcal: float, meal_kcal: float) -> float:
    raw = target_kcal / max(meal_kcal, 1)
    return float(np.clip(round(raw * 4) / 4, 0.75, 1.5))


class MealRecommender:
    def __init__(self, meals: list[dict]):
        self.df = pd.DataFrame(meals)
        self.df["document"] = (
            self.df["name"] + " " + self.df["ingredients"].apply(" ".join)
            + " " + self.df["tags"].apply(lambda t: " ".join(t or []))
        ).str.lower()
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        self.text_matrix = self.vectorizer.fit_transform(self.df["document"])

    def _user_text_vector(self, profile: dict, favourite_foods: list[str]):
        parts = [
            GOAL_KEYWORDS.get(profile.get("fitness_goal"), ""),
            profile.get("food_preferences") or "",
            " ".join(favourite_foods),
        ]
        return self.vectorizer.transform([" ".join(parts).lower()])

    def rank(self, *, profile: dict, targets: dict, meal_type: str, slot_target: dict,
             favourite_foods: list[str] | None = None, exclude_ids=None) -> list[dict]:
        exclude_ids = set(exclude_ids or [])
        allergies = profile.get("allergies") or []
        diet = profile.get("dietary_preference", "non_vegetarian")

        mask = (self.df["meal_type"] == meal_type) & self.df.apply(
            lambda r: is_compatible(r, diet, allergies) and r["id"] not in exclude_ids, axis=1
        )
        candidates = self.df[mask].copy()
        if candidates.empty:
            return []

        # Portion scaling toward the slot calorie target
        candidates["portion"] = candidates["calories"].apply(
            lambda k: _portion(slot_target["calories"], k)
        )
        for col in ["calories", "protein", "carbs", "fat"]:
            candidates[f"scaled_{col}"] = candidates[col] * candidates["portion"]

        # a) macro balance: energy split vectors compared with cosine similarity
        meal_vec = np.column_stack([
            candidates["scaled_protein"] * 4,
            candidates["scaled_carbs"] * 4,
            candidates["scaled_fat"] * 9,
        ])
        target_vec = np.array([[slot_target["protein"] * 4,
                                slot_target["carbs"] * 4,
                                slot_target["fat"] * 9]])
        macro_sim = cosine_similarity(meal_vec, target_vec).ravel()

        # b) calorie closeness (1.0 = exact match)
        gap = np.abs(candidates["scaled_calories"] - slot_target["calories"]) / slot_target["calories"]
        calorie_fit = np.exp(-3 * gap.to_numpy())

        # c) text similarity to the user's preference profile
        user_vec = self._user_text_vector(profile, favourite_foods or [])
        text_sim = cosine_similarity(self.text_matrix[candidates.index], user_vec).ravel()

        # d) protein density (g per 100 kcal), normalised 0..1
        density = (candidates["protein"] / candidates["calories"] * 100).to_numpy()
        protein_bonus = np.clip(density / 10, 0, 1)
        if profile.get("fitness_goal") == "weight_gain":
            protein_bonus *= 0.5

        candidates["score"] = (
            WEIGHTS["macro"] * macro_sim + WEIGHTS["calorie"] * calorie_fit
            + WEIGHTS["text"] * text_sim + WEIGHTS["protein"] * protein_bonus
        )
        candidates["macro_sim"] = macro_sim
        candidates["calorie_fit"] = calorie_fit
        candidates["text_sim"] = text_sim
        candidates = candidates.sort_values("score", ascending=False)

        return [self._format(row, slot_target) for _, row in candidates.iterrows()]

    @staticmethod
    def _format(row, slot_target) -> dict:
        reasons = []
        if row["calorie_fit"] > 0.8:
            reasons.append(f"Close to your {slot_target['calories']} kcal target for this meal")
        if row["protein"] / row["calories"] * 100 >= 6:
            reasons.append("High in protein for its calories")
        if row["text_sim"] > 0.08:
            reasons.append("Matches foods you like or log often")
        if row["macro_sim"] > 0.97:
            reasons.append("Macro balance matches your plan")
        if not reasons:
            reasons.append("Fits your diet type and allergy settings")

        return {
            "id": int(row["id"]),
            "name": row["name"],
            "meal_type": row["meal_type"],
            "diet_type": row["diet_type"],
            "ingredients": list(row["ingredients"]),
            "instructions": row["instructions"],
            "prep_time_min": int(row.get("prep_time_min") or 0),
            "portion": row["portion"],
            "calories": round(row["scaled_calories"]),
            "protein": round(row["scaled_protein"], 1),
            "carbs": round(row["scaled_carbs"], 1),
            "fat": round(row["scaled_fat"], 1),
            "match_score": round(float(row["score"]) * 100),
            "reasons": reasons,
        }
