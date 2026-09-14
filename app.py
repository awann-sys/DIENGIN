#!/usr/bin/env python3
"""DIENGIN UI alignment layer.

The full dashboard implementation lives in app_base.py. This small entrypoint
keeps the lower summary panels on the same visual grid without altering data,
model, or pipeline behavior.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app_base import *  # noqa: F401,F403
import app_base as base

ALIGNMENT_CSS = """
<style>
.dg-panel-title {
    display: flex;
    align-items: center;
    min-height: 32px;
    font-size: 1.22rem;
    font-weight: 650;
    line-height: 1.3;
    margin: .10rem 0 .16rem;
}
.dg-field-note {
    min-height: 20px;
    font-size: .78rem;
    line-height: 1.35;
    opacity: .68;
    margin: 0 0 .24rem;
}
[data-testid="stSelectbox"] { margin-top: 0 !important; }
[data-testid="stSelectbox"] > div { margin-top: 0 !important; }
[data-testid="stRadio"] { margin-top: .14rem !important; }
[data-baseweb="select"] > div { min-height: 44px; }
[data-testid="stHorizontalBlock"] { align-items: flex-start; }
</style>
"""
base.CSS += ALIGNMENT_CSS
CSS = base.CSS


def render_trend(mh):
    st.markdown('<div class="dg-panel-title">Jejak cuaca</div>', unsafe_allow_html=True)
    st.markdown('<div class="dg-field-note">Rentang waktu</div>', unsafe_allow_html=True)
    hours = st.selectbox(
        "Rentang waktu",
        [6, 12, 24, 48],
        index=2,
        format_func=lambda x: f"{x} jam terakhir",
        key="trend_hours",
        label_visibility="collapsed",
    )
    if mh.empty:
        st.info("Riwayat monitoring belum tersedia.")
        return

    subset = base.window(mh, hours)
    options = ["Suhu", "Kelembapan", "Angin", "Hujan AWS"]
    selected = st.radio(
        "Parameter cuaca",
        options,
        horizontal=True,
        key="weather_parameter",
        label_visibility="collapsed",
    )
    mapping = {
        "Suhu": ({"tt_air_avg": "Suhu udara", "tt_air_min": "Minimum observasi"}, "Suhu (°C)"),
        "Kelembapan": ({"rh_avg": "Kelembapan"}, "RH (%)"),
        "Angin": ({"ws_avg": "Angin observasi", "ws_mean_1h": "Rata-rata 1 jam"}, "Kecepatan · unit sumber AWS"),
        "Hujan AWS": ({"rr": "Pembacaan hujan AWS"}, "Pembacaan AWS (mm)"),
    }
    fields, ylabel = mapping[selected]
    base.draw_chart(subset, fields, ylabel, "weather_chart", height=285)
    st.caption(
        f"{base.time_label(subset['_time'].min())} — {base.time_label(subset['_time'].max())} · "
        f"{len(subset)} observasi tersimpan"
    )
    if selected == "Hujan AWS":
        st.caption("Pembacaan sumber belum dikonversi menjadi intensitas atau total hujan periode pilihan.")
    elif selected == "Suhu":
        values = pd.to_numeric(subset.get("tt_air_avg", pd.Series(dtype=float)), errors="coerce")
        if values.notna().any():
            st.markdown(
                f'<div class="dg-summary"><span>Terendah <b>{base.fmt(values.min())} °C</b></span>'
                f'<span>Rata-rata <b>{base.fmt(values.mean())} °C</b></span>'
                f'<span>Tertinggi <b>{base.fmt(values.max())} °C</b></span></div>',
                unsafe_allow_html=True,
            )
    st.caption("Geser atau zoom untuk menjelajah; klik dua kali untuk reset. Jeda data tidak disambungkan.")


def render_prediction_history(rh, nights, pred, now):
    st.markdown('<div class="dg-panel-title">Perjalanan prediksi</div>', unsafe_allow_html=True)
    st.markdown('<div class="dg-field-note">Tanggal target prediksi</div>', unsafe_allow_html=True)

    if rh.empty or "tanggal_target" not in rh:
        st.info("Riwayat rilis belum tersedia.")
        return
    dates = sorted(rh["tanggal_target"].dropna().astype(str).str[:10].unique(), reverse=True)
    if not dates:
        st.info("Tanggal target belum tersedia.")
        return

    target = st.selectbox(
        "Tanggal target prediksi",
        dates,
        format_func=base.date_label,
        key="prediction_date",
        label_visibility="collapsed",
    )
    selected = rh.loc[rh["tanggal_target"].astype(str).str[:10] == target]
    threshold = None
    if str(pred.get("target_night_date"))[:10] == target:
        threshold = base.probability(pred.get("threshold_stacked"))
    elif "tanggal_target" in nights:
        summary = nights.loc[nights["tanggal_target"].astype(str).str[:10] == target]
        if not summary.empty:
            threshold = base.probability(summary.iloc[-1].get("ambang_final"))

    base.release_strip(selected, target, threshold, now)
    base.draw_chart(
        selected,
        {"stack_prob": "DIENGIN"},
        "Probabilitas (%)",
        "release_chart",
        True,
        threshold,
        285,
    )
    st.caption(f"Ambang target {base.pct(threshold)} · probabilitas per rilis, bukan observasi kejadian frost.")
    with st.expander("Bandingkan model"):
        base.draw_chart(selected, base.PROB_LABELS, "Probabilitas (%)", "models_chart", True)
        st.caption(
            "ANN, SVM, dan Random Forest adalah model dasar. DIENGIN menampilkan hasil stacking; "
            "nilainya bukan rata-rata sederhana."
        )
    with st.expander("Tabel rilis dan unduhan"):
        table = selected.drop(columns=["_time"], errors="ignore").copy()
        cols = [
            c
            for c in ["waktu_rilis_wib", "stack_prob", "ann_prob", "svm_prob", "rf_prob", "status_data_rilis"]
            if c in table
        ]
        table = table[cols]
        for col in base.PROB_LABELS:
            if col in table:
                table[col] = (pd.to_numeric(table[col], errors="coerce") * 100).round(2)
        table = table.rename(
            columns={
                **{k: v + " (%)" for k, v in base.PROB_LABELS.items()},
                "waktu_rilis_wib": "Rilis (WIB)",
                "status_data_rilis": "Status data",
            }
        )
        st.dataframe(table, hide_index=True, width="stretch")
        base.download_csv(selected, f"diengin_rilis_{target}.csv", "release_csv")
        st.caption("CSV mempertahankan probabilitas asli pada skala 0–1.")


base.render_trend = render_trend
base.render_prediction_history = render_prediction_history


if __name__ == "__main__":
    base.main()
