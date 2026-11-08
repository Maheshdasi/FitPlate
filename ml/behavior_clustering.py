"""
USER BEHAVIOUR CLUSTERING: K-Means (machine learning, unsupervised)

Each user-week is described by four numbers between 0 and 1:
  calorie_adherence  share of logged days within ±10% of the calorie target
  protein_ratio      average protein / protein target (capped at 1.2)
  workout_ratio      workouts done / workouts planned (capped at 1)
  logging_ratio      days with any food logged / 7

A college project rarely has hundreds of real users, so the model is
trained on a documented synthetic population (NumPy, fixed seed) built
from four behaviour archetypes, plus any real user-weeks passed in.
Clusters are named afterwards by looking at their centroids, which keeps
the labels explainable.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

FEATURES = ["calorie_adherence", "protein_ratio", "workout_ratio", "logging_ratio"]

CLUSTER_DESCRIPTIONS = {
    "Consistent achiever": "You are on track with both food and training. Keep the routine going.",
    "Nutrition-focused": "Your eating is consistent, but workouts are being missed. Small, short sessions can help.",
    "Workout-focused": "You train regularly, but food tracking or targets are slipping. Plan meals ahead.",
    "Getting started": "You are building the habit. Focus on logging food daily and one or two workouts.",
}

_ARCHETYPES = {
    #                     cal   prot  work  log
    "consistent":        [0.85, 1.00, 0.90, 0.95],
    "nutrition_focused": [0.75, 0.90, 0.30, 0.90],
    "workout_focused":   [0.35, 0.65, 0.90, 0.50],
    "starting":          [0.25, 0.55, 0.25, 0.35],
}

_model: dict | None = None


def _synthetic_population(n_per_group=120, seed=42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rows = []
    for centre in _ARCHETYPES.values():
        pts = rng.normal(loc=centre, scale=0.10, size=(n_per_group, 4))
        rows.append(pts)
    data = np.vstack(rows)
    data[:, 1] = np.clip(data[:, 1], 0, 1.2)
    data[:, [0, 2, 3]] = np.clip(data[:, [0, 2, 3]], 0, 1)
    return data


def _name_clusters(centroids: np.ndarray) -> dict[int, str]:
    nutrition = centroids[:, [0, 1, 3]].mean(axis=1)
    workout = centroids[:, 2]
    names: dict[int, str] = {}
    remaining = set(range(len(centroids)))

    best = max(remaining, key=lambda i: nutrition[i] + workout[i])
    names[best] = "Consistent achiever"; remaining.discard(best)
    worst = min(remaining, key=lambda i: nutrition[i] + workout[i])
    names[worst] = "Getting started"; remaining.discard(worst)
    nut = max(remaining, key=lambda i: nutrition[i] - workout[i])
    names[nut] = "Nutrition-focused"; remaining.discard(nut)
    for i in remaining:
        names[i] = "Workout-focused"
    return names


def train(extra_rows: list[list[float]] | None = None) -> dict:
    global _model
    data = _synthetic_population()
    if extra_rows:
        data = np.vstack([data, np.array(extra_rows)])
    scaler = StandardScaler().fit(data)
    km = KMeans(n_clusters=4, n_init=10, random_state=42).fit(scaler.transform(data))
    centroids = scaler.inverse_transform(km.cluster_centers_)
    _model = {"scaler": scaler, "kmeans": km, "names": _name_clusters(centroids),
              "centroids": centroids}
    return _model


def classify(features: dict) -> dict:
    model = _model or train()
    x = np.array([[features[f] for f in FEATURES]])
    cluster = int(model["kmeans"].predict(model["scaler"].transform(x))[0])
    name = model["names"][cluster]
    return {
        "cluster_id": cluster,
        "label": name,
        "description": CLUSTER_DESCRIPTIONS[name],
        "features": {f: round(float(features[f]), 2) for f in FEATURES},
    }
