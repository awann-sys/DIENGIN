#!/usr/bin/env python3
"""Runtime light/dark theme controller for the DIENGIN Streamlit UI."""
from __future__ import annotations

import streamlit as st

THEME_KEY = "dg_theme"
VALID_THEMES = {"light", "dark"}


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


def toggle_theme() -> None:
    """Switch theme and mirror the choice into the URL so refresh preserves it."""
    new_theme = "dark" if current_theme() == "light" else "light"
    st.session_state[THEME_KEY] = new_theme
    try:
        st.query_params["theme"] = new_theme
    except Exception:
        pass
    st.rerun()


def render_toggle() -> None:
    """Render a compact sun/moon button; intended for the top navigation."""
    active = current_theme()
    icon = "☀️" if active == "dark" else "🌙"
    help_text = "Gunakan mode terang" if active == "dark" else "Gunakan mode gelap"
    with st.container(key="dg_theme_toggle_wrap"):
        if st.button(icon, key="dg_theme_toggle", help=help_text, width="stretch"):
            toggle_theme()


def apply_theme() -> str:
    """Apply theme tokens and Streamlit-native widget overrides for this rerun."""
    active = current_theme()
    if active == "dark":
        tokens = {
            "surface": "#0D1420",
            "card": "#151F2E",
            "soft": "#192638",
            "control": "#111B29",
            "ink": "#EAF1FB",
            "muted": "#9EADC1",
            "border": "rgba(176,197,222,.18)",
            "blue": "#67A7FF",
            "cyan": "#58C8F2",
            "shadow": "rgba(0,0,0,.24)",
            "grid": "#263548",
            "chip": "#1D2A3C",
        }
        scheme = "dark"
    else:
        tokens = {
            "surface": "#F4F7FB",
            "card": "#FFFFFF",
            "soft": "#F8FBFF",
            "control": "#FFFFFF",
            "ink": "#1E2B3F",
            "muted": "#6F7D91",
            "border": "rgba(32,54,82,.12)",
            "blue": "#2878F0",
            "cyan": "#35AFE8",
            "shadow": "rgba(25,47,78,.06)",
            "grid": "#E8EDF4",
            "chip": "#F7FAFE",
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
  --dg-card:{tokens['card']};
  --dg-soft:{tokens['soft']};
  --dg-control-bg:{tokens['control']};
  --dg-border:{tokens['border']};
  --dg-shadow:{tokens['shadow']};
  --dg-grid:{tokens['grid']};
  --dg-chip-bg:{tokens['chip']};
}}
html,body,.stApp,[data-testid="stAppViewContainer"],section[data-testid="stMain"]{{
  background:{tokens['surface']}!important;
  color:{tokens['ink']}!important;
}}
[data-testid="stHeader"]{{background:transparent!important;}}

/* Custom DIENGIN surfaces */
.st-key-dg_topbar > div,
.dg-weather-card,
.dg-explorer-card,
.dg-bmkg-card,
.dg-hour-card,
.dg-prospect-card{{
  background:{tokens['card']}!important;
  border-color:{tokens['border']}!important;
  box-shadow:0 8px 24px {tokens['shadow']}!important;
}}
.dg-scale-chip{{background:{tokens['chip']}!important;border-color:{tokens['border']}!important;}}
.dg-current-head h2,.dg-weather-label,.dg-weather-value,.dg-hour-time,.dg-hour-label,.dg-top-brand{{color:{tokens['ink']}!important;}}
.dg-current-head p,.dg-weather-note,.dg-secondary-line,.dg-scale-legend,.dg-explorer-help,.dg-hour-note,.dg-bmkg-meta,.dg-bmkg-time,.dg-bmkg-source{{color:{tokens['muted']}!important;}}
.dg-top-place span{{background:{tokens['soft']}!important;color:{tokens['blue']}!important;}}
.dg-svg-wrap line{{stroke:{tokens['grid']}!important;}}
.dg-svg-wrap text{{fill:{tokens['muted']}!important;}}

/* Streamlit native controls */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
.stMultiSelect label,.stSelectbox label,.stDateInput label,.stTimeInput label,.stTextInput label,.stNumberInput label{{
  color:{tokens['ink']}!important;
}}
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
.stDateInput [data-baseweb="input"],
.stTimeInput [data-baseweb="input"],
.stTextInput [data-baseweb="input"],
.stNumberInput [data-baseweb="input"]{{
  background:{tokens['control']}!important;
  border-color:{tokens['border']}!important;
  color:{tokens['ink']}!important;
  box-shadow:none!important;
}}
input,textarea{{color:{tokens['ink']}!important;-webkit-text-fill-color:{tokens['ink']}!important;}}
input::placeholder,textarea::placeholder{{color:{tokens['muted']}!important;opacity:1!important;}}
[data-baseweb="select"] svg,[data-baseweb="input"] svg{{fill:{tokens['muted']}!important;color:{tokens['muted']}!important;}}
[data-baseweb="tag"]{{background:{tokens['soft']}!important;color:{tokens['ink']}!important;border:1px solid {tokens['border']}!important;}}
[data-baseweb="tag"] span{{color:{tokens['ink']}!important;}}
[data-baseweb="popover"] > div,
[role="listbox"],
[role="dialog"]{{background:{tokens['card']}!important;color:{tokens['ink']}!important;border-color:{tokens['border']}!important;}}
[role="option"]{{background:{tokens['card']}!important;color:{tokens['ink']}!important;}}
[role="option"]:hover{{background:{tokens['soft']}!important;}}

/* Buttons, expanders and tables */
.stButton > button:not([kind="primary"]),
.stDownloadButton > button{{
  background:{tokens['card']}!important;
  color:{tokens['ink']}!important;
  border-color:{tokens['border']}!important;
}}
.stButton > button:not([kind="primary"]):hover,
.stDownloadButton > button:hover{{border-color:{tokens['blue']}!important;color:{tokens['blue']}!important;}}
[data-testid="stExpander"]{{background:{tokens['card']}!important;border-color:{tokens['border']}!important;}}
[data-testid="stDataFrame"], [data-testid="stTable"]{{color:{tokens['ink']}!important;}}

/* Segmented navigation */
.st-key-dg_nav_control button{{color:{tokens['muted']}!important;background:transparent!important;border-color:transparent!important;}}
.st-key-dg_nav_control button[aria-checked="true"],
.st-key-dg_nav_control button[aria-pressed="true"]{{color:{tokens['blue']}!important;background:{tokens['soft']}!important;}}

/* Theme control */
.st-key-dg_theme_toggle_wrap{{display:flex!important;justify-content:flex-end!important;align-items:center!important;}}
.st-key-dg_theme_toggle_wrap button{{
  width:42px!important;min-width:42px!important;height:42px!important;min-height:42px!important;
  padding:0!important;border-radius:12px!important;background:{tokens['soft']}!important;
  color:{tokens['ink']}!important;border:1px solid {tokens['border']}!important;
  font-size:1rem!important;box-shadow:none!important;
}}
.st-key-dg_theme_toggle_wrap button:hover{{border-color:{tokens['blue']}!important;}}

/* Keep custom blue hero readable in both themes */
.dg-hero,.dg-hero *{{color:#FFFFFF!important;}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)
    return active
