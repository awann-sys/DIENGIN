#!/usr/bin/env python3
"""DIENGIN UI alignment layer.

The full dashboard implementation lives in app_base.py. This entrypoint
keeps the two lower summary panels on a shared visual grid without altering
data, model, or pipeline behavior.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app_base import *  # noqa: F401,F403
import app_base as base

ALIGNMENT_CSS = """
<style>
/* =========================================================
   TOP SUMMARY — BOTTOM EDGE ALIGNMENT
   ========================================================= */
@media(min-width: 1001px) {
    .dg-forecast {
        min-height: 340px !important;
    }
}

/* =========================================================
   LOWER SUMMARY PANELS — SHARED GRID
   ========================================================= */
.st-key-weather_panel,
.st-key-prediction_panel {
    min-height: 620px;
}

/* Keep both bordered cards visually identical. */
.st-key-weather_panel > div,
.st-key-prediction_panel > div {
    height: 100%;
}

/* Typography hierarchy inside the paired cards. */
.dg-panel-title {
    min-height: 30px;
    display: flex;
    align-items: center;
    margin: 0 0 .08rem;
    padding: 0;
    font-size: 1.15rem;
    font-weight: 680;
    line-height: 1.28;
    letter-spacing: -.01em;
}
.dg-field-note,
.dg-secondary-note {
    min-height: 18px;
    display: flex;
    align-items: center;
    margin: 0 0 .22rem;
    padding: 0;
    font-size: .76rem;
    font-weight: 450;
    line-height: 1.35;
    opacity: .66;
}
.dg-secondary-note {
    margin-top: .52rem;
    margin-bottom: .18rem;
}

/* Primary selectors: same width, height and vertical slot. */
.st-key-weather_primary,
.st-key-prediction_primary {
    min-height: 50px;
}
.st-key-weather_primary [data-testid="stSelectbox"],
.st-key-prediction_primary [data-testid="stSelectbox"] {
    margin: 0 !important;
}
.st-key-weather_primary [data-baseweb="select"] > div,
.st-key-prediction_primary [data-baseweb="select"] > div {
    min-height: 42px !important;
    border-radius: 9px !important;
}
.st-key-weather_primary [data-baseweb="select"] span,
.st-key-prediction_primary [data-baseweb="select"] span {
    font-size: .86rem !important;
}

/* Secondary controls share one fixed band. This is the key alignment rule. */
.st-key-weather_secondary,
.st-key-prediction_secondary {
    min-height: 92px;
    max-height: 92px;
    overflow: hidden;
}

/* Left: radio row occupies exactly the same control height as release boxes. */
.st-key-weather_secondary [data-testid="stRadio"] {
    margin: 0 !important;
}
.st-key-weather_secondary [role="radiogroup"] {
    min-height: 50px;
    display: flex;
    align-items: center;
    gap: .72rem;
}
.st-key-weather_secondary [data-testid="stRadio"] label p {
    font-size: .84rem !important;
    line-height: 1.2 !important;
}

/* Right: 11 release boxes begin on the exact same baseline as the radio row. */
.st-key-prediction_secondary .dg-release-row {
    height: 50px;
    min-height: 50px;
    margin: 0 !important;
    display: grid;
    grid-template-columns: repeat(11, minmax(0, 1fr));
    align-items: stretch;
    gap: 5px;
}
.st-key-prediction_secondary .dg-release {
    min-height: 50px;
    height: 50px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: .24rem .05rem !important;
    border-radius: 9px;
    font-size: .67rem !important;
    line-height: 1.05;
}
.st-key-prediction_secondary .dg-release b {
    margin-top: .22rem !important;
    font-size: .76rem !important;
    line-height: 1.05;
}

/* Notes under both controls use the same type and spacing. */
.st-key-weather_secondary [data-testid="stCaptionContainer"],
.st-key-prediction_secondary [data-testid="stCaptionContainer"] {
    margin-top: .18rem !important;
}
.st-key-weather_secondary [data-testid="stCaptionContainer"] p,
.st-key-prediction_secondary [data-testid="stCaptionContainer"] p {
    margin: 0 !important;
    font-size: .72rem !important;
    line-height: 1.35 !important;
}

/* Graphs start at the same y-position and use the same footprint. */
.st-key-weather_chart,
.st-key-prediction_chart {
    min-height: 300px;
    margin-top: .05rem;
}
.st-key-weather_chart [data-testid="stVegaLiteChart"],
.st-key-prediction_chart [data-testid="stVegaLiteChart"] {
    margin-top: 0 !important;
}

/* Keep card-level captions readable but subordinate. */
.st-key-weather_panel > div > div [data-testid="stCaptionContainer"] p,
.st-key-prediction_panel > div > div [data-testid="stCaptionContainer"] p {
    font-size: .74rem;
    line-height: 1.42;
}

/* Prevent Streamlit column stretching from shifting either card. */
[data-testid="stHorizontalBlock"] {
    align-items: flex-start;
}

@media(max-width: 1100px) {
    .st-key-weather_secondary [role="radiogroup"] {
        gap: .45rem;
    }
    .st-key-weather_secondary [data-testid="stRadio"] label p {
        font-size: .79rem !important;
    }
    .st-key-prediction_secondary .dg-release-row {
        gap: 3px;
    }
    .st-key-prediction_secondary .dg-release {
        font-size: .63rem !important;
    }
    .st-key-prediction_secondary .dg-release b {
        font-size: .70rem !important;
    }
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
    .st-key-prediction_secondary .dg-release-row {
        height: auto;
        min-height: 0;
        grid-template-columns: repeat(6, minmax(0, 1fr));
    }
    .st-key-prediction_secondary .dg-release {
        min-height: 48px;
        height: 48px;
    }
}
</style>
"""

base.CSS += ALIGNMENT_CSS
CSS = base.CSS


def compact_release_strip(releases, target, threshold, now):
    """Render the hourly releases in a fixed-height row for panel alignment."""
    target_dt = base.stamp(target)
    if pd.isna(target_dt):
        return

    selected = (
        releases.loc[
            releases["tanggal_target"].astype(str).str[:10]
            == target_dt.date().isoformat()
        ]
        if "tanggal_target" in releases
        else pd.DataFrame()
    )

    boxes = []
    for hour in [21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]:
        when = target_dt.normalize() + pd.Timedelta(hours=hour) - (
            pd.Timedelta(days=1) if hour >= 21 else pd.Timedelta(0)
        )
        rows = (
            selected.loc[
                pd.to_numeric(selected["jam_rilis_wib"], errors="coerce") == hour
            ]
            if "jam_rilis_wib" in selected
            else pd.DataFrame()
        )
        p = base.probability(rows.iloc[-1].get("stack_prob")) if not rows.empty else None
        css, label = "", "Nanti" if when > now else "—"
        if p is not None:
            css = " hit" if threshold is not None and p >= threshold else " has"
            label = base.pct(p)
        title = f"{base.time_label(when)} · " + (
            label if p is not None else "Belum ada rilis valid"
        )
        boxes.append(
            f'<div class="dg-release{css}" title="{base.esc(title)}">'
            f'{hour:02d}<b>{base.esc(label)}</b></div>'
        )

    st.markdown(
        '<div class="dg-release-row">' + "".join(boxes) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Jam rilis WIB · — belum tersedia · garis kuning menandai ambang pada grafik.")


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
            values = pd.to_numeric(
                subset.get("tt_air_avg", pd.Series(dtype=float)), errors="coerce"
            )
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
        dates = sorted(
            rh["tanggal_target"].dropna().astype(str).str[:10].unique(), reverse=True
        )
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
            summary = nights.loc[
                nights["tanggal_target"].astype(str).str[:10] == target
            ]
            if not summary.empty:
                threshold = base.probability(summary.iloc[-1].get("ambang_final"))

        st.markdown('<div class="dg-secondary-note">Rilis per jam (WIB)</div>', unsafe_allow_html=True)
        with st.container(key="prediction_secondary"):
            compact_release_strip(selected, target, threshold, now)

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

        st.caption(
            f"Ambang target {base.pct(threshold)} · probabilitas per rilis, bukan observasi kejadian frost."
        )
        with st.expander("Bandingkan model"):
            base.draw_chart(
                selected, base.PROB_LABELS, "Probabilitas (%)", "models_chart", True
            )
            st.caption(
                "ANN, SVM, dan Random Forest adalah model dasar. DIENGIN menampilkan hasil stacking; "
                "nilainya bukan rata-rata sederhana."
            )
        with st.expander("Tabel rilis dan unduhan"):
            table = selected.drop(columns=["_time"], errors="ignore").copy()
            cols = [
                c
                for c in [
                    "waktu_rilis_wib",
                    "stack_prob",
                    "ann_prob",
                    "svm_prob",
                    "rf_prob",
                    "status_data_rilis",
                ]
                if c in table
            ]
            table = table[cols]
            for col in base.PROB_LABELS:
                if col in table:
                    table[col] = (
                        pd.to_numeric(table[col], errors="coerce") * 100
                    ).round(2)
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