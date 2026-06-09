"""Бизнес Анализатор — уеб приложение (Streamlit).

Стартиране:  streamlit run app.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import metrics
from analytics.data import load_costs, load_sales
from analytics.forecast import forecast_revenue
from db.costs_repo import upsert_costs
from db.sales_repo import insert_sales, replace_all_sales
from db.supabase_client import has_service_key
from ingest.load_costs import read_costs_excel
from ingest.load_excel import read_sales_excel

st.set_page_config(page_title="Бизнес Анализатор", page_icon="📊", layout="wide")


@st.cache_data(ttl=300)
def get_data():
    return load_sales()


@st.cache_data(ttl=300)
def get_costs():
    try:
        return load_costs()
    except Exception:
        return pd.DataFrame()


st.title("📊 Бизнес Анализатор")
df_all = get_data()
costs = get_costs()

if df_all.empty:
    st.warning(
        "Няма данни. Качи Excel с:  "
        "`python -m ingest.load_excel файл.xlsx`"
    )
    st.stop()

# --- Филтър по обект (важи за таблото и чата, не за управлението на цените) ---
objects = ["Всички обекти"] + sorted(df_all["object_name"].dropna().unique().tolist())
chosen = st.sidebar.selectbox("Обект", objects)
df = df_all if chosen == "Всички обекти" else df_all[df_all["object_name"] == chosen]

tab_dash, tab_sales, tab_costs, tab_chat = st.tabs(
    ["📈 Табло", "⬆️ Продажби", "💰 Себестойности", "💬 Чат с асистента"]
)

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


def _refresh():
    """Изчиства кеша и презарежда, за да се видят новокачените данни."""
    get_data.clear()
    get_costs.clear()
    st.rerun()


with tab_sales:
    if not has_service_key():
        st.warning(
            "⚠️ За качване е нужен **service_role** ключ. Добави "
            "`SUPABASE_SERVICE_KEY` в Streamlit secrets (при деплой) или в "
            "`.env` (локално). Без него можеш само да преглеждаш данните."
        )
    can_write = has_service_key()

    st.subheader("⬆️ Качване на продажби (Excel)")
    st.caption(
        "Суров експорт с колоните от касовата система (Oбект, Номер, "
        "Дата и час, Мат. №, Стойност, Партньор...). Файлът се обработва "
        "автоматично (работен ден, доставка, връщане)."
    )
    up = st.file_uploader("Избери .xlsx файл", type=["xlsx"], key="sales_upload")
    if up is not None:
        try:
            parsed = read_sales_excel(up)
            bdates = parsed["business_date"].dropna()
            period = (
                f"{bdates.min()} – {bdates.max()}" if not bdates.empty else "—"
            )
            st.write(
                f"Разпознати **{len(parsed)}** реда · работни дни: **{period}**"
            )
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

            if st.button(
                "Качи в Supabase",
                type="primary",
                disabled=not (can_write and confirm),
                key="sales_upload_btn",
            ):
                with st.spinner("Качвам..."):
                    n = (
                        replace_all_sales(parsed)
                        if replace
                        else insert_sales(parsed)
                    )
                st.success(f"Готово! {'Заменени' if replace else 'Добавени'} {n} реда.")
                _refresh()
        except Exception as e:  # noqa: BLE001
            st.error(f"Проблем с файла или качването: {e}")


with tab_costs:
    if not has_service_key():
        st.warning(
            "⚠️ За качване и редакция е нужен **service_role** ключ. Добави "
            "`SUPABASE_SERVICE_KEY` в `.env` (локално) или в Streamlit secrets "
            "(при деплой). Без него можеш само да преглеждаш."
        )
    can_write = has_service_key()

    # --- Липсващи себестойности (продукти с продажби, но без цена) ---
    st.subheader("⚠️ Продукти без себестойност")
    missing = metrics.missing_costs(df_all, costs)
    if missing.empty:
        st.success("Всички продавани продукти имат себестойност. 👌")
    else:
        st.caption(
            f"{len(missing)} комбинации продукт×канал нямат себестойност — "
            "печалбата им излиза подвеждащо висока. Добави ги в таблицата по-долу."
        )
        st.dataframe(missing, use_container_width=True, hide_index=True)

    st.divider()

    # --- Качване на Excel със себестойности ---
    st.subheader("📤 Качване на Excel")
    st.caption(
        "Файл с лист Обекти (на място) и лист Доставки — колони "
        "Артикул и Обща стойност с ДДС."
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
                st.success(f"Качени/обновени {n} реда.")
                _refresh()
        except Exception as e:  # noqa: BLE001
            st.error(f"Проблем с файла: {e}")

    st.divider()

    # --- Редакция на съществуващите себестойности ---
    st.subheader("✏️ Редакция на себестойностите")
    base = costs.copy()
    if base.empty:
        base = pd.DataFrame(columns=["product_name", "channel", "unit_cost"])
    edited = st.data_editor(
        base[["product_name", "channel", "unit_cost"]]
        if not base.empty else base,
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
