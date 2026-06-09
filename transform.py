"""Превръща суровия Excel в чисти, готови за анализ записи.

Тук се случва ключовата бизнес логика:
  * работен ден (business_date) с граница config.BUSINESS_DAY_CUTOFF_HOUR
  * флаг за доставка (is_delivery) според колоната "Партньор"
"""
import re
from datetime import timedelta

import pandas as pd

import config


def _norm_object(name: str) -> str:
    """Нормализира името на обекта (маха двойни интервали)."""
    if not isinstance(name, str):
        return name
    return re.sub(r"\s+", " ", name).strip()


def business_date(ts: pd.Timestamp) -> pd.Timestamp:
    """Връща работния ден за даден час.

    Продажба преди CUTOFF часа -> предишния календарен ден.
    Изваждаме CUTOFF часа и взимаме датата: чисто и без if-ове.
    """
    if pd.isna(ts):
        return pd.NaT
    return (ts - timedelta(hours=config.BUSINESS_DAY_CUTOFF_HOUR)).normalize()


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Сурова Excel таблица -> чист DataFrame с колоните за базата."""
    df = df.rename(columns=config.COLUMN_MAP).copy()

    # Час на продажбата
    df["sold_at"] = pd.to_datetime(
        df["sold_at"], format="%d.%m.%Y %H:%M:%S", errors="coerce"
    )

    # Нормализираме обекта
    if "object_name" in df:
        df["object_name"] = df["object_name"].map(_norm_object)

    # Работен ден + действителен час (за анализ по часове)
    df["business_date"] = df["sold_at"].map(business_date).dt.date
    df["sale_hour"] = df["sold_at"].dt.hour

    # Доставка = има попълнен партньор
    df["is_delivery"] = df["partner"].notna() & (df["partner"].astype(str).str.strip() != "")

    # Връщане = отрицателна стойност
    df["is_return"] = df["amount"] < 0

    return df


def to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> списък записи, годни за Supabase (JSON-safe)."""
    out = []
    for row in df.to_dict(orient="records"):
        rec = {}
        for k, v in row.items():
            if pd.isna(v):
                rec[k] = None
            elif isinstance(v, pd.Timestamp):
                rec[k] = v.isoformat()
            elif hasattr(v, "isoformat"):  # datetime.date
                rec[k] = v.isoformat()
            elif hasattr(v, "item"):  # numpy скалари -> native python
                rec[k] = v.item()
            else:
                rec[k] = v
        out.append(rec)
    return out
