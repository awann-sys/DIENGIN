#!/usr/bin/env python3
"""DIENGIN UI alignment layer.

The full dashboard implementation lives in app_base.py. This entrypoint
rebuilds the two lower summary panels as matched visual cards so their
headers, selectors, secondary controls, and charts share the same grid.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app_base import *  # noqa: F401,F403
import app_base as base

ALIGNMENT_CSS = """
<style>
/* Matched lower-panel geometry */
.st-key-weather_panel,
.st-key-prediction_panel {
    min-height: 610px;
}
.st-key-weather_panel > div,
.st-key-prediction_panel > div {
    height: 100%;
}

.dg-panel-title {
    min-height: 34px;
    display: flex;
    align-items: center;
    font-size: 1.22rem;
    font-weight: 680;
    line-height: 1.25;
    margin: 0 0 .12rem;
    padding: 0;
}
.dg-field-note,
.dg-secondary-note {
    min-height: 20px;
    display: flex;
    align-items: center;
    font-size: .78rem;
    line-height: 1.35;
    opacity: .68;
    margin: 0 0 .24rem;
}
.dg-secondary-note {
    margin-top: .62rem;
    margin-bottom: .18rem;
}

/* Both primary selectors occupy an identical slot. */
.st-key-weather_primary,
.st-key-prediction_primary {
    min-height: 52px;
}
.st-key-weather_primary [data-testid="stSelectbox"],
.st-key-prediction_primary [data-testid="stSelectbox"] {
    margin: 0 !important;
}
.st-key-weather_primary [data-baseweb="select"] > div,
.st-key-prediction_primary [data-baseweb="select"] > div {
    min-height: 44px;
}

/* Secondary controls reserve exactly the same vertical band before charts. */
.st-key-weather_secondary,
.st-key-prediction_secondary {
    min-height: 118px;
    max-height: 118px;
    overflow: hidden;
}
.st-key-weather_secondary [data-testid="stRadio"] {
    margin-top: .08rem !important;
}
.st-key-weather_secondary [data-testid="stCaptionContainer"] p,
.st-key-prediction_secondary [data-testid="stCaptionContainer"] p {
    margin-top: .28rem;
}

/* Release boxes stay compact enough to fit the shared control band. */
.st-key-prediction_secondary .dg-release-row {
    margin: .2rem 0 .25rem;
}
.st-key-prediction_secondary .dg-release {
    padding-top: .52rem;
    padding-bottom: .52rem;
}

/* Keep both chart areas on the same baseline and height. */
.st-key-weather_chart,
.st-key-prediction_chart {
    min-height: 300px;
}
.st-key-weather_chart [data-testid="stVegaLiteChart"],
.st-key-prediction_chart [data-testid="stVegaLiteChart"] {
    margin-top: 0 !important;
}

/* Avoid inherited column stretching from shifting one card. */
[data-testid="stHorizontalBlock"] {
    align-items: flex-start;
}

@media(max-width: 1000px) {
    .st-key-weather_panel,
    .st-key-prediction_panel {
        min-height: 0;
    }
    .st-key-weather_secondary,
    .st-key-prediction_secondary {
        min-height: 0;
        max-height: none;
        overflow: visible;
    }
}
</style>
"""

base.CSS += ALIGNMENT_CSS
CSS = base.CSS


def render_trend(mh):
    with st.container(border=True, key="weather_panel"):
        st.markdown('<div class="dg-panel-title">Jejak cuaca</div>', unsafe_allow_html=True)
        st.markdown('<div class="dg-field-note">Rentang waktu</div>', unsafe_allow_html=True)

        with st.container(key="weather_primary"):
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

        st.markdown('<div class="dg-secondary-note">Parameter grafik</div>', unsafe_allow_html=True)
        with st.container(key="weather_secondary"):
            selected = st.radio(
                "Parameter cuaca",
                options,
                horizontal=True,
                key="weather_parameter",
                label_visibility="collapsed",
            )
            st.caption("Pilih unsur cuaca yang ingin ditampilkan.")

        mapping = {
            "Suhu": ({"tt_air_avg": "Suhu udara", "tt_air_min": "Minimum observasi"}, "Suhu (°C)"),
            "Kelembapan": ({"rh_avg": "Kelembapan"}, "RH (%)"),
            "Angin": ({"ws_avg": "Angin observasi", "ws_mean_1h": "Rata-rata 1 jam"}, "Kecepatan · unit sumber AWS"),
            "Hujan AWS": ({"rr": "Pembacaan hujan AWS"}, "Pembacaan AWS (mm)"),
        }
        fields, ylabel = mapping[selected]

        with st.container(key="weather_chart"):
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
    with st.container(border=True, key="prediction_panel"):
        st.markdown('<div class="dg-panel-title">Perjalanan prediksi</div>', unsafe_allow_html=True)
        st.markdown('<div class="dg-field-note">Tanggal target prediksi</div>', unsafe_allow_html=True)

        if rh.empty or "tanggal_target" not in rh:
            st.info("Riwayat rilis belum tersedia.")
            return
        dates = sorted(rh["tanggal_target"].dropna().astype(str).str[:10].unique(), reverse=True)
        if not dates:
            st.info("Tanggal target belum tersedia.")
            return

        with st.container(key="prediction_primary"):
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

        st.markdown('<div class="dg-secondary-note">Rilis per jam (WIB)</div>', unsafe_allow_html=True)
        with st.container(key="prediction_secondary"):
            base.release_strip(selected, target, threshold, now)

        with st.container(key="prediction_chart"):
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
