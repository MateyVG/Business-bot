"""Качване на себестойности на продуктите в Supabase (таблица product_costs).

Excel-ът има по един лист на канал (виж config.COST_SHEET_CHANNELS):
    "Обекти"   -> onsite    (продажба на място)
    "Доставки" -> delivery  (доставка по домовете)
Всеки лист има колони:
    Артикул               -> product_name  (връзка към sales.product_name)
    Обща стойност с ДДС   -> unit_cost      (себестойност за единица)

Употреба:
    python -m ingest.load_costs path/to/себестойности.xlsx

Ползва upsert по (product_name, channel), така че повторно качване ОБНОВЯВА
цените, без да дублира редове. Нужен е service_role ключ (заобикаля RLS).
"""
import argparse

import pandas as pd

import config
from db.supabase_client import get_client
from transform import to_records, transform_costs


def load_costs(path: str, batch_size: int = 500) -> int:
    xl = pd.ExcelFile(path)

    frames = []
    for sheet, channel in config.COST_SHEET_CHANNELS.items():
        if sheet in xl.sheet_names:
            frames.append(transform_costs(pd.read_excel(xl, sheet_name=sheet), channel))
            print(f"  лист '{sheet}' -> канал '{channel}': {len(frames[-1])} реда")

    # Резервен вариант: ако очакваните листове ги няма, ползваме първия като onsite.
    if not frames:
        frames.append(transform_costs(pd.read_excel(xl, xl.sheet_names[0]), "onsite"))
        print(f"  (резервно) лист '{xl.sheet_names[0]}' -> 'onsite'")

    df = pd.concat(frames, ignore_index=True)
    records = to_records(df)

    client = get_client(use_service_key=True)
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table(config.COSTS_TABLE).upsert(batch).execute()
        total += len(batch)
        print(f"  качени {total}/{len(records)} реда...")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Качване на себестойности (Excel) в Supabase"
    )
    parser.add_argument("path", help="път до .xlsx файла със себестойностите")
    args = parser.parse_args()
    n = load_costs(args.path)
    print(f"Готово! Качени/обновени {n} реда в '{config.COSTS_TABLE}'.")
