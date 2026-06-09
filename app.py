"""Бизнес Анализатор — уеб приложение (Streamlit).

Стартиране:  streamlit run app.py
"""
import plotly.express as px
import streamlit as st

from analytics import metrics
from analytics.data import load_costs, load_sales
from analytics.forecast import forecast_revenue

st.set_page_config(page_title="Бизнес Анализатор", page_icon="📊", layout="wide")


@st.cache_data(ttl=300)
def get_data():
    return load_sales()


@st.cache_data(ttl=300)
def get_costs():
    try:
        return load_costs()
    except Exception:
        import pandas as pd
        return pd.DataFrame()


st.title("📊 Бизнес Анализатор")
df = get_data()
costs = get_costs()

if df.empty:
    st.warning(
        "Няма данни. Качи Excel с:  "
        "`python -m ingest.load_excel файл.xlsx`"
    )
    st.stop()

# --- Филтър по обект ---
objects = ["Всички обекти"] + sorted(df["object_name"].dropna().unique().tolist())
chosen = st.sidebar.selectbox("Обект", objects)
if chosen != "Всички обекти":
    df = df[df["object_name"] == chosen]

tab_dash, tab_chat = st.tabs(["📈 Табло", "💬 Чат с асистента"])

with tab_dash:
    deliv = metrics.delivery_split(df)
    deliv_rev = float(deliv.loc[deliv["channel"] == "Доставка", "revenue"].sum())
    total = metrics.total_revenue(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Общ оборот", f"{total:,.2f} лв.")
    c2.metric("Ръст (последен ден)", f"{metrics.growth_rate(df):+.1f}%")
    c3.metric("Дял доставки", f"{(deliv_rev / total * 100) if total else 0:.0f}%")

    st.subheader("Оборот по работен ден + прогноза")
    fc = forecast_revenue(df, days=7)
    st.plotly_chart(
        px.line(fc, x="business_date", y="revenue", color="kind", markers=True),
        use_container_width=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Оборот по час")
        st.plotly_chart(
            px.bar(metrics.revenue_by_hour(df), x="sale_hour", y="revenue"),
            use_container_width=True,
        )
        st.subheader("На място vs Доставка")
        st.plotly_chart(
            px.pie(deliv, values="revenue", names="channel"),
            use_container_width=True,
        )
    with col_b:
        st.subheader("Топ продукти")
        st.plotly_chart(
            px.bar(metrics.top_products(df), x="revenue", y="product_name", orientation="h"),
            use_container_width=True,
        )
        st.subheader("Оборот по категория")
        st.plotly_chart(
            px.bar(metrics.revenue_by_category(df), x="revenue", y="category", orientation="h"),
            use_container_width=True,
        )

    if not costs.empty:
        st.subheader("Печалба по продукт")
        st.dataframe(metrics.profit_by_product(df, costs), use_container_width=True)

with tab_chat:
    st.caption("Питай за продажбите, доставките, маркетинга, прогнозите...")
    if "history" not in st.session_state:
        st.session_state.history = []
    for m in st.session_state.history:
        st.chat_message(m["role"]).write(m["content"])

    if prompt := st.chat_input("Напиши въпрос..."):
        st.chat_message("user").write(prompt)
        st.session_state.history.append({"role": "user", "content": prompt})
        from bot.assistant import ask
        with st.chat_message("assistant"):
            with st.spinner("Анализирам..."):
                answer = ask(prompt, df, costs, st.session_state.history[:-1])
            st.write(answer)
        st.session_state.history.append({"role": "assistant", "content": answer})
