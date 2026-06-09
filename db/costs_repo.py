"""Запис на себестойности в Supabase (нужен service_role ключ — заобикаля RLS).

Ползва се и от CLI (ingest/load_costs.py), и от приложението (app.py),
за да има едно място за писане в таблицата product_costs.
"""
import pandas as pd

import config
from db.supabase_client import get_client
from transform import to_records


def upsert_costs(df: pd.DataFrame, batch_size: int = 500) -> int:
    """Качва/обновява редове по ключа (product_name, channel). Връща броя."""
    records = to_records(df)
    client = get_client(use_service_key=True)
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table(config.COSTS_TABLE).upsert(batch).execute()
        total += len(batch)
    return total


def delete_cost(product_name: str, channel: str) -> None:
    """Трие един ред себестойност (по име + канал)."""
    client = get_client(use_service_key=True)
    (
        client.table(config.COSTS_TABLE)
        .delete()
        .eq("product_name", product_name)
        .eq("channel", channel)
        .execute()
    )
