"""AI асистент (OpenAI) за бизнес анализ — с достъп до реалните данни.

Принцип: моделът НЕ получава целия файл, а може да ИЗВИКА инструменти, които
смятат точния разрез от реалните данни (pandas). Така отговаря на въпроси по
обект, ден, оператор, продукт, канал, час и т.н. — без да измисля числа.
"""
import datetime as dt
import json
import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from analytics import metrics
from analytics.forecast import forecast_revenue
from analytics.weather import weather_insights, weather_label
import config

load_dotenv()

SYSTEM_PROMPT = (
    "Ти си опитен бизнес анализатор за верига заведения за бързо хранене. "
    "Отговаряй на български, кратко и конкретно. "
    "За всякакви числа ВИНАГИ ползвай инструментите (query_sales, weather_forecast, "
    "weather_vs_sales) — никога не измисляй стойности. Можеш да правиш няколко "
    "извиквания, за да съчетаеш разрези (напр. по обекти, по дни, по оператор). "
    "Работният ден приключва в 07:00 (нощните продажби влизат в предишния ден). "
    "Давай практични препоръки за продажби, маркетинг и асортимент."
)

WEEKDAYS_BG = ["Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък",
               "Събота", "Неделя"]


# ---------- Инструменти върху реалните данни ----------

def _run_query(df, group_by=None, metric="revenue", object=None, category=None,
               channel=None, date_from=None, date_to=None, top_n=20, sort="desc"):
    """Гъвкава агрегация на продажбите."""
    d = df.copy()
    if d.empty:
        return {"rows": [], "note": "няма данни"}

    if object:
        d = d[d["object_name"].astype(str).str.strip().str.casefold()
              == str(object).strip().casefold()]
    if category:
        d = d[d["category"].astype(str).str.casefold() == str(category).casefold()]
    if channel in ("onsite", "delivery"):
        d = d[d["is_delivery"] == (channel == "delivery")]
    bdate = pd.to_datetime(d["business_date"], errors="coerce")
    if date_from:
        d = d[bdate >= pd.to_datetime(date_from, errors="coerce")]
    if date_to:
        d = d[pd.to_datetime(d["business_date"], errors="coerce")
              <= pd.to_datetime(date_to, errors="coerce")]
    if d.empty:
        return {"rows": [], "note": "няма редове за тези филтри"}

    if group_by == "channel":
        d["_g"] = d["is_delivery"].map({True: "доставка", False: "на място"})
        key = "_g"
    elif group_by == "weekday":
        wd = pd.to_datetime(d["business_date"], errors="coerce").dt.weekday
        d["_g"] = wd.map(lambda i: WEEKDAYS_BG[int(i)] if pd.notna(i) else None)
        key = "_g"
    elif group_by == "city":
        d["_g"] = d["object_name"].map(config.city_for)
        key = "_g"
    elif group_by == "hour":
        key = "sale_hour"
    elif group_by in ("object", "category", "product", "operator", "business_date"):
        key = {"object": "object_name", "category": "category",
               "product": "product_name", "operator": "operator",
               "business_date": "business_date"}[group_by]
    else:
        key = None

    def agg(frame):
        if metric == "quantity" and "quantity" in frame:
            return round(float(pd.to_numeric(frame["quantity"], errors="coerce").sum()), 2)
        if metric == "orders":
            return int(frame["order_no"].nunique()) if "order_no" in frame else int(len(frame))
        return round(float(pd.to_numeric(frame["amount"], errors="coerce").sum()), 2)

    if key is None:
        return {"metric": metric, "total": agg(d), "rows_count": int(len(d))}

    rows = []
    for name, frame in d.groupby(key, dropna=True):
        rows.append({group_by: (str(name) if not isinstance(name, (int, float)) else name),
                     metric: agg(frame)})
    rows.sort(key=lambda r: r[metric], reverse=(sort != "asc"))
    return {"metric": metric, "rows": rows[: int(top_n or 20)]}


def _weather_forecast(weather, city=None, days=7):
    """Предстоящо време (прогноза) по град от таблицата weather."""
    if weather is None or weather.empty:
        return {"rows": [], "note": "няма данни за времето — натисни „Обнови времето“"}
    w = weather.copy()
    w["day"] = pd.to_datetime(w["day"], errors="coerce").dt.date
    w = w[w["day"] >= dt.date.today()]
    if city:
        w = w[w["city"].astype(str).str.casefold() == str(city).casefold()]
    if w.empty:
        return {"rows": [], "note": "няма прогноза за този град"}
    out = []
    for c, grp in w.sort_values(["city", "day"]).groupby("city"):
        for _, r in grp.head(int(days or 7)).iterrows():
            code = r.get("weather_code")
            out.append({
                "city": c, "day": str(r["day"]),
                "temp_max": r.get("temp_max"), "temp_min": r.get("temp_min"),
                "precipitation": r.get("precipitation"),
                "condition": weather_label(int(code)) if pd.notna(code) else None,
            })
    return {"rows": out}


def _weather_vs_sales(df, weather):
    """Връзка време↔оборот: дъждовни vs сухи дни и корелации по регион."""
    ins = weather_insights(df, weather)
    return ins or {"note": "няма достатъчно припокриващи се дни"}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sales",
            "description": ("Агрегира реалните продажби. Ползвай за всякакви числа "
                            "по обект, категория, продукт, оператор, ден, ден от "
                            "седмицата, час, канал или град."),
            "parameters": {
                "type": "object",
                "properties": {
                    "group_by": {"type": "string", "enum": [
                        "object", "category", "product", "operator", "weekday",
                        "hour", "business_date", "channel", "city"],
                        "description": "Разрез; пропусни за обща сума."},
                    "metric": {"type": "string",
                               "enum": ["revenue", "quantity", "orders"],
                               "description": "revenue=оборот, quantity=количество, "
                                              "orders=брой поръчки/бонове."},
                    "object": {"type": "string", "description": "Филтър по обект."},
                    "category": {"type": "string", "description": "Филтър по категория."},
                    "channel": {"type": "string", "enum": ["onsite", "delivery"]},
                    "date_from": {"type": "string", "description": "YYYY-MM-DD."},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD."},
                    "top_n": {"type": "integer"},
                    "sort": {"type": "string", "enum": ["desc", "asc"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather_forecast",
            "description": "Предстояща метеорологична прогноза по град (следващи дни).",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Град/регион (по избор)."},
                    "days": {"type": "integer", "description": "Брой дни напред."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather_vs_sales",
            "description": ("Връзка между времето и оборота: оборот и дял доставки "
                            "в дъждовни спрямо сухи дни + корелации по регион."),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _overview(df, weather=None):
    """Кратък контекст, за да знае моделът какви стойности има за филтри."""
    bdate = pd.to_datetime(df["business_date"], errors="coerce")
    ov = {
        "обекти": sorted(df["object_name"].dropna().unique().tolist()),
        "категории": sorted(df["category"].dropna().unique().tolist()),
        "период": [str(bdate.min().date()) if bdate.notna().any() else None,
                   str(bdate.max().date()) if bdate.notna().any() else None],
        "общ_оборот": round(float(pd.to_numeric(df["amount"], errors="coerce").sum()), 2),
        "време_заредено": bool(weather is not None and not weather.empty),
    }
    return ov


def ask(question: str, df: pd.DataFrame, costs: pd.DataFrame | None = None,
        history: list[dict] | None = None, weather: pd.DataFrame | None = None) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": (
        f"Обзор на данните (за валидни стойности):\n"
        f"{json.dumps(_overview(df, weather), ensure_ascii=False)}\n\n"
        f"Въпрос: {question}"
    )})

    for _ in range(6):  # до 6 кръга с инструменти
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS,
            tool_choice="auto", temperature=0.2,
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content or "Нямам отговор."

        messages.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name,
                                         "arguments": tc.function.arguments}}
                           for tc in msg.tool_calls],
        })
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            name = tc.function.name
            if name == "query_sales":
                result = _run_query(df, **args)
            elif name == "weather_forecast":
                result = _weather_forecast(weather, **args)
            elif name == "weather_vs_sales":
                result = _weather_vs_sales(df, weather)
            else:
                result = {"error": f"непознат инструмент {name}"}
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, ensure_ascii=False, default=str)})

    return "Не успях да довърша анализа. Опитай с по-конкретен въпрос."
