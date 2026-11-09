"""
AI FITNESS ASSISTANT: intent classification (machine learning) +
                       data-driven response templates

1. Safety rules run first: questions about diseases, medicines, injuries
   or symptoms get a polite "please see a professional" reply.
2. A TF-IDF (character n-grams) + Logistic Regression classifier predicts
   the user's intent from a small labelled set of example questions.
   Character n-grams make it tolerant of typos ("protien", "dinnr").
3. Simple extractors pull out entities: meal slot, calorie number,
   diet override (vegetarian / vegan), "high protein", and ingredients the
   user doesn't have or want ("I don't have peanut butter", "no eggs").
   A small conversation context (last meal slot, ingredients to avoid,
   meals already suggested) is sent back with each reply, so follow-ups
   like "I don't have peanut butter" or "something else" refine the
   previous suggestion instead of repeating it.
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

# "I don't have peanut butter", "no eggs", "without oats", "ran out of milk", "I don't like the smoothie"
AVOID_PATTERN = re.compile(
    r"(?:\b(?:i\s+)?(?:don'?t|do\s+not|didn'?t|can'?t|cannot)\s+(?:have|like|want|eat|get|find|stand|use)"
    r"|\bnot\s+a\s+fan\s+of|\b(?:ran|run|i'?m|am)\s+out\s+of|\bout\s+of|\ballergic\s+to"
    r"|\bwithout|\binstead\s+of|\bexcept|\bskip|\bavoid|\bhate|\bno)\s+(?P<what>[a-z][a-z '-]*)",
    re.I,
)
AVOID_STOP = re.compile(
    r"\s*(?:\b(?:so|what|which|can|could|should|please|for|today|tonight|right now|now|at home|anymore|any more|"
    r"in the house|instead|then|is|are|suggest|give|another|else|either|too|also|either way|left|with me)\b.*)$", re.I)
NOT_FOOD = {"thanks", "thank you", "problem", "worries", "idea", "time", "money", "way", "clue", "one", "it", "that",
            "this", "more", "much", "need", "longer", "meal", "food", "breakfast", "lunch", "dinner", "snack",
            "snacks", "calories", "kcal", "protein", "workout", "gym"}
OTHER_PATTERN = re.compile(
    r"\b(something else|anything else|another|other (?:option|options|meal|one|idea)|different|"
    r"show me more|more options|not that|next one|try again)\b", re.I)
ARTICLE = re.compile(r"^(?:any|a|an|the|some|my|more|no|without)\s+", re.I)

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

        prev = ctx.get("context") or {}
        avoid = self.extract_avoided(text)
        wants_other = bool(OTHER_PATTERN.search(text))
        intent, confidence = self.classify(text)

        # Follow-ups about food ("I don't have peanut butter", "something else") refine the last meal idea
        food_followup = (avoid or wants_other) and (
            prev.get("intent") in ("meal_suggestion", "calories_remaining")
            or intent in ("meal_suggestion", "calories_remaining"))
        if food_followup:
            if intent != "calories_remaining" or prev.get("intent") == "meal_suggestion":
                intent = "meal_suggestion"
            confidence = max(confidence, 0.5)
        elif confidence < 0.25:
            return self._out(
                "I can help with meals, calories, protein, water and workouts. "
                "Try one of the questions below.", "unknown", confidence, prev)

        if intent == "meal_suggestion":
            reply, context = self._handle_meal_suggestion(text, ctx, prev, avoid, wants_other)
            return self._out(reply, intent, confidence, context)
        if intent == "calories_remaining":
            reply, context = self._handle_calories_remaining(text, ctx, prev, avoid)
            return self._out(reply, intent, confidence, context)
        handler = getattr(self, f"_handle_{intent}")
        # Keep remembered ingredients for later food questions
        return self._out(handler(text, ctx), intent, confidence,
                         {"intent": intent, "avoid": prev.get("avoid", [])})

    @staticmethod
    def _out(reply, intent, confidence, context=None):
        return {"reply": reply, "intent": intent, "confidence": round(confidence, 2),
                "quick_replies": QUICK_REPLIES, "context": context or {}}

    # ------------------------------------------------------------------
    @staticmethod
    def extract_avoided(text: str) -> list[str]:
        """Ingredients the user says they don't have or don't want."""
        found = []
        for m in AVOID_PATTERN.finditer(text.lower().replace("\u2019", "'")):
            chunk = AVOID_STOP.sub("", m.group("what"))
            for part in re.split(r"\s*(?:,|\band\b|\bor\b|\bnor\b|&)\s*", chunk):
                part = ARTICLE.sub("", part.strip(" '-"))
                part = ARTICLE.sub("", part)
                words = part.split()
                if not words or len(words) > 3 or part in NOT_FOOD or words[0] in ("to", "go", "be", "do"):
                    continue
                if part not in found:
                    found.append(part)
        return found

    @staticmethod
    def _matches(term: str, text: str) -> bool:
        """Whole-word match that also accepts simple plurals (egg / eggs, tomato / tomatoes)."""
        stem = re.sub(r"(?:es|s)$", "", term) if len(term) > 3 else term
        return re.search(rf"\b{re.escape(stem)}(?:s|es)?\b", text) is not None

    def _uses_any(self, meal: dict, terms: list[str]) -> list[str]:
        haystack = (meal["name"] + " " + " ".join(meal.get("ingredients") or [])).lower()
        return [t for t in terms if self._matches(t, haystack)]

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
        return (f"**{m['name']}**: {m['calories']} kcal, {m['protein']} g protein, "
                f"{m['carbs']} g carbs, {m['fat']} g fat"
                + (f" ({m['portion']}× portion)" if m["portion"] != 1 else ""))

    def _handle_meal_suggestion(self, text, ctx, prev=None, new_avoid=(), wants_other=False):
        prev = prev or {}
        followup = prev.get("intent") == "meal_suggestion"
        explicit_slot = SLOT_PATTERN.search(text)
        slot = self._slot(text, ctx) if explicit_slot or not followup or not prev.get("slot") else prev["slot"]
        same_slot = followup and slot == prev.get("slot")

        overrides = {**(prev.get("overrides") or {}), **self._overrides(text)} if followup else self._overrides(text)
        avoid = list(dict.fromkeys([*(prev.get("avoid") or []), *new_avoid]))
        shown = list(prev.get("shown") or []) if same_slot else []

        all_meals = ctx["recommend_meals"](slot, overrides)
        if not all_meals:
            return (f"I couldn't find a {slot} option that fits your diet and allergy settings.",
                    {"intent": "meal_suggestion", "slot": slot, "avoid": avoid, "overrides": overrides})

        meals = [m for m in all_meals if not self._uses_any(m, avoid)]
        lines = []
        if new_avoid:
            used = [t for t in new_avoid if any(self._uses_any(m, [t]) for m in all_meals)]
            unused = [t for t in new_avoid if t not in used]
            if used:
                lines.append(f"No {self._join(used)}, got it. I'll leave out meals that use it.")
            if unused:
                lines.append(f"None of my {slot} ideas use {self._join(unused)}, so nothing changes there.")
        if not meals:
            lines.append(f"Every {slot} idea I have uses {self._join(avoid)}. "
                         "Try asking for a different meal, or tell me what you do have.")
            return ("\n".join(lines), {"intent": "meal_suggestion", "slot": slot, "avoid": avoid,
                                       "overrides": overrides, "shown": shown})

        # "Something else" (or a follow-up that removed the last pick): skip meals already suggested
        if wants_other or (same_slot and not new_avoid):
            fresh = [m for m in meals if m["id"] not in shown]
            if not fresh:
                lines.append(f"That's every {slot} idea that fits, so here they are again from the top.")
                shown, fresh = [], meals
            meals = fresh

        if overrides.get("high_protein"):
            meals = sorted(meals[:8], key=lambda m: m["protein"] / max(m["calories"], 1), reverse=True)
        # A new "I don't have X" keeps the current pick when it doesn't need X
        if new_avoid and same_slot and shown:
            current = next((m for m in meals if m["id"] == shown[-1]), None)
            if current:
                meals = [current] + [m for m in meals if m["id"] != current["id"]]
        top = meals[0]
        lines += [f"For {slot}, I suggest {self._format_meal(top)}.",
                  f"Ingredients: {', '.join(top['ingredients'])}.",
                  f"Why: {top['reasons'][0].lower()}."]
        if len(meals) > 1:
            lines.append("Other options: " + "; ".join(m["name"] for m in meals[1:3]) + ".")
        r = ctx["remaining"]
        lines.append(f"You have {r['calories']} kcal and {r['protein']} g protein left for today.")
        context = {"intent": "meal_suggestion", "slot": slot, "avoid": avoid, "overrides": overrides,
                   "shown": [*[i for i in shown if i != top["id"]], top["id"]]}
        return "\n".join(lines), context

    @staticmethod
    def _join(items: list[str]) -> str:
        items = list(items)
        return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " or " + items[-1]

    def _handle_calories_remaining(self, text, ctx, prev=None, new_avoid=()):
        prev = prev or {}
        avoid = list(dict.fromkeys([*(prev.get("avoid") or []), *new_avoid]))
        context = {"intent": "calories_remaining", "avoid": avoid}
        r, c, t = ctx["remaining"], ctx["consumed"], ctx["targets"]
        m = NUMBER_PATTERN.search(text)
        budget = int(m.group(1)) if m and 50 <= int(m.group(1)) <= 3000 else r["calories"]
        lines = [f"Today you've eaten {c['calories']} of {t['daily_calories']} kcal "
                 f"({c['protein']} g protein)."]
        if r["calories"] <= 0:
            lines.append("You've reached your calorie target. If you're hungry, choose something light "
                         "like cucumber, a clear soup or buttermilk.")
            return "\n".join(lines), context
        foods = [f for f in ctx["foods_within"](budget)
                 if not any(self._matches(a, f["name"].lower()) for a in avoid)]
        lines.append(f"With about {budget} kcal, protein-friendly choices are:")
        for f in foods[:4]:
            lines.append(f"• {f['name']} ({f['serving']}): {f['calories']} kcal, {f['protein']} g protein")
        return "\n".join(lines), context

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
            return "Today is a rest day in your plan. A 20 to 30 minute walk or light stretching is a good choice."
        lines = [f"Today's session: **{w['title']}** (about {w['estimated_minutes']} min)."]
        for e in w["exercises"][:6]:
            lines.append(f"• {e['name']}: {e['sets']} × {e['reps']}, rest {e['rest_seconds']} s")
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
