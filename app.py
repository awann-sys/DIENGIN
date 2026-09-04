#!/usr/bin/env python3
"""
DIENGIN - Dashboard v1
Sistem Monitoring dan Prediksi Embun Beku Dieng

Dashboard ini:
- hanya membaca output pipeline;
- tidak mengunduh data;
- tidak menjalankan model;
- tidak melakukan retraining.

Jalankan:
    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# 0. KONFIGURASI
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
HISTORY_DIR = PROJECT_ROOT / "data" / "history"

MONITORING_JSON = OUTPUT_DIR / "monitoring_latest.json"
PREDICTION_JSON = OUTPUT_DIR / "prediction_latest.json"
PIPELINE_JSON = OUTPUT_DIR / "pipeline_status.json"

MONITORING_HISTORY = HISTORY_DIR / "monitoring_history.csv"
RELEASE_HISTORY = HISTORY_DIR / "prediction_release_history.csv"
NIGHT_HISTORY = HISTORY_DIR / "prediction_night_history.csv"

st.set_page_config(
    page_title="DIENGIN",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 1. STYLE
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.3rem;
        padding-bottom: 2rem;
    }

    .diengin-subtitle {
        color: rgba(120,120,120,0.95);
        font-size: 0.95rem;
        margin-top: -0.65rem;
        margin-bottom: 1rem;
    }

    .status-box {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 0.8rem;
        padding: 0.8rem 1rem;
        margin-bottom: 0.8rem;
    }

    .small-note {
        font-size: 0.83rem;
        color: rgba(120,120,120,0.95);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. HELPER
# ============================================================

def read_json(path: Path) -> dict | None:
    if not path.is_file() or path.stat().st_size == 0:
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file() or path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def fmt_float(value, decimals=2, suffix=""):
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{decimals}f}{suffix}"


def fmt_probability(value):
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 100:.2f}%"


def parse_datetime(value):
    if value in (None, "", "null"):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce")


def fmt_wib(value, include_date=True):
    dt = parse_datetime(value)
    if pd.isna(dt):
        return "—"

    if include_date:
        return dt.strftime("%d %b %Y, %H:%M WIB")
    return dt.strftime("%H:%M WIB")


def normalize_status(value):
    if value is None:
        return "unknown"
    return str(value).strip().lower()


def status_icon(value):
    value = normalize_status(value)

    mapping = {
        "success": "✅",
        "valid": "✅",
        "current": "🟢",
        "partial": "🟡",
        "delayed": "🟠",
        "stale": "🔴",
        "invalid": "🔴",
        "error": "🔴",
        "missing": "⚪",
        "unknown": "⚪",
        "future_timestamp": "🔴",
    }
    return mapping.get(value, "⚪")


def prediction_text(prediction_value, complete=False):
    if prediction_value is None or pd.isna(prediction_value):
        return "Belum tersedia"

    try:
        prediction_value = int(prediction_value)
    except Exception:
        return "Belum tersedia"

    if prediction_value == 1:
        base = "Terindikasi embun beku"
    else:
        base = "Belum terindikasi embun beku"

    if complete:
        return base
    return f"{base} (sementara)"


def safe_bool(value):
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


# ============================================================
# 3. SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## ❄️ DIENGIN")
    st.caption("Monitoring & Prediksi Embun Beku Dieng")

    st.divider()

    if st.button("🔄 Muat ulang dashboard", width="stretch"):
        st.rerun()

    st.markdown(
        """
        <div class="small-note">
        Dashboard membaca file hasil pipeline lokal.
        Auto-refresh dashboard tidak menjalankan downloader
        atau model secara otomatis.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.caption("Refresh tampilan: setiap 15 menit")


# ============================================================
# 4. DASHBOARD
# ============================================================

st.title("❄️ DIENGIN")
st.markdown(
    '<div class="diengin-subtitle">'
    "Sistem Monitoring dan Prediksi Embun Beku Dieng"
    "</div>",
    unsafe_allow_html=True,
)


@st.fragment(run_every="15m")
def live_dashboard():
    monitoring = read_json(MONITORING_JSON)
    prediction = read_json(PREDICTION_JSON)
    pipeline = read_json(PIPELINE_JSON)

    monitoring_history = read_csv(MONITORING_HISTORY)
    release_history = read_csv(RELEASE_HISTORY)
    night_history = read_csv(NIGHT_HISTORY)

    # --------------------------------------------------------
    # A. STATUS SISTEM
    # --------------------------------------------------------
    st.subheader("Status Sistem")

    pipeline_status = normalize_status(
        pipeline.get("status") if pipeline else None
    )
    monitoring_status = normalize_status(
        monitoring.get("monitoring_status") if monitoring else None
    )

    latest_obs = (
        monitoring.get("latest_observation", {})
        if monitoring
        else {}
    )

    freshness = normalize_status(
        latest_obs.get("freshness_status")
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Pipeline",
            f"{status_icon(pipeline_status)} {pipeline_status.upper()}",
            border=True,
        )

    with c2:
        st.metric(
            "Monitoring",
            f"{status_icon(monitoring_status)} {monitoring_status.upper()}",
            border=True,
        )

    with c3:
        st.metric(
            "Freshness data",
            f"{status_icon(freshness)} {freshness.upper()}",
            border=True,
        )

    with c4:
        data_age = latest_obs.get("data_age_minutes")
        st.metric(
            "Umur data",
            fmt_float(data_age, 1, " menit"),
            border=True,
        )

    if monitoring is None:
        st.error(
            "monitoring_latest.json belum tersedia. "
            "Jalankan pipeline DIENGIN terlebih dahulu."
        )
        return

    if monitoring.get("status") != "success":
        st.error(
            monitoring.get(
                "message",
                "Monitoring terakhir tidak berhasil.",
            )
        )
        return

    if freshness in {"stale", "future_timestamp"}:
        st.warning(
            "Data AWS terbaru tidak berada dalam status current. "
            "Interpretasi kondisi terkini dan prediksi perlu dilakukan dengan hati-hati."
        )
    elif monitoring_status in {"partial", "invalid"}:
        st.warning(
            "Sebagian parameter monitoring tidak tersedia atau tidak lolos "
            "aturan QC operasional DIENGIN."
        )

    # --------------------------------------------------------
    # B. MONITORING TERKINI
    # --------------------------------------------------------
    st.subheader("Monitoring AWS Terkini")

    station = monitoring.get("station") or {}
    params = latest_obs.get("parameters") or {}
    source_values = latest_obs.get("source_values") or {}
    adapter = latest_obs.get("operational_adapter") or {}
    trend = monitoring.get("trend_1h") or {}

    st.caption(
        f"Observasi terbaru: **{fmt_wib(latest_obs.get('time_wib'))}**"
        + (
            f" · {station.get('station_name')}"
            if station.get("station_name")
            else ""
        )
    )

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            "Suhu udara",
            fmt_float(params.get("tt_air_avg"), 2, " °C"),
            delta=(
                fmt_float(trend.get("tt_air_avg_change"), 2, " °C / ~1 jam")
                if trend.get("tt_air_avg_change") is not None
                else None
            ),
            border=True,
        )

    with m2:
        st.metric(
            "Suhu minimum",
            fmt_float(params.get("tt_air_min"), 2, " °C"),
            delta=(
                fmt_float(trend.get("tt_air_min_change"), 2, " °C / ~1 jam")
                if trend.get("tt_air_min_change") is not None
                else None
            ),
            border=True,
        )

    rh_effective = params.get("rh_avg")
    rh_source = source_values.get("rh_avg_source")
    rh_invalid = safe_bool(adapter.get("rh_adapter_invalid"))

    with m3:
        if rh_effective is not None:
            rh_display = fmt_float(rh_effective, 1, " %")
        elif rh_invalid and rh_source is not None:
            rh_display = "Unavailable"
        else:
            rh_display = "—"

        st.metric(
            "Kelembapan relatif",
            rh_display,
            delta=(
                fmt_float(trend.get("rh_avg_change"), 1, " % / ~1 jam")
                if trend.get("rh_avg_change") is not None
                else None
            ),
            border=True,
        )

        if rh_invalid and rh_source is not None:
            st.caption(
                f"Nilai sumber: {fmt_float(rh_source, 1, ' %')} · "
                "tidak dipakai oleh adapter operasional."
            )

    with m4:
        st.metric(
            "Kecepatan angin",
            fmt_float(params.get("ws_avg"), 2),
            delta=(
                fmt_float(trend.get("ws_avg_change"), 2, " / ~1 jam")
                if trend.get("ws_avg_change") is not None
                else None
            ),
            border=True,
        )

    e1, e2, e3, e4 = st.columns(4)

    with e1:
        st.metric(
            "Titik embun",
            fmt_float(params.get("dew_point_c"), 2, " °C"),
            border=True,
        )

    with e2:
        st.metric(
            "Curah hujan",
            fmt_float(params.get("rr"), 2, " mm"),
            border=True,
        )

    with e3:
        st.metric(
            "Tekanan",
            fmt_float(params.get("pp_air"), 2, " hPa"),
            border=True,
        )

    with e4:
        wd = params.get("wd_avg")
        st.metric(
            "Arah angin",
            fmt_float(wd, 1, "°"),
            border=True,
        )

    # --------------------------------------------------------
    # C. PREDIKSI
    # --------------------------------------------------------
    st.subheader("Prediksi Embun Beku")

    if prediction is None:
        st.info(
            "prediction_latest.json belum tersedia."
        )
    elif prediction.get("status") != "success":
        st.warning(
            prediction.get(
                "message",
                "Prediksi terbaru belum tersedia.",
            )
        )
    else:
        threshold = prediction.get("threshold_stacked")
        pmax = prediction.get("probability_max_so_far")
        latest_release = prediction.get("latest_release") or {}
        latest_prob = latest_release.get("stacked_probability")
        prediction_value = prediction.get("prediction_so_far")
        night_complete = safe_bool(prediction.get("night_complete"))
        available = prediction.get("releases_available")
        expected = prediction.get("releases_expected")

        p1, p2, p3, p4 = st.columns(4)

        with p1:
            st.metric(
                "Probabilitas rilis terakhir",
                fmt_probability(latest_prob),
                border=True,
            )

        with p2:
            st.metric(
                "Probabilitas maksimum",
                fmt_probability(pmax),
                border=True,
            )

        with p3:
            st.metric(
                "Ambang klasifikasi",
                fmt_probability(threshold),
                border=True,
            )

        with p4:
            st.metric(
                "Rilis tersedia",
                (
                    f"{available}/{expected}"
                    if available is not None and expected is not None
                    else "—"
                ),
                border=True,
            )

        pred_label = prediction_text(
            prediction_value,
            complete=night_complete,
        )

        if prediction_value == 1:
            st.warning(f"**{pred_label}**")
        elif prediction_value == 0:
            st.success(f"**{pred_label}**")
        else:
            st.info("**Prediksi malam belum tersedia.**")

        if latest_release:
            st.caption(
                "Rilis terakhir: "
                f"**{int(latest_release.get('hour_wib')):02d}:00 WIB**"
                if latest_release.get("hour_wib") is not None
                else "Rilis terakhir: —"
            )

        if not night_complete:
            st.caption(
                "Status masih sementara karena seluruh 11 jam rilis "
                "malam target belum lengkap."
            )

        if pmax is not None:
            progress_value = min(max(float(pmax), 0.0), 1.0)
            st.progress(
                progress_value,
                text=(
                    f"Probabilitas maksimum sementara {progress_value * 100:.2f}% "
                    f"· ambang {float(threshold) * 100:.2f}%"
                    if threshold is not None
                    else f"Probabilitas maksimum sementara {progress_value * 100:.2f}%"
                ),
            )

    # --------------------------------------------------------
    # D. GRAFIK HISTORY MONITORING
    # --------------------------------------------------------
    st.subheader("Riwayat Monitoring")

    if monitoring_history.empty:
        st.info(
            "History monitoring belum cukup untuk ditampilkan."
        )
    else:
        mh = monitoring_history.copy()
        mh["observation_time_wib"] = pd.to_datetime(
            mh["observation_time_wib"],
            errors="coerce",
        )
        mh = mh.dropna(subset=["observation_time_wib"]).sort_values(
            "observation_time_wib"
        )

        # batasi tampilan untuk performa dashboard
        mh = mh.tail(288)  # ~48 jam bila data 10-menitan tersimpan lengkap

        tab_temp, tab_rh, tab_wind = st.tabs(
            ["Suhu", "Kelembapan", "Angin"]
        )

        with tab_temp:
            temp_cols = [
                col for col in ["tt_air_avg", "tt_air_min", "tmin_min_1h"]
                if col in mh.columns
            ]
            if temp_cols:
                st.line_chart(
                    mh,
                    x="observation_time_wib",
                    y=temp_cols,
                    x_label="Waktu",
                    y_label="Suhu (°C)",
                    height=330,
                )
            else:
                st.info("Data suhu belum tersedia pada history.")

        with tab_rh:
            if "rh_avg" in mh.columns:
                st.line_chart(
                    mh,
                    x="observation_time_wib",
                    y="rh_avg",
                    x_label="Waktu",
                    y_label="RH (%)",
                    height=330,
                )
            else:
                st.info("Data RH belum tersedia pada history.")

        with tab_wind:
            wind_cols = [
                col for col in ["ws_avg", "ws_mean_1h", "ws_max_1h"]
                if col in mh.columns
            ]
            if wind_cols:
                st.line_chart(
                    mh,
                    x="observation_time_wib",
                    y=wind_cols,
                    x_label="Waktu",
                    y_label="Kecepatan angin",
                    height=330,
                )
            else:
                st.info("Data angin belum tersedia pada history.")

    # --------------------------------------------------------
    # E. RIWAYAT PROBABILITAS RILIS
    # --------------------------------------------------------
    st.subheader("Riwayat Probabilitas Rilis")

    if release_history.empty:
        st.info(
            "History rilis prediksi belum tersedia."
        )
    else:
        rh = release_history.copy()

        if "waktu_rilis_wib" in rh.columns:
            rh["waktu_rilis_wib"] = pd.to_datetime(
                rh["waktu_rilis_wib"],
                errors="coerce",
            )

        if "stack_prob" in rh.columns:
            rh["stack_prob_pct"] = (
                pd.to_numeric(
                    rh["stack_prob"],
                    errors="coerce",
                )
                * 100.0
            )

            threshold_value = None
            if prediction and prediction.get("threshold_stacked") is not None:
                threshold_value = float(
                    prediction["threshold_stacked"]
                ) * 100.0

            if threshold_value is not None:
                rh["ambang_pct"] = threshold_value

            rh_plot = (
                rh.dropna(
                    subset=["waktu_rilis_wib"]
                    if "waktu_rilis_wib" in rh.columns
                    else []
                )
                .sort_values(
                    "waktu_rilis_wib"
                    if "waktu_rilis_wib" in rh.columns
                    else rh.columns[0]
                )
                .tail(55)
            )

            y_cols = ["stack_prob_pct"]
            if "ambang_pct" in rh_plot.columns:
                y_cols.append("ambang_pct")

            if "waktu_rilis_wib" in rh_plot.columns:
                st.line_chart(
                    rh_plot,
                    x="waktu_rilis_wib",
                    y=y_cols,
                    x_label="Jam rilis",
                    y_label="Probabilitas (%)",
                    height=330,
                )

        show_cols = [
            col for col in [
                "tanggal_target",
                "jam_rilis_wib",
                "waktu_rilis_wib",
                "stack_prob",
                "ann_prob",
                "svm_prob",
                "rf_prob",
                "status_data_rilis",
            ]
            if col in rh.columns
        ]

        if show_cols:
            table = rh[show_cols].tail(22).copy()

            for col in ["stack_prob", "ann_prob", "svm_prob", "rf_prob"]:
                if col in table.columns:
                    table[col] = (
                        pd.to_numeric(table[col], errors="coerce") * 100
                    ).round(3)

            st.dataframe(
                table,
                width="stretch",
                hide_index=True,
            )

    # --------------------------------------------------------
    # F. NIGHT HISTORY
    # --------------------------------------------------------
    with st.expander("Riwayat ringkasan malam"):
        if night_history.empty:
            st.info("Ringkasan history malam belum tersedia.")
        else:
            nh = night_history.tail(30).copy()
            st.dataframe(
                nh,
                width="stretch",
                hide_index=True,
            )

    # --------------------------------------------------------
    # G. FOOTER
    # --------------------------------------------------------
    st.divider()

    generated_monitoring = (
        monitoring.get("generated_at_wib")
        if monitoring
        else None
    )
    generated_prediction = (
        prediction.get("generated_at_wib")
        if prediction
        else None
    )

    st.caption(
        f"Monitoring diperbarui sistem: {fmt_wib(generated_monitoring)} · "
        f"Prediksi diperbarui sistem: {fmt_wib(generated_prediction)}"
    )
    st.caption(
        "DIENGIN merupakan prototipe penelitian monitoring dan prediksi "
        "embun beku berbasis AWS dan model skripsi; bukan produk peringatan resmi BMKG."
    )


live_dashboard()
