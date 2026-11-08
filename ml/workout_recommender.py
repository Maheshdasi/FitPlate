"""
WORKOUT RECOMMENDATION: rule-based split + similarity-based exercise choice

Rule-based part
  * Weekly split chosen from the number of workout days and level
    (e.g. 3 days beginner -> 3 full-body sessions).
  * Sets / reps / rest chosen from the goal and level using common
    strength-training guidelines.

Machine-learning part (similarity-based recommendation)
  * Each exercise is encoded as a feature vector:
      difficulty (one-hot) | equipment (one-hot) | strength/cardio |
      compound movement | goal suitability tags
  * The user is encoded in the same feature space from their level,
    preferred workout type and goal.
  * Exercises are ranked by cosine similarity to the user vector, then
    picked with Maximal Marginal Relevance (MMR) so a session does not
    repeat the same target muscle.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

CATEGORIES = ["chest", "back", "shoulders", "arms", "legs", "core", "full_body", "cardio"]
DIFFICULTIES = ["beginner", "intermediate", "advanced"]
EQUIPMENT = ["bodyweight", "dumbbell", "barbell", "machine", "cable"]
GOAL_TAGS = ["fat_loss", "strength", "hypertrophy", "endurance", "mobility"]

LEVEL_PREFERENCE = {
    "beginner": [1.0, 0.3, 0.0],
    "intermediate": [0.4, 1.0, 0.3],
    "advanced": [0.1, 0.6, 1.0],
}

WORKOUT_TYPE_EQUIPMENT = {
    "gym": [0.5, 0.9, 1.0, 0.9, 0.8],
    "home": [1.0, 0.7, 0.0, 0.0, 0.0],
    "bodyweight": [1.0, 0.0, 0.0, 0.0, 0.0],
    "mixed": [0.8, 0.9, 0.6, 0.6, 0.5],
}

GOAL_TAG_WEIGHTS = {
    "weight_loss": [1.0, 0.3, 0.4, 0.8, 0.2],
    "weight_gain": [0.1, 0.8, 1.0, 0.2, 0.2],
    "muscle_gain": [0.1, 0.8, 1.0, 0.2, 0.2],
    "maintenance": [0.5, 0.6, 0.6, 0.5, 0.4],
    "general_fitness": [0.6, 0.5, 0.5, 0.7, 0.6],
}

# Rule-based prescriptions: (sets, reps, rest seconds)
PRESCRIPTION = {
    "weight_loss": (3, "12-15", 45),
    "weight_gain": (4, "8-10", 90),
    "muscle_gain": (4, "8-12", 75),
    "maintenance": (3, "10-12", 60),
    "general_fitness": (3, "10-12", 60),
}
LEVEL_SET_ADJUST = {"beginner": -1, "intermediate": 0, "advanced": 0}


def weekly_split(days: int, level: str, goal: str) -> list[dict]:
    """Return a list of session templates: {title, focus: {category: count}}."""
    full_body = {"title": "Full body", "focus": {"full_body": 1, "legs": 1, "chest": 1, "back": 1, "core": 1}}
    push = {"title": "Push (chest, shoulders, triceps)", "focus": {"chest": 2, "shoulders": 2, "arms": 1}}
    pull = {"title": "Pull (back, biceps)", "focus": {"back": 3, "arms": 1, "core": 1}}
    legs = {"title": "Legs and core", "focus": {"legs": 3, "core": 2}}
    upper = {"title": "Upper body", "focus": {"chest": 1, "back": 2, "shoulders": 1, "arms": 1}}
    lower = {"title": "Lower body and core", "focus": {"legs": 3, "core": 2}}
    cardio = {"title": "Cardio and core", "focus": {"cardio": 3, "core": 2}}

    days = int(np.clip(days, 2, 6))
    if days == 2:
        plan = [full_body, full_body]
    elif days == 3:
        plan = [full_body] * 3 if level == "beginner" else [push, pull, legs]
    elif days == 4:
        plan = [upper, lower, upper, lower]
    elif days == 5:
        plan = [push, pull, legs, upper, cardio]
    else:
        plan = [push, pull, legs, push, pull, legs]

    plan = [dict(p, focus=dict(p["focus"])) for p in plan]
    if goal == "weight_loss":
        # Add a short cardio finisher to every strength day
        for p in plan:
            if "cardio" not in p["focus"]:
                p["focus"]["cardio"] = 1
    return plan


class WorkoutRecommender:
    def __init__(self, exercises: list[dict]):
        self.exercises = exercises
        self.features = np.array([self._encode_exercise(e) for e in exercises])

    @staticmethod
    def _encode_exercise(e: dict) -> list[float]:
        diff = [1.0 if e["difficulty"] == d else 0.0 for d in DIFFICULTIES]
        equip = [1.0 if e["equipment"] == q else 0.0 for q in EQUIPMENT]
        kind = [1.0 if e["exercise_type"] == "strength" else 0.0,
                1.0 if e["exercise_type"] == "cardio" else 0.0]
        compound = [1.0 if e.get("is_compound") else 0.0]
        tags = [1.0 if t in (e.get("goal_tags") or []) else 0.0 for t in GOAL_TAGS]
        return diff + equip + kind + compound + tags

    @staticmethod
    def _encode_user(profile: dict) -> np.ndarray:
        level = profile.get("workout_level", "beginner")
        wtype = profile.get("preferred_workout_type", "mixed")
        goal = profile.get("fitness_goal", "general_fitness")
        cardio_pref = 0.9 if wtype == "cardio" or goal == "weight_loss" else 0.3
        compound_pref = 0.9 if level != "advanced" else 0.6
        return np.array(
            LEVEL_PREFERENCE[level]
            + WORKOUT_TYPE_EQUIPMENT.get(wtype, WORKOUT_TYPE_EQUIPMENT["mixed"])
            + [1.0, cardio_pref]
            + [compound_pref]
            + GOAL_TAG_WEIGHTS[goal]
        )

    def _allowed(self, e: dict, profile: dict) -> bool:
        wtype = profile.get("preferred_workout_type", "mixed")
        level = profile.get("workout_level", "beginner")
        if wtype in ("home", "bodyweight") and e["equipment"] not in ("bodyweight", "dumbbell"):
            return False
        if wtype == "bodyweight" and e["equipment"] != "bodyweight":
            return False
        # Never give a user exercises above their level
        if level == "beginner" and e["difficulty"] == "advanced":
            return False
        if level == "intermediate" and e["difficulty"] == "advanced":
            return False
        return True

    def build_plan(self, profile: dict) -> dict:
        goal = profile.get("fitness_goal", "general_fitness")
        level = profile.get("workout_level", "beginner")
        days = profile.get("workout_days_per_week", 3)
        user_vec = self._encode_user(profile).reshape(1, -1)
        sims = cosine_similarity(self.features, user_vec).ravel()

        sets, reps, rest = PRESCRIPTION[goal]
        sets = max(2, sets + LEVEL_SET_ADJUST[level])
        used_counts: dict[int, int] = {}
        sessions = []

        for day_index, template in enumerate(weekly_split(days, level, goal)):
            chosen = []
            for category, count in template["focus"].items():
                pool = [i for i, e in enumerate(self.exercises)
                        if e["category"] == category and self._allowed(e, profile)]
                picks = self._mmr_pick(pool, sims, count, used_counts,
                                       already=[c["_idx"] for c in chosen])
                for idx in picks:
                    used_counts[idx] = used_counts.get(idx, 0) + 1
                    chosen.append(self._prescribe(idx, sims[idx], sets, reps, rest))
            for c in chosen:
                c.pop("_idx")
            sessions.append({
                "day_number": day_index + 1,
                "title": template["title"],
                "exercises": chosen,
                "estimated_minutes": self._estimate_minutes(chosen),
            })

        return {
            "days_per_week": len(sessions),
            "level": level,
            "goal": goal,
            "sessions": sessions,
            "method": "Rule-based weekly split + cosine-similarity exercise ranking with MMR diversity",
        }

    def _mmr_pick(self, pool, sims, k, used_counts, already, lam=0.7):
        """Maximal Marginal Relevance: relevant to the user, different from what is picked."""
        picked: list[int] = []
        candidates = list(pool)
        while candidates and len(picked) < k:
            best, best_score = None, -1e9
            for i in candidates:
                relevance = sims[i] - 0.15 * used_counts.get(i, 0)  # rotate across days
                redundancy = 0.0
                for j in picked + already:
                    same_muscle = self.exercises[i]["target_muscle"] == self.exercises[j]["target_muscle"]
                    redundancy = max(redundancy, 1.0 if same_muscle else 0.0)
                score = lam * relevance - (1 - lam) * redundancy
                if score > best_score:
                    best, best_score = i, score
            picked.append(best)
            candidates.remove(best)
        return picked

    def _prescribe(self, idx, sim, sets, reps, rest):
        e = self.exercises[idx]
        if e["exercise_type"] == "cardio":
            sets_, reps_, rest_ = 1, e.get("default_duration") or "10 min", 60
        elif e["category"] == "core" and e.get("is_timed"):
            sets_, reps_, rest_ = sets, "30-45 sec", 45
        else:
            sets_, reps_, rest_ = sets, reps, rest
        return {
            "_idx": idx,
            "exercise_id": e["id"],
            "name": e["name"],
            "category": e["category"],
            "target_muscle": e["target_muscle"],
            "equipment": e["equipment"],
            "difficulty": e["difficulty"],
            "instructions": e.get("instructions", ""),
            "sets": sets_,
            "reps": reps_,
            "rest_seconds": rest_,
            "similarity": round(float(sim), 3),
        }

    @staticmethod
    def _estimate_minutes(exercises) -> int:
        total = 0
        for e in exercises:
            if e["category"] == "cardio":
                total += int(str(e["reps"]).split()[0]) if str(e["reps"]).split()[0].isdigit() else 10
            else:
                total += e["sets"] * (0.75 + e["rest_seconds"] / 60)
        return int(round(total + 8))  # + warm-up
