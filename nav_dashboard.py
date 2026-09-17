#!/usr/bin/env python3
"""Primary DIENGIN dashboard navigation and composition.

Prediksi: current probability, concise trend/prospect, current AWS hierarchy,
nightly release journey, and fully custom multi-variable exploration.
Prospek BMKG: external forecast context only.
Monitoring: all AWS parameters plus on-demand historical AWS exploration.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

import app
import centered_dashboard as ui
import dashboard_features as features
import theme_controller as theme
from ews_narrative import build_ews_narrative

base = app.base

TOPNAV_CSS = r"""
<style>
.st-key-dg_topbar{
  margin:.15rem 0 1rem!important;
  position:sticky!important;
  top:.5rem!important;
  z-index:999!important;
}
.st-key-dg_topbar > div{
  background:color-mix(in srgb,var(--dg-card) 94%,transparent)!important;
  border:1px solid var(--dg-border)!important;
  border-radius:20px!important;
  padding:.52rem .72rem!important;
  box-shadow:0 10px 30px var(--dg-shadow)!important;
  backdrop-filter:blur(16px)!important;
  -webkit-backdrop-filter:blur(16px)!important;
}
.st-key-dg_topbar [data-testid="stHorizontalBlock"]{
  align-items:center!important;
  gap:.55rem!important;
}
.dg-top-brand{
  display:flex;align-items:center;gap:.62rem;min-height:40px;
  color:var(--dg-ink);font-family:"Plus Jakarta Sans",sans-serif;
  font-size:1.02rem;font-weight:800;letter-spacing:.025em;white-space:nowrap;
}
.dg-top-brand-badge{
  width:36px;height:36px;display:grid;place-items:center;border-radius:11px;
  background:linear-gradient(135deg,var(--dg-blue),var(--dg-cyan));color:#fff;
  font-size:17px;box-shadow:0 6px 14px var(--dg-glow);flex:0 0 36px;
}
.dg-top-brand-place{
  margin-left:.15rem;padding-left:.72rem;border-left:1px solid var(--dg-border);
  color:var(--dg-muted);font-size:.78rem;font-weight:650;letter-spacing:0;
}
.st-key-dg_nav_control{
  display:flex!important;justify-content:center!important;align-items:center!important;
  min-height:40px!important;
}
.st-key-dg_nav_control [data-testid="stSegmentedControl"]{
  width:auto!important;justify-content:center!important;margin:0 auto!important;
}
.st-key-dg_nav_control [data-testid="stSegmentedControl"] > div{
  width:auto!important;justify-content:center!important;gap:.12rem!important;
  background:transparent!important;border:0!important;padding:0!important;
}
.st-key-dg_nav_control button{
  min-width:112px!important;min-height:38px!important;padding:.42rem .72rem!important;
  border-radius:10px!important;font-family:"Plus Jakarta Sans",sans-serif!important;
  font-size:.92rem!important;font-weight:720!important;
}
.st-key-dg_theme_col{
  display:flex!important;justify-content:flex-end!important;align-items:center!important;
  min-height:40px!important;
}
.dg-hero-copy-note{margin-top:.75rem;font-size:.78rem;opacity:.78}

@media(max-width:980px){
  .dg-top-brand-place{display:none}
  .st-key-dg_nav_control button{min-width:94px!important}
}
@media(max-width:760px){
  .st-key-dg_topbar{top:.25rem!important}
  .st-key-dg_topbar > div{padding:.46rem .5rem!important;border-radius:16px!important}
  .dg-top-brand span:nth-child(2){display:none}
  .dg-top-brand-badge{width:34px;height:34px;flex-basis:34px}
  .st-key-dg_nav_control button{min-width:auto!important;font-size:.79rem!important;padding:.36rem .42rem!important}
}
</style>
"""
base.CSS += TOPNAV_CSS


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _top_nav() -> str:
    # Equal side columns keep the navigation optically centered at all widths.
    with st.container(key="dg_topbar"):
        brand_col, nav_col, theme_col = st.columns([1.0, 1.65, 1.0], vertical_alignment="center")
        with brand_col:
            st.markdown(
                '<div class="dg-top-brand">'
                '<span class="dg-top-brand-badge">❄</span>'
                '<span>DIENGIN</span>'
                '<span class="dg-top-brand-place">Dieng</span>'
                '</div>',
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
        with theme_col:
            with st.container(key="dg_theme_col"):
                theme.render_toggle()
    return page or "Prediksi"


def _load_data():
    monitor, ms = base.read_file("output/monitoring_latest.json")
    pred, ps = base.read_file("output/prediction_latest.json")
    pipeline, ss = base.read_file("output/pipeline_status.json")
    monitoring_history, hs = base.read_file("data/history/monitoring_history.csv", "csv")
    release_history, rs = base.read_file("data/history/prediction_release_history.csv", "csv")
    nights, ns = base.read_file("data/history/prediction_night_history.csv", "csv")
    mh = base.timed_frame(monitoring_history, "observation_time_wib")
    rh = base.timed_frame(release_history, "waktu_rilis_wib")
    return monitor, pred, pipeline, mh, rh, nights, {
        "monitoring": ms, "prediksi": ps, "pipeline": ss,
        "riwayat_monitoring": hs, "riwayat_rilis": rs, "riwayat_malam": ns,
    }


def _future_bmkg_points(payload, now: pd.Timestamp):
    rows = []
    if not isinstance(payload, dict):
        return rows
    for block in payload.get("data") or []:
        if not isinstance(block, dict):
            continue
        for daily in block.get("cuaca") or []:
            if not isinstance(daily, list):
                continue
            for row in daily:
                if not isinstance(row, dict):
                    continue
                try:
                    ts = pd.Timestamp(row.get("local_datetime"))
                    ts = ts.tz_localize(base.WIB) if ts.tzinfo is None else ts.tz_convert(base.WIB)
                except Exception:
                    continue
                if ts >= now:
                    rows.append((ts, row))
    rows.sort(key=lambda x: x[0])
    return rows


def _prospect_sentence(payload, now: pd.Timestamp) -> str:
    rows = _future_bmkg_points(payload, now)[:3]
    if not rows:
        return "Prospek beberapa jam ke depan belum tersedia."
    temps = [_num(row.get("t")) for _, row in rows]
    temps = [x for x in temps if x is not None]
    weather = rows[0][1].get("weather_desc") or rows[0][1].get("weather_desc_en") or "kondisi cuaca tersedia"
    if len(temps) >= 2:
        delta = temps[-1] - temps[0]
        if delta <= -1.0:
            direction = "suhu masih cenderung menurun"
        elif delta >= 1.0:
            direction = "suhu cenderung meningkat"
        else:
            direction = "suhu cenderung relatif stabil"
        return f"Prospek beberapa jam ke depan menunjukkan {weather.lower()} dan {direction}."
    return f"Prospek cuaca terdekat menunjukkan {weather.lower()}."


def _hero_text(result: dict, monitor: dict, prospect: str) -> str:
    code = str(result.get("trajectory_code") or "")
    if code in {"MENINGKAT_BERTAHAP", "MENINGKAT", "MENINGKAT_KUAT"}:
        first = "Probabilitas naik pada beberapa rilis terakhir."
    elif code in {"MENURUN_BERTAHAP", "MENURUN", "MENURUN_KUAT"}:
        first = "Probabilitas menurun pada beberapa rilis terakhir."
    elif code == "RELATIF_STABIL":
        first = "Probabilitas hanya berubah kecil pada beberapa rilis terakhir."
    else:
        first = "Arah perkembangan probabilitas masih perlu dipantau pada rilis berikutnya."

    trend = monitor.get("trend_1h") or {}
    temp_change = _num(trend.get("tt_air_avg_change"))
    wind_change = _num(trend.get("ws_avg_change"))
    condition_parts = []
    if temp_change is not None:
        condition_parts.append("suhu masih menurun" if temp_change <= -0.3 else "suhu mulai meningkat" if temp_change >= 0.3 else "suhu relatif stabil")
    if wind_change is not None:
        condition_parts.append("angin melemah" if wind_change <= -0.2 else "angin menguat" if wind_change >= 0.2 else "angin relatif stabil")
    current = ("Kondisi aktual menunjukkan " + " dan ".join(condition_parts) + ".") if condition_parts else ""
    return " ".join(x for x in [first, current, prospect] if x)


def _render_hero(monitor, pred, rh, now):
    latest_obs = monitor.get("latest_observation") or {}
    latest_release = pred.get("latest_release") or {}
    fresh, fresh_text, _ = base.freshness(latest_obs.get("time_wib"), now)

    try:
        bmkg_payload, _ = app.get_bmkg_forecast()
    except Exception:
        bmkg_payload = {}
    result = build_ews_narrative(monitor, pred, rh, bmkg_payload, now)
    p_now = result.get("probability_now")
    delta = result.get("probability_change")
    headline = result.get("headline") or "Potensi frost saat ini"
    prospect = _prospect_sentence(bmkg_payload, now)
    hero_text = _hero_text(result, monitor, prospect)

    hour = _num(latest_release.get("hour_wib"))
    update_text = f"RILIS {int(hour):02d}.00 WIB" if hour is not None else "PEMBARUAN TERBARU"
    freshness_text = fresh_text.upper() if fresh_text else "STATUS DATA"
    prob_text = "—" if p_now is None else f"{p_now * 100:.0f}%"
    if delta is None:
        delta_text = "Menunggu pembanding rilis"
    elif abs(delta) < 0.005:
        delta_text = "→ relatif stabil"
    else:
        delta_text = f"↑ +{delta * 100:.0f} poin" if delta > 0 else f"↓ {abs(delta) * 100:.0f} poin"

    st.markdown(
        '<div class="dg-hero"><div>'
        f'<div class="dg-hero-kicker">DIENG · {base.esc(update_text)} · {base.esc(freshness_text)}</div>'
        f'<h1>{base.esc(headline)}</h1>'
        f'<p>{base.esc(hero_text)}</p>'
        '<div class="dg-hero-copy-note">Prospek cuaca eksternal hanya menjadi konteks dan tidak mengubah probabilitas model DIENGIN.</div>'
        '</div><div class="dg-hero-score">'
        '<div class="label">Probabilitas saat ini</div>'
        f'<div class="value">{base.esc(prob_text)}</div>'
        f'<div class="sub">{base.esc(delta_text)}</div>'
        '</div></div>',
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
        st.markdown('<div class="dg-info warn">' + base.esc(" ".join(notices)) + '</div>', unsafe_allow_html=True)


def dashboard() -> None:
    theme.apply_theme()
    now = pd.Timestamp.now(tz=base.WIB)
    monitor, pred, pipeline, mh, rh, nights, statuses = _load_data()
    page = _top_nav()

    if page == "Prediksi":
        fresh = _render_hero(monitor, pred, rh, now)
        features.render_prediction_weather(monitor, mh, now)
        _render_notices(monitor, pipeline, statuses["monitoring"], fresh)

        ui._section(
            "PERKEMBANGAN PREDIKSI",
            "Perkembangan prediksi selama satu malam",
            "Setiap kartu menunjukkan probabilitas pada satu rilis DIENGIN. Jam yang belum dirilis tetap ditandai sebagai menunggu.",
        )
        ui._render_hourly_cards(rh, pred)

        ui._section(
            "EKSPLORASI DATA",
            "Bandingkan parameter dan probabilitas model",
            "Pilih kombinasi variabel apa pun pada setiap grafik. Setiap seri memakai skala otomatis sendiri agar arah tren tetap terlihat.",
        )
        features.render_custom_explorer(
            mh,
            rh,
            key_prefix="prediction_explore",
            include_models=True,
            default_labels=["Suhu udara", "Probabilitas Stacked / Final"],
            allow_download=False,
        )

    elif page == "Prospek BMKG":
        ui._section(
            "PROSPEK BMKG",
            "Prakiraan cuaca Dieng",
            "Prakiraan BMKG menjadi konteks prospek dan tidak mengubah probabilitas frost DIENGIN.",
        )
        app.render_bmkg_forecast(now)

    else:
        features.render_monitoring_cards(monitor)
        latest_obs = monitor.get("latest_observation") or {}
        fresh, _, _ = base.freshness(latest_obs.get("time_wib"), now)
        _render_notices(monitor, pipeline, statuses["monitoring"], fresh)

        ui._section(
            "HISTORI AWS",
            "Pilih sendiri periode yang ingin dilihat",
            "Data historis baru diminta ketika tombol Muat Data ditekan. Setelah tersedia, data dapat digrafikkan dan diunduh.",
        )
        features.render_on_demand_monitoring_explorer()

        with st.expander("Panduan & status sistem"):
            base.render_info(monitor, pred, pipeline, statuses, now)

    st.markdown(
        '<div class="dg-footer">DIENGIN · Prototipe penelitian, bukan peringatan resmi BMKG. '
        'Prakiraan eksternal hanya menjadi konteks. Seluruh waktu dalam WIB.</div>',
        unsafe_allow_html=True,
    )