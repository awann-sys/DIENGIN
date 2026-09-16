#!/usr/bin/env python3
"""DIENGIN dashboard entrypoint with BMKG public forecast integration."""
# Operational redeploy trigger: 2026-09-15
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pandas as pd
import streamlit as st

# Import UI refinement layer first; it patches app_base renderers/CSS.
import app_ui  # noqa: F401
import app_base as base

BMKG_ADM4 = "33.04.16.2008"
BMKG_API_URL = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={BMKG_ADM4}"

BMKG_CSS = """
<style>
.dg-bmkg-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .9rem;
    margin: .75rem 0 .95rem;
}
.dg-bmkg-card {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    background: rgba(128,128,128,.045);
    min-height: 160px;
}
.dg-bmkg-time {
    font-size: .86rem;
    font-weight: 500;
    opacity: .7;
    margin-bottom: .48rem;
}
.dg-bmkg-weather {
    font-size: 1.2rem;
    font-weight: 680;
    line-height: 1.32;
    min-height: 50px;
    display: flex;
    align-items: flex-start;
}
.dg-bmkg-weather .emoji {
    font-size: 1.55rem;
    line-height: 1;
    margin-right: .42rem;
    flex-shrink: 0;
}
.dg-bmkg-temp {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: -.03em;
    margin: .56rem 0 .32rem;
}
.dg-bmkg-meta {
    font-size: .88rem;
    line-height: 1.55;
    opacity: .8;
}
.dg-bmkg-hero {
    border-left: 3px solid #22b8a7;
    background: rgba(34,184,167,.065);
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.08rem;
    margin: .55rem 0 1rem;
    font-size: .94rem;
    line-height: 1.6;
}
.dg-bmkg-hero strong { font-size: 1.18rem; }
.dg-bmkg-source {
    font-size: .82rem;
    opacity: .72;
    margin-top: .65rem;
}
@media(max-width: 1000px) {
    .dg-bmkg-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media(max-width: 620px) {
    .dg-bmkg-grid { grid-template-columns: 1fr; }
    .dg-bmkg-weather { font-size: 1.08rem; }
    .dg-bmkg-weather .emoji { font-size: 1.4rem; }
    .dg-bmkg-temp { font-size: 2rem; }
}
</style>
"""
base.CSS += BMKG_CSS


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_bmkg_forecast():
    """Fetch official BMKG public forecast for Dieng Kulon."""
    request = urllib.request.Request(
        BMKG_API_URL,
        headers={
            "User-Agent": "DIENGIN/1.0 (+https://github.com/awann-sys/DIENGIN)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Respons BMKG bukan objek JSON.")
    return payload


def get_bmkg_forecast():
    try:
        return fetch_bmkg_forecast(), "ok"
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
        OSError,
    ):
        return {}, "error"


def flatten_bmkg_rows(payload):
    rows = []
    for block in payload.get("data") or []:
        if not isinstance(block, dict):
            continue
        for daily in block.get("cuaca") or []:
            if isinstance(daily, list):
                rows.extend(item for item in daily if isinstance(item, dict))
    rows.sort(
        key=lambda row: (
            base.stamp(row.get("local_datetime"))
            if not pd.isna(base.stamp(row.get("local_datetime")))
            else pd.Timestamp.max.tz_localize(base.WIB)
        )
    )
    return rows


def bmkg_weather_emoji(description):
    text = str(description or "").lower()
    if "petir" in text:
        return "⛈️"
    if "hujan" in text:
        return "🌧️"
    if "kabut" in text or "asap" in text:
        return "🌫️"
    if "berawan" in text:
        return "☁️"
    if "cerah" in text:
        return "☀️"
    return "🌤️"


def render_bmkg_forecast(now):
    st.subheader("Prediksi BMKG · Dieng Kulon")
    st.caption(
        "Prakiraan cuaca resmi BMKG untuk ADM4 33.04.16.2008. "
        "Data BMKG tersedia untuk 3 hari dengan interval prakiraan 3 jam."
    )

    payload, status = get_bmkg_forecast()
    if status != "ok":
        st.warning(
            "Data prakiraan BMKG sedang tidak dapat diambil. "
            "Coba gunakan tombol Segarkan beberapa saat lagi."
        )
        st.caption("Sumber data: BMKG · API Prakiraan Cuaca Terbuka")
        return

    location = payload.get("lokasi") or {}
    rows = flatten_bmkg_rows(payload)
    if not rows:
        st.info("Respons BMKG diterima, tetapi detail prakiraan belum tersedia.")
        return

    village = location.get("desa") or "Dieng Kulon"
    district = location.get("kecamatan") or "—"
    regency = location.get("kotkab") or "—"
    province = location.get("provinsi") or "—"
    st.caption(f"{village} · {district} · {regency} · {province}")

    parsed = []
    for row in rows:
        dt = base.stamp(row.get("local_datetime"))
        if not pd.isna(dt):
            parsed.append((dt, row))

    next_pair = next((item for item in parsed if item[0] >= now), parsed[0] if parsed else None)
    if next_pair:
        dt, row = next_pair
        desc = row.get("weather_desc") or "Cuaca"
        icon = bmkg_weather_emoji(desc)
        st.markdown(
            '<div class="dg-bmkg-hero">'
            f'<strong>{icon} {base.esc(desc)}</strong> · '
            f'{base.esc(base.date_label(dt))}, {dt.strftime("%H:%M")} WIB<br>'
            f'Suhu <b>{base.esc(base.fmt(row.get("t"), 0))} °C</b> · '
            f'RH <b>{base.esc(base.fmt(row.get("hu"), 0))}%</b> · '
            f'Angin <b>{base.esc(base.fmt(row.get("ws"), 1))} km/jam</b> '
            f'dari {base.esc(row.get("wd") or "—")}'
            '</div>',
            unsafe_allow_html=True,
        )

    grouped = {}
    for dt, row in parsed:
        grouped.setdefault(dt.date(), []).append((dt, row))
    dates = list(grouped)[:3]
    if not dates:
        return

    tabs = st.tabs([base.date_label(pd.Timestamp(day, tz=base.WIB)) for day in dates])
    for tab, day in zip(tabs, dates):
        with tab:
            cards = []
            for dt, row in grouped[day]:
                desc = row.get("weather_desc") or "—"
                cards.append(
                    '<div class="dg-bmkg-card">'
                    f'<div class="dg-bmkg-time">{dt.strftime("%H:%M")} WIB</div>'
                    f'<div class="dg-bmkg-weather"><span class="emoji">{bmkg_weather_emoji(desc)}</span>'
                    f'{base.esc(desc)}</div>'
                    f'<div class="dg-bmkg-temp">{base.esc(base.fmt(row.get("t"), 0))}°C</div>'
                    f'<div class="dg-bmkg-meta">RH {base.esc(base.fmt(row.get("hu"), 0))}% · '
                    f'Angin {base.esc(base.fmt(row.get("ws"), 1))} km/jam<br>'
                    f'Dari {base.esc(row.get("wd") or "—")} · '
                    f'Jarak pandang {base.esc(row.get("vs_text") or "—")}</div>'
                    '</div>'
                )
            st.markdown(
                '<div class="dg-bmkg-grid">' + "".join(cards) + "</div>",
                unsafe_allow_html=True,
            )

    analysis = base.stamp(rows[0].get("analysis_date"))
    analysis_text = base.time_label(analysis) if not pd.isna(analysis) else "—"
    st.markdown(
        f'<div class="dg-bmkg-source">Sumber data: BMKG · '
        f'ADM4 {BMKG_ADM4} · Waktu produksi data: {base.esc(analysis_text)}</div>',
        unsafe_allow_html=True,
    )


@st.fragment(run_every="60s")
def dashboard():
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

    brand, refresh = st.columns([5.5, 1])
    with brand:
        st.markdown(
            '<div class="dg-brand"><div class="dg-mark">❄</div><div><h1>DIENGIN</h1>'
            '<p>Cuaca Dieng. Prediksi embun beku.</p></div></div>',
            unsafe_allow_html=True,
        )
    with refresh:
        if st.button(
            "↻ Segarkan",
            width="stretch",
            help="Membaca hasil terbaru yang sudah tersedia.",
            key="refresh",
        ):
            fetch_bmkg_forecast.clear()
            st.rerun()

    pill = "dg-fresh" if fresh == "current" else "dg-old"
    st.markdown(
        f'<div class="dg-strip">'
        f'<span class="dg-pill {pill}"><i class="dg-dot"></i>{base.esc(fresh_text)}</span>'
        f'<span class="dg-muted">{base.esc(base.time_label(latest.get("time_wib")))} · '
        f'{base.esc(base.age_label(age))}</span></div>',
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
        st.markdown(
            '<div class="dg-info warn">' + base.esc(" ".join(notices)) + "</div>",
            unsafe_allow_html=True,
        )

    overview, bmkg_tab, explore, info = st.tabs(
        ["Ringkasan", "Prediksi BMKG", "Eksplorasi data", "Panduan & status"]
    )

    with overview:
        forecast_col, weather_col = st.columns([1, 2.15])
        with forecast_col:
            base.render_forecast(pred, now)
        with weather_col:
            base.render_weather(monitor)
            change = base.number((monitor.get("trend_1h") or {}).get("tt_air_avg_change"))
            if change is not None and monitor.get("status") == "success":
                st.markdown(
                    '<div class="dg-info">' + base.esc(
                        f"Suhu {'turun' if change < 0 else 'naik' if change > 0 else 'tetap'} "
                        f"{base.fmt(abs(change))} °C dibanding referensi sekitar 1 jam sebelumnya. "
                        "Tren ini bukan konfirmasi frost."
                    ) + "</div>",
                    unsafe_allow_html=True,
                )

        weather_plot, release_plot = st.columns([1, 1])
        with weather_plot:
            base.render_trend(mh)
        with release_plot:
            base.render_prediction_history(rh, nights, pred, now)

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
        )

    with bmkg_tab:
        render_bmkg_forecast(now)

    with explore:
        base.render_explore(mh, nights)

    with info:
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


base.dashboard = dashboard


if __name__ == "__main__":
    base.main()
