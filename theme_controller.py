#!/usr/bin/env python3
"""Runtime light/dark theme controller for the DIENGIN Streamlit UI."""
from __future__ import annotations

import streamlit as st

THEME_KEY = "dg_theme"
THEME_SELECTOR_KEY = "dg_theme_selector"
VALID_THEMES = {"light", "dark"}
DISPLAY_TO_THEME = {"☀ Terang": "light", "🌙 Gelap": "dark"}
THEME_TO_DISPLAY = {value: key for key, value in DISPLAY_TO_THEME.items()}


def current_theme() -> str:
    """Resolve theme from session, then URL query, then default to light."""
    if THEME_KEY not in st.session_state:
        try:
            requested = st.query_params.get("theme", "light")
            if isinstance(requested, list):
                requested = requested[-1] if requested else "light"
        except Exception:
            requested = "light"
        requested = str(requested).lower().strip()
        st.session_state[THEME_KEY] = requested if requested in VALID_THEMES else "light"
    return st.session_state[THEME_KEY]


def _persist_theme(value: str) -> None:
    value = value if value in VALID_THEMES else "light"
    st.session_state[THEME_KEY] = value
    try:
        st.query_params["theme"] = value
    except Exception:
        pass


def _selector_changed() -> None:
    selected = st.session_state.get(THEME_SELECTOR_KEY)
    _persist_theme(DISPLAY_TO_THEME.get(selected, "light"))


def render_toggle() -> None:
    """Render a proper two-state light/dark control in the top navigation."""
    active = current_theme()
    expected = THEME_TO_DISPLAY[active]
    if st.session_state.get(THEME_SELECTOR_KEY) != expected:
        st.session_state[THEME_SELECTOR_KEY] = expected

    with st.container(key="dg_theme_selector_wrap"):
        st.segmented_control(
            "Tema tampilan",
            list(DISPLAY_TO_THEME),
            key=THEME_SELECTOR_KEY,
            on_change=_selector_changed,
            label_visibility="collapsed",
        )


def apply_theme() -> str:
    """Apply theme tokens and Streamlit-native widget overrides for this rerun."""
    active = current_theme()
    if active == "dark":
        tokens = {
            "surface": "#0B1220",
            "surface2": "#101A2A",
            "card": "#141F30",
            "soft": "#1A293D",
            "control": "#111C2B",
            "ink": "#EDF4FF",
            "muted": "#9FAFC4",
            "border": "rgba(181,202,229,.18)",
            "blue": "#69A9FF",
            "cyan": "#54C8F3",
            "shadow": "rgba(0,0,0,.30)",
            "grid": "#29394E",
            "chip": "#1C2B40",
            "hero1": "#205FD4",
            "hero2": "#128FC4",
            "glow": "rgba(90,184,255,.18)",
        }
        scheme = "dark"
    else:
        tokens = {
            "surface": "#F4F7FB",
            "surface2": "#EEF4FB",
            "card": "#FFFFFF",
            "soft": "#F2F7FD",
            "control": "#FFFFFF",
            "ink": "#1E2B3F",
            "muted": "#6F7D91",
            "border": "rgba(32,54,82,.12)",
            "blue": "#2878F0",
            "cyan": "#35AFE8",
            "shadow": "rgba(25,47,78,.08)",
            "grid": "#E5ECF5",
            "chip": "#F7FAFE",
            "hero1": "#2878F0",
            "hero2": "#35AFE8",
            "glow": "rgba(40,120,240,.13)",
        }
        scheme = "light"

    css = f"""
<style>
:root{{
  color-scheme:{scheme};
  --dg-blue:{tokens['blue']};
  --dg-cyan:{tokens['cyan']};
  --dg-ink:{tokens['ink']};
  --dg-muted:{tokens['muted']};
  --dg-surface:{tokens['surface']};
  --dg-surface-2:{tokens['surface2']};
  --dg-card:{tokens['card']};
  --dg-soft:{tokens['soft']};
  --dg-control-bg:{tokens['control']};
  --dg-border:{tokens['border']};
  --dg-shadow:{tokens['shadow']};
  --dg-grid:{tokens['grid']};
  --dg-chip-bg:{tokens['chip']};
  --dg-hero-1:{tokens['hero1']};
  --dg-hero-2:{tokens['hero2']};
  --dg-glow:{tokens['glow']};
}}

@keyframes dgFadeUp{{
  from{{opacity:.55;transform:translateY(5px)}}
  to{{opacity:1;transform:translateY(0)}}
}}
@keyframes dgHeroFlow{{
  0%{{background-position:0% 50%}}
  50%{{background-position:100% 50%}}
  100%{{background-position:0% 50%}}
}}
@keyframes dgSoftPulse{{
  0%,100%{{transform:scale(1);opacity:1}}
  50%{{transform:scale(1.025);opacity:.96}}
}}

html,body,.stApp,[data-testid="stAppViewContainer"],section[data-testid="stMain"]{{
  background:
    radial-gradient(circle at 12% -10%, var(--dg-glow), transparent 28rem),
    {tokens['surface']}!important;
  color:{tokens['ink']}!important;
  transition:background-color .28s ease,color .28s ease!important;
}}
[data-testid="stHeader"]{{background:transparent!important;}}

/* Smooth theme changes and micro-interactions. */
.st-key-dg_topbar > div,
.dg-weather-card,.dg-explorer-card,.dg-bmkg-card,.dg-hour-card,.dg-prospect-card,
[data-baseweb="select"] > div,[data-baseweb="input"] > div,[data-testid="stExpander"],
.stButton > button,.stDownloadButton > button{{
  transition:background-color .24s ease,color .24s ease,border-color .24s ease,
             box-shadow .24s ease,transform .22s ease!important;
}}
.dg-weather-card:hover,.dg-bmkg-card:hover,.dg-hour-card:hover{{
  transform:translateY(-3px)!important;
  box-shadow:0 14px 34px {tokens['shadow']}!important;
}}
.dg-explorer-card:hover{{box-shadow:0 12px 30px {tokens['shadow']}!important;}}

/* Custom DIENGIN surfaces */
.st-key-dg_topbar > div,
.dg-weather-card,.dg-explorer-card,.dg-bmkg-card,.dg-hour-card,.dg-prospect-card{{
  background:{tokens['card']}!important;
  border-color:{tokens['border']}!important;
  box-shadow:0 8px 24px {tokens['shadow']}!important;
}}
.dg-scale-chip{{background:{tokens['chip']}!important;border-color:{tokens['border']}!important;}}
.dg-current-head h2,.dg-weather-label,.dg-weather-value,.dg-hour-time,.dg-hour-label,.dg-top-brand,
.dg-bmkg-weather,.dg-bmkg-temp{{color:{tokens['ink']}!important;}}
.dg-current-head p,.dg-weather-note,.dg-secondary-line,.dg-scale-legend,.dg-explorer-help,.dg-hour-note,
.dg-bmkg-meta,.dg-bmkg-time,.dg-bmkg-source{{color:{tokens['muted']}!important;}}
.dg-top-place span{{background:{tokens['soft']}!important;color:{tokens['blue']}!important;}}
.dg-svg-wrap line{{stroke:{tokens['grid']}!important;}}
.dg-svg-wrap text{{fill:{tokens['muted']}!important;}}

/* Hero stays visually alive but restrained. */
.dg-hero{{
  position:relative!important;
  overflow:hidden!important;
  background:linear-gradient(120deg,var(--dg-hero-1),var(--dg-hero-2),var(--dg-hero-1))!important;
  background-size:220% 220%!important;
  animation:dgHeroFlow 12s ease-in-out infinite!important;
  box-shadow:0 18px 42px {tokens['glow']}!important;
}}
.dg-hero::after{{
  content:"";position:absolute;inset:auto -8% -65% auto;width:320px;height:320px;
  border-radius:50%;background:rgba(255,255,255,.08);pointer-events:none;
}}
.dg-hero-score .value{{animation:dgSoftPulse 4.8s ease-in-out infinite!important;}}
.dg-hero,.dg-hero *{{color:#FFFFFF!important;}}

/* Streamlit native controls */
[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] *,
.stMultiSelect label,.stSelectbox label,.stDateInput label,.stTimeInput label,.stTextInput label,.stNumberInput label{{
  color:{tokens['ink']}!important;
}}
[data-baseweb="select"] > div,[data-baseweb="input"] > div,[data-baseweb="base-input"],
.stDateInput [data-baseweb="input"],.stTimeInput [data-baseweb="input"],
.stTextInput [data-baseweb="input"],.stNumberInput [data-baseweb="input"]{{
  background:{tokens['control']}!important;
  border-color:{tokens['border']}!important;
  color:{tokens['ink']}!important;
  box-shadow:none!important;
}}
[data-baseweb="select"] > div:hover,[data-baseweb="input"] > div:hover{{border-color:{tokens['blue']}!important;}}
input,textarea{{color:{tokens['ink']}!important;-webkit-text-fill-color:{tokens['ink']}!important;}}
input::placeholder,textarea::placeholder{{color:{tokens['muted']}!important;opacity:1!important;}}
[data-baseweb="select"] svg,[data-baseweb="input"] svg{{fill:{tokens['muted']}!important;color:{tokens['muted']}!important;}}
[data-baseweb="tag"]{{background:{tokens['soft']}!important;color:{tokens['ink']}!important;border:1px solid {tokens['border']}!important;}}
[data-baseweb="tag"] span{{color:{tokens['ink']}!important;}}
[data-baseweb="popover"] > div,[role="listbox"],[role="dialog"]{{
  background:{tokens['card']}!important;color:{tokens['ink']}!important;border-color:{tokens['border']}!important;
}}
[role="option"]{{background:{tokens['card']}!important;color:{tokens['ink']}!important;}}
[role="option"]:hover{{background:{tokens['soft']}!important;}}

/* Buttons, expanders and tables */
.stButton > button:not([kind="primary"]),.stDownloadButton > button{{
  background:{tokens['card']}!important;color:{tokens['ink']}!important;border-color:{tokens['border']}!important;
}}
.stButton > button:not([kind="primary"]):hover,.stDownloadButton > button:hover{{
  border-color:{tokens['blue']}!important;color:{tokens['blue']}!important;transform:translateY(-1px)!important;
}}
[data-testid="stExpander"]{{background:{tokens['card']}!important;border-color:{tokens['border']}!important;}}
[data-testid="stDataFrame"],[data-testid="stTable"]{{color:{tokens['ink']}!important;}}

/* Primary navigation */
.st-key-dg_nav_control button{{
  color:{tokens['muted']}!important;background:transparent!important;border-color:transparent!important;
  transition:all .22s ease!important;
}}
.st-key-dg_nav_control button:hover{{color:{tokens['blue']}!important;background:{tokens['soft']}!important;}}
.st-key-dg_nav_control button[aria-checked="true"],
.st-key-dg_nav_control button[aria-pressed="true"]{{
  color:{tokens['blue']}!important;background:{tokens['soft']}!important;box-shadow:inset 0 0 0 1px {tokens['border']}!important;
}}

/* Proper two-state theme selector. */
.st-key-dg_theme_selector_wrap{{display:flex!important;justify-content:flex-end!important;align-items:center!important;}}
.st-key-dg_theme_selector_wrap [data-testid="stSegmentedControl"]{{width:100%!important;}}
.st-key-dg_theme_selector_wrap [data-testid="stSegmentedControl"] > div{{
  width:100%!important;padding:3px!important;gap:2px!important;border-radius:13px!important;
  background:{tokens['soft']}!important;border:1px solid {tokens['border']}!important;
}}
.st-key-dg_theme_selector_wrap button{{
  min-height:36px!important;padding:.35rem .55rem!important;border-radius:10px!important;border:0!important;
  background:transparent!important;color:{tokens['muted']}!important;font-size:.82rem!important;font-weight:750!important;
  white-space:nowrap!important;transition:all .22s ease!important;
}}
.st-key-dg_theme_selector_wrap button:hover{{color:{tokens['blue']}!important;}}
.st-key-dg_theme_selector_wrap button[aria-checked="true"],
.st-key-dg_theme_selector_wrap button[aria-pressed="true"]{{
  background:{tokens['card']}!important;color:{tokens['blue']}!important;
  box-shadow:0 3px 10px {tokens['shadow']}!important;transform:translateY(-1px)!important;
}}

/* Gentle entrance when switching pages/theme. */
.dg-hero,.dg-current-wrap,.dg-explorer-card,.dg-bmkg-grid,.dg-hour-scroll{{animation:dgFadeUp .34s ease both;}}

@media(max-width:760px){{
  .st-key-dg_theme_selector_wrap button{{font-size:0!important;padding:.3rem!important;min-width:38px!important;}}
  .st-key-dg_theme_selector_wrap button:first-child::after{{content:"☀";font-size:1rem!important;}}
  .st-key-dg_theme_selector_wrap button:last-child::after{{content:"🌙";font-size:1rem!important;}}
}}
@media(prefers-reduced-motion:reduce){{
  *,*::before,*::after{{animation:none!important;transition:none!important;scroll-behavior:auto!important;}}
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)
    return active
