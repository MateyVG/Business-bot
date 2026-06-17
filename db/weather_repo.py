"""Запис на синоптични данни в Supabase (нужен service_role ключ).

Ключът на таблицата weather е (city, day), затова ползваме upsert — повторно
дърпане на същия период обновява, без дубликати.
"""
import pandas as pd

import config
from db.supabase_client import get_client
from transform import to_records


def upsert_weather(df: pd.DataFrame, batch_size: int = 500) -> int:
    """Качва/обновява редове време по (city, day). Връща броя."""
    if df.empty:
        return 0
    records = to_records(df)
    client = get_client(use_service_key=True)
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table(config.WEATHER_TABLE).upsert(batch).execute()
        total += len(batch)
    return total
