#!/usr/bin/env python3
"""Three-tab top navigation for the Figma-aligned DIENGIN dashboard.

The navbar is the actual page switcher: Prediksi, Prospek BMKG, and Monitoring.
All model, QC, runtime, and BMKG behavior remains in the existing modules.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import app
import centered_dashboard as ui
import figma_dashboard as figma

base = app.base

TOPNAV_CSS = r"""
<style>
/* Real interactive navbar, replacing the lower Streamlit tabs. */
.st-key-dg_topbar{
  margin:.15rem 0 1rem!important;
}
.st-key-dg_topbar > div{
  background:#fff!important;
  border:1px solid var(--dg-border)!important;
  border-radius:20px!important;
  padding:.62rem .78rem!important;
  box-shadow:0 8px 26px rgba(25,47,78,.045)!important;
}
.st-key-dg_topbar [data-testid="stHorizontalBlock"]{
  align-items:center!important;
  gap:.7rem!important;
}
.dg-top-brand{
  display:flex;
  align-items:center;
  gap:.68rem;
  min-height:42px;
  color:var(--dg-ink);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:1.05rem;
  font-weight:800;
  letter-spacing:.025em;
}
.dg-top-brand-badge{
  width:36px;height:36px;
  display:grid;place-items:center;
  border-radius:11px;
  background:var(--dg-blue);
  color:#fff;
  font-size:18px;
}
.dg-top-place{
  min-height:42px;
  display:flex;
  align-items:center;
  justify-content:flex-end;
}
.dg-top-place span{
  display:inline-flex;
  align-items:center;
  gap:.38rem;
  padding:.55rem .82rem;
  border-radius:999px;
  background:#edf5ff;
  color:var(--dg-blue);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.95rem;
  font-weight:700;
}
.st-key-dg_nav_control{
  display:flex!important;
  justify-content:center!important;
  align-items:center!important;
  min-height:42px;
}
.st-key-dg_nav_control [data-testid="stSegmentedControl"]{
  width:100%!important;
  justify-content:center!important;
}
.st-key-dg_nav_control [data-testid="stSegmentedControl"] > div{
  justify-content:center!important;
  gap:.2rem!important;
  background:transparent!important;
  border:0!important;
}
.st-key-dg_nav_control button{
  min-height:38px!important;
  padding:.45rem .72rem!important;
  border-radius:10px!important;
  font-family:"Plus Jakarta Sans",sans-serif!important;
  font-size:.96rem!important;
  font-weight:700!important;
}
/* Remove old tab styling from this composition; no st.tabs are used here. */
@media(max-width:800px){
  .dg-top-place{display:none;}
  .st-key-dg_topbar [data-testid="column"]:last-child{display:none!important;}
  .dg-top-brand{justify-content:flex-start;}
}
@media(max-width:620px){
  .st-key-dg_topbar > div{padding:.55rem!important;}
  .dg-top-brand span:last-child{display:none;}
  .st-key-dg_nav_control button{font-size:.88rem!important;padding:.4rem .5rem!important;}
}
</style>
"""
base.CSS += TOPNAV_CSS


def _top_nav() -> str:
    """Render the real navigation control inside the white top bar."""
    with st.container(key="dg_topbar"):
        brand_col, nav_col, place_col = st.columns([1.0, 1.55, 1.0], vertical_alignment="center")
        with brand_col:
            st.markdown(
                '<div class="dg-top-brand"><span class="dg-top-brand-badge">❄</span>'
                '<span>DIENGIN</span></div>',
                unsafe_allow_html=True,
            )
        with nav_col:
            with st.container(key="dg_nav_control"):
                page = st.segmented_control(
                    "Navigasi utama",
                    ["Prediksi", "Prospek BMKG", "Monitoring"],
                    default="Prediksi",
                    key="dg_primary_nav",
                    label_visibility="collapsed",
                )
        with place_col:
            st.markdown(
                '<div class="dg-top-place"><span>⌖ Dieng Plateau</span></div>',
                unsafe_allow_html=True,
            )
    return page or "Prediksi"


def _load_data(now):
    monitor, ms = base.read_file("output/monitoring_latest.json")
    pred, ps = base.read_file("output/prediction_latest.json")
    pipeline, ss = base.read_file("output/pipeline_status.json")
    monitoring_history, hs = base.read_file("data/history/monitoring_history.csv", "csv")
    release_history, rs = base.read_file("data/history/prediction_release_history.csv", "csv")
    nights, ns = base.read_file("data/history/prediction_night_history.csv", "csv")
    mh = base.timed_frame(monitoring_history, "observation_time_wib")
    rh = base.timed_frame(release_history, "waktu_rilis_wib")
    return monitor, pred, pipeline, mh, rh, nights, {
        "monitoring": ms,
        "prediksi": ps,
        "pipeline": ss,
        "riwayat_monitoring": hs,
        "riwayat_rilis": rs,
        "riwayat_malam": ns,
    }


def _render_hero(monitor, pred, rh, now):
    latest_obs = monitor.get("latest_observation") or {}
    latest_release = pred.get("latest_release") or {}
    fresh, fresh_text, _ = base.freshness(latest_obs.get("time_wib"), now)

    p_now = ui._prob(latest_release.get("stacked_probability"))
    selected = ui._selected_releases(rh, pred.get("target_night_date"))
    p_prev = None
    if not selected.empty and "stack_prob" in selected:
        probs = [
            p for p in pd.to_numeric(selected["stack_prob"], errors="coerce").tolist()
            if ui._prob(p) is not None
        ]
        if p_now is not None and probs and abs(probs[-1] - p_now) < 1e-9 and len(probs) >= 2:
            p_prev = probs[-2]
        elif probs:
            p_prev = probs[-1]

    threshold = ui._prob(pred.get("threshold_stacked"))
    hero_title, hero_text = ui._hero_copy(p_now, p_prev, threshold)
    hour = figma._num(latest_release.get("hour_wib"))
    update_text = f"RILIS {int(hour):02d}.00 WIB" if hour is not None else "PEMBARUAN TERBARU"
    freshness_text = fresh_text.upper() if fresh_text else "STATUS DATA"
    temp = figma._num((latest_obs.get("parameters") or {}).get("tt_air_avg"))
    temp_text = "—" if temp is None else f"{temp:.1f}°C"
    prob_text = "—" if p_now is None else f"{p_now * 100:.0f}%"

    st.markdown(
        '<div class="dg-hero">'
        '<div>'
        f'<div class="dg-hero-kicker">DIENG · {base.esc(update_text)} · {base.esc(freshness_text)}</div>'
        f'<h1>{base.esc(hero_title)}</h1>'
        f'<p>{base.esc(hero_text)} Suhu aktual {base.esc(temp_text)}.</p>'
        '</div>'
        '<div class="dg-hero-score">'
        '<div class="label">Probabilitas saat ini</div>'
        f'<div class="value">{base.esc(prob_text)}</div>'
        f'<div class="sub">Suhu {base.esc(temp_text)}</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    return fresh


def _render_notices(monitor, pipeline, ms, fresh):
    notices = []
    if ms != "ok" or monitor.get("status") != "success":
        notices.append("Monitoring belum tersedia sepenuhnya.")
    elif fresh in {"stale", "future", "delayed"}:
        notices.append("Perhatikan waktu observasi karena data belum sepenuhnya menggambarkan kondisi terbaru.")
    if monitor.get("monitoring_status") in {"partial", "invalid"}:
        notices.append("Sebagian parameter tidak tersedia atau tidak lolos pemeriksaan kualitas.")
    if pipeline and pipeline.get("status") not in {"success", None}:
        notices.append("Pembaruan sistem terakhir belum berhasil.")
    if notices:
        st.markdown(
            '<div class="dg-info warn">' + base.esc(" ".join(notices)) + "</div>",
            unsafe_allow_html=True,
        )


def dashboard() -> None:
    now = pd.Timestamp.now(tz=base.WIB)
    monitor, pred, pipeline, mh, rh, nights, statuses = _load_data(now)
    page = _top_nav()

    if page == "Prediksi":
        fresh = _render_hero(monitor, pred, rh, now)

        # Keep the current AWS summary immediately below the blue hero, as in the master design.
        figma.render_aws_current_conditions(monitor)
        _render_notices(monitor, pipeline, statuses["monitoring"], fresh)

        ui._section(
            "PREDIKSI PER JAM",
            "Bagaimana potensi frost berkembang malam ini?",
            "Setiap kartu menunjukkan probabilitas pada satu rilis DIENGIN. Geser horizontal untuk melihat seluruh jam.",
        )
        ui._render_hourly_cards(rh, pred)

        ui._section(
            "PROSPEK KONDISI",
            "Apa yang mendukung atau melemahkan perkembangan potensi?",
            "Ringkasan menggabungkan trajectory probabilitas, AWS aktual, dan konteks BMKG tanpa mengubah output model.",
        )
        ui._render_prospect_cards(monitor, pred, rh, now)

        ui._section(
            "ANALISIS EWS",
            "Analisis otomatis perkembangan potensi",
            "Narasi berbasis aturan menggunakan probabilitas DIENGIN, AWS aktual, dan konteks prakiraan BMKG.",
        )
        figma._render_ews(monitor, pred, rh, now)

        ui._section(
            "GRAFIK",
            "Perjalanan probabilitas",
            "Lihat perubahan probabilitas antar-rilis secara lebih rinci.",
        )
        base.render_prediction_history(rh, nights, pred, now)

    elif page == "Prospek BMKG":
        ui._section(
            "PROSPEK BMKG",
            "Prakiraan cuaca Dieng",
            "Prakiraan BMKG menjadi konteks prospek dan tidak mengubah probabilitas frost DIENGIN.",
        )
        app.render_bmkg_forecast(now)

    else:  # Monitoring
        figma.render_aws_current_conditions(monitor)
        latest_obs = monitor.get("latest_observation") or {}
        fresh, _, _ = base.freshness(latest_obs.get("time_wib"), now)
        _render_notices(monitor, pipeline, statuses["monitoring"], fresh)

        ui._section(
            "OBSERVASI",
            "Jejak cuaca",
            "Bandingkan perubahan suhu, kelembapan, angin, dan hujan dari AWS.",
        )
        base.render_trend(mh)

        with st.expander("Eksplorasi data"):
            base.render_explore(mh, nights)
        with st.expander("Panduan & status sistem"):
            base.render_info(monitor, pred, pipeline, statuses, now)

    st.markdown(
        '<div class="dg-footer">DIENGIN · Prototipe penelitian, bukan peringatan resmi BMKG. '
        'Prakiraan cuaca pada menu Prospek BMKG bersumber dari BMKG. Seluruh waktu dalam WIB.</div>',
        unsafe_allow_html=True,
    )
