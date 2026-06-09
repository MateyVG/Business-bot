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


def _norm_header(name: object) -> str:
    """Привежда заглавие на колона към сравним вид: без интервали, точки и
    главни букви (за гъвкаво разпознаване на Excel колоните)."""
    s = re.sub(r"\s+", "", str(name)).lower()
    return s.replace(".", "").replace("№", "no")


def _resolve_columns(df: pd.DataFrame, aliases: dict[str, list[str]]) -> dict[str, str]:
    """Намира за всяка целева колона коя реална Excel колона ѝ съответства.

    Връща map {реално_заглавие: целево_име}, годен за df.rename(columns=...).
    """
    found = {_norm_header(c): c for c in df.columns}
    mapping = {}
    for target, names in aliases.items():
        for name in names:
            real = found.get(_norm_header(name))
            if real is not None:
                mapping[real] = target
                break
    return mapping


def transform_costs(df: pd.DataFrame, channel: str) -> pd.DataFrame:
    """Сурова Excel таблица със себестойности (един лист) -> чист DataFrame.

    Очаквани (целеви) колони: product_name, unit_cost. Реалните заглавия се
    разпознават гъвкаво чрез config.COST_COLUMN_ALIASES. Десетичните стойности
    със запетая ("1,50") се приемат коректно.

    `channel` маркира канала ('onsite' / 'delivery'), защото себестойността на
    един и същ продукт се различава на място спрямо доставка. Свързването с
    продажбите после е по (product_name, channel), а каналът идва от is_delivery.
    """
    df = df.rename(columns=_resolve_columns(df, config.COST_COLUMN_ALIASES)).copy()

    missing = {"product_name", "unit_cost"} - set(df.columns)
    if missing:
        raise ValueError(
            f"Липсват задължителни колони {sorted(missing)}. "
            f"Намерени заглавия в Excel: {list(df.columns)}. "
            f"Добави подходящ псевдоним в config.COST_COLUMN_ALIASES."
        )

    df = df[["product_name", "unit_cost"]].copy()
    df["product_name"] = df["product_name"].map(_norm_object)
    df["unit_cost"] = pd.to_numeric(
        df["unit_cost"].astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )

    # Без име продуктът е безполезен (връзката към sales е по име)
    df = df.dropna(subset=["product_name"])
    df = df[df["product_name"].astype(str).str.strip() != ""]
    df["channel"] = channel
    # При дубликати на име в един лист пазим последния (приемаме го за актуален)
    df = df.drop_duplicates(subset=["product_name"], keep="last")

    # Маркер кога е обновена цената (product_costs.updated_at се пази при upsert)
    df["updated_at"] = pd.Timestamp.now(tz="UTC").isoformat()

    return df.reset_index(drop=True)


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
