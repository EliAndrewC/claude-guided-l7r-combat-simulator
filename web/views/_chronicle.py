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
[data-testid="stMarkdownContainer"] li {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 17px;
  line-height: 1.55;
  color: var(--ink-soft);
}
/* Bare spans inside markdown come from our custom HTML (status pills, ribbon
   chips, etc.) and own their colors/fonts — don't force a default. */
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
/* Button labels are nested inside stMarkdownContainer, whose <p> rule above
   would otherwise force them to --ink-soft (dark-on-dark).  Make them inherit
   from the button so they stay legible at rest, on hover, and in the sidebar. */
.stButton > button [data-testid="stMarkdownContainer"] p,
.stButton > button [data-testid="stMarkdownContainer"] span,
.stDownloadButton > button [data-testid="stMarkdownContainer"] p,
.stDownloadButton > button [data-testid="stMarkdownContainer"] span,
.stFormSubmitButton > button [data-testid="stMarkdownContainer"] p,
.stFormSubmitButton > button [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] .stButton > button [data-testid="stMarkdownContainer"] * {
  color: inherit !important;
  -webkit-text-fill-color: inherit !important;
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
.chronicle-masthead .wordmark .wordmark-title {
  font-family: 'Shippori Mincho', serif;
  font-size: 38px;
  font-weight: 800;
  letter-spacing: 0.2em;
  color: var(--ink);
  line-height: 1;
  text-indent: 0.2em;
}
.chronicle-masthead .wordmark .wordmark-sub {
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
  position: absolute; bottom: -28px; left: 50%;
  transform: translateX(-50%) rotate(-8deg);
  width: 60px; height: 70px;
  filter: drop-shadow(0 2px 8px rgba(122,26,20,0.35));
}
.chronicle-card .vs .stamp svg { display: block; width: 100%; height: 100%; }
.chronicle-card .vs .stamp path {
  fill: var(--seal);
  stroke: var(--seal-deep);
  stroke-width: 5;
  stroke-linejoin: round;
}
.chronicle-card .vs .stamp text {
  fill: var(--paper);
  font-family: 'Shippori Mincho', serif;
  font-weight: 800; font-size: 56px;
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

/* Character card — sumi-e roster panel */
.chronicle-character {
  background: var(--paper-2);
  border: 1.5px solid var(--ink);
  padding: 22px 26px 18px;
  margin-bottom: 18px;
  position: relative;
}
.chronicle-character .head {
  border-bottom: 1px solid var(--ink-faded);
  padding-bottom: 14px;
  margin-bottom: 16px;
}
.chronicle-character .clan {
  font-family: 'Shippori Mincho', serif;
  font-size: 12px; letter-spacing: 0.32em; text-transform: uppercase;
  color: var(--seal);
  margin-bottom: 4px;
}
.chronicle-character .clan .clan-en {
  color: var(--ink-faded);
  margin-left: 6px;
}
.chronicle-character .name {
  font-family: 'Shippori Mincho', serif;
  font-weight: 700; font-size: 30px; line-height: 1;
  color: var(--ink);
  margin-bottom: 6px;
}
.chronicle-character .meta-row {
  display: flex; gap: 10px; align-items: baseline;
  font-family: 'Cormorant Garamond', serif; font-style: italic;
}
.chronicle-character .school {
  font-size: 15px; color: var(--ink-soft); flex: 1;
}
.chronicle-character .rank-pip {
  font-family: 'Shippori Mincho', serif; font-style: normal;
  font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
  background: var(--ink); color: var(--paper);
  padding: 2px 8px;
}
.chronicle-character .xp-tag {
  font-family: 'JetBrains Mono', monospace; font-style: normal;
  font-size: 11px; color: var(--ink-faded); letter-spacing: 0.04em;
}
.chronicle-character .stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px 8px;
}
.chronicle-character .stat {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
}
.chronicle-character .stat .val {
  font-family: 'Shippori Mincho', serif;
  font-size: 22px; font-weight: 700; color: var(--ink); line-height: 1;
}
.chronicle-character .stat .label {
  font-family: 'Shippori Mincho', serif;
  font-size: 9px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ink-faded);
}
.chronicle-character .stat.ring-fire   .val { color: var(--seal); }
.chronicle-character .stat.ring-water  .val { color: var(--crab-blue); }
.chronicle-character .stat.ring-earth  .val { color: #6b4f2a; }
.chronicle-character .stat.ring-air    .val { color: #5a6d7e; }
.chronicle-character .ribbon {
  margin-top: 14px; padding-top: 10px;
  border-top: 1px solid var(--ink-faded);
  display: flex; flex-wrap: wrap; gap: 14px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; color: var(--ink-soft); letter-spacing: 0.05em;
}
.chronicle-character .badges {
  margin-top: 12px;
  display: flex; flex-wrap: wrap; gap: 6px;
}
.chronicle-character .badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  padding: 2px 8px;
  background: var(--paper-3);
  border: 1px solid var(--ink-faded);
  color: var(--ink-soft);
  letter-spacing: 0.04em;
}
.chronicle-character .badge.adv {
  border-color: var(--jade);
  color: var(--jade);
}
.chronicle-character .badge.dis {
  border-color: var(--seal);
  color: var(--seal);
}

/* Study card — chronicle-styled analysis index entry */
.chronicle-study {
  background: var(--paper-2);
  border: 1px solid var(--ink-faded);
  border-left: 4px solid var(--ink);
  padding: 18px 22px;
  margin-bottom: 14px;
}
.chronicle-study .meta {
  display: flex; align-items: baseline; gap: 14px;
  margin-bottom: 10px;
}
.chronicle-study .title {
  font-family: 'Shippori Mincho', serif;
  font-weight: 700; font-size: 22px;
  color: var(--ink);
  letter-spacing: -0.005em;
  flex: 1;
}
.chronicle-study .status {
  font-family: 'Shippori Mincho', serif;
  font-size: 9.5px; letter-spacing: 0.28em;
  text-transform: uppercase;
  padding: 2px 10px;
}
.chronicle-study .status.ready {
  background: var(--ink);
  color: var(--paper);
}
.chronicle-study .status.pending {
  background: var(--paper-3);
  color: var(--ink-faded);
  border: 1px solid var(--ink-faded);
}
.chronicle-study .question {
  font-family: 'Cormorant Garamond', serif;
  font-style: italic;
  font-size: 16px;
  color: var(--ink);
  margin-bottom: 6px;
}
.chronicle-study .desc {
  font-family: 'Cormorant Garamond', serif;
  font-size: 14.5px;
  color: var(--ink-soft);
  line-height: 1.5;
}

/* Round divider — visible between rounds in the trace */
.chronicle-round-divider {
  display: flex; align-items: baseline; gap: 12px;
  margin: 24px 0 12px;
  font-family: 'Shippori Mincho', serif;
}
.chronicle-round-divider .roman-numeral {
  font-size: 28px; font-weight: 800; color: var(--seal);
  letter-spacing: 0.06em;
}
.chronicle-round-divider .roman {
  font-size: 12px; letter-spacing: 0.36em; text-transform: uppercase;
  color: var(--seal);
}
.chronicle-round-divider .line {
  flex: 1; height: 1px; background: var(--ink); opacity: 0.3;
}

/* ── Chronicle event cards ──────────────────────────────────── */
.chronicle-evt {
  padding: 12px 18px 12px 22px;
  border-left: 2px solid var(--ink-faded);
  margin-bottom: 4px;
  position: relative;
}
.chronicle-evt + .chronicle-evt { margin-top: -1px; }
.chronicle-evt.crit  { border-left-color: var(--seal); background: rgba(179,38,30,0.05); }
.chronicle-evt.heal  { border-left-color: var(--jade); }
.chronicle-evt.death { border-left-color: var(--ink); background: var(--ink); color: var(--paper); }
.chronicle-evt.fall  { border-left-color: var(--gold); background: rgba(176,134,66,0.07); }

.chronicle-evt .meta {
  display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px; color: var(--ink-faded);
  letter-spacing: 0.08em; text-transform: uppercase;
  margin-bottom: 6px;
}
.chronicle-evt.death .meta { color: var(--gold); }
.chronicle-evt .meta .phase { color: var(--seal); font-weight: 600; }
.chronicle-evt .meta .actor {
  font-family: 'Shippori Mincho', serif;
  font-weight: 700; letter-spacing: 0.04em; font-size: 13px;
  color: var(--ink); text-transform: none;
}
.chronicle-evt.death .meta .actor { color: var(--paper); }
.chronicle-evt .meta .kind { color: var(--ink-soft); }

.chronicle-evt .body {
  font-family: 'Cormorant Garamond', serif; font-size: 16.5px;
  color: var(--ink); line-height: 1.5;
}
.chronicle-evt .body .strong {
  font-family: 'Shippori Mincho', serif; font-weight: 700;
}
.chronicle-evt .body .red { color: var(--seal); font-weight: 600; }
.chronicle-evt .body .dim { color: var(--ink-faded); }
.chronicle-evt.death .body { font-style: italic; font-size: 18px; }

/* Dice tile row */
.chronicle-evt .dice {
  margin-top: 8px; display: flex; flex-wrap: wrap;
  gap: 3px; align-items: center;
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
}
.chronicle-evt .die {
  width: 22px; height: 26px;
  display: inline-flex; align-items: center; justify-content: center;
}
.chronicle-evt .die svg { width: 100%; height: 100%; display: block; }
.chronicle-evt .die path {
  fill: var(--paper);
  stroke: var(--ink);
  stroke-width: 4;
  stroke-linejoin: round;
}
.chronicle-evt .die text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 52px; font-weight: 700;
  fill: var(--ink);
}
.chronicle-evt .die.dropped { opacity: 0.32; }
.chronicle-evt .die.dropped path { fill: var(--paper-3); }
.chronicle-evt .die.crit path {
  fill: var(--seal);
  stroke: var(--seal-deep);
}
.chronicle-evt .die.crit text { fill: var(--paper); }
.chronicle-evt .arrow {
  color: var(--ink-faded); padding: 0 4px;
}
.chronicle-evt .total {
  font-family: 'Shippori Mincho', serif;
  font-size: 16px; font-weight: 700; letter-spacing: 0.02em;
  color: var(--ink); padding: 0 6px;
}
.chronicle-evt .vs-tn {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px; color: var(--ink-faded);
  margin-left: 8px; letter-spacing: 0.06em;
  font-weight: normal;
}

/* Outcome stamp */
.chronicle-evt .outcome {
  margin-left: auto;
  font-family: 'Shippori Mincho', serif;
  font-size: 12px; letter-spacing: 0.22em;
  text-transform: uppercase; padding: 4px 12px;
  font-weight: 700;
}
.chronicle-evt .outcome.hit       { background: var(--seal); color: var(--paper); }
.chronicle-evt .outcome.miss      { background: var(--paper-3); color: var(--ink-faded); border: 1px solid var(--ink-faded); }
.chronicle-evt .outcome.succeeded { background: var(--ink); color: var(--paper); }
.chronicle-evt .outcome.failed    { background: var(--paper-3); color: var(--ink-faded); border: 1px solid var(--ink-faded); }
.chronicle-evt .outcome.won       { background: var(--gold); color: var(--ink); }
.chronicle-evt .outcome.lost      { background: var(--paper-3); color: var(--ink-faded); border: 1px solid var(--ink-faded); }
.chronicle-evt .outcome.passed    { background: var(--jade); color: var(--paper); }

/* Modifier / breakdown pills */
.chronicle-evt .pills {
  margin-top: 8px;
  display: flex; flex-wrap: wrap; gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}
.chronicle-evt .pill {
  background: var(--paper);
  border: 1px solid var(--ink-faded);
  padding: 3px 9px;
  display: inline-flex; gap: 6px; align-items: baseline;
  letter-spacing: 0.02em;
  color: var(--ink-soft);
}
.chronicle-evt .pill .v { font-weight: 700; color: var(--ink); }
.chronicle-evt .pill .src {
  font-size: 9.5px;
  color: var(--ink-faded);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.chronicle-evt .pill.school {
  background: rgba(179,38,30,0.04);
  border-color: var(--seal);
  color: var(--seal);
}
.chronicle-evt .pill.school .v { color: var(--seal); }
.chronicle-evt .pill.school .src { color: var(--seal); }
.chronicle-evt .pill.weapon {
  border-color: var(--ink); color: var(--ink);
}
.chronicle-evt .pill.weapon .v { color: var(--ink); }

/* Status snapshot inside trace */
.chronicle-evt-status {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 12px; margin: 14px 0;
  padding: 14px 18px;
  background: var(--paper-2);
  border: 1px solid var(--ink-faded);
  border-left: 4px solid var(--ink);
}
.chronicle-evt-status .who {
  font-family: 'Shippori Mincho', serif;
  font-weight: 700; letter-spacing: 0.04em; font-size: 14px;
  color: var(--ink);
}
.chronicle-evt-status .meta-bars {
  display: flex; gap: 12px; margin-top: 6px;
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--ink-soft);
}
.chronicle-evt-status .bar {
  display: flex; flex-direction: column; gap: 2px; min-width: 78px;
}
.chronicle-evt-status .bar .label {
  font-size: 9px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ink-faded);
}
.chronicle-evt-status .bar .track {
  height: 6px; background: var(--paper-3); position: relative;
  border: 1px solid var(--ink-faded); overflow: hidden;
}
.chronicle-evt-status .bar .fill { height: 100%; background: var(--ink); }
.chronicle-evt-status .bar.lw .fill   { background: var(--seal); }
.chronicle-evt-status .bar.sw .fill   { background: var(--seal-deep); }
.chronicle-evt-status .bar.void .fill { background: var(--ink); }
.chronicle-evt-status .bar .num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600; color: var(--ink); font-size: 11.5px;
}
.chronicle-evt-status .who.crippled::after {
  content: " · CRIPPLED";
  color: var(--seal); font-weight: 700; font-size: 10px; letter-spacing: 0.18em;
}

/* Generic fallback event (delegated to BulletedRenderer) */
.chronicle-evt-generic {
  padding: 6px 16px;
  font-family: 'Cormorant Garamond', serif;
  font-size: 15.5px;
  color: var(--ink-soft);
  border-left: 1px solid var(--paper-3);
  line-height: 1.55;
}
.chronicle-evt-generic strong { color: var(--ink); }

/* Initiative roll block */
.chronicle-evt-initiative {
  background: var(--paper-2);
  border: 1px solid var(--ink-faded);
  padding: 14px 18px;
  margin: 12px 0 4px;
}
.chronicle-evt-initiative .h {
  font-family: 'Shippori Mincho', serif;
  font-weight: 700; font-size: 13px;
  letter-spacing: 0.32em; text-transform: uppercase;
  color: var(--seal); margin-bottom: 8px;
}
.chronicle-evt-initiative .row {
  display: flex; gap: 10px; align-items: baseline;
  font-family: 'Cormorant Garamond', serif; font-size: 15px;
  margin: 4px 0;
}
.chronicle-evt-initiative .row .who {
  font-family: 'Shippori Mincho', serif; font-weight: 700;
  color: var(--ink); min-width: 100px;
}
.chronicle-evt-initiative .row .actions {
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  color: var(--ink-soft); margin-left: auto;
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
    nav = ["Combat Setup", "Run Simulation", "Characters", "Analysis"]
    mid = len(nav) // 2
    def _li(items: list[str]) -> str:
        return " · ".join(
            f'<span style="{"color:var(--ink);border-bottom:1.5px solid var(--seal);padding-bottom:2px;" if label == active else ""}">'
            f'{html.escape(label)}</span>'
            for label in items
        )
    block = (
        '<div class="chronicle-masthead">'
        f'<nav class="nav-left">{_li(nav[:mid])}</nav>'
        '<div class="wordmark">'
        '<div class="wordmark-title">L7R</div>'
        '<div class="wordmark-sub">combat chronicle</div>'
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

# Canonical d10 silhouette — kite outline with rounded corners (radius 8).
# Top apex 70°, other three corners ~96.67°; viewBox 100×116.  Shape and
# coordinates match the dice animation in EliAndrewC/character-sheet so the
# stamp on the matchup card reads as the same die as the rolls in the trace.
_D10_PATH = (
    "M 54.59 6.55 L 95.41 64.85 Q 100 71.4 94.03 76.73 "
    "L 55.97 110.67 Q 50 116 44.03 110.67 L 5.97 76.73 "
    "Q 0 71.4 4.59 64.85 L 45.41 6.55 Q 50 0 54.59 6.55 Z"
)


def render_fight_card(
    left: dict[str, Any],
    right: dict[str, Any],
    sub_label: str = "single combat",
    stamp: str = "I",
) -> None:
    """Render the vs-styled fight card.

    Each side dict is ``{"clan": str, "name": str, "school": str,
    "rings": dict, "ribbon": list[str]}``.
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
            f'<div class="clan">{html.escape(d.get("clan", ""))}</div>'
            f'<div class="name">{html.escape(d.get("name", ""))}</div>'
            f'<div class="school">{html.escape(d.get("school", ""))}</div>'
            f'<div class="stat-grid">{stats}</div>'
            f'<div class="ribbon">{ribbon}</div>'
            '</div>'
        )
    # d10 silhouette: canonical kite path (matches the dice elsewhere in the
    # chronicle so the matchup "die" reads as the same shape as the rolls).
    stamp_svg = (
        '<svg viewBox="0 0 100 116" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{_D10_PATH}" />'
        '<text x="50" y="65" text-anchor="middle" dominant-baseline="central">'
        f'{html.escape(stamp)}</text>'
        '</svg>'
    )
    st.markdown(
        '<div class="chronicle-card">'
        f'{_side(left, "left")}'
        '<div class="vs">'
        '<div class="label">VS</div>'
        f'<div class="sub">{html.escape(sub_label)}</div>'
        f'<div class="stamp">{stamp_svg}</div>'
        '</div>'
        f'{_side(right, "right")}'
        '</div>',
        unsafe_allow_html=True,
    )


_ROMAN_NUMERALS = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
    6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
    11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
    16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX",
}


def to_roman(n: int) -> str:
    """Return the Roman numeral for ``n`` (1–20), falling back to the
    arabic form for larger values."""
    return _ROMAN_NUMERALS.get(n, str(n))


def render_round_divider(number: int) -> None:
    """Render a small brushwork divider between rounds, with the
    round number rendered in Roman numerals (I, II, III, …)."""
    roman = to_roman(number)
    st.markdown(
        '<div class="chronicle-round-divider">'
        f'<span class="roman-numeral">{html.escape(roman)}</span>'
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


def render_character_card(d: dict[str, Any]) -> None:
    """Render a single-character sumi-e card.

    ``d`` accepts ``{"name", "clan", "school", "rank", "xp",
    "rings", "ribbon", "advantages", "disadvantages"}``; optional
    keys are omitted gracefully.
    """
    rings = "".join(
        f'<div class="stat ring-{r}">'
        f'<div class="val">{d.get("rings", {}).get(r, 2)}</div>'
        f'<div class="label">{r.title()}</div>'
        '</div>'
        for r in _RING_ORDER
    )
    ribbon_items = d.get("ribbon", [])
    ribbon = "".join(
        f"<span>{html.escape(s)}</span>" for s in ribbon_items
    )
    rank = d.get("rank")
    rank_html = (
        f'<span class="rank-pip">{html.escape(str(rank))}</span>'
        if rank is not None else ""
    )
    xp = d.get("xp")
    xp_html = (
        f'<span class="xp-tag">{html.escape(str(xp))} xp</span>'
        if xp is not None else ""
    )
    school = d.get("school") or "Ronin"
    advs = d.get("advantages") or []
    disadvs = d.get("disadvantages") or []
    badge_html = ""
    if advs or disadvs:
        adv_pills = "".join(
            f'<span class="badge adv">{html.escape(a)}</span>' for a in advs
        )
        dis_pills = "".join(
            f'<span class="badge dis">{html.escape(d_)}</span>' for d_ in disadvs
        )
        badge_html = f'<div class="badges">{adv_pills}{dis_pills}</div>'
    st.markdown(
        '<div class="chronicle-character">'
        '<div class="head">'
        f'<div class="clan">{html.escape(d.get("clan", ""))}</div>'
        f'<div class="name">{html.escape(d.get("name", ""))}</div>'
        '<div class="meta-row">'
        f'<span class="school">{html.escape(school)}</span>'
        f'{rank_html}{xp_html}'
        '</div>'
        '</div>'
        f'<div class="stat-grid">{rings}</div>'
        f'<div class="ribbon">{ribbon}</div>'
        f'{badge_html}'
        '</div>',
        unsafe_allow_html=True,
    )


def render_study_card(
    title: str, question: str, description: str,
    status: str, status_ready: bool, button_label: str, button_key: str,
) -> bool:
    """Render a sumi-e study summary panel with a Streamlit-driven
    "View" button.  Returns the button's click value so callers can
    wire navigation.
    """
    status_class = "ready" if status_ready else "pending"
    st.markdown(
        '<div class="chronicle-study">'
        '<div class="meta">'
        f'<span class="title">{html.escape(title)}</span>'
        f'<span class="status {status_class}">{html.escape(status)}</span>'
        '</div>'
        f'<div class="question">{html.escape(question)}</div>'
        f'<div class="desc">{html.escape(description)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    return st.button(button_label, key=button_key)


# ── Clan / kanji lookup ──────────────────────────────────────────


_CLAN_BY_SCHOOL = {
    "Akodo Bushi School":              "Lion",
    "Bayushi Bushi School":            "Scorpion",
    "Brotherhood of Shinsei Monk School": "Brotherhood",
    "Courtier School":                  "Imperial",
    "Daidoji Yojimbo School":          "Crane",
    "Doji Artisan School":             "Crane",
    "Hida Bushi School":               "Crab",
    "Hiruma Scout School":             "Crab",
    "Ide Diplomat School":             "Unicorn",
    "Ikoma Bard School":               "Lion",
    "Isawa Duelist School":            "Phoenix",
    "Isawa Ishi School":               "Phoenix",
    "Kakita Bushi School":             "Crane",
    "Kitsuki Magistrate School":       "Dragon",
    "Kuni Witch Hunter School":        "Crab",
    "Matsu Bushi School":              "Lion",
    "Merchant School":                 "Merchant",
    "Mirumoto Bushi School":           "Dragon",
    "Otaku Bushi School":              "Unicorn",
    "Priest School":                   "Temple",
    "Shiba Bushi School":              "Phoenix",
    "Shinjo Bushi School":             "Unicorn",
    "Shosuro Actor School":            "Scorpion",
    "Togashi Ise Zumi School":         "Dragon",
    "Yogo Warden School":              "Scorpion",
}


def clan_for(school: str | None) -> str:
    """Return the clan name for a school name.  Falls back to
    ``"Ronin"`` for unknown / blank inputs."""
    if not school:
        return "Ronin"
    return _CLAN_BY_SCHOOL.get(school, "Ronin")
