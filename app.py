"""Призма — уеб приложение за бизнес анализ (Streamlit).

Стартиране:  streamlit run app.py
"""
import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.subplots import make_subplots

import config
import ingest.load_weather as weather_ingest
import prizma
import theme
from analytics import metrics
from analytics.data import load_costs, load_sales, load_weather
from analytics.forecast import forecast_revenue
from analytics.weather import correlate_with_sales
from db.costs_repo import upsert_costs
from db.sales_repo import insert_sales, replace_all_sales
from db.supabase_client import get_secret, has_secret, has_service_key
from ingest.load_costs import read_costs_excel
from ingest.load_excel import read_sales_excel

st.set_page_config(page_title="Призма", layout="wide", initial_sidebar_state="expanded")
st.markdown(theme.css(), unsafe_allow_html=True)


def require_password():
    expected = get_secret("APP_PASSWORD")
    if not expected or st.session_state.get("auth_ok"):
        return
    st.markdown(theme.header_html("Призма", "Въведи парола за достъп"),
                unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Парола", type="password")
        if st.form_submit_button("Вход"):
            if pwd == expected:
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Грешна парола.")
    st.stop()


require_password()


@st.cache_data(ttl=300)
def get_data():
    try:
        return load_sales()
    except Exception:
        return pd.DataFrame()


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


def _refresh():
    get_data.clear(); get_costs.clear(); st.rerun()


def chart(fig, height=320):
    st.plotly_chart(theme.style_fig(fig, height), use_container_width=True,
                    config={"displayModeBar": False})


def _orders(d):
    return int(d["order_no"].nunique()) if "order_no" in d and d["order_no"].notna().any() else len(d)


def _kpis(d):
    total = float(pd.to_numeric(d["amount"], errors="coerce").sum())
    n = _orders(d)
    avg = total / n if n else 0.0
    deliv = float(pd.to_numeric(d.loc[d["is_delivery"], "amount"], errors="coerce").sum()) if "is_delivery" in d else 0.0
    dshare = deliv / total * 100 if total else 0.0
    return total, n, avg, dshare


def _pct(cur, prev):
    return (cur - prev) / prev * 100 if prev else None


df_all = get_data()
costs = get_costs()
has_data = not df_all.empty

# ===== Странична лента =====
with st.sidebar:
    st.markdown('<div class="pz-brand">Призма<small>АНАЛИЗИ</small></div>',
                unsafe_allow_html=True)
    st.write("")
    NAV = ["Табло", "AI Чат", "Метрики", "Прогнози", "Сегменти", "Качи данни"]
    nav = st.radio("Навигация", NAV, label_visibility="collapsed")
    st.divider()
    if has_data:
        objects = ["Всички обекти"] + sorted(df_all["object_name"].dropna().unique().tolist())
        chosen = st.selectbox("Обект", objects)
    else:
        chosen = "Всички обекти"

df = df_all if chosen == "Всички обекти" else df_all[df_all["object_name"] == chosen]


def period_filter(d):
    """Лента с период (по референтна дата = последния работен ден в данните)."""
    opts = {"7 дни": 7, "30 дни": 30, "90 дни": 90, "12 мес": 365}
    sel = st.radio("Период", list(opts), index=2, horizontal=True,
                   label_visibility="collapsed")
    days = opts[sel]
    bdate = pd.to_datetime(d["business_date"], errors="coerce")
    if bdate.notna().any():
        end = bdate.max()
        cur = d[bdate > end - pd.Timedelta(days=days)]
        prev = d[(bdate <= end - pd.Timedelta(days=days)) &
                 (bdate > end - pd.Timedelta(days=2 * days))]
        return cur, prev, sel
    return d, d.iloc[0:0], sel


def greeting():
    hr = dt.datetime.now().hour
    g = "Добро утро" if hr < 12 else ("Добър ден" if hr < 18 else "Добра вечер")
    return g


# ===== Без данни (освен на „Качи данни") =====
if not has_data and nav != "Качи данни":
    st.markdown(theme.header_html("Призма", "Анализ на продажби, печалба и прогнози"),
                unsafe_allow_html=True)
    st.info("Все още няма данни. Отвори раздел Качи данни от менюто и качи продажби.")
    st.stop()


# ===== ТАБЛО =====
if nav == "Табло":
    cur, prev, sel = period_filter(df)
    st.markdown(f'<div class="pz-hello">{greeting()}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pz-sub">Преглед за продажби и операции · {sel} · '
                f'спрямо предходен период</div>', unsafe_allow_html=True)

    t, n, avg, ds = _kpis(cur)
    pt, pn, pavg, pds = _kpis(prev)
    spark = metrics.revenue_by_business_day(cur)["revenue"].tail(30).tolist()
    cards = [
        prizma.kpi_card("Приходи", f"€{t:,.0f}".replace(",", " "), _pct(t, pt), spark),
        prizma.kpi_card("Поръчки", f"{n:,}".replace(",", " "), _pct(n, pn), spark),
        prizma.kpi_card("Среден чек", f"€{avg:,.0f}".replace(",", " "), _pct(avg, pavg), spark),
        prizma.kpi_card("Дял доставки", f"{ds:.0f}%", _pct(ds, pds), spark,
                        theme.CHART_COLORS[1]),
    ]
    st.markdown(prizma.kpi_row(cards), unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Приходи · тренд")
        fc = forecast_revenue(cur, days=7)
        chart(px.line(fc, x="business_date", y="revenue", color="kind", markers=True), 330)
    with c2:
        st.subheader("Канали")
        deliv = metrics.delivery_split(cur)
        chart(px.pie(deliv, values="revenue", names="channel", hole=0.6), 250)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Топ продукти")
        st.markdown(prizma.top_list(metrics.top_products(cur), "product_name", "revenue"),
                    unsafe_allow_html=True)
    with c4:
        st.subheader("AI инсайти")
        ins = []
        obj = metrics.revenue_by_object(cur)
        if not obj.empty:
            ins.append(("pos", f"Най-силен обект: {obj.iloc[0]['object_name']} "
                               f"({obj.iloc[0]['revenue']:,.0f} лв.)"))
        cat = metrics.revenue_by_category(cur)
        if not cat.empty:
            ins.append(("info", f"Водеща категория: {cat.iloc[0]['category']}"))
        ins.append(("warn" if ds < 25 else "pos",
                    f"Доставките са {ds:.0f}% от оборота"))
        miss = metrics.missing_costs(cur, costs)
        if not miss.empty:
            ins.append(("neg", f"{len(miss)} продукта без себестойност — печалбата е неточна"))
        st.markdown(prizma.insights(ins), unsafe_allow_html=True)

# ===== AI ЧАТ =====
elif nav == "AI Чат":
    st.markdown('<div class="pz-hello">AI Чат</div>', unsafe_allow_html=True)
    st.markdown('<div class="pz-sub">Питай за приходите, обектите, продуктите, '
                'прогнозите и времето — отговарям с реалните числа.</div>',
                unsafe_allow_html=True)
    if not has_secret("OPENAI_API_KEY"):
        st.info("Чатът иска `OPENAI_API_KEY` в Streamlit secrets, за да отговаря.")
    if "history" not in st.session_state:
        st.session_state.history = []
    examples = ["Кой обект е най-силен?", "Кои дни от седмицата водят?",
                "Какъв оборот да очаквам?", "При дъжд какво става с доставките?"]
    if not st.session_state.history:
        cols = st.columns(len(examples))
        for col, q in zip(cols, examples):
            if col.button(q, key="ex_" + q, use_container_width=True):
                st.session_state.pending = q
                st.rerun()
    for m in st.session_state.history:
        st.chat_message(m["role"]).write(m["content"])
    typed = st.chat_input("Питай за данните си...")
    question = typed or st.session_state.pop("pending", None)
    if question:
        st.chat_message("user").write(question)
        st.session_state.history.append({"role": "user", "content": question})
        with st.chat_message("assistant"):
            with st.spinner("Анализирам..."):
                try:
                    from bot.assistant import ask
                    answer = ask(question, df_all, costs,
                                 st.session_state.history[:-1], weather=get_weather())
                except Exception as e:  # noqa: BLE001
                    answer = f"Не успях да отговоря: {e}"
            st.write(answer)
        st.session_state.history.append({"role": "assistant", "content": answer})

# ===== МЕТРИКИ =====
elif nav == "Метрики":
    cur, prev, sel = period_filter(df)
    st.markdown('<div class="pz-hello">Детайлен анализ</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pz-sub">Разбивки · {sel}</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        st.subheader("Оборот по час")
        chart(px.bar(metrics.revenue_by_hour(cur), x="sale_hour", y="revenue"))
        st.subheader("Оборот по обект")
        chart(px.bar(metrics.revenue_by_object(cur), x="revenue", y="object_name",
                     orientation="h"), 380)
    with b:
        st.subheader("Оборот по категория")
        chart(px.bar(metrics.revenue_by_category(cur), x="revenue", y="category",
                     orientation="h"))
        st.subheader("На място спрямо доставка")
        chart(px.pie(metrics.delivery_split(cur), values="revenue", names="channel",
                     hole=0.6), 280)
    if not costs.empty:
        st.subheader("Печалба по продукт")
        st.dataframe(metrics.profit_by_product(cur, costs), use_container_width=True,
                     hide_index=True)

# ===== ПРОГНОЗИ =====
elif nav == "Прогнози":
    st.markdown('<div class="pz-hello">Прогнози и сценарии</div>', unsafe_allow_html=True)
    st.markdown('<div class="pz-sub">Тренд и очаквания за следващите дни</div>',
                unsafe_allow_html=True)
    scenario = st.radio("Сценарий", ["Оптимистичен", "Базов", "Консервативен"],
                        index=1, horizontal=True, label_visibility="collapsed")
    factor = {"Оптимистичен": 1.1, "Базов": 1.0, "Консервативен": 0.9}[scenario]
    fc = forecast_revenue(df, days=14).copy()
    fc.loc[fc["kind"] == "forecast", "revenue"] *= factor
    chart(px.line(fc, x="business_date", y="revenue", color="kind", markers=True), 360)
    fut = fc[fc["kind"] == "forecast"]["revenue"].sum()
    k1, k2, k3 = st.columns(3)
    k1.metric("Прогноза (14 дни)", f"{fut:,.0f} лв.")
    k2.metric("Сценарий", scenario)
    k3.metric("Дневен ръст", f"{metrics.growth_rate(df):+.1f}%")

    st.subheader("Време и оборот")
    if chosen != "Всички обекти":
        city = config.city_for(chosen)
        sales_for_corr = df
        st.caption(f"Регион на обекта: {city}" if city else "Няма зададен регион.")
    else:
        cities = sorted(set(config.OBJECT_CITY.values()))
        city = st.selectbox("Град", cities, key="weather_city")
        sales_for_corr = df_all[df_all["object_name"].map(lambda n: config.city_for(n) == city)]
    if has_service_key() and st.button("Обнови времето"):
        with st.spinner("Дърпам времето от Open-Meteo..."):
            try:
                bd = df_all["business_date"].dropna()
                n = weather_ingest.load_weather(start=min(bd) if len(bd) else None,
                                                end=dt.date.today() + dt.timedelta(days=14))
                st.success(f"Обновени {n} реда."); get_weather.clear(); st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Проблем с Open-Meteo: {e}")
    wall = get_weather()
    wcity = wall[wall["city"] == city] if city and not wall.empty else wall.iloc[0:0]
    if city and not wcity.empty:
        merged = correlate_with_sales(metrics.revenue_by_business_day(sales_for_corr), wcity)
        if not merged.empty:
            ct, cr = merged.attrs.get("corr_temp"), merged.attrs.get("corr_rain")
            w1, w2 = st.columns(2)
            w1.metric("Корелация с температурата",
                      f"{ct:+.2f}" if ct is not None and ct == ct else "—")
            w2.metric("Корелация с валежите",
                      f"{cr:+.2f}" if cr is not None and cr == cr else "—")
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            m = merged.sort_values("day")
            fig.add_bar(x=m["day"], y=m["revenue"], name="Оборот", marker_color=theme.ACCENT)
            fig.add_scatter(x=m["day"], y=m["temp_max"], name="Макс. темп.",
                            mode="lines+markers", line=dict(color=theme.CHART_COLORS[1]),
                            secondary_y=True)
            theme.style_fig(fig, 340)
            fig.update_yaxes(title_text="°C", secondary_y=True, showgrid=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    elif city:
        st.info("Няма данни за времето за този регион. Натисни Обнови времето.")

# ===== СЕГМЕНТИ (по обект/регион) =====
elif nav == "Сегменти":
    cur, prev, sel = period_filter(df)
    st.markdown('<div class="pz-hello">Сегменти</div>', unsafe_allow_html=True)
    st.markdown('<div class="pz-sub">По обекти и региони · '
                'нямаме клиентски данни, затова сегментираме обектите</div>',
                unsafe_allow_html=True)
    obj = metrics.revenue_by_object(cur)
    a, b = st.columns([3, 2])
    with a:
        st.subheader("Оборот по обект")
        chart(px.bar(obj, x="revenue", y="object_name", orientation="h"), 460)
    with b:
        st.subheader("По регион")
        reg = cur.copy()
        reg["region"] = reg["object_name"].map(config.city_for)
        rg = reg.groupby("region")["amount"].sum().sort_values(ascending=False).reset_index(name="revenue")
        chart(px.pie(rg, values="revenue", names="region", hole=0.6), 320)

# ===== КАЧИ ДАННИ =====
elif nav == "Качи данни":
    st.markdown('<div class="pz-hello">Качи данни</div>', unsafe_allow_html=True)
    can_write = has_service_key()
    if not can_write:
        st.warning("За качване е нужен `SUPABASE_SERVICE_KEY` в Streamlit secrets.")
    st.subheader("Продажби")
    up = st.file_uploader("Excel с продажби", type=["xlsx"], key="sales_up")
    if up is not None:
        try:
            parsed = read_sales_excel(up)
            st.write(f"Разпознати {len(parsed)} реда.")
            mode = st.radio("Режим", ["Добави", "Замести всички"], horizontal=True)
            replace = mode.startswith("Замести")
            ok = st.checkbox("Потвърждавам изтриването", value=False) if replace else True
            if st.button("Качи продажби", type="primary", disabled=not (can_write and ok)):
                with st.spinner("Качвам..."):
                    nrec = replace_all_sales(parsed) if replace else insert_sales(parsed)
                st.success(f"Готово: {nrec} реда."); _refresh()
        except Exception as e:  # noqa: BLE001
            st.error(f"Проблем: {e}")

    st.divider()
    st.subheader("Себестойности")
    if has_data:
        miss = metrics.missing_costs(df_all, costs)
        if not miss.empty:
            st.caption(f"{len(miss)} продукта без себестойност:")
            st.dataframe(miss, use_container_width=True, hide_index=True, height=180)
    upc = st.file_uploader("Excel със себестойности", type=["xlsx"], key="costs_up")
    if upc is not None:
        try:
            parsed = read_costs_excel(upc)
            st.write(f"Разпознати {len(parsed)} реда.")
            if st.button("Качи себестойности", type="primary", disabled=not can_write):
                with st.spinner("Качвам..."):
                    nrec = upsert_costs(parsed)
                st.success(f"Готово: {nrec} реда."); _refresh()
        except Exception as e:  # noqa: BLE001
            st.error(f"Проблем: {e}")
