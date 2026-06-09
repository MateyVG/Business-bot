"""Качване на себестойности на продуктите в Supabase (таблица product_costs).

Очаква Excel със себестойности. Заглавията се разпознават гъвкаво
(виж config.COST_COLUMN_ALIASES), но по същество трябват:
    Мат. №            -> material_id   (връзка към sales.material_id)
    Себестойност      -> unit_cost     (себестойност за единица)
    Име на материал   -> product_name  (по желание)

Употреба:
    python -m ingest.load_costs path/to/себестойности.xlsx

Ползва upsert по material_id, така че повторно качване ОБНОВЯВА цените,
без да дублира редове. Нужен е service_role ключ (заобикаля RLS).
"""
import argparse

import pandas as pd

import config
from db.supabase_client import get_client
from transform import to_records, transform_costs


def load_costs(path: str, batch_size: int = 500) -> int:
    raw = pd.read_excel(path)
    df = transform_costs(raw)
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
