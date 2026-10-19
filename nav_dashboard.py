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
import expressive_dashboard as design
from ews_narrative import build_ews_narrative

base = app.base

TOPNAV_CSS = r"""
<style>
.st-key-dg_topbar{
  margin:.15rem 0 1rem!important;
  position:sticky!important;
  top:.2rem!important;
  z-index:999!important;
}
.st-key-dg_topbar > div{
  background:color-mix(in srgb,var(--dg-card) 94%,transparent)!important;
  border:1px solid var(--dg-border)!important;
  border-radius:18px!important;
  padding:.52rem .72rem!important;
  box-shadow:0 10px 30px var(--dg-shadow)!important;
  backdrop-filter:blur(16px)!important;
  -webkit-backdrop-filter:blur(16px)!important;
}
.st-key-dg_topbar [data-testid="stHorizontalBlock"]{
  align-items:center!important;
  gap:.45rem!important;
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
.st-key-dg_nav_control{
  display:flex!important;justify-content:center!important;align-items:center!important;
  min-height:40px!important;
}
.st-key-dg_nav_control [data-testid="stSegmentedControl"]{
  width:auto!important;justify-content:center!important;margin:0 auto!important;
}
.st-key-dg_nav_control [data-testid="stSegmentedControl"] > div{
  width:auto!important;justify-content:center!important;gap:.16rem!important;
  background:transparent!important;border:0!important;padding:0!important;
}
.st-key-dg_nav_control button{
  min-width:105px!important;min-height:38px!important;padding:.42rem .72rem!important;
  border-radius:10px!important;font-family:"Plus Jakarta Sans",sans-serif!important;
  font-size:.83rem!important;font-weight:720!important;
}
.st-key-dg_theme_col{
  display:flex!important;justify-content:flex-end!important;align-items:center!important;
  min-height:40px!important;
}
.st-key-dg_theme_col > div{width:auto!important;margin-left:auto!important}
.dg-top-brand{color:#137F85!important;font-size:1.25rem!important}
.st-key-dg_topbar > div{background:rgba(255,255,255,.97)!important;border-radius:16px!important;box-shadow:0 8px 24px rgba(18,49,60,.08)!important}
.st-key-dg_nav_control button[aria-pressed="true"]{background:#DFF3EF!important;color:#137F85!important}
.dg-hero-copy-note{margin-top:.75rem;font-size:.78rem;opacity:.78}

@media(max-width:980px){
  .st-key-dg_nav_control button{min-width:96px!important}
}
@media(max-width:760px){
  .st-key-dg_topbar{top:.25rem!important}
  .st-key-dg_topbar > div{padding:.46rem .5rem!important;border-radius:16px!important}
  .dg-top-brand span:last-child{display:none}
  .dg-top-brand-badge{width:34px;height:34px;flex-basis:34px}
  .st-key-dg_nav_control button{min-width:auto!important;font-size:.79rem!important;padding:.36rem .42rem!important}
}

/* DIENGIN Web 2.0: Figma/Vercel-inspired layout, scoped to existing live Streamlit data */
.stApp{background:#F5FAF9!important}
.block-container{max-width:1480px!important;padding-top:1.2rem!important}
.st-key-dg_topbar{top:0!important;z-index:1001!important;margin:0 0 1.7rem!important}
.st-key-dg_topbar > div{background:rgba(255,255,255,.96)!important;border:1px solid #E3EFEC!important;border-radius:0 0 19px 19px!important;box-shadow:0 9px 26px rgba(18,49,60,.07)!important}
.dg-top-brand-badge{background:transparent!important;box-shadow:none!important;color:#137F85!important;font-size:27px!important}
.dg-top-brand{font-size:1.45rem!important;letter-spacing:.035em!important}
.st-key-dg_nav_control button{border-radius:14px!important}
.dg-hero.figma-web2{display:grid!important;grid-template-columns:minmax(0,1.45fr) minmax(310px,1fr)!important;gap:0!important;border-radius:30px!important;overflow:hidden!important;background:#12313C!important;color:#F4FFFF!important;box-shadow:0 16px 35px rgba(18,49,60,.12)!important}
.dg-hero.figma-web2 .dg-web2-left{min-width:0;padding:clamp(1.5rem,3.2vw,3.2rem)!important}
.dg-hero.figma-web2 .dg-hero-kicker{color:#9BDEDC!important;font-weight:750!important;letter-spacing:.1em}
.dg-hero.figma-web2 h1{color:#FFFFFF!important;font-size:clamp(1.6rem,2.55vw,2.8rem)!important;line-height:1.19!important;margin:.75rem 0!important}
.dg-hero.figma-web2 p{color:#C9DFE1!important;font-size:1rem!important;max-width:700px}
.dg-web2-prob-row{display:flex;align-items:baseline;gap:1rem;margin:1.2rem 0 .3rem}
.dg-web2-prob{color:#fff;font:800 clamp(4.5rem,8vw,7.8rem)/1 'Plus Jakarta Sans',sans-serif;letter-spacing:-.075em}
.dg-web2-model-status{font-size:.95rem;color:#9EDFD8}
.dg-web2-track{height:11px;background:#3B6570;border-radius:20px;overflow:hidden;margin:.95rem 0 .5rem}
.dg-web2-fill{height:100%;background:#74D5CD;border-radius:20px}
.dg-web2-meta{display:flex;gap:1rem;flex-wrap:wrap;font-size:.84rem;color:#B5D4D6}
.dg-web2-right{background:linear-gradient(180deg,#E8F7F4,#D7EBE9);padding:1.5rem;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#12313C;min-width:0}
.dg-web2-right .dg-scene{transform:scale(1.45);transform-origin:center center;margin:28px auto 37px}
.dg-web2-right .dg-web2-scene-label{text-align:center;color:#56747A;font-size:.94rem;font-weight:650}
.dg-web2-right .dg-web2-observation{text-align:center;border-top:1px solid #BEDBD9;padding-top:1rem;margin-top:1rem;width:100%;font-size:.87rem;color:#43676E}
.dg-web2-right .dg-web2-observation strong{display:block;font-size:1.45rem;color:#12313C;margin:.2rem}
.dg-heading{display:none!important}
.dg-current-head{text-align:left!important;margin-bottom:1rem!important}
.dg-current-head h2{font-size:1.8rem!important;letter-spacing:-.03em!important}
.dg-current-head p{font-size:.88rem!important}
.dg-weather-card.instrument{box-shadow:0 4px 20px rgba(18,49,60,.035)}
.dg-weather-card.instrument .dg-weather-value{font-size:clamp(2.7rem,3.3vw,4rem)!important}
.dg-prediction-instruments .dg-weather-card.instrument{min-height:190px!important}
@media(max-width:860px){.dg-hero.figma-web2{grid-template-columns:1fr!important}.dg-web2-right .dg-scene{transform:scale(1.1);margin:12px auto 16px}.dg-web2-right{padding:1rem!important}.dg-heading{display:none!important}}
@media(max-width:620px){.dg-web2-prob{font-size:4.75rem}.dg-hero.figma-web2 .dg-web2-left{padding:1.3rem!important}.dg-web2-right .dg-scene{transform:scale(.95);margin:0 auto 6px}.dg-weather-card.instrument .dg-weather-value{font-size:clamp(1.85rem,6.8vw,2.6rem)!important}}
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
    # Migrate old navigation state after changing the labels in production.
    options = ["Prediksi Frost", "Monitoring AWS", "Tren & Historis", "Tentang"]
    previous = st.session_state.get("dg_primary_nav")
    legacy = {"Prediksi": "Prediksi Frost", "Monitoring": "Monitoring AWS",
              "Prospek BMKG": "Tentang"}
    if previous is not None and previous not in options:
        st.session_state["dg_primary_nav"] = legacy.get(previous, "Prediksi Frost")
    # Equal side columns keep the center navigation genuinely centered.
    with st.container(key="dg_topbar"):
        brand_col, nav_col, theme_col = st.columns([1.0, 1.75, 1.0], vertical_alignment="center")
        with brand_col:
            st.markdown(
                '<div class="dg-top-brand">'
                '<span class="dg-top-brand-badge">❄</span>'
                '<span>DIENGIN</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with nav_col:
            with st.container(key="dg_nav_control"):
                page = st.segmented_control(
                    "Navigasi utama",
                    options,
                    default="Prediksi Frost",
                    key="dg_primary_nav",
                    label_visibility="collapsed",
                )
        with theme_col:
            with st.container(key="dg_theme_col"):
                theme.render_toggle()
    return page or "Prediksi Frost"


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

    phase, sky, orb = design.phase_at(now.hour + now.minute / 60)
    progress = ((now.hour + now.minute / 60 - (18 if phase == "malam" else 6)) % 24) / 12
    progress = min(1.0, max(0.0, progress))
    orb_x = 12 + progress * 110
    orb_y = 42 - math.sin(progress * math.pi) * 31
    scene_class = "night" if phase == "malam" else ""
    params = latest_obs.get("parameters") or {}
    temp = _num(params.get("tt_air_avg"))
    temp_text = "—" if temp is None else f"{temp:.1f} °C"
    threshold = _num(pred.get("threshold_stacked"))
    target = pred.get("target_night_date") or "—"
    p_model = _num(latest_release.get("stacked_probability"))
    model_text = "—" if p_model is None else f"{p_model*100:.2f}%"
    threshold_text = "—" if threshold is None else f"{threshold*100:.2f}%"
    progress_width = min(100, max(0, p_model*100)) if p_model is not None else 0
    flag = "Di atas ambang model" if p_model is not None and threshold is not None and p_model >= threshold else "Di bawah ambang model" if p_model is not None and threshold is not None else "Status belum tersedia"
    st.markdown(
        '<section class="dg-hero figma-web2"><div class="dg-web2-left">'
        f'<div class="dg-hero-kicker">DIENGIN / PREDIKSI FROST · {base.esc(update_text)}</div>'
        '<h1>Potensi frost di Dataran Tinggi Dieng</h1>'
        f'<div class="dg-web2-prob-row"><span class="dg-web2-prob">{base.esc(model_text)}</span></div>'
        f'<div class="dg-web2-model-status">{base.esc(flag)} · Ambang model {base.esc(threshold_text)}</div>'
        f'<div class="dg-web2-track"><div class="dg-web2-fill" style="width:{progress_width:.2f}%"></div></div>'
        f'<div class="dg-web2-meta"><span>Target {base.esc(str(target))}</span><span>{base.esc(freshness_text)}</span><span>{base.esc(delta_text)}</span></div>'
        f'<p>{base.esc(hero_text)}</p>'
        '<div class="dg-hero-copy-note">Probabilitas model bukan konfirmasi frost dan bukan peringatan resmi BMKG.</div>'
        '</div><div class="dg-web2-right">'
        f'<div class="dg-scene {scene_class}" role="img" aria-label="Ilustrasi suasana {base.esc(phase)}" style="--sky:{sky};--orb:{orb};--orb-x:{orb_x:.0f}px;--orb-y:{orb_y:.0f}px">'
        '<div class="sky"><div class="orb"></div></div><div class="mountain"></div><div class="mountain front"></div><div class="ground"></div><div class="cloud"></div></div>'
        f'<div class="dg-web2-scene-label">Suasana {base.esc(phase)} · ilustrasi WIB</div>'
        '<div class="dg-web2-observation">Suhu AWS Batur terbaru'
        f'<strong>{base.esc(temp_text)}</strong>Observasi {base.esc(str(latest_obs.get("time_wib") or "—"))}</div>'
        '</div></section>',
        unsafe_allow_html=True,
    )
    return fresh, result


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
    # Render on every run; module-import side effects alone are lost after
    # Streamlit reloads modules or starts a fresh browser session.
    st.markdown(ui.FRAMER_CSS + TOPNAV_CSS, unsafe_allow_html=True)
    theme.apply_theme()
    st.markdown(design.CSS, unsafe_allow_html=True)
    now = pd.Timestamp.now(tz=base.WIB)
    monitor, pred, pipeline, mh, rh, nights, statuses = _load_data()
    page = _top_nav()
    # Weather is forecast context; the illustration never asserts observed frost.
    try:
        payload, _ = app.get_bmkg_forecast()
        points = _future_bmkg_points(payload, now)
        weather = str(points[0][1].get("weather_desc") or "") if points else ""
    except Exception:
        weather = ""
    release = pred.get("latest_release") or {}
    current_probability = _num(release.get("stacked_probability"))
    threshold = _num(pred.get("threshold_stacked"))
    # Illustration is now integrated in the prediction hero; avoid a duplicate header.

    if page == "Prediksi Frost":
        fresh, result = _render_hero(monitor, pred, rh, now)
        features.render_prediction_weather(monitor, mh, now)
        _render_notices(monitor, pipeline, statuses["monitoring"], fresh)

        with st.container(key="dg_lower"):
            chart_col, analysis_col = st.columns([1.6, 1], gap="large")
            with chart_col:
                design.render_journey(mh, rh, pred)
            with analysis_col:
                design.render_insights(monitor, pred, result)

        ui._section(
            "EKSPLORASI DATA",
            "Bandingkan parameter dan probabilitas model",
            "Pilih kombinasi variabel apa pun pada setiap grafik. Setiap seri memakai skala otomatis sendiri agar arah tren tetap terlihat.",
        )
        with st.expander("Eksplorasi lanjutan & perbandingan variabel"):
            features.render_custom_explorer(
                mh, rh, key_prefix="prediction_explore", include_models=True,
                default_labels=["Suhu udara", "Probabilitas Stacked / Final"],
                allow_download=False,
            )

        with st.expander("Lihat juga prospek cuaca BMKG"):
            app.render_bmkg_forecast(now)

    elif page == "Monitoring AWS":
        features.render_monitoring_cards(monitor)
        design.render_journey(mh, pd.DataFrame(), {}, include_models=False)
        latest_obs = monitor.get("latest_observation") or {}
        fresh, _, _ = base.freshness(latest_obs.get("time_wib"), now)
        _render_notices(monitor, pipeline, statuses["monitoring"], fresh)
        ui._section(
            "HISTORI AWS",
            "Grafik dan data pengamatan",
            "Grafik historis menggunakan observasi AWS. Data tambahan diminta saat tombol Muat Data ditekan.",
        )
        features.render_on_demand_monitoring_explorer()

    elif page == "Tren & Historis":
        ui._section(
            "TREN & HISTORIS",
            "Perjalanan prediksi dan pengamatan Dieng",
            "Lihat riwayat rilis probabilitas model serta perubahan meteorologi dari data yang tersedia.",
        )
        design.render_journey(mh, rh, pred)
        features.render_custom_explorer(
            mh, rh, key_prefix="history_explore", include_models=True,
            default_labels=["Suhu udara", "Probabilitas Stacked / Final"],
            allow_download=False,
        )
        features.render_on_demand_monitoring_explorer()

    else:
        ui._section(
            "TENTANG DIENGIN",
            "Sistem pendukung kewaspadaan frost",
            "DIENGIN adalah prototipe penelitian. Probabilitas model bukan konfirmasi terjadinya frost ataupun peringatan resmi BMKG.",
        )
        st.info("Data pengamatan berasal dari AWS Batur Dieng. Prakiraan BMKG digunakan sebagai konteks, tidak mengubah hasil model.")
        with st.expander("Prospek cuaca BMKG"):
            app.render_bmkg_forecast(now)
        base.render_info(monitor, pred, pipeline, statuses, now)

    st.markdown(
        '<div class="dg-footer">DIENGIN · Prototipe penelitian, bukan peringatan resmi BMKG. '
        'Prakiraan eksternal hanya menjadi konteks. Seluruh waktu dalam WIB.</div>',
        unsafe_allow_html=True,
    )
