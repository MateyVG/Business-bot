"""Визуални блокове в стил „Призма" — KPI карти, спарклайни, списъци, инсайти.

Генерира HTML/SVG, който се вмъква през st.markdown(..., unsafe_allow_html=True),
за да съвпада с дизайна (картите/спарклайните не са вградени в Streamlit).
"""
from __future__ import annotations

import pandas as pd

import theme


def sparkline(values, color: str = theme.ACCENT, w: int = 120, h: int = 34) -> str:
    """Малък SVG спарклайн от поредица числа."""
    vals = [float(v) for v in values if v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    step = w / (len(vals) - 1)
    pts = " ".join(
        f"{i*step:.1f},{h-4 - (v-lo)/rng*(h-8):.1f}" for i, v in enumerate(vals)
    )
    last = pts.split()[-1]
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="none" style="display:block">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{last.split(",")[0]}" cy="{last.split(",")[1]}" r="2.6" fill="{color}"/>'
        f"</svg>"
    )


def _delta_badge(delta) -> str:
    if delta is None or delta != delta:
        return ""
    up = delta >= 0
    col = theme.ACCENT if up else "#c5573f"
    bg = theme.ACCENT_SOFT if up else "#f7e3de"
    sign = "+" if up else ""
    return (f'<span style="background:{bg};color:{col};border-radius:999px;'
            f'padding:2px 8px;font-size:.72rem;font-weight:700">{sign}{delta:.1f}%</span>')


def kpi_card(label: str, value: str, delta=None, spark=None,
             spark_color: str = theme.ACCENT) -> str:
    return (
        f'<div class="pz-kpi">'
        f'<div class="pz-kpi-top"><span class="pz-kpi-label">{label}</span>{_delta_badge(delta)}</div>'
        f'<div class="pz-kpi-value">{value}</div>'
        f'<div class="pz-kpi-spark">{sparkline(spark or [], spark_color)}</div>'
        f"</div>"
    )


def kpi_row(cards: list[str]) -> str:
    return f'<div class="pz-kpis">{"".join(cards)}</div>'


def top_list(df: pd.DataFrame, label_col: str, value_col: str,
             unit: str = "€", n: int = 6) -> str:
    if df.empty:
        return '<div class="pz-muted">Няма данни.</div>'
    d = df.head(n)
    mx = float(d[value_col].max()) or 1.0
    rows = []
    for _, r in d.iterrows():
        pct = max(4, float(r[value_col]) / mx * 100)
        val = f"€{r[value_col]:,.0f}".replace(",", " ")
        rows.append(
            f'<div class="pz-row"><div class="pz-row-top">'
            f'<span>{r[label_col]}</span><b>{val}</b></div>'
            f'<div class="pz-bar"><div class="pz-bar-fill" style="width:{pct:.0f}%"></div></div></div>'
        )
    return "".join(rows)


def insights(items: list[tuple[str, str]]) -> str:
    """items: списък от (тип, текст); тип in {pos, neg, warn, info}."""
    cmap = {"pos": theme.ACCENT, "neg": "#c5573f", "warn": "#c98a2b", "info": theme.MUTED}
    rows = []
    for kind, text in items:
        c = cmap.get(kind, theme.MUTED)
        rows.append(
            f'<div class="pz-insight"><span class="pz-dot" style="background:{c}"></span>'
            f'<span>{text}</span></div>'
        )
    return "".join(rows)


def card_open(title: str, value: str = "") -> str:
    v = f'<span class="pz-card-value">{value}</span>' if value else ""
    return f'<div class="pz-card"><div class="pz-card-title">{title}{v}</div>'


def card_close() -> str:
    return "</div>"
