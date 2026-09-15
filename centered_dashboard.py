#!/usr/bin/env python3
"""Centered, symmetric dashboard composition for DIENGIN.

This module only changes presentation. Data ingestion, model inference,
probabilities, QC, history, and BMKG retrieval remain owned by the existing
DIENGIN modules.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import app

base = app.base

CENTERED_CSS = r"""
<style>
.block-container {
    max-width: 1240px !important;
    padding: 2.8rem 2.2rem 3rem !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
.dg-centered-header {
    text-align: center;
    max-width: 760px;
    margin: .2rem auto .65rem;
}
.dg-centered-mark {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    margin: 0 auto .72rem;
    display: grid;
    place-items: center;
    font-size: 34px;
    background: rgba(34,184,167,.13);
    border: 1px solid rgba(34,184,167,.18);
}
.dg-centered-title {
    margin: 0;
    font-size: clamp(2rem, 4vw, 3.15rem);
    line-height: 1;
    letter-spacing: .08em;
    font-weight: 760;
}
.dg-centered-subtitle {
    margin: .65rem auto 0;
    max-width: 620px;
    font-size: 1rem;
    line-height: 1.55;
    opacity: .72;
}
.dg-centered-strip {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
    gap: .55rem 1rem;
    margin: .7rem auto 1.1rem;
    text-align: center;
}
.dg-section-title {
    text-align: center;
    font-size: 1.28rem;
    line-height: 1.3;
    font-weight: 700;
    letter-spacing: -.015em;
    margin: 1.3rem auto .25rem;
}
.dg-section-note {
    text-align: center;
    max-width: 760px;
    margin: 0 auto .8rem;
    font-size: .88rem;
    line-height: 1.5;
    opacity: .68;
}
.dg-forecast {
    max-width: 720px;
    min-height: 0 !important;
    margin: 0 auto !important;
    padding: 1.55rem 1.7rem !important;
    text-align: center;
    border-top-width: 2px !important;
    box-shadow: 0 12px 34px rgba(0,0,0,.035);
}
.dg-forecast .dg-eyebrow,
.dg-forecast .dg-meta,
.dg-forecast h2,
.dg-forecast .dg-score {
    text-align: center !important;
}
.dg-forecast h2 { margin-top: .55rem !important; }
.dg-score {
    font-size: clamp(4.2rem, 9vw, 6.1rem) !important;
    margin: .75rem 0 .3rem !important;
}
.dg-pair {
    justify-content: center !important;
    gap: .75rem 1.6rem !important;
}
.dg-meter {
    max-width: 560px;
    margin: 1.15rem auto .5rem !important;
}
.dg-weather {
    max-width: 1000px;
    margin: .25rem auto 0 !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    gap: 1rem !important;
}
.dg-weather .dg-card {
    min-height: 148px !important;
    padding: 1.05rem .9rem !important;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.dg-weather .dg-label-row {
    justify-content: center !important;
    text-align: center;
}
.dg-weather .dg-value,
.dg-weather .dg-delta { text-align: center !important; }
.dg-weather .dg-value { font-size: 2.45rem !important; }
.dg-info,
.dg-bmkg-hero {
    max-width: 960px;
    margin-left: auto !important;
    margin-right: auto !important;
}
.dg-info {
    text-align: center;
    padding: .85rem 1.15rem !important;
    border-left: 0 !important;
    border-top: 2px solid rgba(34,184,167,.58);
    border-radius: 12px !important;
}
.dg-info.warn { border-top-color: var(--dg-amber) !important; }
.st-key-weather_panel,
.st-key-prediction_panel {
    max-width: 1080px;
    min-height: 0 !important;
    margin-left: auto;
    margin-right: auto;
}
.st-key-weather_panel > div,
.st-key-prediction_panel > div { height: auto !important; }
.dg-panel-title,
.dg-field-note,
.dg-secondary-note {
    justify-content: center !important;
    text-align: center !important;
}
.st-key-weather_primary,
.st-key-prediction_primary,
.st-key-weather_secondary,
.st-key-prediction_secondary {
    max-width: 920px;
    margin-left: auto;
    margin-right: auto;
}
.st-key-weather_secondary [role="radiogroup"] { justify-content: center; }
.st-key-prediction_secondary .dg-release-row {
    max-width: 900px;
    margin-left: auto !important;
    margin-right: auto !important;
}
.dg-bmkg-grid {
    max-width: 1080px;
    margin-left: auto !important;
    margin-right: auto !important;
}
.dg-bmkg-card,
.dg-bmkg-hero,
.dg-bmkg-source { text-align: center; }
.dg-bmkg-weather {
    justify-content: center;
    text-align: center;
}
[data-testid="stTabs"] [role="tablist"] { justify-content: center; }
[data-testid="stCaptionContainer"] p { text-align: center; }
[data-testid="stDataFrame"] *,
[data-testid="stTable"] * { text-align: initial; }
.dg-download-wrap {
    max-width: 330px;
    margin: 1rem auto 0;
}
@media(max-width: 900px) {
    .block-container { padding: 2rem 1rem 2.5rem !important; }
    .dg-weather { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
    .dg-score { font-size: 4.3rem !important; }
}
@media(max-width: 620px) {
    .dg-centered-title { font-size: 2.15rem; }
    .dg-centered-subtitle { font-size: .92rem; }
    .dg-weather {
        grid-template-columns: 1fr !important;
        max-width: 440px;
    }
    .dg-forecast { padding: 1.25rem 1rem !important; }
    .dg-score { font-size: 3.8rem !important; }
    .st-key-prediction_secondary .dg-release-row {
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
        height: auto !important;
        max-height: none !important;
    }
}
</style>
"""

base.CSS += CENTERED_CSS


def _section(title: str, note: str | None = None) -> None:
    st.markdown(f'<div class="dg-section-title">{base.esc(title)}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="dg-section-note">{base.esc(note)}</div>', unsafe_allow_html=True)


def dashboard() -> None:
    now = pd.Timestamp.now(tz=base.WIB)
    monitor, ms = base.read_file("output/monitoring_latest.json")
    pred, ps = base.read_file("output/prediction_latest.json")
    pipeline, ss = base.read_file("output/pipeline_status.json")
    monitoring_history, hs = base.read_file("data/history/monitoring_history.csv", "csv")
    release_history, rs = base.read_file("data/history/prediction_release_history.csv", "csv")
    nights, ns = base.read_file("data/history/prediction_night_history.csv", "csv")

    mh = base.timed_frame(monitoring_history, "observation_time_wib")
    rh = base.timed_frame(release_history, "waktu_rilis_wib")
    latest = monitor.get("latest_observation") or {}
    fresh, fresh_text, age = base.freshness(latest.get("time_wib"), now)

    left, center, right = st.columns([1, 5, 1], vertical_alignment="center")
    with center:
        st.markdown(
            '<div class="dg-centered-header">'
            '<div class="dg-centered-mark">❄</div>'
            '<h1 class="dg-centered-title">DIENGIN</h1>'
            '<div class="dg-centered-subtitle">Monitoring cuaca dan perkembangan potensi embun beku Dataran Tinggi Dieng</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with right:
        if st.button("↻ Segarkan", width="stretch", help="Membaca hasil terbaru yang sudah tersedia.", key="refresh"):
            try:
                app.fetch_bmkg_forecast.clear()
            except Exception:
                pass
            st.rerun()

    pill = "dg-fresh" if fresh == "current" else "dg-old"
    st.markdown(
        f'<div class="dg-centered-strip">'
        f'<span class="dg-pill {pill}"><i class="dg-dot"></i>{base.esc(fresh_text)}</span>'
        f'<span class="dg-muted">{base.esc(base.time_label(latest.get("time_wib")))} · {base.esc(base.age_label(age))}</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    notices = []
    if ms != "ok" or monitor.get("status") != "success":
        notices.append("Monitoring belum tersedia; prediksi dan arsip yang tersedia tetap dapat dibuka.")
    elif fresh in {"stale", "future", "delayed"}:
        notices.append("Perhatikan waktu observasi: data ini belum menggambarkan kondisi terbaru.")
    if monitor.get("monitoring_status") in {"partial", "invalid"}:
        notices.append("Sebagian parameter tidak tersedia atau tidak lolos pemeriksaan kualitas.")
    if pipeline and pipeline.get("status") not in {"success", None}:
        notices.append("Pembaruan sistem terakhir belum berhasil.")
    if notices:
        st.markdown('<div class="dg-info warn">' + base.esc(" ".join(notices)) + '</div>', unsafe_allow_html=True)

    overview, bmkg_tab, explore, info = st.tabs(
        ["Ringkasan", "Prediksi BMKG", "Eksplorasi data", "Panduan & status"]
    )

    with overview:
        _section("Potensi Frost", "Probabilitas pada rilis DIENGIN dan perkembangan kondisi malam berjalan.")
        pad_l, forecast_col, pad_r = st.columns([1, 2.2, 1])
        with forecast_col:
            base.render_forecast(pred, now)

        _section("Kondisi Cuaca Terkini", "Observasi AWS terbaru sebagai konteks perkembangan potensi frost.")
        base.render_weather(monitor)

        _section("Perkembangan Probabilitas", "Jejak rilis per jam untuk melihat apakah potensi menguat, bertahan, atau melemah.")
        base.render_prediction_history(rh, nights, pred, now)

        _section("Jejak Cuaca", "Perkembangan unsur cuaca aktual yang menyertai perubahan probabilitas.")
        base.render_trend(mh)

        st.markdown('<div class="dg-download-wrap">', unsafe_allow_html=True)
        st.download_button(
            "↓ Simpan ringkasan",
            data=(
                f"DIENGIN\nObservasi: {base.time_label(latest.get('time_wib'))}\n"
                f"Status data: {fresh_text}\nTarget prediksi: {base.date_label(pred.get('target_night_date'))}\n"
                f"Hasil: {base.prediction_state(pred, now)['label']}\n"
                f"Probabilitas maksimum dari rilis tersedia: {base.pct(pred.get('probability_max_so_far'))}\n"
                f"Rilis terakhir: {base.time_label((pred.get('latest_release') or {}).get('release_time_wib'))}\n"
                "Prototipe penelitian; bukan peringatan resmi BMKG.\n"
            ).encode("utf-8"),
            file_name="diengin_ringkasan.txt",
            mime="text/plain",
            key="summary_download",
            width="stretch",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with bmkg_tab:
        _section("Prospek Cuaca BMKG", "Prakiraan resmi BMKG digunakan sebagai konteks, bukan untuk mengubah probabilitas model DIENGIN.")
        app.render_bmkg_forecast(now)

    with explore:
        _section("Eksplorasi Data")
        base.render_explore(mh, nights)

    with info:
        _section("Panduan & Status Sistem")
        base.render_info(
            monitor,
            pred,
            pipeline,
            {
                "monitoring": ms,
                "prediksi": ps,
                "pipeline": ss,
                "riwayat_monitoring": hs,
                "riwayat_rilis": rs,
                "riwayat_malam": ns,
            },
            now,
        )

    st.markdown(
        '<div class="dg-footer">DIENGIN · Prototipe penelitian, bukan peringatan resmi BMKG. '
        'Prakiraan cuaca pada tab Prediksi BMKG bersumber dari BMKG. '
        'Seluruh waktu dalam WIB. Data kosong tidak berarti nol.</div>',
        unsafe_allow_html=True,
    )
