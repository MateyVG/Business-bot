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
from db.costs_repo import upsert_costs
from transform import transform_costs


def read_costs_excel(source) -> pd.DataFrame:
    """Чете Excel (път или файлов обект) и връща обединените себестойности.

    Преминава през всеки познат лист и му слага съответния канал. Ако нито
    един от очакваните листове не е намерен, ползва първия като 'onsite'.
    """
    xl = pd.ExcelFile(source)
    frames = []
    for sheet, channel in config.COST_SHEET_CHANNELS.items():
        if sheet in xl.sheet_names:
            frames.append(transform_costs(pd.read_excel(xl, sheet_name=sheet), channel))
    if not frames:
        frames.append(transform_costs(pd.read_excel(xl, xl.sheet_names[0]), "onsite"))
    return pd.concat(frames, ignore_index=True)


def load_costs(path: str, batch_size: int = 500) -> int:
    df = read_costs_excel(path)
    print(f"  прочетени {len(df)} реда от Excel-а...")
    n = upsert_costs(df, batch_size)
    return n


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Качване на себестойности (Excel) в Supabase"
    )
    parser.add_argument("path", help="път до .xlsx файла със себестойностите")
    args = parser.parse_args()
    n = load_costs(args.path)
    print(f"Готово! Качени/обновени {n} реда в '{config.COSTS_TABLE}'.")
