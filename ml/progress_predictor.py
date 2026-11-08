"""
WEIGHT TREND PREDICTION — Linear Regression (machine learning, supervised)

Fits weight = a + b * day on the user's recent weight logs.
  * b * 7          -> average weekly change (kg/week)
  * prediction     -> expected weight in 4 weeks if the trend continues
  * R²             -> how steady the trend is (shown as confidence)
The prediction is only a trend line, not a promise, and is hidden when
there is too little data.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from sklearn.linear_model import LinearRegression

MIN_POINTS = 4
MIN_SPAN_DAYS = 7


def predict_weight(logs: list[tuple[date, float]], target_weight: float | None,
                   horizon_days: int = 28, window_days: int = 60) -> dict:
    if not logs:
        return {"available": False, "reason": "No weight entries yet."}

    logs = sorted(logs)
    last_day = logs[-1][0]
    recent = [(d, w) for d, w in logs if (last_day - d).days <= window_days]
    span = (recent[-1][0] - recent[0][0]).days
    if len(recent) < MIN_POINTS or span < MIN_SPAN_DAYS:
        return {"available": False,
                "reason": f"Log your weight at least {MIN_POINTS} times over {MIN_SPAN_DAYS}+ days to see a trend."}

    start = recent[0][0]
    X = np.array([(d - start).days for d, _ in recent]).reshape(-1, 1)
    y = np.array([w for _, w in recent])
    model = LinearRegression().fit(X, y)

    slope = float(model.coef_[0])
    current_fit = float(model.predict([[X[-1][0]]])[0])
    future_x = X[-1][0] + horizon_days
    predicted = float(model.predict([[future_x]])[0])
    r2 = float(model.score(X, y)) if len(set(y)) > 1 else 1.0

    eta = None
    if target_weight is not None and abs(slope) > 0.005:
        remaining = target_weight - current_fit
        if remaining * slope > 0:  # moving toward the target
            days_needed = remaining / slope
            if days_needed <= 730:
                eta = (last_day + timedelta(days=int(days_needed))).isoformat()

    trend_line = [
        {"date": (start + timedelta(days=int(x))).isoformat(),
         "weight": round(float(model.predict([[x]])[0]), 2)}
        for x in [0, X[-1][0], future_x]
    ]

    return {
        "available": True,
        "weekly_change_kg": round(slope * 7, 2),
        "predicted_weight": round(predicted, 1),
        "prediction_date": (last_day + timedelta(days=horizon_days)).isoformat(),
        "target_eta": eta,
        "confidence": "high" if r2 >= 0.7 else "medium" if r2 >= 0.4 else "low",
        "r2": round(r2, 2),
        "trend_line": trend_line,
        "points_used": len(recent),
    }
