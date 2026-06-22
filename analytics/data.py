"""Зареждане на данните от Supabase в pandas DataFrame."""
import pandas as pd

import config
from db.supabase_client import get_client


def _load_table(table: str) -> pd.DataFrame:
    client = get_client()
    rows, page, size = [], 0, 1000
    while True:
        resp = (
            client.table(table)
            .select("*")
            .range(page * size, (page + 1) * size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < size:
            break
        page += 1
    return pd.DataFrame(rows)


def load_sales() -> pd.DataFrame:
    df = _load_table(config.SALES_TABLE)
    if df.empty:
        return df
    df["sold_at"] = pd.to_datetime(df["sold_at"], errors="coerce")
    df["business_date"] = pd.to_datetime(df["business_date"], errors="coerce").dt.date
    for col in ("amount", "quantity", "material_id", "sale_hour"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "is_delivery" in df:
        df["is_delivery"] = df["is_delivery"].astype(bool)
    return df


def load_costs() -> pd.DataFrame:
    return _load_table(config.COSTS_TABLE)
