# ruff: noqa: E501  # CSS data URLs cannot use string concatenation; the inline-SVG noise filter is unavoidably long.
"""Sumi-e / scroll-report theme for the L7R combat simulator UI.

Lives under ``web/views/`` so it inherits the coverage-omit pattern
that applies to Streamlit page modules (``pyproject.toml`` →
``[tool.coverage.run].omit``).  These helpers are pure markup; they
emit HTML strings via ``st.markdown(unsafe_allow_html=True)`` and
have no engine-side semantics.

Aesthetic direction:
  * Cream / parchment background, brushwork ink black, vermillion
    seal-stamp accents, single gold trim.
  * Display: Shippori Mincho.  Body: Cormorant Garamond.  Numeric /
    dice / pills: JetBrains Mono.
  * Status carriers (fight cards, status snapshots, section heads)
    are rendered as discrete HTML blocks so they stand apart from
    the surrounding Streamlit widgets and the rendered combat-trace
    markdown.

The intent is intentional restraint — bold via typography, negative
space, and one strong accent colour, not via density.  Constitution
Principle II is preserved: nothing here imports from ``simulation/``.
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

# ── Fonts + global theme CSS ──────────────────────────────────────────

_GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Shippori+Mincho:wght@500;700;800&'
    'family=Cormorant+Garamond:ital,wght@0,400;0,500;0,700;1,400&'
    'family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">'
)

_THEME_CSS = """
<style>
:root {
  --paper:      #f4ecd8;
  --paper-2:    #ede2c4;
  --paper-3:    #e3d4b0;
  --ink:        #14110d;
  --ink-soft:   #3a322a;
  --ink-faded:  #6e6354;
  --seal:       #b3261e;
  --seal-deep:  #7a1a14;
  --gold:       #b08642;
  --jade:       #5a7a3a;
  --crab-blue:  #1d3550;
}

/* ── Page surface ───────────────────────────────────────────────── */
html, body, .stApp, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(ellipse 80% 60% at 30% 20%, rgba(255,255,255,0.5), transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(0,0,0,0.04), transparent 60%),
    var(--paper) !important;
  color: var(--ink) !important;
  font-family: 'Cormorant Garamond', Georgia, serif !important;
}

/* paper grain overlay — inline SVG noise filter as a data URL; the
   long line is unavoidable since CSS data URLs do not support
   string concatenation. */
[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.08 0 0 0 0 0.07 0 0 0 0 0.05 0 0 0 0.08 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  opacity: 0.4;
  pointer-events: none;
  z-index: 0;
  mix-blend-mode: multiply;
}
[data-testid="stMain"] { z-index: 1; position: relative; }

.stMainBlockContainer {
  max-width: 100% !important;
  padding-top: 1rem !important;
}

/* ── Typography ────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
  font-family: 'Shippori Mincho', serif !important;
  color: var(--ink) !important;
  letter-spacing: -0.01em;
  font-weight: 700;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span:not(.chronicle-strong):not(.chronicle-red) {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 17px;
  line-height: 1.55;
  color: var(--ink-soft);
}
[data-testid="stMarkdownContainer"] strong { color: var(--ink); }
[data-testid="stMarkdownContainer"] code {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 13px;
  background: var(--paper-2);
  color: var(--ink) !important;
  padding: 1px 6px;
  border: 1px solid var(--ink-faded);
  border-radius: 0;
}

/* ── Streamlit chrome overrides ─────────────────────────────── */
[data-testid="stHeader"] {
  background: transparent !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: var(--paper-2) !important;
  border-right: 1.5px solid var(--ink) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * {
  color: var(--ink) !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  font-family: 'Shippori Mincho', serif !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.14em !important;
  text-transform: uppercase !important;
  background: var(--ink) !important;
  color: var(--paper) !important;
  border: 1.5px solid var(--ink) !important;
  border-radius: 0 !important;
  padding: 10px 22px !important;
  transition: background .12s, color .12s !important;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  background: var(--seal) !important;
  border-color: var(--seal-deep) !important;
  color: var(--paper) !important;
}
.stButton > button:focus, .stDownloadButton > button:focus, .stFormSubmitButton > button:focus {
  box-shadow: 0 0 0 2px var(--paper), 0 0 0 3px var(--seal) !important;
  outline: none !important;
}

/* Tertiary buttons — used by the combat trace as click-for-modal
   roll links.  Keep them looking like prose, not buttons. */
button[kind="tertiary"] {
  font-family: 'JetBrains Mono', monospace !important;
  background: transparent !important;
  border: none !important;
  border-bottom: 1px dotted var(--seal) !important;
  color: var(--ink-soft) !important;
  padding: 0 2px !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  font-size: 13px !important;
  line-height: 1.5 !important;
  margin: 0 !important;
}
button[kind="tertiary"]:hover {
  background: rgba(179,38,30,0.08) !important;
  color: var(--seal) !important;
  border-bottom-color: var(--seal-deep) !important;
}
button[kind="tertiary"], button[kind="tertiary"] * {
  user-select: text !important;
  -webkit-user-select: text !important;
  cursor: text;
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div {
  background: var(--paper) !important;
  border: 1.5px solid var(--ink) !important;
  border-radius: 0 !important;
  color: var(--ink) !important;
  font-family: 'Cormorant Garamond', Georgia, serif !important;
}
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stMultiSelect label, .stSlider label, .stCheckbox label,
.stRadio label {
  font-family: 'Shippori Mincho', serif !important;
  font-size: 11px !important;
  letter-spacing: 0.24em !important;
  text-transform: uppercase !important;
  color: var(--ink-soft) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  border-bottom: 1.5px solid var(--ink) !important;
  gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Shippori Mincho', serif !important;
  font-weight: 700 !important;
  font-size: 12px !important;
  letter-spacing: 0.22em !important;
  text-transform: uppercase !important;
  color: var(--ink-faded) !important;
  padding: 10px 22px !important;
  background: transparent !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: var(--ink) !important;
  border-bottom: 2px solid var(--seal) !important;
}

/* Expander */
[data-testid="stExpander"] {
  background: var(--paper-2) !important;
  border: 1px solid var(--ink-faded) !important;
  border-left: 3px solid var(--ink) !important;
  border-radius: 0 !important;
}
[data-testid="stExpander"] summary {
  font-family: 'Shippori Mincho', serif !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.16em !important;
  text-transform: uppercase !important;
  color: var(--ink) !important;
}

/* Metric tiles */
[data-testid="stMetric"] {
  background: var(--paper-2);
  border: 1px solid var(--ink-faded);
  border-left: 4px solid var(--ink);
  padding: 14px 18px;
}
[data-testid="stMetricLabel"] {
  font-family: 'Shippori Mincho', serif !important;
  font-size: 10px !important;
  letter-spacing: 0.32em !important;
  text-transform: uppercase !important;
  color: var(--ink-faded) !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Shippori Mincho', serif !important;
  font-weight: 800 !important;
  font-size: 36px !important;
  color: var(--ink) !important;
  line-height: 1 !important;
}

/* Alerts */
[data-testid="stAlert"] {
  background: var(--paper-2) !important;
  border: 1px solid var(--ink-faded) !important;
  border-left: 4px solid var(--seal) !important;
  border-radius: 0 !important;
  color: var(--ink) !important;
}

/* Dividers */
hr, [data-testid="stDivider"] {
  border-color: var(--ink-faded) !important;
  opacity: 0.5;
}

/* Dialog (modal) */
[role="dialog"] {
  background: var(--paper) !important;
  border: 2px solid var(--ink) !important;
  border-radius: 0 !important;
}
[role="dialog"] h1, [role="dialog"] h2, [role="dialog"] h3 {
  font-family: 'Shippori Mincho', serif !important;
  color: var(--ink) !important;
}

/* Spinner */
.stSpinner > div {
  border-color: var(--ink-faded) !important;
  border-top-color: var(--seal) !important;
}

/* Bar chart base color (Streamlit's built-in chart uses Altair).
   Best-effort tweak; we'll re-skin via custom HTML in Iteration 3. */
[data-testid="stArrowVegaLiteChart"] {
  background: var(--paper) !important;
}

/* ── Chronicle helper classes ──────────────────────────────────── */
.chronicle-masthead {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 32px;
  border-bottom: 2px solid var(--ink);
  padding: 4px 0 22px 0;
  margin-bottom: 28px;
}
.chronicle-masthead .nav-left,
.chronicle-masthead .nav-right {
  font-family: 'Shippori Mincho', serif;
  font-size: 11px;
  letter-spacing: 0.36em;
  text-transform: uppercase;
  color: var(--ink-faded);
}
.chronicle-masthead .nav-right { text-align: right; }
.chronicle-masthead .wordmark {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.chronicle-masthead .wordmark .kanji {
  font-family: 'Shippori Mincho', serif;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--ink);
  line-height: 1;
}
.chronicle-masthead .wordmark .romaji {
  font-family: 'Shippori Mincho', serif;
  font-size: 10px;
  letter-spacing: 0.5em;
  text-transform: uppercase;
  color: var(--seal);
  text-indent: 0.5em;
  margin-top: 4px;
}

/* Section heads — used to introduce major page sections */
.chronicle-section {
  display: flex; align-items: baseline; gap: 16px;
  margin: 32px 0 12px 0;
  font-family: 'Shippori Mincho', serif;
}
.chronicle-section .num {
  font-size: 13px; letter-spacing: 0.4em; color: var(--seal);
}
.chronicle-section .title {
  font-size: 26px; font-weight: 700; letter-spacing: -0.005em;
  color: var(--ink);
}
.chronicle-section .dot {
  flex: 1; height: 1px; background: var(--ink); opacity: 0.4;
}
.chronicle-section .meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; color: var(--ink-faded); letter-spacing: 0.06em;
}

/* Fight card — symmetric vs banner */
.chronicle-card {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  margin: 8px 0 24px 0;
  align-items: stretch;
}
.chronicle-card .fighter {
  padding: 26px 30px;
  background: var(--paper-2);
  border: 1.5px solid var(--ink);
}
.chronicle-card .fighter.left  { border-right: none; }
.chronicle-card .fighter.right { border-left: none; text-align: right; }
.chronicle-card .clan {
  font-family: 'Shippori Mincho', serif;
  font-size: 11px; letter-spacing: 0.4em; text-transform: uppercase;
  color: var(--ink-faded);
  margin-bottom: 4px;
}
.chronicle-card .name {
  font-family: 'Shippori Mincho', serif;
  font-weight: 700; font-size: 36px;
  line-height: 1; color: var(--ink);
  margin-bottom: 4px;
}
.chronicle-card .school {
  font-style: italic; font-size: 16px;
  color: var(--ink-soft); margin-bottom: 22px;
}
.chronicle-card .stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px 8px;
}
.chronicle-card .fighter.right .stat-grid { direction: rtl; }
.chronicle-card .fighter.right .stat-grid > * { direction: ltr; }
.chronicle-card .stat {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
}
.chronicle-card .stat .label {
  font-family: 'Shippori Mincho', serif;
  font-size: 9.5px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ink-faded);
}
.chronicle-card .stat .val {
  font-family: 'Shippori Mincho', serif;
  font-size: 26px; font-weight: 700;
  color: var(--ink); line-height: 1;
}
.chronicle-card .stat.ring-fire   .val { color: var(--seal); }
.chronicle-card .stat.ring-water  .val { color: var(--crab-blue); }
.chronicle-card .stat.ring-earth  .val { color: #6b4f2a; }
.chronicle-card .stat.ring-air    .val { color: #5a6d7e; }
.chronicle-card .stat.ring-void   .val { color: var(--ink); }
.chronicle-card .ribbon {
  margin-top: 18px; padding-top: 12px;
  border-top: 1px solid var(--ink-faded);
  display: flex; gap: 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; color: var(--ink-soft); letter-spacing: 0.05em;
}
.chronicle-card .fighter.right .ribbon { justify-content: flex-end; }
.chronicle-card .vs {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: var(--ink); color: var(--paper);
  padding: 22px 28px; position: relative; min-width: 130px;
}
.chronicle-card .vs .label {
  font-family: 'Shippori Mincho', serif;
  font-size: 54px; font-weight: 800;
  line-height: 0.9; letter-spacing: -0.04em;
}
.chronicle-card .vs .sub {
  font-family: 'Shippori Mincho', serif;
  font-size: 9.5px; letter-spacing: 0.36em;
  text-transform: uppercase; margin-top: 6px; color: var(--gold);
}
.chronicle-card .vs .stamp {
  position: absolute; bottom: -22px; left: 50%;
  transform: translateX(-50%) rotate(-8deg);
  width: 60px; height: 60px; background: var(--seal);
  border: 3px solid var(--seal-deep); border-radius: 4px;
  font-family: 'Shippori Mincho', serif;
  color: var(--paper); font-weight: 800; font-size: 28px;
  line-height: 60px; text-align: center;
  box-shadow: 0 2px 12px rgba(122,26,20,0.35);
}

/* Status snapshot — compact between-phase HUD */
.chronicle-status {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 18px 0 8px;
  padding: 14px 18px;
  background: var(--paper-2);
  border: 1px solid var(--ink-faded);
  border-left: 4px solid var(--ink);
}
.chronicle-status .who {
  font-family: 'Shippori Mincho', serif;
  font-weight: 700; letter-spacing: 0.04em;
  font-size: 14px; color: var(--ink);
}
.chronicle-status .bars {
  display: flex; gap: 14px; margin-top: 6px;
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--ink-soft);
}
.chronicle-status .bar {
  display: flex; flex-direction: column; gap: 2px; min-width: 70px;
}
.chronicle-status .bar .label {
  font-size: 9px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ink-faded);
}
.chronicle-status .bar .track {
  height: 8px; background: var(--paper-3); position: relative;
  border: 1px solid var(--ink-faded); overflow: hidden;
}
.chronicle-status .bar .fill { height: 100%; background: var(--ink); }
.chronicle-status .bar.lw .fill   { background: var(--seal); }
.chronicle-status .bar.sw .fill   { background: var(--seal-deep); }
.chronicle-status .bar.void .fill { background: var(--ink); }
.chronicle-status .bar .num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600; color: var(--ink); font-size: 12px;
}

/* Trace container — wraps the existing markdown trace renderer so
   it visually belongs to the chronicle, even before Iteration 3
   replaces the renderer outright. */
.chronicle-trace-container {
  background: var(--paper);
  border: 1px solid var(--ink-faded);
  border-left: 3px solid var(--ink);
  padding: 18px 22px;
  margin-top: 8px;
}

/* Round divider — visible between rounds in the trace */
.chronicle-round-divider {
  display: flex; align-items: baseline; gap: 12px;
  margin: 24px 0 12px;
  font-family: 'Shippori Mincho', serif;
}
.chronicle-round-divider .kanji {
  font-size: 28px; font-weight: 800; color: var(--ink);
}
.chronicle-round-divider .roman {
  font-size: 12px; letter-spacing: 0.36em; text-transform: uppercase;
  color: var(--seal);
}
.chronicle-round-divider .line {
  flex: 1; height: 1px; background: var(--ink); opacity: 0.3;
}
</style>
"""


def inject_theme() -> None:
    """Inject the sumi-e theme on the current page.  Idempotent in
    practice (Streamlit deduplicates identical st.markdown calls
    across reruns; the duplicate <link> tags are inert)."""
    st.markdown(_GOOGLE_FONTS, unsafe_allow_html=True)
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


# ── Render helpers (pure HTML, injected via st.markdown) ──────────


def render_masthead(active: str) -> None:
    """Render the page-top masthead with simple nav cues.

    The nav links are pure label text — Streamlit's ``st.navigation``
    already drives actual routing; this masthead is decorative,
    establishing identity without competing with the live tab strip.
    """
    nav = [
        ("Combat Setup", "設定"),
        ("Run Simulation", "戦"),
        ("Characters", "侍"),
        ("Analysis", "記録"),
    ]
    mid = len(nav) // 2
    def _li(items: list[tuple[str, str]]) -> str:
        return " · ".join(
            f'<span style="{"color:var(--ink);border-bottom:1.5px solid var(--seal);padding-bottom:2px;" if label == active else ""}">'
            f'{html.escape(kanji)} {html.escape(label)}</span>'
            for label, kanji in items
        )
    block = (
        '<div class="chronicle-masthead">'
        f'<nav class="nav-left">{_li(nav[:mid])}</nav>'
        '<div class="wordmark">'
        '<div class="kanji">合戦譜 GASSEN-FU</div>'
        '<div class="romaji">l7r combat chronicle</div>'
        '</div>'
        f'<nav class="nav-right">{_li(nav[mid:])}</nav>'
        '</div>'
    )
    st.markdown(block, unsafe_allow_html=True)


def render_section_head(num: str, title: str, meta: str = "") -> None:
    """Render a brushwork section header with optional metadata."""
    meta_html = (
        f'<span class="meta">{html.escape(meta)}</span>' if meta else ""
    )
    st.markdown(
        '<div class="chronicle-section">'
        f'<span class="num">{html.escape(num)}</span>'
        f'<span class="title">{html.escape(title)}</span>'
        '<span class="dot"></span>'
        f'{meta_html}'
        '</div>',
        unsafe_allow_html=True,
    )


_RING_ORDER = ["air", "earth", "fire", "water", "void"]


def render_fight_card(
    left: dict[str, Any],
    right: dict[str, Any],
    sub_label: str = "single combat",
    stamp_kanji: str = "決",
) -> None:
    """Render the vs-styled fight card.

    Each side dict is ``{"clan_kanji": str, "clan": str, "name": str,
    "school": str, "rings": dict, "ribbon": list[str]}``.
    """
    def _side(d: dict[str, Any], side: str) -> str:
        stats = "".join(
            f'<div class="stat ring-{r}">'
            f'<div class="val">{d.get("rings", {}).get(r, 2)}</div>'
            f'<div class="label">{r.title()}</div>'
            '</div>'
            for r in _RING_ORDER
        )
        ribbon = "".join(f"<span>{html.escape(s)}</span>" for s in d.get("ribbon", []))
        return (
            f'<div class="fighter {side}">'
            f'<div class="clan">{html.escape(d.get("clan_kanji", ""))} — {html.escape(d.get("clan", ""))}</div>'
            f'<div class="name">{html.escape(d.get("name", ""))}</div>'
            f'<div class="school">{html.escape(d.get("school", ""))}</div>'
            f'<div class="stat-grid">{stats}</div>'
            f'<div class="ribbon">{ribbon}</div>'
            '</div>'
        )
    st.markdown(
        '<div class="chronicle-card">'
        f'{_side(left, "left")}'
        '<div class="vs">'
        '<div class="label">VS</div>'
        f'<div class="sub">{html.escape(sub_label)}</div>'
        f'<div class="stamp">{html.escape(stamp_kanji)}</div>'
        '</div>'
        f'{_side(right, "right")}'
        '</div>',
        unsafe_allow_html=True,
    )


def render_round_divider(number: int) -> None:
    """Render a small brushwork divider between rounds."""
    kanji_map = {
        1: "壱", 2: "弐", 3: "参", 4: "肆", 5: "伍",
        6: "陸", 7: "漆", 8: "捌", 9: "玖", 10: "拾",
    }
    kanji = kanji_map.get(number, str(number))
    st.markdown(
        '<div class="chronicle-round-divider">'
        f'<span class="kanji">{html.escape(kanji)}</span>'
        f'<span class="roman">Round {html.escape(str(number))}</span>'
        '<span class="line"></span>'
        '</div>',
        unsafe_allow_html=True,
    )


def open_trace_container() -> None:
    """Open the styled container that wraps the live trace renderer."""
    st.markdown('<div class="chronicle-trace-container">', unsafe_allow_html=True)


def close_trace_container() -> None:
    """Close the trace container.  Symmetric with ``open_trace_container``."""
    st.markdown('</div>', unsafe_allow_html=True)


# ── Clan / kanji lookup ──────────────────────────────────────────


_CLAN_BY_SCHOOL = {
    "Akodo Bushi School":              ("Lion",        "獅子"),
    "Bayushi Bushi School":            ("Scorpion",    "蠍"),
    "Brotherhood of Shinsei Monk School": ("Brotherhood", "兄弟"),
    "Courtier School":                  ("Imperial",    "宮廷"),
    "Daidoji Yojimbo School":          ("Crane",       "鶴"),
    "Doji Artisan School":             ("Crane",       "鶴"),
    "Hida Bushi School":               ("Crab",        "蟹"),
    "Hiruma Scout School":             ("Crab",        "蟹"),
    "Ide Diplomat School":             ("Unicorn",     "麒麟"),
    "Ikoma Bard School":               ("Lion",        "獅子"),
    "Isawa Duelist School":            ("Phoenix",     "鳳凰"),
    "Isawa Ishi School":               ("Phoenix",     "鳳凰"),
    "Kakita Bushi School":             ("Crane",       "鶴"),
    "Kitsuki Magistrate School":       ("Dragon",      "龍"),
    "Kuni Witch Hunter School":        ("Crab",        "蟹"),
    "Matsu Bushi School":              ("Lion",        "獅子"),
    "Merchant School":                 ("Merchant",    "商"),
    "Mirumoto Bushi School":           ("Dragon",      "龍"),
    "Otaku Bushi School":              ("Unicorn",     "麒麟"),
    "Priest School":                   ("Temple",      "寺"),
    "Shiba Bushi School":              ("Phoenix",     "鳳凰"),
    "Shinjo Bushi School":             ("Unicorn",     "麒麟"),
    "Shosuro Actor School":            ("Scorpion",    "蠍"),
    "Togashi Ise Zumi School":         ("Dragon",      "龍"),
    "Yogo Warden School":              ("Scorpion",    "蠍"),
}


def clan_for(school: str | None) -> tuple[str, str]:
    """Return ``(clan_name, clan_kanji)`` for a school name.  Falls
    back to ``("Rōnin", "浪人")`` for unknown / blank inputs."""
    if not school:
        return ("Rōnin", "浪人")
    return _CLAN_BY_SCHOOL.get(school, ("Rōnin", "浪人"))
