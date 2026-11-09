"""Household and metric units for logging food.

Every food can be logged by its own serving, in grams or in ounces. On top of that each food gets the
units that make sense for it: ml / tsp / tbsp / cup / glass for drinks and oils, katori and cup for dal,
curries and other bowl foods, tbsp / tsp for spreads and seeds, and pieces for things like idli.

Each unit is stored as its weight in grams for that food, so any amount converts to a number of servings:
servings = amount x grams_per_unit / serving_g.
"""

from __future__ import annotations

OZ_G = 28.35
KATORI_G = 150   # a standard Indian katori holds about 150 ml
CUP_ML = 240
GLASS_ML = 250
TBSP_ML = 15
TSP_ML = 5

# Drinks and other liquids: name -> density in g per ml
LIQUIDS = {
    "Toned milk": 1.03, "Buttermilk (chaas)": 1.0, "Masala chai (with sugar)": 1.0,
    "Black coffee": 1.0, "Coconut water": 1.0,
}
# Liquids used by the spoon, not the glass
SPOON_LIQUIDS = {"Ghee": 0.91, "Olive oil": 0.92, "Honey": 1.42}

# Foods eaten from a bowl or plate: name -> grams in one cup
BOWL_FOODS = {
    "White rice (cooked)": 150, "Brown rice (cooked)": 150, "Quinoa (cooked)": 185, "Poha (cooked)": 160,
    "Upma": 200, "Vegetable khichdi": 220, "Vegetable biryani": 170, "Chicken biryani": 180,
    "Dal (toor / arhar)": 230, "Moong dal": 230, "Rajma curry": 230, "Chole (chickpea curry)": 230,
    "Sambar": 230, "Sprouts salad": 100, "Boiled chickpeas": 150,
    "Curd (dahi)": 245, "Greek yogurt (low fat)": 245,
    "Chicken curry": 230, "Fish curry": 230, "Mutton curry": 230,
    "Mixed vegetable curry": 200, "Palak sabzi": 200, "Bhindi sabzi": 180, "Aloo sabzi": 200,
    "Cucumber salad": 120, "Mixed green salad": 100, "Broccoli (steamed)": 90,
    "Papaya": 145, "Mango": 165, "Watermelon": 150, "Pomegranate": 174,
}
# Spoonable foods: name -> grams in one tablespoon
SPOONABLE = {
    "Peanut butter": 16, "Chia seeds": 12, "Flax seeds": 10, "Coconut chutney": 15, "Hummus": 15,
    "Rolled oats (dry)": 5, "Roasted chana": 9, "Almonds": 9, "Walnuts": 8, "Cashews": 9,
    "Peanuts (roasted)": 9, "Curd (dahi)": 15, "Greek yogurt (low fat)": 15, "Ghee": 13.7,
    "Olive oil": 13.8, "Honey": 21, "Whey protein": 8,
}
# Extra cup sizes for dry foods
DRY_CUPS = {"Rolled oats (dry)": 80, "Makhana (roasted)": 30, "Paneer": 130, "Tofu (firm)": 250,
            "Soya chunks (dry)": 50, "Almonds": 140, "Peanuts (roasted)": 145, "Cashews": 130}
# Foods counted in pieces: name -> grams per piece
PIECES = {"Idli": 40, "Dhokla": 50, "Dark chocolate (70%)": 10, "Roti / chapati (whole wheat)": 40,
          "Paratha (plain)": 60, "Boiled egg": 50, "Egg white": 33, "Samosa": 100,
          "Whole wheat bread": 30, "Cheese slice": 20, "Almonds": 1.2, "Cashews": 1.6, "Walnuts": 4}
PIECE_LABELS = {"Whole wheat bread": "slice", "Cheese slice": "slice", "Dark chocolate (70%)": "square",
                "Almonds": "nut", "Cashews": "nut", "Walnuts": "half"}


def _unit(key: str, label: str, grams: float, step: float = 1) -> dict:
    return {"key": key, "label": label, "grams": round(grams, 2), "step": step}


def units_for(name: str, serving_desc: str, serving_g: float) -> list[dict]:
    """Units a food can be logged in, most natural first. The first one is the default."""
    units = [_unit("serving", f"serving: {serving_desc}", serving_g, 0.25)]
    if name in LIQUIDS:
        d = LIQUIDS[name]
        units += [_unit("ml", "ml", d, 10), _unit("glass", f"glass ({GLASS_ML} ml)", GLASS_ML * d, 0.25),
                  _unit("cup", f"cup ({CUP_ML} ml)", CUP_ML * d, 0.25),
                  _unit("tbsp", "tbsp", TBSP_ML * d), _unit("tsp", "tsp", TSP_ML * d)]
    elif name in SPOON_LIQUIDS:
        d = SPOON_LIQUIDS[name]
        units += [_unit("tsp", "tsp", TSP_ML * d), _unit("tbsp", "tbsp", TBSP_ML * d),
                  _unit("ml", "ml", d, 5)]
    else:
        if name in PIECES:
            label = PIECE_LABELS.get(name, "piece")
            units.append(_unit("piece", label, PIECES[name]))
        if name in BOWL_FOODS:
            units += [_unit("katori", f"katori ({KATORI_G} ml)", KATORI_G * BOWL_FOODS[name] / CUP_ML, 0.25),
                      _unit("cup", "cup", BOWL_FOODS[name], 0.25)]
        elif name in DRY_CUPS:
            units.append(_unit("cup", "cup", DRY_CUPS[name], 0.25))
        if name in SPOONABLE:
            units += [_unit("tbsp", "tbsp", SPOONABLE[name]), _unit("tsp", "tsp", SPOONABLE[name] / 3)]
    units += [_unit("g", "g", 1, 5), _unit("oz", "oz", OZ_G, 0.5)]
    return units


def unit_by_key(name: str, serving_desc: str, serving_g: float, key: str) -> dict | None:
    return next((u for u in units_for(name, serving_desc, serving_g) if u["key"] == key), None)


def amount_text(amount: float, unit: dict) -> str:
    """Readable amount for the log, e.g. '2 katori (150 ml)', '150 g', '1.5 × 1 cup'."""
    n = f"{amount:g}"
    if unit["key"] == "serving":
        return f"{n} × {unit['label'].removeprefix('serving: ')}"
    if unit["key"] in ("g", "ml", "oz", "tsp", "tbsp", "katori"):
        label = unit["label"]
    else:
        base, _, extra = unit["label"].partition(" (")
        if amount == 1:
            plural = base
        elif base == "half":
            plural = "halves"
        else:
            plural = base + ("es" if base.endswith(("ch", "sh", "ss")) else "s")
        label = plural + (f" ({extra}" if extra else "")
    return f"{n} {label}"
