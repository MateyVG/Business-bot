"""Качване на сурови Excel данни за продажби в Supabase.

Употреба:
    python -m ingest.load_excel path/to/файл.xlsx [--replace]

--replace заменя цялата таблица (трие старите редове), иначе добавя.
Същата логика се ползва и от приложението (app.py) през read_sales_excel.
"""
import argparse

import pandas as pd

import config
from db.sales_repo import insert_sales, replace_all_sales
from transform import transform


def read_sales_excel(source) -> pd.DataFrame:
    """Чете Excel (път или файлов обект) и връща готовите за базата редове."""
    raw = pd.read_excel(source)
    return transform(raw)


def load_sales(path: str, replace: bool = False, batch_size: int = 500) -> int:
    df = read_sales_excel(path)
    print(f"  прочетени {len(df)} реда от Excel-а...")
    if replace:
        return replace_all_sales(df, batch_size)
    return insert_sales(df, batch_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Качване на Excel продажби в Supabase")
    parser.add_argument("path", help="път до .xlsx файла")
    parser.add_argument(
        "--replace", action="store_true", help="замести всички стари редове"
    )
    args = parser.parse_args()
    n = load_sales(args.path, replace=args.replace)
    print(f"Готово! Качени {n} реда в '{config.SALES_TABLE}'.")
