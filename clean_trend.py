#!/usr/bin/env python3
"""Clean Figma-style weather trace panel for DIENGIN.

Presentation only. Uses the existing history data and chart renderer.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import app_base as base

TRACE_CSS = r"""
<style>
.dg-trace-label{
  margin:0 0 .42rem;
  color:#1e2b3f;
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.96rem;
  line-height:1.35;
  font-weight:700;
}
.st-key-trace_period,
.st-key-trace_parameter{
  margin:0!important;
}
.st-key-trace_period [data-testid="stSelectbox"],
.st-key-trace_parameter [data-testid="stSelectbox"]{
  margin:0!important;
}
.st-key-trace_period [data-baseweb="select"] > div,
.st-key-trace_parameter [data-baseweb="select"] > div{
  min-height:48px!important;
  border-radius:14px!important;
  border-color:rgba(32,54,82,.14)!important;
  background:#fff!important;
  box-shadow:none!important;
}
.st-key-trace_period [data-baseweb="select"] span,
.st-key-trace_parameter [data-baseweb="select"] span{
  font-size:.96rem!important;
  color:#1e2b3f!important;
}
.st-key-trace_chart_card{
  margin-top:1rem!important;
}
.st-key-trace_chart_card > div{
  background:#fff!important;
  border:1px solid rgba(32,54,82,.12)!important;
  border-radius:22px!important;
  padding:1.15rem 1.2rem .8rem!important;
  box-shadow:0 8px 24px rgba(25,47,78,.035)!important;
}
.st-key-trace_chart_card [data-testid="stVegaLiteChart"]{
  margin:0!important;
}
.dg-trace-meta{
  margin:.75rem 0 0;
  color:#6f7d91;
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.92rem;
  line-height:1.5;
  text-align:center;
}
.dg-trace-summary{
  display:flex;
  justify-content:center;
  align-items:center;
  flex-wrap:wrap;
  gap:.55rem;
  margin:.85rem 0 0;
}
.dg-trace-chip{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  min-height:34px;
  padding:.35rem .7rem;
  border:1px solid rgba(32,54,82,.12);
  border-radius:999px;
  background:#f7f9fc;
  color:#526174;
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.9rem;
  line-height:1.2;
}
.dg-trace-chip b{color:#1e2b3f;font-weight:800;margin-left:.3rem;}
.dg-trace-note{
  margin:.6rem 0 0;
  color:#6f7d91;
  font-size:.88rem;
  line-height:1.5;
  text-align:center;
}
@media(max-width:700px){
  .dg-trace-label{font-size:.92rem;}
  .st-key-trace_chart_card > div{padding:.8rem .65rem .55rem!important;}
  .dg-trace-meta{font-size:.86rem;}
}
</style>
"""
base.CSS += TRACE_CSS


def render_trend(mh: pd.DataFrame) -> None:
    """Render one compact control row + one clean chart card, without duplicate title."""
    if mh.empty:
        st.info("Riwayat monitoring belum tersedia.")
        return

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown('<div class="dg-trace-label">Rentang waktu</div>', unsafe_allow_html=True)
        with st.container(key="trace_period"):
            hours = st.selectbox(
                "Rentang waktu",
                [6, 12, 24, 48],
                index=2,
                format_func=lambda x: f"{x} jam terakhir",
                key="trace_hours",
                label_visibility="collapsed",
            )

    with c2:
        st.markdown('<div class="dg-trace-label">Parameter grafik</div>', unsafe_allow_html=True)
        with st.container(key="trace_parameter"):
            selected = st.selectbox(
                "Parameter grafik",
                ["Suhu", "Kelembapan", "Angin", "Hujan AWS"],
                index=0,
                key="trace_parameter_choice",
                label_visibility="collapsed",
            )

    subset = base.window(mh, hours)
    mapping = {
        "Suhu": (
            {"tt_air_avg": "Suhu udara", "tt_air_min": "Minimum observasi"},
            "Suhu (°C)",
        ),
        "Kelembapan": ({"rh_avg": "Kelembapan"}, "RH (%)"),
        "Angin": (
            {"ws_avg": "Angin observasi", "ws_mean_1h": "Rata-rata 1 jam"},
            "Kecepatan · unit sumber AWS",
        ),
        "Hujan AWS": ({"rr": "Pembacaan hujan AWS"}, "Pembacaan AWS (mm)"),
    }
    fields, ylabel = mapping[selected]

    with st.container(border=True, key="trace_chart_card"):
        base.draw_chart(subset, fields, ylabel, "clean_weather_chart", height=340)

    start = base.time_label(subset["_time"].min()) if not subset.empty else "—"
    end = base.time_label(subset["_time"].max()) if not subset.empty else "—"
    st.markdown(
        f'<div class="dg-trace-meta">{base.esc(start)} — {base.esc(end)} · '
        f'{len(subset)} observasi tersimpan</div>',
        unsafe_allow_html=True,
    )

    if selected == "Suhu":
        values = pd.to_numeric(
            subset.get("tt_air_avg", pd.Series(dtype=float)), errors="coerce"
        )
        if values.notna().any():
            st.markdown(
                '<div class="dg-trace-summary">'
                f'<span class="dg-trace-chip">Terendah <b>{base.esc(base.fmt(values.min()))} °C</b></span>'
                f'<span class="dg-trace-chip">Rata-rata <b>{base.esc(base.fmt(values.mean()))} °C</b></span>'
                f'<span class="dg-trace-chip">Tertinggi <b>{base.esc(base.fmt(values.max()))} °C</b></span>'
                '</div>',
                unsafe_allow_html=True,
            )
    elif selected == "Hujan AWS":
        st.markdown(
            '<div class="dg-trace-note">Pembacaan sumber belum dikonversi menjadi '
            'intensitas atau total hujan untuk periode pilihan.</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="dg-trace-note">Grafik dapat digeser atau diperbesar; klik dua kali untuk reset. '
        'Jeda data tidak disambungkan.</div>',
        unsafe_allow_html=True,
    )
