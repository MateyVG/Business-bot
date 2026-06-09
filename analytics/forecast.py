"""Прогнозни продажби по работен ден.

Започваме с прост линеен тренд — надежден при малко данни.
По-късно лесно минаваме към ARIMA/Prophet при повече история.
"""
import datetime as dt

import numpy as np
import pandas as pd

from analytics.metrics import revenue_by_business_day


def forecast_revenue(df: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    """Прогнозира оборота за следващите `days` работни дни.

    Връща DataFrame с колони: business_date, revenue, kind ('actual'|'forecast').
    """
    hist = revenue_by_business_day(df).copy()
    hist["kind"] = "actual"
    if len(hist) < 3:
        return hist

    y = hist["revenue"].to_numpy(dtype=float)
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(y), len(y) + days)
    future_y = np.clip(slope * future_x + intercept, 0, None)

    last_day = pd.to_datetime(hist["business_date"].iloc[-1])
    future_days = [(last_day + dt.timedelta(days=i + 1)).date() for i in range(days)]

    fc = pd.DataFrame(
        {"business_date": future_days, "revenue": future_y, "kind": "forecast"}
    )
    return pd.concat([hist, fc], ignore_index=True)
