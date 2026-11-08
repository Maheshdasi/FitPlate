"""
FORMULA-BASED CALCULATIONS (not machine learning)

Every number here comes from a published, deterministic formula so the
user can see exactly how it was produced.

  BMI   = weight_kg / height_m^2                       (WHO definition)
  BMR   = Mifflin-St Jeor equation (1990)
          male:   10*kg + 6.25*cm - 5*age + 5
          female: 10*kg + 6.25*cm - 5*age - 161
          other:  average of the two constants (-78)
  TDEE  = BMR * activity factor
  Calories = TDEE adjusted for the goal
  Protein  = g per kg of body weight (depends on goal)
  Fat      = 25% of calories (9 kcal / g)
  Carbs    = remaining calories (4 kcal / g)
"""

from dataclasses import asdict, dataclass

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
}

ACTIVITY_LABELS = {
    "sedentary": "sedentary, little or no exercise",
    "lightly_active": "lightly active, exercise 1-3 days a week",
    "moderately_active": "moderately active, exercise 3-5 days a week",
    "very_active": "very active, hard exercise 6-7 days a week",
}

# Calorie change applied to TDEE for each goal
GOAL_CALORIE_ADJUSTMENT = {
    "weight_loss": -0.20,
    "weight_gain": 0.15,
    "muscle_gain": 0.10,
    "maintenance": 0.0,
    "general_fitness": 0.0,
}

# Protein in grams per kg of body weight
GOAL_PROTEIN_PER_KG = {
    "weight_loss": 1.8,
    "weight_gain": 1.6,
    "muscle_gain": 2.0,
    "maintenance": 1.4,
    "general_fitness": 1.4,
}

FAT_SHARE = 0.25
MIN_CALORIES = {"male": 1500, "female": 1200, "other": 1350}


@dataclass
class NutritionTargets:
    bmi: float
    bmi_category: str
    bmr: int
    tdee: int
    daily_calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    water_ml: int
    current_weight: float
    target_weight: float
    explanation: list

    def to_dict(self):
        return asdict(self)


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float) -> str:
    # WHO adult cut-offs
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    constant = {"male": 5, "female": -161}.get(gender, -78)
    return base + constant


def calculate_targets(*, weight_kg, height_cm, age, gender, activity_level,
                      fitness_goal, target_weight_kg=None) -> NutritionTargets:
    bmi = calculate_bmi(weight_kg, height_cm)
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    factor = ACTIVITY_FACTORS[activity_level]
    tdee = bmr * factor

    adjustment = GOAL_CALORIE_ADJUSTMENT[fitness_goal]
    calories = tdee * (1 + adjustment)
    floor = MIN_CALORIES.get(gender, 1350)
    floored = calories < floor
    calories = max(calories, floor)

    protein_per_kg = GOAL_PROTEIN_PER_KG[fitness_goal]
    protein_g = weight_kg * protein_per_kg
    fat_g = calories * FAT_SHARE / 9
    carbs_kcal = calories - protein_g * 4 - fat_g * 9
    carbs_g = max(carbs_kcal / 4, 50)

    # ~35 ml per kg is a common general hydration guideline
    water_ml = int(round(weight_kg * 35 / 250) * 250)

    goal_text = {
        -0.20: "reduced by 20% to create a moderate calorie deficit",
        0.15: "increased by 15% to support gradual weight gain",
        0.10: "increased by 10% to support muscle building",
        0.0: "kept equal to your TDEE to maintain your weight",
    }[adjustment]

    explanation = [
        f"BMI = {weight_kg} kg / ({height_cm / 100:.2f} m)² = {bmi} ({bmi_category(bmi)}).",
        f"BMR (Mifflin-St Jeor) = {round(bmr)} kcal, the energy your body uses at complete rest.",
        f"TDEE = BMR × {factor} ({ACTIVITY_LABELS[activity_level]}) = {round(tdee)} kcal, "
        "your estimated daily energy use.",
        f"Daily calories = TDEE {goal_text} → {round(calories)} kcal.",
        f"Protein = {protein_per_kg} g per kg × {weight_kg} kg = {round(protein_g)} g.",
        f"Fat = 25% of calories ÷ 9 kcal/g = {round(fat_g)} g.",
        f"Carbohydrates = remaining calories ÷ 4 kcal/g = {round(carbs_g)} g.",
    ]
    if floored:
        explanation.append(
            f"Calories were raised to a safe minimum of {floor} kcal for general guidance."
        )

    return NutritionTargets(
        bmi=bmi,
        bmi_category=bmi_category(bmi),
        bmr=round(bmr),
        tdee=round(tdee),
        daily_calories=int(round(calories)),
        protein_g=int(round(protein_g)),
        carbs_g=int(round(carbs_g)),
        fat_g=int(round(fat_g)),
        water_ml=water_ml,
        current_weight=weight_kg,
        target_weight=target_weight_kg if target_weight_kg is not None else weight_kg,
        explanation=explanation,
    )


# Share of daily targets given to each meal slot (rule-based)
MEAL_SPLIT = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.30, "snacks": 0.10}
