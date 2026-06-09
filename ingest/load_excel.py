"""Качване на сурови Excel данни за продажби в Supabase.

Употреба:
    python -m ingest.load_excel path/to/файл.xlsx
"""
import argparse

import pandas as pd

import config
from db.supabase_client import get_client
from transform import to_records, transform


def load_sales(path: str, batch_size: int = 500) -> int:
    raw = pd.read_excel(path)
    df = transform(raw)
    records = to_records(df)

    client = get_client(use_service_key=True)
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table(config.SALES_TABLE).insert(batch).execute()
        total += len(batch)
        print(f"  качени {total}/{len(records)} реда...")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Качване на Excel продажби в Supabase")
    parser.add_argument("path", help="път до .xlsx файла")
    args = parser.parse_args()
    n = load_sales(args.path)
    print(f"Готово! Качени {n} реда в '{config.SALES_TABLE}'.")
