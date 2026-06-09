"""Бизнес метрики, смятани директно от данните.

Всички времеви справки ползват `business_date` (работен ден),
а не календарния ден.
"""
import numpy as np
import pandas as pd


def _net(df: pd.DataFrame) -> pd.DataFrame:
    """Само редовете, които броим за оборот (тук включваме и връщанията,
    защото те намаляват оборота чрез отрицателна стойност)."""
    return df


def total_revenue(df: pd.DataFrame) -> float:
    return float(df["amount"].sum())


def revenue_by_business_day(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("business_date")["amount"].sum().reset_index(name="revenue")
    return g.sort_values("business_date")


def revenue_by_object(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("object_name")["amount"].sum().sort_values(ascending=False)
    return g.reset_index(name="revenue")


def revenue_by_category(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    return g.reset_index(name="revenue")


def revenue_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Оборот по час на денонощието (полезно за пиковите часове)."""
    g = df.groupby("sale_hour")["amount"].sum().reset_index(name="revenue")
    return g.sort_values("sale_hour")


def top_products(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    g = (
        df.groupby("product_name")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(n)
    )
    return g.reset_index(name="revenue")


def delivery_split(df: pd.DataFrame) -> pd.DataFrame:
    """Оборот на място vs доставка."""
    g = df.groupby("is_delivery")["amount"].sum()
    return pd.DataFrame(
        {
            "channel": ["Доставка" if k else "На място" for k in g.index],
            "revenue": g.values,
        }
    )


def growth_rate(df: pd.DataFrame) -> float:
    """Процентен ръст на последния работен ден спрямо предходния."""
    rev = revenue_by_business_day(df)
    if len(rev) < 2:
        return 0.0
    prev, last = rev["revenue"].iloc[-2], rev["revenue"].iloc[-1]
    return float((last - prev) / prev * 100) if prev else 0.0


def profit_by_product(df: pd.DataFrame, costs: pd.DataFrame) -> pd.DataFrame:
    """Печалба по продукт = приход - (себестойност × количество).

    `costs` трябва да има колони: product_name, channel, unit_cost.
    Себестойността зависи от канала (на място / доставка), затова свързваме по
    (product_name, channel), а каналът се определя от is_delivery в продажбите.
    """
    if costs is None or costs.empty:
        return pd.DataFrame(columns=["product_name", "revenue", "cost", "profit", "margin_pct"])

    sales = df.copy()
    sales["channel"] = np.where(sales.get("is_delivery", False), "delivery", "onsite")

    costs = costs[["product_name", "channel", "unit_cost"]].copy()
    costs["unit_cost"] = pd.to_numeric(costs["unit_cost"], errors="coerce")

    merged = sales.merge(costs, on=["product_name", "channel"], how="left")
    merged["cost"] = merged["unit_cost"].fillna(0) * merged["quantity"]
    g = merged.groupby("product_name").agg(
        revenue=("amount", "sum"), cost=("cost", "sum")
    ).reset_index()
    g["profit"] = g["revenue"] - g["cost"]
    g["margin_pct"] = np.where(
        g["revenue"] != 0, (g["profit"] / g["revenue"] * 100).round(1), 0.0
    )
    return g.sort_values("profit", ascending=False)
