"""
Reproduce the evaluation results reported in docs/PROJECT_REPORT.md.

    python -m ml.evaluate          (run from the project root)

1. Meal recommender safety and calorie fit over every combination of
   diet type x allergy set x fitness goal x meal slot.
2. Assistant intent classifier: 5-fold stratified cross-validation and
   misspelt questions it has never seen.
3. K-Means behaviour clustering: silhouette score.
"""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import silhouette_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

from . import behavior_clustering
from .calculations import calculate_targets
from .chat_assistant import TRAINING_DATA, ChatAssistant
from .meal_recommender import MEAL_TYPES, MealRecommender, is_compatible, slot_targets

SEED_DIR = Path(__file__).resolve().parents[1] / "database" / "seed_data"

DIETS = ["vegan", "vegetarian", "eggetarian", "non_vegetarian"]
ALLERGY_SETS = [[], ["dairy"], ["gluten"], ["peanuts", "nuts"], ["eggs"], ["soy"]]
GOALS = ["weight_loss", "muscle_gain", "weight_gain", "maintenance"]

UNSEEN_QUESTIONS = {
    "what shud i eat for dinr": "meal_suggestion",
    "protien target": "protein_query",
    "which exercise today": "workout_today",
    "how much water": "water",
    "i have 300 kcal left what to eat": "calories_remaining",
    "am i losing weight": "progress",
    "suggest a vegan lunch": "meal_suggestion",
    "whats my bmi": "calorie_target",
}


def evaluate_meals():
    meals = json.loads((SEED_DIR / "meals.json").read_text(encoding="utf-8"))
    for i, m in enumerate(meals, start=1):
        m["id"] = i
    by_id = {m["id"]: m for m in meals}
    model = MealRecommender(meals)
    scenarios, violations, gaps = 0, 0, []
    for diet in DIETS:
        for allergies in ALLERGY_SETS:
            for goal in GOALS:
                targets = calculate_targets(weight_kg=70, height_cm=170, age=25, gender="male",
                                            activity_level="lightly_active", fitness_goal=goal).to_dict()
                slots = slot_targets(targets, {})
                for slot in MEAL_TYPES:
                    scenarios += 1
                    ranked = model.rank(profile={"dietary_preference": diet, "allergies": allergies,
                                                 "fitness_goal": goal},
                                        targets=targets, meal_type=slot, slot_target=slots[slot])
                    if not ranked:
                        continue
                    top = ranked[0]
                    if not is_compatible(by_id[top["id"]], diet, allergies):
                        violations += 1
                    gaps.append(abs(top["calories"] - slots[slot]["calories"]) / slots[slot]["calories"])
    gaps = np.array(gaps)
    return {
        "scenarios": scenarios,
        "with_a_recommendation": len(gaps),
        "diet_or_allergy_violations": violations,
        "median_calorie_gap_pct": round(float(np.median(gaps)) * 100, 1),
        "within_15pct_of_target_pct": round(float(np.mean(gaps <= 0.15)) * 100),
    }


def evaluate_assistant():
    assistant = ChatAssistant()
    texts, labels = [], []
    for intent, examples in TRAINING_DATA.items():
        texts += examples
        labels += [intent] * len(examples)
    cv = cross_val_score(assistant.model, texts, labels, cv=StratifiedKFold(5, shuffle=True, random_state=1))
    correct = sum(assistant.classify(q)[0] == intent for q, intent in UNSEEN_QUESTIONS.items())
    return {
        "training_examples": len(texts),
        "intents": len(TRAINING_DATA),
        "cv_accuracy_mean": round(float(cv.mean()), 2),
        "cv_accuracy_std": round(float(cv.std()), 2),
        "unseen_misspelt_correct": f"{correct} / {len(UNSEEN_QUESTIONS)}",
    }


def evaluate_clustering():
    model = behavior_clustering.train()
    data = behavior_clustering._synthetic_population()
    labels = model["kmeans"].labels_[: len(data)]
    return {"points": len(data), "clusters": 4,
            "silhouette": round(float(silhouette_score(model["scaler"].transform(data), labels)), 2)}


def main():
    sections = [
        ("Meal recommender (content-based filtering)", evaluate_meals()),
        ("Assistant intent classifier (TF-IDF + logistic regression)", evaluate_assistant()),
        ("Behaviour clustering (K-Means)", evaluate_clustering()),
    ]
    for title, results in sections:
        print(f"\n{title}")
        for key, value in results.items():
            print(f"  {key.replace('_', ' '):32} {value}")


if __name__ == "__main__":
    main()
