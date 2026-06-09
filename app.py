"""Бизнес Анализатор — уеб приложение (Streamlit).

Стартиране:  streamlit run app.py
"""
import datetime as dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import config
import ingest.load_weather as weather_ingest
import theme
from analytics import metrics
from analytics.data import load_costs, load_sales, load_weather
from analytics.forecast import forecast_revenue
from analytics.weather import correlate_with_sales
from db.costs_repo import upsert_costs
from db.sales_repo import insert_sales, replace_all_sales
from db.supabase_client import has_secret, has_service_key
from ingest.load_costs import read_costs_excel
from ingest.load_excel import read_sales_excel

st.set_page_config(page_title="Бизнес Анализатор", layout="wide")
st.markdown(theme.css(), unsafe_allow_html=True)


@st.cache_data(ttl=300)
def get_data():
    return load_sales()


@st.cache_data(ttl=300)
def get_costs():
    try:
        return load_costs()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_weather():
    try:
        return load_weather()
    except Exception:
        return pd.DataFrame()


def chart(fig, height: int = 340):
    st.plotly_chart(theme.style_fig(fig, height), use_container_width=True,
                    config={"displayModeBar": False})


def weather_chart(merged):
    """Оборот (стълбове) и максимална температура (линия) по ден, две оси Y."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=merged["day"], y=merged["revenue"], name="Оборот",
                marker_color=theme.ACCENT)
    fig.add_scatter(x=merged["day"], y=merged["temp_max"], name="Макс. температура",
                    mode="lines+markers", line=dict(color=theme.CHART_COLORS[1]),
                    secondary_y=True)
    theme.style_fig(fig, 360)
    fig.update_yaxes(title_text="°C", secondary_y=True, showgrid=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


st.markdown(
    theme.header_html("Бизнес Анализатор", "Продажби, печалба и прогнози на едно място"),
    unsafe_allow_html=True,
)

df_all = get_data()
costs = get_costs()

if df_all.empty:
    st.warning(
        "Няма данни. Качи продажби от таб Продажби или с командата "
        "`python -m ingest.load_excel файл.xlsx`."
    )
    st.stop()

# --- Филтър по обект (важи за таблото и чата, не за управлението на цените) ---
objects = ["Всички обекти"] + sorted(df_all["object_name"].dropna().unique().tolist())
chosen = st.sidebar.selectbox("Обект", objects)
df = df_all if chosen == "Всички обекти" else df_all[df_all["object_name"] == chosen]

tab_dash, tab_sales, tab_costs, tab_chat = st.tabs(
    ["Табло", "Продажби", "Себестойности", "Чат асистент"]
)

with tab_dash:
    deliv = metrics.delivery_split(df)
    deliv_rev = float(deliv.loc[deliv["channel"] == "Доставка", "revenue"].sum())
    total = metrics.total_revenue(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Общ оборот", f"{total:,.2f} лв.")
    c2.metric("Ръст (последен ден)", f"{metrics.growth_rate(df):+.1f}%")
    c3.metric("Дял доставки", f"{(deliv_rev / total * 100) if total else 0:.0f}%")

    st.subheader("Оборот по работен ден и прогноза")
    fc = forecast_revenue(df, days=7)
    chart(px.line(fc, x="business_date", y="revenue", color="kind", markers=True), 360)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Оборот по час")
        chart(px.bar(metrics.revenue_by_hour(df), x="sale_hour", y="revenue"))
        st.subheader("На място спрямо доставка")
        chart(px.pie(deliv, values="revenue", names="channel", hole=0.55))
    with col_b:
        st.subheader("Топ продукти")
        chart(px.bar(metrics.top_products(df), x="revenue", y="product_name",
                     orientation="h"))
        st.subheader("Оборот по категория")
        chart(px.bar(metrics.revenue_by_category(df), x="revenue", y="category",
                     orientation="h"))

    if not costs.empty:
        st.subheader("Печалба по продукт")
        st.dataframe(metrics.profit_by_product(df, costs), use_container_width=True,
                     hide_index=True)

    # --- Време и оборот ---
    st.subheader("Време и оборот")
    cities = sorted(set(config.OBJECT_CITY.values()))
    default_city = config.OBJECT_CITY.get(chosen) if chosen != "Всички обекти" else None
    idx = cities.index(default_city) if default_city in cities else 0

    wc1, wc2 = st.columns([3, 1])
    city = wc1.selectbox("Град", cities, index=idx, key="weather_city")
    if has_service_key():
        if wc2.button("Обнови времето", key="weather_refresh",
                      use_container_width=True):
            with st.spinner("Дърпам времето от Open-Meteo..."):
                try:
                    bdates = df_all["business_date"].dropna()
                    start = min(bdates) if len(bdates) else None
                    end = dt.date.today() + dt.timedelta(days=14)
                    n = weather_ingest.load_weather(start=start, end=end)
                    st.success(f"Обновени {n} реда за времето.")
                    get_weather.clear()
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Проблем с Open-Meteo: {e}")

    weather_all = get_weather()
    wcity = (
        weather_all[weather_all["city"] == city]
        if not weather_all.empty else weather_all
    )
    if wcity.empty:
        st.info(
            "Няма данни за времето за този град. Натисни бутона Обнови времето "
            "(иска service_role ключ и изходящ интернет)."
        )
    else:
        objs = [o for o, c in config.OBJECT_CITY.items() if c == city]
        daily = metrics.revenue_by_business_day(df_all[df_all["object_name"].isin(objs)])
        merged = correlate_with_sales(daily, wcity)
        if merged.empty:
            st.info("Няма припокриване между продажбите и времето за този град.")
        else:
            ct, cr = merged.attrs.get("corr_temp"), merged.attrs.get("corr_rain")
            m1, m2 = st.columns(2)
            m1.metric("Корелация с температурата",
                      f"{ct:+.2f}" if ct is not None and ct == ct else "—",
                      help="От -1 до +1. Положително = повече оборот при по-топло.")
            m2.metric("Корелация с валежите",
                      f"{cr:+.2f}" if cr is not None and cr == cr else "—",
                      help="Положително = повече оборот при дъжд (напр. доставки).")
            weather_chart(merged.sort_values("day"))


def _refresh():
    """Изчиства кеша и презарежда, за да се видят новокачените данни."""
    get_data.clear()
    get_costs.clear()
    st.rerun()


with tab_sales:
    can_write = has_service_key()
    if not can_write:
        st.warning(
            "За качване е нужен service_role ключ. Добави `SUPABASE_SERVICE_KEY` "
            "в Streamlit secrets (при деплой) или в `.env` (локално). Без него "
            "можеш само да преглеждаш данните."
        )

    st.subheader("Качване на продажби")
    st.caption(
        "Суров експорт от касовата система (Oбект, Номер, Дата и час, Мат. №, "
        "Стойност, Партньор...). Файлът се обработва автоматично — работен ден, "
        "доставка, връщане."
    )
    up = st.file_uploader("Избери .xlsx файл", type=["xlsx"], key="sales_upload")
    if up is not None:
        try:
            parsed = read_sales_excel(up)
            bdates = parsed["business_date"].dropna()
            period = f"{bdates.min()} – {bdates.max()}" if not bdates.empty else "—"
            st.write(f"Разпознати **{len(parsed)}** реда · работни дни: **{period}**")
            st.dataframe(parsed.head(50), use_container_width=True, hide_index=True)

            mode = st.radio(
                "Режим на качване",
                ["Добави към съществуващите", "Замести всички продажби"],
                help=(
                    "„Добави\" вкарва редовете към текущите (внимавай с дубликати "
                    "при повторно качване на същия файл). „Замести\" първо изтрива "
                    "всички стари продажби, после вкарва тези."
                ),
            )
            replace = mode.startswith("Замести")
            confirm = True
            if replace:
                confirm = st.checkbox(
                    "Потвърждавам, че ще изтрия всички досегашни продажби", value=False
                )

            if st.button("Качи в Supabase", type="primary",
                         disabled=not (can_write and confirm), key="sales_upload_btn"):
                with st.spinner("Качвам..."):
                    n = replace_all_sales(parsed) if replace else insert_sales(parsed)
                st.success(f"Готово. {'Заменени' if replace else 'Добавени'} {n} реда.")
                _refresh()
        except Exception as e:  # noqa: BLE001
            st.error(f"Проблем с файла или качването: {e}")


with tab_costs:
    can_write = has_service_key()
    if not can_write:
        st.warning(
            "За качване и редакция е нужен service_role ключ "
            "(`SUPABASE_SERVICE_KEY`). Без него можеш само да преглеждаш."
        )

    st.subheader("Продукти без себестойност")
    missing = metrics.missing_costs(df_all, costs)
    if missing.empty:
        st.success("Всички продавани продукти имат себестойност.")
    else:
        st.caption(
            f"{len(missing)} комбинации продукт и канал нямат себестойност — "
            "печалбата им излиза подвеждащо висока. Добави ги в таблицата по-долу."
        )
        st.dataframe(missing, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Качване на себестойности")
    st.caption(
        "Файл с лист Обекти (на място) и лист Доставки — колони Артикул и "
        "Обща стойност с ДДС."
    )
    up = st.file_uploader("Избери .xlsx файл", type=["xlsx"], key="costs_upload")
    if up is not None:
        try:
            parsed = read_costs_excel(up)
            st.write(f"Разпознати **{len(parsed)}** реда:")
            st.dataframe(parsed, use_container_width=True, hide_index=True, height=240)
            if st.button("Качи в Supabase", type="primary", disabled=not can_write):
                with st.spinner("Качвам..."):
                    n = upsert_costs(parsed)
                st.success(f"Качени или обновени {n} реда.")
                _refresh()
        except Exception as e:  # noqa: BLE001
            st.error(f"Проблем с файла: {e}")

    st.divider()

    st.subheader("Редакция на себестойностите")
    base = costs.copy()
    if base.empty:
        base = pd.DataFrame(columns=["product_name", "channel", "unit_cost"])
    edited = st.data_editor(
        base[["product_name", "channel", "unit_cost"]] if not base.empty else base,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        disabled=not can_write,
        column_config={
            "product_name": st.column_config.TextColumn("Продукт", required=True),
            "channel": st.column_config.SelectboxColumn(
                "Канал", options=["onsite", "delivery"], required=True
            ),
            "unit_cost": st.column_config.NumberColumn(
                "Себестойност", min_value=0.0, step=0.01, format="%.4f"
            ),
        },
        key="costs_editor",
    )
    if st.button("Запази промените", type="primary", disabled=not can_write):
        clean = edited.copy()
        clean["product_name"] = clean["product_name"].astype(str).str.strip()
        clean = clean[
            (clean["product_name"] != "")
            & clean["channel"].isin(["onsite", "delivery"])
        ]
        clean["unit_cost"] = pd.to_numeric(clean["unit_cost"], errors="coerce")
        clean = clean.drop_duplicates(subset=["product_name", "channel"], keep="last")
        clean["updated_at"] = pd.Timestamp.now(tz="UTC").isoformat()
        if clean.empty:
            st.warning("Няма валидни редове за запис.")
        else:
            try:
                with st.spinner("Запазвам..."):
                    n = upsert_costs(clean)
                st.success(f"Запазени {n} реда.")
                _refresh()
            except Exception as e:  # noqa: BLE001
                st.error(f"Проблем при запис: {e}")


with tab_chat:
    st.subheader("Чат асистент")
    st.caption(
        "Питай на естествен език за продажбите, доставките, маркетинга и "
        "прогнозите. Отговорите се смятат от реалните данни."
    )
    if not has_secret("OPENAI_API_KEY"):
        st.info(
            "Чатът иска `OPENAI_API_KEY` в Streamlit secrets или `.env`, за да "
            "отговаря. Таблото и качването работят и без него."
        )

    if "history" not in st.session_state:
        st.session_state.history = []

    examples = [
        "Кой е най-печелившият продукт?",
        "Как вървят доставките спрямо на място?",
        "Какъв оборот да очаквам следващата седмица?",
    ]
    if not st.session_state.history:
        cols = st.columns(len(examples))
        for col, q in zip(cols, examples):
            if col.button(q, key="ex_" + q, use_container_width=True):
                st.session_state.pending = q
                st.rerun()

    for m in st.session_state.history:
        st.chat_message(m["role"]).write(m["content"])

    typed = st.chat_input("Напиши въпрос...")
    question = typed or st.session_state.pop("pending", None)
    if question:
        st.chat_message("user").write(question)
        st.session_state.history.append({"role": "user", "content": question})
        with st.chat_message("assistant"):
            with st.spinner("Анализирам..."):
                try:
                    from bot.assistant import ask

                    answer = ask(question, df, costs, st.session_state.history[:-1])
                except Exception as e:  # noqa: BLE001
                    answer = f"Не успях да отговоря: {e}"
            st.write(answer)
        st.session_state.history.append({"role": "assistant", "content": answer})
