"""Споделена визуална тема „Призма": палитра, CSS и стил на графиките.

Топла, землиста светла тема: кремав фон, тийл-зелен акцент, меки карти.
Ползва се от app.py, за да е консистентно навсякъде.
"""

ACCENT = "#2f7a6f"        # тийл-зелен (основен акцент)
ACCENT_DARK = "#256156"
ACCENT_SOFT = "#e4f0ee"
TEXT = "#1b1c17"
MUTED = "#6c6f64"
BG = "#f4f2ed"            # кремав фон
SURFACE = "#ffffff"       # карти
BORDER = "#e6e3da"

# Палитра за графиките (землисти, но четими)
CHART_COLORS = ["#2f7a6f", "#c98a2b", "#b5654a", "#6a7bd6", "#2f8f5b", "#c5573f"]

FONT = "'Hanken Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"


def style_fig(fig, height: int = 340):
    """Прилага консистентен стил на „Призма" върху Plotly фигура."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT, size=13, color=TEXT),
        colorway=CHART_COLORS,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        margin=dict(l=8, r=8, t=14, b=8),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title_text=""),
        hoverlabel=dict(font_size=13, font_family=FONT),
    )
    fig.update_xaxes(gridcolor="#efece4", zerolinecolor="#efece4", title_text="")
    fig.update_yaxes(gridcolor="#efece4", zerolinecolor="#efece4", title_text="")
    return fig


def css() -> str:
    """CSS, който придава вида на „Призма" (вмъква се през st.markdown)."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown,
[class*="st-"], button, input, textarea, select {{ font-family: {FONT} !important; }}
.stApp {{ background: {BG}; }}

#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px; }}

/* Заглавия */
h1, h2, h3 {{ color: {TEXT}; letter-spacing: -0.01em; }}
/* Ляв акцентен кант на секциите (подпис на „Призма") */
.stApp h3 {{
  font-weight: 650; font-size: 1.02rem; margin: 0.6rem 0 0.5rem;
  border-left: 3px solid {ACCENT}; padding-left: 10px;
}}

/* Хедър */
.app-header {{ margin-bottom: 0.6rem; }}
.app-header .name {{ font-size: 1.8rem; font-weight: 800; color: {TEXT}; }}
.app-header .tag {{ color: {MUTED}; font-size: 0.95rem; margin-top: 2px; }}
.app-rule {{ height: 3px; width: 56px; background: {ACCENT};
  border-radius: 3px; margin: 10px 0 4px; }}

/* Метрики като меки карти */
[data-testid="stMetric"] {{
  background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px;
  padding: 16px 18px; box-shadow: 0 4px 16px rgba(0,0,0,0.04);
}}
[data-testid="stMetricLabel"] p {{ color: {MUTED}; font-weight: 500; font-size: 0.85rem; }}
[data-testid="stMetricValue"] {{ font-weight: 800; color: {TEXT}; }}

/* Табове */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{
  background: transparent; border: none; padding: 10px 14px;
  font-weight: 600; color: {MUTED};
}}
.stTabs [aria-selected="true"] {{ color: {ACCENT}; box-shadow: inset 0 -2px 0 {ACCENT}; }}

/* Бутони */
.stButton > button {{
  border-radius: 10px; font-weight: 600; border: 1px solid {BORDER};
  padding: 0.45rem 1.1rem; transition: all .15s ease; color: {TEXT};
}}
.stButton > button[kind="primary"] {{
  background: {ACCENT}; border-color: {ACCENT}; color: white;
}}
.stButton > button[kind="primary"]:hover {{ background: {ACCENT_DARK}; border-color: {ACCENT_DARK}; }}

/* Графични карти */
[data-testid="stPlotlyChart"] {{
  background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px;
  padding: 10px 8px 4px; box-shadow: 0 4px 16px rgba(0,0,0,0.04);
}}

/* Чат / таблици / качване */
[data-testid="stChatMessage"] {{ background: {SURFACE}; border: 1px solid {BORDER};
  border-radius: 16px; }}
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
[data-testid="stFileUploaderDropzone"] {{ border-radius: 12px; border: 1.5px dashed {BORDER};
  background: {SURFACE}; }}
hr {{ border-color: {BORDER}; }}

/* ===== Скелет „Призма" ===== */
/* Тъмна странична лента */
[data-testid="stSidebar"] {{ background: #181a14; }}
[data-testid="stSidebar"] * {{ color: #e8e7e1 !important; }}
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
  display: flex; align-items: center; padding: 9px 12px; border-radius: 10px;
  margin: 1px 0; cursor: pointer; transition: background .12s ease;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background: rgba(255,255,255,.06); }}
[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"],
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background: rgba(47,122,111,.22); box-shadow: inset 2.5px 0 0 {ACCENT};
}}
[data-testid="stSidebar"] [role="radiogroup"] div[data-testid="stMarkdownContainer"] {{ font-weight: 600; }}
.pz-brand {{ font-size: 1.4rem; font-weight: 800; color: #fff !important; }}
.pz-brand small {{ display:block; font-size:.62rem; letter-spacing:.18em;
  color:#9aa08f !important; font-weight:700; margin-top:2px; }}

/* Поздрав */
.pz-hello {{ font-size: 1.7rem; font-weight: 800; color: {TEXT}; margin: 2px 0 2px; }}
.pz-sub {{ color: {MUTED}; font-size: .92rem; margin-bottom: 14px; }}

/* KPI карти */
.pz-kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }}
.pz-kpi {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px;
  padding: 14px 16px; box-shadow: 0 4px 16px rgba(0,0,0,.04); }}
.pz-kpi-top {{ display:flex; justify-content:space-between; align-items:center; }}
.pz-kpi-label {{ color:{MUTED}; font-size:.72rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; }}
.pz-kpi-value {{ font-size:1.55rem; font-weight:800; color:{TEXT}; margin:6px 0 2px; }}
.pz-kpi-spark {{ margin-top:4px; }}

/* Карти */
.pz-card {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:16px;
  padding:16px 18px; box-shadow:0 4px 16px rgba(0,0,0,.04); margin-bottom:16px; }}
.pz-card-title {{ font-size:.72rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:{MUTED}; display:flex; justify-content:space-between; }}
.pz-card-value {{ color:{TEXT}; font-size:1.2rem; font-weight:800; letter-spacing:0; text-transform:none; }}

/* Списък топ + барове */
.pz-row {{ margin:9px 0; }}
.pz-row-top {{ display:flex; justify-content:space-between; font-size:.9rem; color:{TEXT}; }}
.pz-bar {{ height:6px; background:#efece4; border-radius:999px; margin-top:5px; overflow:hidden; }}
.pz-bar-fill {{ height:100%; background:{ACCENT}; border-radius:999px; }}

/* Инсайти */
.pz-insight {{ display:flex; gap:9px; align-items:flex-start; padding:8px 0;
  border-bottom:1px solid {BORDER}; font-size:.9rem; color:{TEXT}; }}
.pz-insight:last-child {{ border-bottom:none; }}
.pz-dot {{ width:8px; height:8px; border-radius:50%; margin-top:6px; flex:0 0 auto; }}
.pz-muted {{ color:{MUTED}; font-size:.9rem; }}
</style>
"""


def header_html(title: str, tagline: str) -> str:
    """HTML за хедъра на „Призма"."""
    return (
        f'<div class="app-header"><div class="name">{title}</div>'
        f'<div class="app-rule"></div>'
        f'<div class="tag">{tagline}</div></div>'
    )
