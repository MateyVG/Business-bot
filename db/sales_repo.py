"""Запис на продажби в Supabase (нужен service_role ключ — заобикаля RLS).

Таблицата sales няма естествен уникален ключ (id е автоматичен), затова
вкарваме нови редове. За да няма дубликати при повторно качване на същия файл,
предлагаме и режим „замести всички" (трие и вкарва наново).
"""
import pandas as pd

import config
from db.supabase_client import get_client
from transform import to_records


def insert_sales(df: pd.DataFrame, batch_size: int = 500) -> int:
    """Добавя редове продажби. Връща броя качени редове."""
    records = to_records(df)
    client = get_client(use_service_key=True)
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table(config.SALES_TABLE).insert(batch).execute()
        total += len(batch)
    return total


def delete_all_sales() -> None:
    """Изтрива ВСИЧКИ редове от sales (id е always-positive identity)."""
    client = get_client(use_service_key=True)
    client.table(config.SALES_TABLE).delete().gte("id", 0).execute()


def replace_all_sales(df: pd.DataFrame, batch_size: int = 500) -> int:
    """Заменя цялата таблица: първо трие всичко, после вкарва подадените редове."""
    delete_all_sales()
    return insert_sales(df, batch_size)
