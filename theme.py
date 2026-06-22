"""Споделена визуална тема: палитра, CSS за приложението и стил на графиките.

Светла тема с топъл (коралово-оранжев) акцент, без емоджи икони.
Ползва се от app.py (и от демо прегледа), за да е консистентно навсякъде.
"""

ACCENT = "#F25C3B"        # топъл коралово-оранжев
ACCENT_DARK = "#D8431F"
ACCENT_SOFT = "#FFEAE2"
TEXT = "#15181C"
MUTED = "#6B7280"
BG = "#FFFFFF"
BG_SOFT = "#F6F7F9"
BORDER = "#E8EAEE"

# Палитра за графиките (топло-водеща, но четима)
CHART_COLORS = [ACCENT, "#2DB5A3", "#3B82F6", "#F2B705", "#9B5DE5", "#64748B"]

FONT = "Inter, -apple-system, Segoe UI, Roboto, system-ui, sans-serif"


def style_fig(fig, height: int = 340):
    """Прилага консистентен, изчистен стил върху Plotly фигура."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT, size=13, color=TEXT),
        colorway=CHART_COLORS,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=8, r=8, t=14, b=8),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title_text=""),
        hoverlabel=dict(font_size=13, font_family=FONT),
    )
    fig.update_xaxes(gridcolor="#EEF0F3", zerolinecolor="#EEF0F3", title_text="")
    fig.update_yaxes(gridcolor="#EEF0F3", zerolinecolor="#EEF0F3", title_text="")
    return fig


def css() -> str:
    """CSS, който модернизира Streamlit (вмъква се през st.markdown)."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stMetric {{ font-family: {FONT}; }}
.stApp {{ background: {BG}; }}

/* Скриваме шумните елементи на Streamlit */
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }}

/* Заглавия */
h1, h2, h3 {{ color: {TEXT}; letter-spacing: -0.01em; }}
h2 {{ font-weight: 700; font-size: 1.15rem; margin: 0.4rem 0 0.6rem; }}
h3 {{ font-weight: 600; font-size: 1.0rem; color: {MUTED}; }}

/* Хедър на приложението */
.app-header {{ margin-bottom: 0.6rem; }}
.app-header .name {{ font-size: 1.7rem; font-weight: 800; color: {TEXT}; }}
.app-header .tag {{ color: {MUTED}; font-size: 0.95rem; margin-top: 2px; }}
.app-rule {{ height: 3px; width: 56px; background: {ACCENT};
  border-radius: 3px; margin: 10px 0 4px; }}

/* Метрики като карти */
[data-testid="stMetric"] {{
  background: {BG}; border: 1px solid {BORDER}; border-radius: 14px;
  padding: 16px 18px; box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}}
[data-testid="stMetricLabel"] p {{ color: {MUTED}; font-weight: 500; font-size: 0.85rem; }}
[data-testid="stMetricValue"] {{ font-weight: 800; color: {TEXT}; }}

/* Табове — изчистени, с акцентна подчертавка */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{
  background: transparent; border: none; padding: 10px 14px;
  font-weight: 600; color: {MUTED};
}}
.stTabs [aria-selected="true"] {{ color: {TEXT}; box-shadow: inset 0 -2px 0 {ACCENT}; }}

/* Бутони */
.stButton > button {{
  border-radius: 10px; font-weight: 600; border: 1px solid {BORDER};
  padding: 0.45rem 1.1rem; transition: all .15s ease;
}}
.stButton > button[kind="primary"] {{
  background: {ACCENT}; border-color: {ACCENT}; color: white;
}}
.stButton > button[kind="primary"]:hover {{ background: {ACCENT_DARK}; border-color: {ACCENT_DARK}; }}

/* Графични „карти" около plotly */
[data-testid="stPlotlyChart"] {{
  background: {BG}; border: 1px solid {BORDER}; border-radius: 14px;
  padding: 8px 6px 2px; box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}}

/* Чат */
[data-testid="stChatMessage"] {{ background: {BG_SOFT}; border-radius: 14px; }}

/* Полета за качване / редактор */
[data-testid="stFileUploaderDropzone"] {{ border-radius: 12px; border: 1.5px dashed {BORDER}; }}
hr {{ border-color: {BORDER}; }}

/* Чипове с примерни въпроси */
.chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 6px 0 2px; }}
.chip {{ background: {ACCENT_SOFT}; color: {ACCENT_DARK}; border-radius: 999px;
  padding: 6px 12px; font-size: 0.85rem; font-weight: 500; }}
</style>
"""


def header_html(title: str, tagline: str) -> str:
    """HTML за чистия хедър (вместо st.title с емоджи)."""
    return (
        f'<div class="app-header"><div class="name">{title}</div>'
        f'<div class="app-rule"></div>'
        f'<div class="tag">{tagline}</div></div>'
    )
