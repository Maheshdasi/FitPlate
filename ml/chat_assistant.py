"""
AI FITNESS ASSISTANT — intent classification (machine learning) +
                       data-driven response templates

1. Safety rules run first: questions about diseases, medicines, injuries
   or symptoms get a polite "please see a professional" reply.
2. A TF-IDF (character n-grams) + Logistic Regression classifier predicts
   the user's intent from a small labelled set of example questions.
   Character n-grams make it tolerant of typos ("protien", "dinnr").
3. Simple extractors pull out entities: meal slot, calorie number,
   diet override (vegetarian / vegan), "high protein".
4. The answer is built from the user's own data: profile, today's food
   log, remaining calories and the meal / workout recommenders.

It runs fully offline, so the demo works without any paid API key.
"""

from __future__ import annotations

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

TRAINING_DATA = {
    "meal_suggestion": [
        "what should i eat for dinner", "suggest a breakfast", "what can i have for lunch",
        "give me a meal idea", "suggest a high protein vegetarian breakfast", "healthy snack ideas",
        "what to eat tonight", "recommend a vegan lunch", "dinner ideas please", "what should i cook",
        "suggest an evening snack", "high protein breakfast", "meal for muscle gain",
        "what is a good post workout meal", "suggest food for weight loss", "breakfast options",
    ],
    "calories_remaining": [
        "i have 500 calories remaining what can i eat", "how many calories do i have left",
        "calories left today", "what can i eat with 300 kcal", "remaining calories",
        "how much more can i eat today", "i have 400 kcal left", "am i over my calories",
        "how many calories have i eaten", "did i eat too much today",
    ],
    "protein_query": [
        "how much protein do i need today", "how much protein should i eat", "protein target",
        "how much protein is left", "am i getting enough protein", "protein remaining",
        "how many grams of protein", "protein goal for today", "did i hit my protein",
    ],
    "workout_today": [
        "what workout should i do today", "today's workout", "what exercise today",
        "give me a workout", "which muscles should i train today", "workout plan for today",
        "what should i train", "suggest exercises", "gym plan today", "home workout today",
    ],
    "calorie_target": [
        "how many calories should i eat", "what is my calorie target", "what is my bmi",
        "what is my tdee", "daily calorie requirement", "how is my calorie goal calculated",
        "what is my bmr", "maintenance calories", "macro targets",
    ],
    "progress": [
        "how is my progress", "am i losing weight", "how much weight have i lost",
        "when will i reach my target weight", "weight trend", "how am i doing",
        "show my progress", "am i on track",
    ],
    "water": [
        "how much water should i drink", "water intake today", "how much water have i had",
        "hydration goal", "did i drink enough water",
    ],
    "greeting": ["hi", "hello", "hey there", "good morning", "thanks", "thank you", "who are you", "help"],
}

MEDICAL_PATTERN = re.compile(
    r"\b(diabet\w*|thyroid|pcos|pcod|blood pressure|bp|cholesterol|heart|kidney|liver|cancer|"
    r"medicine|medication|tablet|pill|insulin|steroid|injur\w*|pain|sprain|fracture|symptom\w*|"
    r"diagnos\w*|disease|disorder|pregnan\w*|treat\w*|cure|dose|dosage|surgery|doctor)\b",
    re.IGNORECASE,
)

SLOT_PATTERN = re.compile(r"\b(breakfast|lunch|dinner|snack|snacks|evening|morning|tonight|night)\b", re.I)
NUMBER_PATTERN = re.compile(r"(\d{2,4})\s*(k?cal|calories|calorie)?", re.I)

SAFETY_REPLY = (
    "I can't give medical advice, diagnose conditions or suggest treatments. "
    "For anything related to a health condition, medicine, injury or pain, please talk to a doctor "
    "or a registered dietitian. I'm happy to help with general meal ideas, calorie targets and workouts."
)

QUICK_REPLIES = [
    "What should I eat for dinner?",
    "How much protein do I need today?",
    "What workout should I do today?",
    "How many calories do I have left?",
]


class ChatAssistant:
    def __init__(self):
        texts, labels = [], []
        for intent, examples in TRAINING_DATA.items():
            texts.extend(examples)
            labels.extend([intent] * len(examples))
        self.model = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True),
            LogisticRegression(max_iter=2000, C=8),
        )
        self.model.fit(texts, labels)

    def classify(self, message: str) -> tuple[str, float]:
        probs = self.model.predict_proba([message.lower()])[0]
        best = probs.argmax()
        return self.model.classes_[best], float(probs[best])

    # ------------------------------------------------------------------
    def reply(self, message: str, ctx: dict) -> dict:
        text = message.strip()
        if MEDICAL_PATTERN.search(text):
            return self._out(SAFETY_REPLY, "medical_safety", 1.0)

        intent, confidence = self.classify(text)
        if confidence < 0.25:
            return self._out(
                "I can help with meals, calories, protein, water and workouts. "
                "Try one of the questions below.", "unknown", confidence)

        handler = getattr(self, f"_handle_{intent}")
        return self._out(handler(text, ctx), intent, confidence)

    @staticmethod
    def _out(reply, intent, confidence):
        return {"reply": reply, "intent": intent, "confidence": round(confidence, 2),
                "quick_replies": QUICK_REPLIES}

    # ------------------------------------------------------------------
    @staticmethod
    def _slot(text: str, ctx: dict) -> str:
        m = SLOT_PATTERN.search(text)
        if m:
            word = m.group(1).lower()
            return {"snack": "snacks", "evening": "snacks", "morning": "breakfast",
                    "tonight": "dinner", "night": "dinner"}.get(word, word)
        hour = ctx.get("hour", 12)
        return "breakfast" if hour < 11 else "lunch" if hour < 15 else "snacks" if hour < 18 else "dinner"

    @staticmethod
    def _overrides(text: str) -> dict:
        t = text.lower()
        o = {}
        if "vegan" in t:
            o["dietary_preference"] = "vegan"
        elif "vegetarian" in t or "veg " in t + " ":
            o["dietary_preference"] = "vegetarian"
        if "protein" in t:
            o["high_protein"] = True
        return o

    @staticmethod
    def _format_meal(m: dict) -> str:
        return (f"**{m['name']}** — {m['calories']} kcal, {m['protein']} g protein, "
                f"{m['carbs']} g carbs, {m['fat']} g fat"
                + (f" ({m['portion']}× portion)" if m["portion"] != 1 else ""))

    def _handle_meal_suggestion(self, text, ctx):
        slot = self._slot(text, ctx)
        overrides = self._overrides(text)
        meals = ctx["recommend_meals"](slot, overrides)
        if not meals:
            return f"I couldn't find a {slot} option that fits your diet and allergy settings."
        if overrides.get("high_protein"):
            meals = sorted(meals[:8], key=lambda m: m["protein"] / max(m["calories"], 1), reverse=True)
        top = meals[0]
        lines = [f"For {slot}, I suggest {self._format_meal(top)}.",
                 f"Ingredients: {', '.join(top['ingredients'])}.",
                 f"Why: {top['reasons'][0].lower()}."]
        if len(meals) > 1:
            lines.append("Other options: " + "; ".join(m["name"] for m in meals[1:3]) + ".")
        r = ctx["remaining"]
        lines.append(f"You have {r['calories']} kcal and {r['protein']} g protein left for today.")
        return "\n".join(lines)

    def _handle_calories_remaining(self, text, ctx):
        r, c, t = ctx["remaining"], ctx["consumed"], ctx["targets"]
        m = NUMBER_PATTERN.search(text)
        budget = int(m.group(1)) if m and 50 <= int(m.group(1)) <= 3000 else r["calories"]
        lines = [f"Today you've eaten {c['calories']} of {t['daily_calories']} kcal "
                 f"({c['protein']} g protein)."]
        if r["calories"] <= 0:
            lines.append("You've reached your calorie target. If you're hungry, choose something light "
                         "like cucumber, a clear soup or buttermilk.")
            return "\n".join(lines)
        foods = ctx["foods_within"](budget)
        lines.append(f"With about {budget} kcal, protein-friendly choices are:")
        for f in foods[:4]:
            lines.append(f"• {f['name']} ({f['serving']}) — {f['calories']} kcal, {f['protein']} g protein")
        return "\n".join(lines)

    def _handle_protein_query(self, text, ctx):
        t, c, r = ctx["targets"], ctx["consumed"], ctx["remaining"]
        goal = ctx["profile"]["fitness_goal"].replace("_", " ")
        lines = [f"Your protein target is {t['protein_g']} g per day, based on your weight "
                 f"({t['current_weight']} kg) and your goal ({goal}).",
                 f"So far today you've had {c['protein']} g, so {r['protein']} g is left."]
        if r["protein"] > 20:
            lines.append("Easy ways to add protein: Greek yogurt (≈15 g per 150 g), paneer (≈18 g per 100 g), "
                         "dal (≈9 g per bowl), eggs (≈6 g each), roasted chana (≈10 g per 50 g).")
        return "\n".join(lines)

    def _handle_workout_today(self, text, ctx):
        w = ctx.get("today_workout")
        if not w:
            return "Today is a rest day in your plan. A 20–30 minute walk or light stretching is a good choice."
        lines = [f"Today's session: **{w['title']}** (about {w['estimated_minutes']} min)."]
        for e in w["exercises"][:6]:
            lines.append(f"• {e['name']} — {e['sets']} × {e['reps']}, rest {e['rest_seconds']} s")
        lines.append("Warm up for 5 minutes first, and stop any exercise that causes pain.")
        return "\n".join(lines)

    def _handle_calorie_target(self, text, ctx):
        t = ctx["targets"]
        return (f"Your estimated daily calorie requirement is {t['daily_calories']} kcal.\n"
                f"BMI {t['bmi']} ({t['bmi_category']}), BMR {t['bmr']} kcal, TDEE {t['tdee']} kcal.\n"
                f"Macros: {t['protein_g']} g protein, {t['carbs_g']} g carbs, {t['fat_g']} g fat.\n"
                "These are estimates from the Mifflin-St Jeor formula, not medical advice. "
                "The Calculator page shows each step.")

    def _handle_progress(self, text, ctx):
        p = ctx.get("prediction") or {}
        w = ctx.get("weight") or {}
        lines = []
        if w.get("latest") is not None:
            lines.append(f"Your latest weight is {w['latest']} kg; your target is {w['target']} kg.")
            if w.get("start") is not None:
                diff = round(w["latest"] - w["start"], 1)
                lines.append(f"That's a change of {diff:+} kg since your first entry.")
        if p.get("available"):
            lines.append(f"Your trend is {p['weekly_change_kg']:+} kg per week. If it continues, "
                         f"you'd be about {p['predicted_weight']} kg by {p['prediction_date']}.")
            if p.get("target_eta"):
                lines.append(f"At this pace you could reach your target around {p['target_eta']}.")
        elif p.get("reason"):
            lines.append(p["reason"])
        return "\n".join(lines) or "Log your weight on the Progress page to start tracking."

    def _handle_water(self, text, ctx):
        t = ctx["targets"]
        had = ctx.get("water_today", 0)
        return (f"A general guideline for you is about {t['water_ml'] / 1000:.1f} L a day "
                f"(≈35 ml per kg). Today you've logged {had / 1000:.2f} L. "
                "Drink more on hot days and after workouts.")

    def _handle_greeting(self, text, ctx):
        name = ctx["profile"].get("name", "").split(" ")[0]
        return (f"Hi{(' ' + name) if name else ''}! I'm your fitness assistant. I use your profile and "
                "today's food log to answer questions about meals, calories, protein, water and workouts.")
