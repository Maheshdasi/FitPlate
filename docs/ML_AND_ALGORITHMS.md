# Formulas, rules and machine learning

The project deliberately separates three kinds of logic so nothing rule-based is mislabelled as "AI".
The UI labels each one too (for example the "Formula-based" chip on the calculator and the
"K-Means cluster" chip on insights).

| Part of the app | Type | Technique | Code |
|---|---|---|---|
| BMI, BMR, TDEE, calories, macros, water | **Formula** | WHO BMI, Mifflin-St Jeor, activity factors | `ml/calculations.py` |
| Diet-type and allergy filtering | **Rule** | Hard constraints | `ml/meal_recommender.py` |
| Calorie split across meal slots | **Rule** | Fixed shares of what is left today | `ml/meal_recommender.py` |
| Meal ranking | **ML** | Content-based filtering: TF-IDF + cosine similarity | `ml/meal_recommender.py` |
| Weekly workout split; sets/reps/rest | **Rule** | Strength-training guidelines | `ml/workout_recommender.py` |
| Exercise selection | **ML** | Feature vectors + cosine similarity + MMR | `ml/workout_recommender.py` |
| Weight trend and target date | **ML** | Linear regression | `ml/progress_predictor.py` |
| Habit pattern | **ML** | K-Means clustering (k = 4) | `ml/behavior_clustering.py` |
| Weekly statistics | **Data analysis** | Pandas aggregation | `ml/weekly_insights.py` |
| Weekly suggestions | **Rule** | Threshold rules on the statistics | `ml/weekly_insights.py` |
| Assistant intent | **ML** | TF-IDF (char n-grams) + logistic regression | `ml/chat_assistant.py` |
| Assistant answer | **Rule / template** | Filled with the user's own data | `ml/chat_assistant.py` |
| Medical-question guard | **Rule** | Keyword pattern, checked first | `ml/chat_assistant.py` |

---

## 1. Formula-based calculations

```
BMI      = weight_kg / height_m²
BMR      = 10·weight + 6.25·height_cm − 5·age + s     s = +5 (male), −161 (female), −78 (other)
TDEE     = BMR × activity factor                      1.2 / 1.375 / 1.55 / 1.725
Calories = TDEE × (1 + goal adjustment)               −20% loss, +15% gain, +10% muscle, 0 otherwise
           (never below 1500 male / 1200 female / 1350 other)
Protein  = weight × g/kg                              1.8 loss, 1.6 gain, 2.0 muscle, 1.4 otherwise
Fat      = 25% of calories ÷ 9
Carbs    = (calories − protein·4 − fat·9) ÷ 4
Water    = 35 ml × weight, rounded to 250 ml
```

Worked example (demo user: male, 24 y, 175 cm, 78 kg, moderately active, weight loss):
BMR = 780 + 1093.75 − 120 + 5 = 1759 kcal · TDEE = 1759 × 1.55 = 2726 · Calories = 2726 × 0.8 = 2181 kcal ·
Protein = 1.8 × 78 = 140 g · Fat = 545 ÷ 9 = 61 g · Carbs = (2181 − 560 − 545) ÷ 4 = 269 g.

## 2. Meal recommendation (content-based filtering)

1. **Filter (rules)** — keep meals whose diet type is allowed (vegan ⊂ vegetarian ⊂ eggetarian ⊂ non-vegetarian)
   and that share no allergen with the user.
2. **Slot target (rules)** — remaining calories and protein for the day are divided among meal slots not yet eaten
   in proportion 25 / 35 / 30 / 10 % (breakfast / lunch / dinner / snacks).
3. **Portion scaling** — `portion = clip(round4(target_kcal / meal_kcal), 0.75, 1.5)`.
4. **Scoring** for each candidate *m*:

```
macro_sim   = cosine([4P, 4C, 9F]_m , [4P, 4C, 9F]_target)        energy split similarity
calorie_fit = exp(−3 · |kcal_m − kcal_target| / kcal_target)
text_sim    = cosine(TFIDF(name + ingredients + tags)_m , TFIDF(user profile text))
protein     = clip((protein / kcal × 100) / 10, 0, 1)              halved for weight-gain goal

score = 0.40·macro_sim + 0.30·calorie_fit + 0.20·text_sim + 0.10·protein
```

The user profile text combines goal keywords, the user's stated food preferences and the names of the
ten foods they log most (implicit feedback), so recommendations personalise as the user logs more.

5. **Replace** returns the highest-scoring meal not yet shown for that slot today (exclusions stored in
   `meal_recommendations.excluded_meal_ids`); when all are exhausted it starts again.

## 3. Workout recommendation

**Rules — weekly split**

| Days | Split |
|---|---|
| 2 | Full body × 2 |
| 3 | Full body × 3 (beginner) or Push / Pull / Legs |
| 4 | Upper / Lower × 2 |
| 5 | Push / Pull / Legs / Upper / Cardio-core |
| 6 | Push / Pull / Legs × 2 |

Weight-loss goal adds a cardio finisher to each day. Sets/reps/rest by goal: loss 3×12-15/45 s,
gain 4×8-10/90 s, muscle 4×8-12/75 s, maintenance and general 3×10-12/60 s; beginners do one set fewer.
Users never get exercises above their level; home and bodyweight users get no gym equipment.

**ML — similarity ranking.** Each exercise becomes a 16-dimension vector
`[difficulty one-hot (3) | equipment one-hot (5) | strength, cardio | compound | goal tags (5)]`.
The user is encoded in the same space (level preference weights, equipment weights from workout type,
cardio and compound preference, goal-tag weights). Exercises are ranked by cosine similarity.

**MMR** picks each next exercise with
`0.7·(similarity − 0.15·times_used_this_week) − 0.3·(1 if same target muscle as an already chosen exercise)`,
so sessions are relevant, varied within a day, and rotate across days.

## 4. Weight trend — linear regression

`weight = a + b·day` fitted on entries from the last 60 days (needs ≥ 4 entries over ≥ 7 days).
Reported: weekly change `7b`, the prediction 28 days ahead, R² as confidence (high ≥ 0.7, medium ≥ 0.4),
and the date the target would be reached if the trend continues and is moving toward it (hidden if > 2 years).

## 5. Behaviour clustering — K-Means

Each user-week is a vector `[calorie adherence, protein ratio, workout ratio, logging ratio]` (0–1).
Because a project has few real users, the model is trained on a documented synthetic population
(4 archetypes × 120 points, Gaussian noise σ = 0.10, seed 42) plus any real weeks passed in.
Features are standardised; K-Means with k = 4, n_init = 10. Clusters are **named from their centroids**
(best overall → "Consistent achiever", worst → "Getting started", nutrition > workout → "Nutrition-focused",
remaining → "Workout-focused"), so labels are explainable.

## 6. Weekly insights

Pandas aggregates the seven daily rows; rules then produce sentences, for example:

| Statistic | Rule | Output |
|---|---|---|
| days within ±10% of calorie goal | always | "You stayed close to your calorie target on 5 out of 7 days." |
| average protein < 90% of target | warn | "Your average protein intake was 96 g, below your target of 140 g." + snack suggestion |
| workouts done < planned | suggestion | schedule tip with number missed |
| weekly average weight vs previous week | info | "Your weight has gone down by 0.6 kg compared with last week." |
| ≥ 3 days over / under target | suggestion | portion or snack suggestion |
| average water < 80% goal | warn | water bottle suggestion |

No rule makes medical claims.

## 7. AI assistant

1. **Safety rule first** — a regular expression for conditions, medicines, injuries, symptoms, pregnancy, etc.
   returns a fixed "please consult a doctor or dietitian" reply.
2. **Intent classification** — character 2–4-gram TF-IDF + logistic regression (C = 8) trained on 75 labelled
   example questions across 8 intents. Character n-grams tolerate typos. Below 25% confidence the assistant asks
   the user to rephrase.
3. **Entity extraction** — meal slot (or time of day), calorie numbers ("500 calories"), diet override
   ("vegan", "vegetarian"), "protein".
4. **Answer** — templates filled with the user's targets, today's totals, the meal recommender, the food
   database (highest protein per calorie within the budget), today's workout session and the regression trend.

It runs fully offline, so the demo works without an external API key. Connecting a large language model is
listed under future scope.
