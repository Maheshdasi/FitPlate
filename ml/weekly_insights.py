"""
WEEKLY INSIGHTS: Pandas/NumPy data analysis + rule-based suggestions
                  + K-Means behaviour cluster

1. Pandas aggregates the week's daily records (calories, protein, water,
   workouts, food logging).
2. Simple, explainable rules turn the numbers into sentences and
   practical suggestions (no medical claims).
3. The week's behaviour vector is classified with the K-Means model in
   behavior_clustering.py.
"""

from __future__ import annotations

import pandas as pd

from . import behavior_clustering

CALORIE_TOLERANCE = 0.10  # within ±10% counts as "close to target"


def analyse_week(days: list[dict], targets: dict, planned_workouts: int,
                 weight_this_week: float | None, weight_last_week: float | None) -> dict:
    df = pd.DataFrame(days)
    df["logged"] = df["calories"] > 0
    logged = df[df["logged"]]
    logged_days = int(df["logged"].sum())

    cal_target = targets["daily_calories"]
    prot_target = targets["protein_g"]
    water_target = targets["water_ml"]

    within = logged[(logged["calories"] - cal_target).abs() <= cal_target * CALORIE_TOLERANCE]
    over = logged[logged["calories"] > cal_target * (1 + CALORIE_TOLERANCE)]
    under = logged[logged["calories"] < cal_target * (1 - CALORIE_TOLERANCE)]

    avg_cal = float(logged["calories"].mean()) if logged_days else 0.0
    avg_protein = float(logged["protein"].mean()) if logged_days else 0.0
    protein_days = int((logged["protein"] >= prot_target * 0.9).sum())
    avg_water = float(df.loc[df["water_ml"] > 0, "water_ml"].mean()) if (df["water_ml"] > 0).any() else 0.0
    workouts = int(df["workout_done"].sum())
    weight_change = (round(weight_this_week - weight_last_week, 1)
                     if weight_this_week is not None and weight_last_week is not None else None)

    insights, suggestions = [], []

    def add(tone, text):
        insights.append({"tone": tone, "text": text})

    # --- Food logging & calories
    if logged_days == 0:
        add("warn", "No food was logged this week, so calorie insights are not available.")
        suggestions.append("Start by logging just one meal a day. Breakfast is the easiest to remember.")
    else:
        add("good" if len(within) >= 4 else "info",
            f"You stayed close to your calorie target on {len(within)} out of 7 days.")
        if logged_days < 5:
            add("warn", f"Food was logged on {logged_days} of 7 days. Missing days make the averages less accurate.")
            suggestions.append("Set a reminder after dinner to log the day's food.")
        if len(over) >= 3:
            suggestions.append("Calories went over target on several days. Check portion sizes of rice, roti and oils, "
                               "and try fruit or curd as snacks instead of fried items.")
        elif len(under) >= 3:
            suggestions.append("You ate well below your target on several days. Very low intake can leave you tired; "
                               "add a handful of nuts or a glass of milk between meals.")

        # --- Protein
        ratio = avg_protein / prot_target if prot_target else 0
        if ratio < 0.9:
            add("warn", f"Your average protein intake was {round(avg_protein)} g, below your target of {prot_target} g.")
            suggestions.append("Try adding a protein-rich snack in the afternoon (roasted chana, curd, paneer, "
                               "eggs or a sprouts salad) to help you reach your protein target.")
        else:
            add("good", f"Your average protein intake was {round(avg_protein)} g, meeting your target of {prot_target} g.")

    # --- Workouts
    tone = "good" if workouts >= planned_workouts else "info" if workouts > 0 else "warn"
    add(tone, f"You completed {workouts} workout{'s' if workouts != 1 else ''} this week "
              f"(plan: {planned_workouts}).")
    if workouts < planned_workouts:
        missed = planned_workouts - workouts
        suggestions.append(f"You missed {missed} planned workout{'s' if missed > 1 else ''}. "
                           "Schedule them at a fixed time, or do a 20-minute full-body session on busy days.")

    # --- Weight
    if weight_change is not None:
        direction = "gone down" if weight_change < 0 else "gone up" if weight_change > 0 else "stayed the same"
        text = (f"Your weight has {direction} by {abs(weight_change)} kg compared with last week."
                if weight_change != 0 else "Your weight stayed the same compared with last week.")
        add("info", text)
    else:
        add("info", "Log your weight at least once in two consecutive weeks to see a weekly change.")

    # --- Water
    if avg_water:
        if avg_water < water_target * 0.8:
            add("warn", f"Average water intake was {round(avg_water / 1000, 1)} L, below your goal of "
                        f"{round(water_target / 1000, 1)} L.")
            suggestions.append("Keep a water bottle at your desk and finish one before lunch.")
        else:
            add("good", f"Average water intake was {round(avg_water / 1000, 1)} L. Well done.")

    if not suggestions:
        suggestions.append("Great week. Keep the same routine and review your targets if your weight changes.")

    behaviour = behavior_clustering.classify({
        "calorie_adherence": len(within) / 7,
        "protein_ratio": min((avg_protein / prot_target) if prot_target else 0, 1.2),
        "workout_ratio": min(workouts / max(planned_workouts, 1), 1.0),
        "logging_ratio": logged_days / 7,
    })

    return {
        "metrics": {
            "days_logged": logged_days,
            "days_on_calorie_target": len(within),
            "avg_calories": round(avg_cal),
            "avg_protein": round(avg_protein, 1),
            "protein_target_days": protein_days,
            "workouts_completed": workouts,
            "workouts_planned": planned_workouts,
            "avg_water_ml": round(avg_water),
            "weight_change_kg": weight_change,
        },
        "insights": insights,
        "suggestions": suggestions,
        "behaviour": behaviour,
        "daily": df.drop(columns=["logged"]).to_dict(orient="records"),
    }
