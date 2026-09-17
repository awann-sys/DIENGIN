#!/usr/bin/env python3
"""Runtime light/dark theme controller for the DIENGIN Streamlit UI."""
from __future__ import annotations

import streamlit as st

THEME_KEY = "dg_theme"
THEME_SELECTOR_KEY = "dg_theme_selector"
VALID_THEMES = {"light", "dark"}
DISPLAY_TO_THEME = {"☀️": "light", "🌙": "dark"}
THEME_TO_DISPLAY = {value: key for key, value in DISPLAY_TO_THEME.items()}


def current_theme() -> str:
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
    """Compact two-state theme switch for the top navigation."""
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
    active = current_theme()
    if active == "dark":
        t = {
            "surface": "#0B1220",
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
        t = {
            "surface": "#F4F7FB",
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
  --dg-blue:{t['blue']};--dg-cyan:{t['cyan']};--dg-ink:{t['ink']};
  --dg-muted:{t['muted']};--dg-surface:{t['surface']};--dg-card:{t['card']};
  --dg-soft:{t['soft']};--dg-control-bg:{t['control']};--dg-border:{t['border']};
  --dg-shadow:{t['shadow']};--dg-grid:{t['grid']};--dg-chip-bg:{t['chip']};
  --dg-hero-1:{t['hero1']};--dg-hero-2:{t['hero2']};--dg-glow:{t['glow']};
}}

@keyframes dgHeroFlow{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}

html,body,.stApp,[data-testid="stAppViewContainer"],section[data-testid="stMain"]{{
  background:radial-gradient(circle at 12% -10%,var(--dg-glow),transparent 28rem),var(--dg-surface)!important;
  color:var(--dg-ink)!important;
  transition:background-color .24s ease,color .24s ease!important;
}}
[data-testid="stHeader"]{{background:transparent!important}}

.st-key-dg_topbar > div,.dg-weather-card,.dg-explorer-card,.dg-bmkg-card,.dg-hour-card,.dg-prospect-card{{
  background:var(--dg-card)!important;border-color:var(--dg-border)!important;
  box-shadow:0 8px 24px var(--dg-shadow)!important;
  transition:background-color .22s ease,color .22s ease,border-color .22s ease,box-shadow .22s ease,transform .18s ease!important;
}}
.dg-weather-card:hover,.dg-bmkg-card:hover,.dg-hour-card:hover{{transform:translateY(-2px)!important;box-shadow:0 13px 30px var(--dg-shadow)!important}}
.dg-scale-chip{{background:var(--dg-chip-bg)!important;border-color:var(--dg-border)!important}}
.dg-current-head h2,.dg-weather-label,.dg-weather-value,.dg-hour-time,.dg-hour-label,.dg-top-brand,.dg-bmkg-weather,.dg-bmkg-temp{{color:var(--dg-ink)!important}}
.dg-current-head p,.dg-weather-note,.dg-secondary-line,.dg-scale-legend,.dg-explorer-help,.dg-hour-note,.dg-bmkg-meta,.dg-bmkg-time,.dg-bmkg-source{{color:var(--dg-muted)!important}}
.dg-svg-wrap line{{stroke:var(--dg-grid)!important}}.dg-svg-wrap text{{fill:var(--dg-muted)!important}}

.dg-hero{{
  background:linear-gradient(120deg,var(--dg-hero-1),var(--dg-hero-2),var(--dg-hero-1))!important;
  background-size:220% 220%!important;animation:dgHeroFlow 12s ease-in-out infinite!important;
  box-shadow:0 18px 42px var(--dg-glow)!important;
}}
.dg-hero,.dg-hero *{{color:#fff!important}}

[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] *,
.stMultiSelect label,.stSelectbox label,.stDateInput label,.stTimeInput label,.stTextInput label,.stNumberInput label{{color:var(--dg-ink)!important}}
[data-baseweb="select"] > div,[data-baseweb="input"] > div,[data-baseweb="base-input"],
.stDateInput [data-baseweb="input"],.stTimeInput [data-baseweb="input"],.stTextInput [data-baseweb="input"],.stNumberInput [data-baseweb="input"]{{
  background:var(--dg-control-bg)!important;border-color:var(--dg-border)!important;color:var(--dg-ink)!important;box-shadow:none!important;
}}
[data-baseweb="select"] > div:hover,[data-baseweb="input"] > div:hover{{border-color:var(--dg-blue)!important}}
input,textarea{{color:var(--dg-ink)!important;-webkit-text-fill-color:var(--dg-ink)!important}}
input::placeholder,textarea::placeholder{{color:var(--dg-muted)!important;opacity:1!important}}
[data-baseweb="select"] svg,[data-baseweb="input"] svg{{fill:var(--dg-muted)!important;color:var(--dg-muted)!important}}
[data-baseweb="tag"]{{background:var(--dg-soft)!important;color:var(--dg-ink)!important;border:1px solid var(--dg-border)!important}}
[data-baseweb="tag"] span{{color:var(--dg-ink)!important}}
[data-baseweb="popover"] > div,[role="listbox"],[role="dialog"]{{background:var(--dg-card)!important;color:var(--dg-ink)!important;border-color:var(--dg-border)!important}}
[role="option"]{{background:var(--dg-card)!important;color:var(--dg-ink)!important}}[role="option"]:hover{{background:var(--dg-soft)!important}}

.stButton > button:not([kind="primary"]),.stDownloadButton > button{{background:var(--dg-card)!important;color:var(--dg-ink)!important;border-color:var(--dg-border)!important}}
.stButton > button:not([kind="primary"]):hover,.stDownloadButton > button:hover{{border-color:var(--dg-blue)!important;color:var(--dg-blue)!important}}
[data-testid="stExpander"]{{background:var(--dg-card)!important;border-color:var(--dg-border)!important}}

/* Center navigation: equal button widths and quiet active state. */
.st-key-dg_nav_control button{{color:var(--dg-muted)!important;background:transparent!important;border-color:transparent!important}}
.st-key-dg_nav_control button:hover{{color:var(--dg-blue)!important;background:var(--dg-soft)!important}}
.st-key-dg_nav_control button[aria-checked="true"],.st-key-dg_nav_control button[aria-pressed="true"]{{
  color:var(--dg-blue)!important;background:var(--dg-soft)!important;box-shadow:inset 0 0 0 1px var(--dg-border)!important;
}}

/* Compact sun/moon control: no text, no stretched right block. */
.st-key-dg_theme_selector_wrap{{display:flex!important;justify-content:flex-end!important;align-items:center!important;width:auto!important}}
.st-key-dg_theme_selector_wrap [data-testid="stSegmentedControl"]{{width:auto!important;min-width:0!important}}
.st-key-dg_theme_selector_wrap [data-testid="stSegmentedControl"] > div{{
  width:auto!important;min-width:0!important;padding:3px!important;gap:2px!important;
  border-radius:12px!important;background:var(--dg-soft)!important;border:1px solid var(--dg-border)!important;
}}
.st-key-dg_theme_selector_wrap button{{
  width:36px!important;min-width:36px!important;max-width:36px!important;height:34px!important;min-height:34px!important;
  padding:0!important;border-radius:9px!important;border:0!important;background:transparent!important;
  color:var(--dg-muted)!important;font-size:.93rem!important;font-weight:700!important;
}}
.st-key-dg_theme_selector_wrap button:hover{{color:var(--dg-blue)!important}}
.st-key-dg_theme_selector_wrap button[aria-checked="true"],.st-key-dg_theme_selector_wrap button[aria-pressed="true"]{{
  background:var(--dg-card)!important;color:var(--dg-blue)!important;box-shadow:0 3px 9px var(--dg-shadow)!important;
}}

@media(max-width:760px){{
  .st-key-dg_theme_selector_wrap button{{width:32px!important;min-width:32px!important;max-width:32px!important;height:32px!important;min-height:32px!important}}
}}
@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important;transition:none!important;scroll-behavior:auto!important}}}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)
    return active
