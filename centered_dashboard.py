#!/usr/bin/env python3
"""Framer-inspired centered dashboard composition for DIENGIN.

Presentation only. Model inference, QC, history storage, live runtime data,
and BMKG retrieval stay in the existing DIENGIN modules.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

import app

base = app.base

FRAMER_CSS = r"""
<style>
:root{
  --dg-blue:#2878f0;
  --dg-cyan:#35afe8;
  --dg-ink:#1e2b3f;
  --dg-muted:#6f7d91;
  --dg-surface:#f4f7fb;
  --dg-card:#ffffff;
  --dg-border:rgba(32,54,82,.12);
  --dg-orange:#ff9d1a;
  --dg-purple:#8b5cf6;
  --dg-green:#19a974;
}
.block-container{
  max-width:1280px!important;
  padding:1.35rem 1.55rem 3rem!important;
  margin:0 auto!important;
}
[data-testid="stAppViewContainer"]{background:var(--dg-surface);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stHorizontalBlock"]{align-items:stretch;}
[data-testid="stTabs"] [role="tablist"]{
  justify-content:center;
  gap:1.15rem;
  border-bottom:0;
  margin:.25rem 0 .75rem;
}
[data-testid="stTabs"] [role="tab"]{
  font-size:1rem!important;
  font-weight:700!important;
  min-height:46px;
  padding:.7rem 1rem!important;
}
[data-testid="stCaptionContainer"] p{
  font-size:.95rem!important;
  line-height:1.55!important;
}
.dg-framer-nav{
  display:grid;
  grid-template-columns:1fr auto 1fr;
  align-items:center;
  gap:1rem;
  background:#fff;
  border:1px solid var(--dg-border);
  border-radius:20px;
  padding:.78rem 1rem;
  box-shadow:0 8px 26px rgba(25,47,78,.045);
  margin:.15rem 0 1rem;
}
.dg-brand-mini{
  display:flex;align-items:center;gap:.65rem;
  font-size:1rem;font-weight:800;letter-spacing:.025em;color:var(--dg-ink);
}
.dg-brand-badge{
  width:34px;height:34px;border-radius:11px;display:grid;place-items:center;
  background:var(--dg-blue);color:#fff;font-size:18px;
}
.dg-nav-center{
  display:flex;gap:.55rem;justify-content:center;align-items:center;
  font-size:.95rem;font-weight:700;color:var(--dg-muted);
}
.dg-nav-active{color:var(--dg-blue);}
.dg-place{
  justify-self:end;
  display:inline-flex;align-items:center;gap:.38rem;
  padding:.5rem .78rem;border-radius:999px;
  background:#edf5ff;color:var(--dg-blue);
  font-size:.92rem;font-weight:700;
}
.dg-hero{
  position:relative;overflow:hidden;
  display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;
  gap:1.5rem;
  min-height:190px;
  padding:1.45rem 1.65rem;
  border-radius:24px;
  color:white;
  background:linear-gradient(115deg,var(--dg-blue),var(--dg-cyan));
  box-shadow:0 14px 36px rgba(40,120,240,.12);
}
.dg-hero-kicker{
  font-size:.95rem;font-weight:800;letter-spacing:.065em;text-transform:uppercase;
  opacity:.92;margin-bottom:.4rem;
}
.dg-hero h1{
  margin:0;padding:0;color:#fff;
  font-size:clamp(1.75rem,3vw,2.55rem);line-height:1.14;font-weight:800;
  letter-spacing:-.025em;
}
.dg-hero p{
  margin:.62rem 0 0;max-width:720px;
  font-size:1.03rem;line-height:1.58;color:rgba(255,255,255,.92);
}
.dg-hero-score{
  min-width:170px;text-align:center;font-variant-numeric:tabular-nums;
}
.dg-hero-score .label{font-size:.93rem;font-weight:700;opacity:.9;margin-bottom:.2rem;}
.dg-hero-score .value{
  font-size:clamp(3.8rem,7vw,5.6rem);line-height:.95;font-weight:800;letter-spacing:-.06em;
}
.dg-hero-score .sub{font-size:.95rem;font-weight:700;opacity:.88;margin-top:.5rem;}
.dg-section{
  margin:1.55rem 0 .7rem;
}
.dg-section-kicker{
  color:var(--dg-blue);
  font-size:.92rem;font-weight:800;letter-spacing:.065em;text-transform:uppercase;
  text-align:left;margin-bottom:.18rem;
}
.dg-section-title{
  color:var(--dg-ink);
  font-size:1.65rem;line-height:1.25;font-weight:800;letter-spacing:-.025em;
  margin:0;
}
.dg-section-note{
  margin:.32rem 0 0;
  color:var(--dg-muted);font-size:1rem;line-height:1.55;
}
.dg-hourly-scroll{
  display:flex;gap:.85rem;overflow-x:auto;padding:.18rem .1rem .8rem;
  scrollbar-width:thin;
  scroll-snap-type:x proximity;
}
.dg-hour-card{
  flex:0 0 155px;min-height:155px;
  scroll-snap-align:start;
  background:#fff;border:1px solid var(--dg-border);border-radius:18px;
  padding:1rem 1rem .9rem;
  box-sizing:border-box;
  box-shadow:0 7px 20px rgba(25,47,78,.035);
}
.dg-hour-card.current{border-color:rgba(40,120,240,.42);box-shadow:0 8px 24px rgba(40,120,240,.09);}
.dg-hour-time{font-size:.95rem;font-weight:800;color:var(--dg-ink);}
.dg-hour-prob{
  margin:.55rem 0 .34rem;
  font-size:2.05rem;line-height:1;font-weight:800;color:var(--dg-blue);
}
.dg-hour-status{font-size:.95rem;line-height:1.38;font-weight:700;color:var(--dg-ink);}
.dg-hour-meta{margin-top:.46rem;font-size:.9rem;line-height:1.35;color:var(--dg-muted);}
.dg-prospect-grid{
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;
}
.dg-prospect{
  border-radius:18px;padding:1.15rem 1.2rem;min-height:126px;border:1px solid transparent;
}
.dg-prospect.orange{background:#fff7e8;border-color:#f5dba6;}
.dg-prospect.purple{background:#f5efff;border-color:#ddcff9;}
.dg-prospect.green{background:#eaf9f3;border-color:#c8eadc;}
.dg-prospect-icon{font-size:1.4rem;margin-bottom:.45rem;}
.dg-prospect-title{font-size:1.08rem;font-weight:800;color:var(--dg-ink);margin-bottom:.35rem;}
.dg-prospect-text{font-size:.96rem;line-height:1.5;color:#526174;}
.dg-weather{
  max-width:none!important;margin:.1rem 0 0!important;
  grid-template-columns:repeat(3,minmax(0,1fr))!important;
  gap:1rem!important;
}
.dg-weather .dg-card{
  min-height:150px!important;
  background:#fff!important;
  border:1px solid var(--dg-border)!important;
  border-radius:18px!important;
  padding:1rem!important;
  text-align:center!important;
  display:flex!important;
  flex-direction:column!important;
  justify-content:center!important;
  align-items:center!important;
}
.dg-weather .dg-label-row{justify-content:center!important;}
.dg-weather .dg-label{font-size:.98rem!important;font-weight:700!important;}
.dg-weather .dg-value{font-size:2.35rem!important;}
.dg-weather .dg-delta{font-size:.92rem!important;line-height:1.45!important;}
.dg-panel-title{
  justify-content:center!important;text-align:center!important;
  font-size:1.22rem!important;font-weight:800!important;
}
.dg-field-note,.dg-secondary-note{
  justify-content:center!important;text-align:center!important;
  font-size:.92rem!important;
}
.st-key-weather_panel,.st-key-prediction_panel{min-height:0!important;}
.st-key-weather_panel>div,.st-key-prediction_panel>div{
  height:auto!important;background:#fff;border-radius:20px!important;border-color:var(--dg-border)!important;
}
.st-key-weather_secondary,.st-key-prediction_secondary{
  min-height:0!important;max-height:none!important;overflow:visible!important;
}
.st-key-prediction_secondary .dg-release-row{
  grid-template-columns:repeat(11,minmax(64px,1fr))!important;
  overflow-x:auto;gap:6px;
}
.st-key-prediction_secondary .dg-release{
  min-height:56px!important;height:auto!important;font-size:.82rem!important;
}
.st-key-prediction_secondary .dg-release b{font-size:.9rem!important;}
.st-key-weather_secondary [data-testid="stRadio"] label p{
  font-size:.92rem!important;
}
.dg-bmkg-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:1rem!important;}
.dg-bmkg-card{border-radius:18px!important;min-height:180px!important;text-align:center;}
.dg-bmkg-time{font-size:.95rem!important;}
.dg-bmkg-weather{font-size:1.12rem!important;justify-content:center;text-align:center;}
.dg-bmkg-meta{font-size:.95rem!important;}
.dg-bmkg-source{font-size:.9rem!important;text-align:center;}
.dg-info{
  max-width:none!important;
  margin:.8rem 0!important;
  border-left:0!important;border-top:3px solid rgba(34,184,167,.65)!important;
  border-radius:16px!important;
  padding:1rem 1.15rem!important;
  text-align:center;
  font-size:.98rem!important;line-height:1.55!important;
}
.dg-footer{font-size:.9rem!important;line-height:1.5!important;text-align:center!important;}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button{
  min-height:44px!important;font-size:.95rem!important;font-weight:700!important;border-radius:12px!important;
}
[data-baseweb="select"] span{font-size:.95rem!important;}
[data-testid="stDataFrame"] *,[data-testid="stTable"] *{text-align:initial;}

@media(max-width:900px){
  .block-container{padding:1rem .9rem 2.2rem!important;}
  .dg-framer-nav{grid-template-columns:1fr auto;}
  .dg-nav-center{display:none;}
  .dg-hero{grid-template-columns:1fr;min-height:0;}
  .dg-hero-score{text-align:left;min-width:0;}
  .dg-hero-score .value{font-size:4rem;}
  .dg-prospect-grid{grid-template-columns:1fr;}
  .dg-weather{grid-template-columns:repeat(2,minmax(0,1fr))!important;}
  .dg-bmkg-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;}
}
@media(max-width:620px){
  .dg-place{display:none;}
  .dg-framer-nav{grid-template-columns:1fr;}
  .dg-brand-mini{justify-content:center;}
  .dg-hero{padding:1.2rem 1.15rem;border-radius:20px;}
  .dg-hero h1{font-size:1.7rem;}
  .dg-hero p{font-size:1rem;}
  .dg-section-title{font-size:1.42rem;}
  .dg-section-note{font-size:.96rem;}
  .dg-weather{grid-template-columns:1fr!important;}
  .dg-bmkg-grid{grid-template-columns:1fr!important;}
  .dg-hour-card{flex-basis:145px;}
}
</style>
"""
base.CSS += FRAMER_CSS


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _prob(value):
    out = _num(value)
    return out if out is not None and 0 <= out <= 1 else None


def _target_text(value):
    try:
        return pd.Timestamp(value).date().isoformat()
    except Exception:
        text = str(value or "")
        return text[:10] if len(text) >= 10 else None


def _selected_releases(rh: pd.DataFrame, target) -> pd.DataFrame:
    if rh.empty or "tanggal_target" not in rh:
        return pd.DataFrame()
    target_text = _target_text(target)
    if not target_text:
        return pd.DataFrame()
    selected = rh.loc[rh["tanggal_target"].astype(str).str[:10].eq(target_text)].copy()
    if selected.empty:
        return selected
    order = {21: 0, 22: 1, 23: 2, 0: 3, 1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10}
    selected["_hour"] = pd.to_numeric(selected.get("jam_rilis_wib"), errors="coerce")
    selected["_order"] = selected["_hour"].map(order)
    return selected.sort_values("_order")


def _prob_status(p: float | None, threshold: float | None) -> str:
    if p is None:
        return "Belum tersedia"
    if threshold is not None and p >= threshold:
        return "Potensi terpantau"
    if p >= 0.15:
        return "Mulai meningkat"
    if p >= 0.07:
        return "Perlu dipantau"
    return "Relatif rendah"


def _hero_copy(p_now, p_prev, threshold):
    if p_now is None:
        return "Menunggu rilis berikutnya.", "Probabilitas frost belum tersedia pada pembaruan ini."
    delta = p_now - p_prev if p_prev is not None else None
    if threshold is not None and p_now >= threshold:
        if delta is not None and delta >= 0.03:
            return "Potensi frost sedang menguat.", "Probabilitas terbaru melampaui ambang dan meningkat dibanding rilis sebelumnya."
        if delta is not None and delta <= -0.03:
            return "Potensi masih terpantau, namun mulai melemah.", "Probabilitas masih berada pada tingkat terpantau tetapi menurun pada rilis terbaru."
        return "Potensi frost masih terpantau.", "Probabilitas terbaru masih berada pada tingkat yang perlu diperhatikan."
    if delta is not None and delta >= 0.03:
        return "Potensi mulai meningkat.", "Probabilitas naik dibanding rilis sebelumnya, namun belum melampaui ambang model."
    if delta is not None and delta <= -0.03:
        return "Potensi sedang melemah.", "Probabilitas turun dibanding rilis sebelumnya."
    return "Potensi saat ini relatif rendah.", "Probabilitas terbaru masih rendah dan belum menunjukkan penguatan yang berarti."


def _section(kicker: str, title: str, note: str | None = None):
    html = (
        '<div class="dg-section">'
        f'<div class="dg-section-kicker">{base.esc(kicker)}</div>'
        f'<div class="dg-section-title">{base.esc(title)}</div>'
    )
    if note:
        html += f'<div class="dg-section-note">{base.esc(note)}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _render_hourly_cards(rh: pd.DataFrame, pred: dict):
    selected = _selected_releases(rh, pred.get("target_night_date"))
    threshold = _prob(pred.get("threshold_stacked"))
    latest = pred.get("latest_release") or {}
    latest_hour = _num(latest.get("hour_wib"))
    by_hour = {}
    if not selected.empty:
        for _, row in selected.iterrows():
            hour = _num(row.get("jam_rilis_wib"))
            if hour is not None:
                by_hour[int(hour)] = row

    cards = []
    for hour in [21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]:
        row = by_hour.get(hour)
        p = _prob(row.get("stack_prob")) if row is not None else None
        status = _prob_status(p, threshold)
        current = " current" if latest_hour is not None and int(latest_hour) == hour else ""
        if p is None:
            prob_text = "—"
            meta = "Menunggu rilis"
        else:
            prob_text = f"{p * 100:.0f}%"
            meta = "Di atas ambang" if threshold is not None and p >= threshold else "Belum melampaui ambang"
        cards.append(
            f'<div class="dg-hour-card{current}">'
            f'<div class="dg-hour-time">{hour:02d}.00 WIB</div>'
            f'<div class="dg-hour-prob">{base.esc(prob_text)}</div>'
            f'<div class="dg-hour-status">{base.esc(status)}</div>'
            f'<div class="dg-hour-meta">{base.esc(meta)}</div>'
            "</div>"
        )
    st.markdown('<div class="dg-hourly-scroll">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def _next_bmkg(now):
    try:
        payload, status = app.get_bmkg_forecast()
    except Exception:
        return None
    if status != "ok":
        return None
    rows = app.flatten_bmkg_rows(payload)
    parsed = []
    for row in rows:
        dt = base.stamp(row.get("local_datetime"))
        if not pd.isna(dt):
            parsed.append((dt, row))
    if not parsed:
        return None
    return next((pair for pair in parsed if pair[0] >= now), parsed[-1])


def _render_prospect_cards(monitor, pred, rh, now):
    latest = monitor.get("latest_observation") or {}
    params = latest.get("parameters") or {}
    trend = monitor.get("trend_1h") or {}
    temp = _num(params.get("tt_air_avg"))
    dtemp = _num(trend.get("tt_air_avg_change"))

    selected = _selected_releases(rh, pred.get("target_night_date"))
    probs = []
    if not selected.empty and "stack_prob" in selected:
        probs = [p for p in pd.to_numeric(selected["stack_prob"], errors="coerce").tolist() if _prob(p) is not None]
    delta = probs[-1] - probs[-2] if len(probs) >= 2 else None

    if delta is None:
        prob_title, prob_text = "Perkembangan potensi", "Arah perubahan probabilitas akan terlihat setelah sedikitnya dua rilis tersedia."
    elif delta >= 0.03:
        prob_title, prob_text = "Potensi menguat", f"Probabilitas naik sekitar {delta * 100:.0f} poin dari rilis sebelumnya."
    elif delta <= -0.03:
        prob_title, prob_text = "Potensi melemah", f"Probabilitas turun sekitar {abs(delta) * 100:.0f} poin dari rilis sebelumnya."
    else:
        prob_title, prob_text = "Potensi relatif stabil", "Perubahan probabilitas antar rilis masih kecil."

    if temp is None:
        temp_title, temp_text = "Kondisi suhu", "Suhu aktual belum tersedia."
    elif dtemp is None:
        temp_title, temp_text = f"Suhu {temp:.1f} °C", "Perubahan sekitar satu jam belum dapat dihitung."
    elif dtemp <= -0.3:
        temp_title, temp_text = "Pendinginan berlanjut", f"Suhu {temp:.1f} °C, turun sekitar {abs(dtemp):.1f} °C dalam ±1 jam."
    elif dtemp >= 0.3:
        temp_title, temp_text = "Suhu menghangat", f"Suhu {temp:.1f} °C, naik sekitar {abs(dtemp):.1f} °C dalam ±1 jam."
    else:
        temp_title, temp_text = "Suhu relatif stabil", f"Suhu aktual sekitar {temp:.1f} °C."

    bmkg = _next_bmkg(now)
    if bmkg:
        dt, row = bmkg
        weather = row.get("weather_desc") or "Cuaca"
        bt = _num(row.get("t"))
        wind = _num(row.get("ws"))
        parts = [f"{weather} sekitar {dt.strftime('%H:%M')} WIB"]
        if bt is not None:
            parts.append(f"suhu {bt:.0f} °C")
        if wind is not None:
            parts.append(f"angin {wind:.1f} km/jam")
        bmkg_title, bmkg_text = "Prospek BMKG", " · ".join(parts) + "."
    else:
        bmkg_title, bmkg_text = "Prospek BMKG", "Prakiraan BMKG belum tersedia pada pembaruan ini."

    cards = [
        ("orange", "↗", prob_title, prob_text),
        ("purple", "🌡", temp_title, temp_text),
        ("green", "☁", bmkg_title, bmkg_text),
    ]
    html = '<div class="dg-prospect-grid">'
    for css, icon, title, text in cards:
        html += (
            f'<div class="dg-prospect {css}">'
            f'<div class="dg-prospect-icon">{icon}</div>'
            f'<div class="dg-prospect-title">{base.esc(title)}</div>'
            f'<div class="dg-prospect-text">{base.esc(text)}</div>'
            "</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


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
    latest_obs = monitor.get("latest_observation") or {}
    latest_release = pred.get("latest_release") or {}
    fresh, fresh_text, age = base.freshness(latest_obs.get("time_wib"), now)

    st.markdown(
        '<div class="dg-framer-nav">'
        '<div class="dg-brand-mini"><span class="dg-brand-badge">❄</span><span>DIENGIN</span></div>'
        '<div class="dg-nav-center"><span class="dg-nav-active">Prediksi</span><span>Prospek</span><span>Data</span></div>'
        '<div class="dg-place">⌖ Dieng Plateau</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    p_now = _prob(latest_release.get("stacked_probability"))
    selected = _selected_releases(rh, pred.get("target_night_date"))
    p_prev = None
    if not selected.empty and "stack_prob" in selected:
        probs = [p for p in pd.to_numeric(selected["stack_prob"], errors="coerce").tolist() if _prob(p) is not None]
        if p_now is not None and probs and abs(probs[-1] - p_now) < 1e-9 and len(probs) >= 2:
            p_prev = probs[-2]
        elif len(probs) >= 1:
            p_prev = probs[-1]

    threshold = _prob(pred.get("threshold_stacked"))
    hero_title, hero_text = _hero_copy(p_now, p_prev, threshold)
    hour = _num(latest_release.get("hour_wib"))
    update_text = f"RILIS {int(hour):02d}.00 WIB" if hour is not None else "PEMBARUAN TERBARU"
    freshness_text = fresh_text.upper() if fresh_text else "STATUS DATA"

    temp = _num(((latest_obs.get("parameters") or {}).get("tt_air_avg")))
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
        st.markdown('<div class="dg-info warn">' + base.esc(" ".join(notices)) + "</div>", unsafe_allow_html=True)

    overview, bmkg_tab, explore, info = st.tabs(
        ["Prediksi", "Prospek BMKG", "Eksplorasi data", "Panduan & status"]
    )

    with overview:
        _section("PREDIKSI PER JAM", "Bagaimana potensi frost berkembang malam ini?",
                 "Setiap kartu menunjukkan probabilitas pada satu rilis DIENGIN. Geser horizontal untuk melihat seluruh jam.")
        _render_hourly_cards(rh, pred)

        _section("PROSPEK KONDISI", "Apa yang mendukung atau melemahkan perkembangan potensi?",
                 "Ringkasan ini menggabungkan trajectory probabilitas, AWS aktual, dan konteks prakiraan BMKG tanpa mengubah output model.")
        _render_prospect_cards(monitor, pred, rh, now)

        _section("KONDISI AKTUAL", "Cuaca AWS terkini",
                 "Nilai observasi digunakan sebagai konteks perkembangan, bukan untuk mengubah probabilitas yang sudah dihitung model.")
        base.render_weather(monitor)

        _section("GRAFIK", "Perjalanan probabilitas",
                 "Grafik rilis per jam tetap tersedia untuk melihat pola perkembangan secara lebih rinci.")
        base.render_prediction_history(rh, nights, pred, now)

        _section("OBSERVASI", "Jejak cuaca",
                 "Bandingkan perubahan suhu, kelembapan, angin, dan hujan dengan perkembangan probabilitas.")
        base.render_trend(mh)

    with bmkg_tab:
        _section("PROSPEK BMKG", "Prakiraan cuaca Dieng",
                 "Prakiraan BMKG menjadi konteks prospek dan tidak mengubah probabilitas frost DIENGIN.")
        app.render_bmkg_forecast(now)

    with explore:
        _section("DATA", "Eksplorasi data")
        base.render_explore(mh, nights)

    with info:
        _section("SISTEM", "Panduan & status")
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
        'Prakiraan cuaca pada tab Prospek BMKG bersumber dari BMKG. Seluruh waktu dalam WIB.</div>',
        unsafe_allow_html=True,
    )
