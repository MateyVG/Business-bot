"""AI асистент (OpenAI) за бизнес анализ.

Принцип: числата се смятат от данните (analytics/*); OpenAI само ги
обяснява и дава препоръки. Така няма "измислени" стойности.
"""
import json
import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from analytics import metrics
from analytics.forecast import forecast_revenue

load_dotenv()

SYSTEM_PROMPT = (
    "Ти си опитен бизнес анализатор за верига заведения за бързо хранене. "
    "Отговаряй на български, кратко и по същество. "
    "Използвай САМО числата от подадения контекст — никога не измисляй стойности. "
    "Работният ден приключва в 07:00 (нощните продажби влизат в предишния ден). "
    "Давай конкретни препоръки за продажби, маркетинг и асортимент."
)


def build_context(df: pd.DataFrame, costs: pd.DataFrame | None = None) -> dict:
    ctx = {
        "total_revenue": metrics.total_revenue(df),
        "growth_pct_last_day": round(metrics.growth_rate(df), 1),
        "by_object": metrics.revenue_by_object(df).to_dict(orient="records"),
        "by_category": metrics.revenue_by_category(df).to_dict(orient="records"),
        "by_hour": metrics.revenue_by_hour(df).to_dict(orient="records"),
        "delivery_vs_onsite": metrics.delivery_split(df).to_dict(orient="records"),
        "top_products": metrics.top_products(df, 10).to_dict(orient="records"),
        "daily_revenue": metrics.revenue_by_business_day(df).tail(30).to_dict(orient="records"),
        "forecast": forecast_revenue(df, 7).query("kind=='forecast'").to_dict(orient="records"),
    }
    if costs is not None and not costs.empty:
        ctx["profit_by_product"] = (
            metrics.profit_by_product(df, costs).head(15).to_dict(orient="records")
        )
    return ctx


def ask(question: str, df: pd.DataFrame, costs: pd.DataFrame | None = None,
        history: list[dict] | None = None) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    context = build_context(df, costs)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": (
                f"Реални метрики (JSON):\n"
                f"{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
                f"Въпрос: {question}"
            ),
        }
    )
    resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3)
    return resp.choices[0].message.content
