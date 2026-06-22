"""Дърпане на синоптични данни от Open-Meteo и запис в Supabase (таблица weather).

За всеки град взимаме история + прогноза за зададения период и upsert-ваме по
(city, day). Ползва се и от приложението (бутон „Обнови времето"), и от CLI.

Употреба:
    python -m ingest.load_weather [--back 90] [--fwd 14]

ВАЖНО: Open-Meteo е безплатно (без ключ), но иска изходящ интернет. В някои
ограничени среди връща 403 — тогава пусни от машина с нормален достъп
(локално или деплойнатото приложение).
"""
import argparse
import datetime as dt

import pandas as pd

import config
from analytics.weather import get_weather
from db.weather_repo import upsert_weather


def default_cities() -> list[str]:
    """Уникалните градове, в които има обекти (от config.OBJECT_CITY)."""
    return sorted(set(config.OBJECT_CITY.values()))


def fetch_weather(cities: list[str], start: dt.date, end: dt.date) -> pd.DataFrame:
    """Връща обединено дневно време за списък градове в периода [start, end]."""
    frames = []
    for c in cities:
        try:
            f = get_weather(c, start, end)
            if not f.empty:
                frames.append(f)
        except Exception as e:  # noqa: BLE001 — една грешка да не спира останалите градове
            print(f"  внимание: времето за {c} се провали ({e})")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_weather(cities: list[str] | None = None,
                 start: dt.date | None = None,
                 end: dt.date | None = None) -> int:
    """Дърпа и записва времето. Връща броя качени редове."""
    cities = cities or default_cities()
    today = dt.date.today()
    start = start or today - dt.timedelta(days=90)
    end = end or today + dt.timedelta(days=14)
    df = fetch_weather(cities, start, end)
    return upsert_weather(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Дърпане на времето в Supabase")
    parser.add_argument("--back", type=int, default=90, help="дни история назад")
    parser.add_argument("--fwd", type=int, default=14, help="дни прогноза напред")
    args = parser.parse_args()
    today = dt.date.today()
    n = load_weather(
        start=today - dt.timedelta(days=args.back),
        end=today + dt.timedelta(days=args.fwd),
    )
    print(f"Готово! Качени/обновени {n} реда в '{config.WEATHER_TABLE}'.")
