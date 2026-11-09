"""
WORKOUT RECOMMENDATION: rule-based split + similarity-based exercise choice

Rule-based part
  * Weekly split chosen by the user (full body, upper / lower, push pull legs,
    bro split, Arnold split or their own custom days), or picked automatically
    from the number of workout days and level (e.g. 3 days beginner -> 3
    full-body sessions).
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


MUSCLE_GROUPS = ["chest", "back", "shoulders", "arms", "legs", "core", "full_body", "cardio"]
GROUP_LABELS = {"chest": "Chest", "back": "Back", "shoulders": "Shoulders", "arms": "Arms",
                "legs": "Legs", "core": "Core", "full_body": "Full body", "cardio": "Cardio"}
SPLITS = ["auto", "full_body", "upper_lower", "push_pull_legs", "bro_split", "arnold", "custom"]

_T = {
    "full_body": {"title": "Full body", "focus": {"full_body": 1, "legs": 1, "chest": 1, "back": 1, "core": 1}},
    "push": {"title": "Push (chest, shoulders, triceps)", "focus": {"chest": 2, "shoulders": 2, "arms": 1}},
    "pull": {"title": "Pull (back, biceps)", "focus": {"back": 3, "arms": 1, "core": 1}},
    "legs": {"title": "Legs and core", "focus": {"legs": 3, "core": 2}},
    "upper": {"title": "Upper body", "focus": {"chest": 1, "back": 2, "shoulders": 1, "arms": 1}},
    "lower": {"title": "Lower body and core", "focus": {"legs": 3, "core": 2}},
    "cardio": {"title": "Cardio and core", "focus": {"cardio": 3, "core": 2}},
    # Bro split: one main muscle group per day
    "bro_chest": {"title": "Chest day", "focus": {"chest": 4, "core": 1}},
    "bro_back": {"title": "Back day", "focus": {"back": 4, "core": 1}},
    "bro_shoulders": {"title": "Shoulder day", "focus": {"shoulders": 4, "core": 1}},
    "bro_legs": {"title": "Leg day", "focus": {"legs": 4, "core": 1}},
    "bro_arms": {"title": "Arm day (biceps, triceps)", "focus": {"arms": 4, "core": 1}},
    # Arnold split: chest and back together, shoulders and arms together, then legs
    "arnold_cb": {"title": "Chest and back", "focus": {"chest": 3, "back": 3}},
    "arnold_sa": {"title": "Shoulders and arms", "focus": {"shoulders": 3, "arms": 3}},
    "arnold_legs": {"title": "Legs and core", "focus": {"legs": 4, "core": 2}},
}

# Day patterns for each named split. Patterns repeat to fill the chosen number of days.
SPLIT_PATTERNS = {
    "full_body": ["full_body"],
    "upper_lower": ["upper", "lower"],
    "push_pull_legs": ["push", "pull", "legs"],
    "arnold": ["arnold_cb", "arnold_sa", "arnold_legs"],
}
# Bro split days in priority order, so fewer days still cover the biggest muscle groups
BRO_PRIORITY = ["bro_chest", "bro_back", "bro_legs", "bro_shoulders", "bro_arms", "cardio"]
BRO_WEEK_ORDER = ["bro_chest", "bro_back", "bro_shoulders", "bro_legs", "bro_arms", "cardio"]


def custom_day_template(day: dict, per_day: int = 6) -> dict:
    """Turn a user-defined day ({name, groups}) into a session template.

    The exercise count for the day is shared between the chosen groups, earlier groups first.
    """
    groups = [g for g in dict.fromkeys(day.get("groups") or []) if g in MUSCLE_GROUPS] or ["full_body"]
    base, extra = divmod(per_day, len(groups))
    focus = {g: base + (1 if i < extra else 0) for i, g in enumerate(groups)}
    focus = {g: n for g, n in focus.items() if n > 0}
    title = (day.get("name") or "").strip() or ", ".join(GROUP_LABELS[g] for g in groups)
    return {"title": title, "focus": focus}


def weekly_split(days: int, level: str, goal: str, split: str = "auto",
                 custom_days: list[dict] | None = None) -> list[dict]:
    """Return a list of session templates: {title, focus: {category: count}}.

    split "auto" picks a split from the number of days and level. Any other split follows the
    user's choice; "custom" uses the days the user defined themselves.
    """
    if split == "custom" and custom_days:
        plan = [custom_day_template(d) for d in custom_days[:6]]
    else:
        days = int(np.clip(days, 2, 6))
        if split in SPLIT_PATTERNS:
            pattern = SPLIT_PATTERNS[split]
            plan = [_T[pattern[i % len(pattern)]] for i in range(days)]
        elif split == "bro_split":
            chosen = set(BRO_PRIORITY[:days])
            plan = [_T[k] for k in BRO_WEEK_ORDER if k in chosen]
        elif days == 2:
            plan = [_T["full_body"]] * 2
        elif days == 3:
            plan = [_T["full_body"]] * 3 if level == "beginner" else [_T["push"], _T["pull"], _T["legs"]]
        elif days == 4:
            plan = [_T["upper"], _T["lower"], _T["upper"], _T["lower"]]
        elif days == 5:
            plan = [_T["push"], _T["pull"], _T["legs"], _T["upper"], _T["cardio"]]
        else:
            plan = [_T["push"], _T["pull"], _T["legs"], _T["push"], _T["pull"], _T["legs"]]

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

    def build_plan(self, profile: dict, variation: int = 0, avoid_ids=None) -> dict:
        """Build a weekly plan.

        variation 0 gives the best-scoring plan. A higher variation (used by "Rebuild plan") steers away
        from the exercises in `avoid_ids` (the previous plan) and adds a small seeded random nudge, so
        each rebuild gives a different but still well-matched set of exercises.
        """
        goal = profile.get("fitness_goal", "general_fitness")
        level = profile.get("workout_level", "beginner")
        days = profile.get("workout_days_per_week", 3)
        split = profile.get("workout_split") or "auto"
        custom_days = profile.get("custom_split") or None
        user_vec = self._encode_user(profile).reshape(1, -1)
        sims = cosine_similarity(self.features, user_vec).ravel()
        if variation:
            sims = sims + np.random.default_rng(variation).uniform(0, 0.08, len(sims))
            avoid = set(avoid_ids or [])
            sims = sims - np.array([0.25 if e["id"] in avoid else 0.0 for e in self.exercises])

        sets, reps, rest = PRESCRIPTION[goal]
        sets = max(2, sets + LEVEL_SET_ADJUST[level])
        used_counts: dict[int, int] = {}
        sessions = []

        for day_index, template in enumerate(weekly_split(days, level, goal, split, custom_days)):
            chosen = []
            short = 0
            for category, count in template["focus"].items():
                short += count - self._pick_into(chosen, category, count, profile, sims, used_counts,
                                                 sets, reps, rest)
            # Not enough exercises for a group with this equipment: fill up with related movements
            for filler in ("full_body", "core"):
                if short > 0:
                    short -= self._pick_into(chosen, filler, short, profile, sims, used_counts,
                                             sets, reps, rest)
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
            "split": split,
            "method": "Rule-based weekly split + cosine-similarity exercise ranking with MMR diversity",
        }

    def _pick_into(self, chosen, category, count, profile, sims, used_counts, sets, reps, rest) -> int:
        """Pick up to `count` exercises of one category into `chosen`; return how many were added."""
        taken = {c["_idx"] for c in chosen}
        pool = [i for i, e in enumerate(self.exercises)
                if e["category"] == category and i not in taken and self._allowed(e, profile)]
        picks = self._mmr_pick(pool, sims, count, used_counts, already=list(taken))
        for idx in picks:
            used_counts[idx] = used_counts.get(idx, 0) + 1
            chosen.append(self._prescribe(idx, sims[idx], sets, reps, rest))
        return len(picks)

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
