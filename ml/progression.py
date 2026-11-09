"""
PROGRESSIVE OVERLOAD: set-by-set logging, personal records and next-session targets

Inspired by how workout loggers such as Hevy and Boostcamp coach progression:

* Each exercise is logged as sets. Weighted lifts store kg and reps, bodyweight moves store reps,
  timed holds store seconds and cardio stores minutes.
* Strength is compared with the Epley estimated one-rep max: e1RM = weight x (1 + reps / 30),
  so 60 kg x 10 and 70 kg x 5 can be compared fairly. A set that beats the best e1RM so far is a
  personal record (PR).
* Double progression decides the next target (rule-based):
    - every planned set reached the top of the rep range  -> add weight (2.5 kg, or 5 kg for legs)
    - every set reached the bottom of the range           -> same weight, aim for one more rep
    - several sets fell well short                         -> drop about 10% and rebuild
  Bodyweight moves add reps, timed holds add 5 seconds and cardio adds 2 minutes (up to about double
  the planned time, then the pace goes up instead).
"""

from __future__ import annotations

import re

LOWER_BODY = {"legs", "full_body"}


def exercise_kind(ex: dict) -> str:
    """'weighted', 'reps' (bodyweight), 'timed' (seconds) or 'cardio' (minutes)."""
    if ex.get("category") == "cardio":
        return "cardio"
    if "sec" in str(ex.get("reps", "")):
        return "timed"
    if ex.get("equipment") == "bodyweight":
        return "reps"
    return "weighted"


def parse_range(text) -> tuple[int, int]:
    """'8-12' -> (8, 12); '30-45 sec' -> (30, 45); '10 min' -> (10, 10); 12 -> (12, 12)."""
    nums = [int(n) for n in re.findall(r"\d+", str(text))]
    if not nums:
        return 10, 10
    return nums[0], nums[1] if len(nums) > 1 else nums[0]


def e1rm(weight_kg, reps) -> float:
    """Epley estimated one-rep max. 0 when there is no weight or no reps."""
    if not weight_kg or not reps or weight_kg <= 0 or reps <= 0:
        return 0.0
    return round(weight_kg * (1 + reps / 30), 1) if reps > 1 else float(weight_kg)


def done_sets(sets) -> list[dict]:
    return [s for s in (sets or []) if s.get("done")]


def set_score(kind: str, s: dict) -> float:
    """One number per set for comparing performances of the same exercise."""
    if kind == "weighted":
        return e1rm(s.get("weight_kg"), s.get("reps"))
    if kind == "reps":
        return float(s.get("reps") or 0) + (s.get("weight_kg") or 0)  # extra load counts too
    return float(s.get("seconds") or 0)


def volume(sets) -> float:
    """Total kg lifted: weight x reps over completed sets."""
    return round(sum((s.get("weight_kg") or 0) * (s.get("reps") or 0) for s in done_sets(sets)), 1)


def _round_to(x: float, step: float) -> float:
    return round(round(x / step) * step, 2)


def suggest(ex: dict, last_sets: list[dict] | None) -> dict:
    """Target for the next session from the last one: {text, weight_kg, reps, seconds, minutes}."""
    kind = exercise_kind(ex)
    lo, hi = parse_range(ex.get("reps"))
    planned = int(ex.get("sets") or 1)
    last = done_sets(last_sets)
    out = {"kind": kind, "weight_kg": None, "reps": None, "seconds": None, "minutes": None}

    if kind == "cardio":
        mins = max((s.get("seconds") or 0) for s in last) // 60 if last else 0
        if not mins:
            return {**out, "minutes": lo, "text": f"Aim for {lo} minutes at a pace where you can still talk."}
        cap = max(lo * 2, lo + 10)
        if mins >= cap:
            return {**out, "minutes": cap, "text": f"Last time {mins} min. Keep it at {cap} minutes and push the "
                                                   "pace or incline a little instead."}
        nxt = min(mins + 2, cap) if mins >= lo else lo
        return {**out, "minutes": nxt, "text": f"Last time {mins} min. Try {nxt} minutes today."}

    if kind == "timed":
        secs = min((s.get("seconds") or 0) for s in last) if last else 0
        if not secs:
            return {**out, "seconds": lo, "text": f"Hold each set for {lo} to {hi} seconds with good form."}
        nxt = secs + 5 if secs >= hi and len(last) >= planned else max(secs, lo)
        why = "You held the full time on every set." if nxt > secs else "Build up to the full time on every set."
        return {**out, "seconds": nxt, "text": f"{why} Aim for {nxt} seconds."}

    if kind == "reps":
        reps = [s.get("reps") or 0 for s in last]
        if not reps:
            return {**out, "reps": hi, "text": f"Do {planned} sets of {lo} to {hi} reps with slow, controlled form."}
        if len(reps) >= planned and min(reps) >= hi:
            nxt = hi + 2
            return {**out, "reps": nxt, "text": f"You hit {hi} reps on every set. Aim for {nxt}, or slow the lowering "
                                               "to 3 seconds to make it harder."}
        nxt = min(max(reps) + 1, hi + 2)
        return {**out, "reps": nxt, "text": f"Last best {max(reps)} reps. Aim for {nxt} on each set."}

    # weighted: double progression
    weighted = [s for s in last if s.get("weight_kg")]
    if not weighted:
        return {**out, "reps": hi, "text": f"First time: pick a weight you can lift for {lo} to {hi} reps with "
                                           "2 reps left in the tank."}
    w = max(s["weight_kg"] for s in weighted)
    top = [s.get("reps") or 0 for s in weighted if s["weight_kg"] == w]
    step = 5.0 if ex.get("category") in LOWER_BODY and w >= 40 else 2.5
    if len(weighted) >= planned and min(top) >= hi:
        nw = _round_to(w + step, 0.5)
        return {**out, "weight_kg": nw, "reps": lo,
                "text": f"You hit {hi} reps on every set at {w:g} kg. Go up to {nw:g} kg for {lo} to {hi} reps."}
    if min(top) >= lo:
        return {**out, "weight_kg": w, "reps": min(max(top) + 1, hi),
                "text": f"Stay at {w:g} kg and add a rep per set until you reach {hi}."}
    if sum(1 for r in top if r < lo - 2) >= 2:
        nw = _round_to(w * 0.9, 2.5)
        return {**out, "weight_kg": nw, "reps": hi,
                "text": f"{w:g} kg was heavy last time. Drop to {nw:g} kg and build back up."}
    return {**out, "weight_kg": w, "reps": lo, "text": f"Stay at {w:g} kg and aim for at least {lo} reps per set."}


def mark_records(kind: str, sets: list[dict], best_before: float) -> list[int]:
    """Indexes of completed sets that beat the previous best, each one raising the bar for the next."""
    records, bar = [], best_before
    if best_before <= 0:
        return records  # the first time an exercise is logged sets a baseline, not a PR
    for i, s in enumerate(sets or []):
        score = set_score(kind, s) if s.get("done") else 0
        if score > bar:
            records.append(i)
            bar = score
    return records
