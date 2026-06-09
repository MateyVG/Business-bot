"""Синоптични данни и корелация с оборота.

Ползва Open-Meteo (безплатно, без API ключ):
  * исторически данни (archive-api) за минали дни
  * прогноза (forecast api) за следващите дни

Идея: да виждаш дали при дъжд/жега има повече/по-малко оборот и доставки.
WMO weather_code: 0=ясно, 1-3=облачно, 45-48=мъгла, 51-67=дъжд,
71-77=сняг, 80-99=превалявания/гръмотевици.
"""
import datetime as dt

import numpy as np
import pandas as pd
import requests

import config

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DAILY = "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"


def _fetch(url: str, params: dict) -> pd.DataFrame:
    params = {**params, "daily": DAILY, "timezone": "Europe/Sofia"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    daily = r.json().get("daily", {})
    if not daily:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "day": pd.to_datetime(daily["time"]).date,
            "temp_max": daily["temperature_2m_max"],
            "temp_min": daily["temperature_2m_min"],
            "precipitation": daily["precipitation_sum"],
            "weather_code": daily["weather_code"],
        }
    )


def get_weather(city: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Връща дневно време за град между две дати (история + прогноза)."""
    if city not in config.CITY_COORDS:
        return pd.DataFrame()
    lat, lon = config.CITY_COORDS[city]
    today = dt.date.today()
    frames = []

    # Историческа част
    if start < today:
        frames.append(
            _fetch(
                ARCHIVE_URL,
                {"latitude": lat, "longitude": lon,
                 "start_date": start.isoformat(),
                 "end_date": min(end, today - dt.timedelta(days=1)).isoformat()},
            )
        )
    # Прогнозна част (до 16 дни напред)
    if end >= today:
        frames.append(_fetch(FORECAST_URL, {"latitude": lat, "longitude": lon, "forecast_days": 16}))

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True).drop_duplicates("day")
    out["city"] = city
    return out[(out["day"] >= start) & (out["day"] <= end)].reset_index(drop=True)


def weather_label(code: int) -> str:
    if code == 0:
        return "Ясно"
    if code <= 3:
        return "Облачно"
    if code <= 48:
        return "Мъгла"
    if code <= 67:
        return "Дъжд"
    if code <= 77:
        return "Сняг"
    return "Превалявания"


def correlate_with_sales(daily_sales: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Свързва дневния оборот с времето по дата.

    daily_sales: колони business_date, revenue.
    Връща обединена таблица + коефициент на корелация в .attrs.
    """
    if daily_sales.empty or weather.empty:
        return pd.DataFrame()
    s = daily_sales.rename(columns={"business_date": "day"}).copy()
    s["day"] = pd.to_datetime(s["day"]).dt.date
    merged = s.merge(weather, on="day", how="inner")
    if len(merged) >= 3:
        merged.attrs["corr_temp"] = merged["revenue"].corr(merged["temp_max"])
        merged.attrs["corr_rain"] = merged["revenue"].corr(merged["precipitation"])
    return merged


def _round(x) -> float | None:
    """Закръгля, но връща None при NaN (за чист JSON към модела)."""
    return None if x is None or x != x else round(float(x), 2)


def weather_insights(sales: pd.DataFrame, weather: pd.DataFrame,
                     rain_mm: float = 1.0) -> dict:
    """Свързва продажбите с времето по регион и ден и връща изводи за модела.

    Връща речник с:
      * rainy_vs_dry — среден оборот и дял доставки в дъждовни vs сухи дни
      * by_region — корелации оборот↔температура и оборот↔валежи по регион
    Така чат асистентът може да дава съвети тип „при дъжд доставките скачат".
    """
    if sales is None or sales.empty or weather is None or weather.empty:
        return {}

    s = sales.copy()
    s["region"] = s["object_name"].map(config.city_for)
    s = s.dropna(subset=["region", "business_date"])
    if s.empty:
        return {}

    s["deliv_amt"] = np.where(s.get("is_delivery", False), s["amount"], 0.0)
    daily = (
        s.groupby(["region", "business_date"])
        .agg(revenue=("amount", "sum"), deliv=("deliv_amt", "sum"))
        .reset_index()
    )
    daily["delivery_share"] = np.where(
        daily["revenue"] != 0, daily["deliv"] / daily["revenue"] * 100, 0.0
    )
    daily["business_date"] = pd.to_datetime(daily["business_date"]).dt.date

    w = weather.rename(columns={"city": "region", "day": "business_date"})[
        ["region", "business_date", "temp_max", "precipitation"]
    ].copy()
    w["business_date"] = pd.to_datetime(w["business_date"]).dt.date

    m = daily.merge(w, on=["region", "business_date"], how="inner")
    if m.empty:
        return {}

    rainy = m[m["precipitation"] > rain_mm]
    dry = m[m["precipitation"] <= rain_mm]

    def avg(frame, col):
        return _round(frame[col].mean()) if len(frame) else None

    rainy_vs_dry = {
        "rain_threshold_mm": rain_mm,
        "rainy_days": int(len(rainy)),
        "dry_days": int(len(dry)),
        "avg_revenue_rainy": avg(rainy, "revenue"),
        "avg_revenue_dry": avg(dry, "revenue"),
        "delivery_share_rainy_pct": avg(rainy, "delivery_share"),
        "delivery_share_dry_pct": avg(dry, "delivery_share"),
    }

    by_region = []
    for region, g in m.groupby("region"):
        if len(g) >= 3:
            by_region.append({
                "region": region,
                "days": int(len(g)),
                "corr_temp": _round(g["revenue"].corr(g["temp_max"])),
                "corr_rain": _round(g["revenue"].corr(g["precipitation"])),
            })

    return {"rainy_vs_dry": rainy_vs_dry, "by_region": by_region}
