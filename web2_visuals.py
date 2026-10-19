"""DIENGIN Web 2.0 presentation layer for the Streamlit operational dashboard.

No model, threshold, source data, or release scheduling changes are made here.
The mountain illustration reuses the CSS scene already shipped in expressive_dashboard.
"""
from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

from expressive_dashboard import phase_at


CSS = r"""
<style>
/* Web 2.0 design system. Loaded AFTER the older UI/theme styles. */
:root{
 --web2-navy:#12313c;--web2-teal:#137f85;--web2-muted:#68818b;
 --web2-paper:#f5faf9;--web2-mint:#dff3ef;--web2-border:#e3eeec;
}
[data-testid="stAppViewContainer"]{background:var(--web2-paper)!important}
.block-container{max-width:1550px!important;padding:1.25rem 2rem 4rem!important}
.st-key-dg_topbar{position:sticky!important;top:.25rem!important;z-index:1001!important;margin:.15rem 0 1.3rem!important}
.st-key-dg_topbar>div{background:rgba(255,255,255,.97)!important;border:1px solid var(--web2-border)!important;border-radius:18px!important;box-shadow:0 12px 34px rgba(18,49,60,.08)!important;padding:.8rem 1.1rem!important;backdrop-filter:blur(18px)}
.dg-top-brand{color:var(--web2-teal)!important;font-size:1.65rem!important;font-weight:900!important;letter-spacing:.02em!important}
.dg-top-brand-badge{background:transparent!important;color:var(--web2-teal)!important;box-shadow:none!important;font-size:30px!important}
.dg-web2-brandcopy{display:flex;flex-direction:column;line-height:1.05}
.dg-web2-brandcopy small{font-size:.61rem;letter-spacing:.13em;margin-top:5px;color:var(--web2-muted);font-weight:800}
.st-key-dg_nav_control button{min-width:0!important;white-space:nowrap;font-size:.93rem!important;min-height:44px!important;padding:.65rem .92rem!important}
.st-key-dg_nav_control button[aria-pressed="true"]{background:var(--web2-mint)!important;color:var(--web2-teal)!important}
.dg2-page-intro{margin:1.4rem 0 1.15rem}
.dg2-eyebrow{color:var(--web2-teal);font-weight:850;letter-spacing:.13em;font-size:.75rem;text-transform:uppercase}
.dg2-page-intro h1{color:var(--web2-navy);font-size:clamp(2rem,3.2vw,3rem);letter-spacing:-.047em;margin:.27rem 0!important;line-height:1.14}
.dg2-page-intro p{color:var(--web2-muted);font-size:1rem;margin:.3rem 0 0}
.dg2-hero{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,1fr);min-height:410px;border:1px solid #d6e9e7;border-radius:29px;overflow:hidden;box-shadow:0 16px 46px rgba(18,49,60,.08);background:#edf8f5;margin:.85rem 0 1.8rem}
.dg2-risk{padding:2.05rem 2.3rem;background:linear-gradient(135deg,#12313c 0%,#18454c 68%,#216167 100%);color:#fff!important;display:flex;flex-direction:column;align-items:flex-start}
.dg2-risk *{color:#fff!important}
.dg2-risk .dg2-risk-kicker{font-size:.74rem;letter-spacing:.115em;font-weight:800;color:#a9dfdb!important}
.dg2-risk h2{font-size:clamp(1.5rem,2.15vw,2.1rem);font-weight:800;letter-spacing:-.04em;line-height:1.2;margin:.6rem 0 .12rem!important}
.dg2-risk .dg2-date{font-size:.92rem;color:#bfd6d9!important}
.dg2-number{font-size:clamp(5rem,8.2vw,8.1rem);font-weight:850;letter-spacing:-.095em;line-height:1.05;font-variant-numeric:tabular-nums;margin:.65rem 0 .25rem}
.dg2-number span{font-size:.39em;letter-spacing:-.035em;vertical-align:baseline;margin-left:.14em}
.dg2-risk-status{display:inline-flex;align-items:center;gap:.45rem;padding:.42rem .7rem;border:1px solid rgba(201,239,227,.23);border-radius:999px;background:rgba(255,255,255,.095);font-size:.8rem;font-weight:750}
.dg2-meter{height:9px;width:100%;border-radius:20px;background:#45676c;margin:1.05rem 0 .5rem;overflow:hidden}
.dg2-meter>span{display:block;height:100%;background:linear-gradient(90deg,#58bdba,#a7ebe0);border-radius:20px;min-width:0}
.dg2-risk-meta{width:100%;display:flex;gap:.6rem;flex-wrap:wrap;justify-content:space-between;font-size:.76rem;color:#c0d9db!important}
.dg2-risk-meta span{color:#c0d9db!important}
.dg2-risk-explain{max-width:640px;line-height:1.55;color:#d4e5e4!important;font-size:.85rem;margin:1rem 0 0}
.dg2-scene-area{display:flex;flex-direction:column;justify-content:space-around;align-items:center;padding:1.6rem 1.4rem;text-align:center;background:radial-gradient(circle at 50% 28%,#f7fffd 0%,#e7f5f2 55%,#dff0ee 100%);color:var(--web2-navy)}
.dg2-scene-head{font-size:.8rem;font-weight:850;letter-spacing:.08em;color:var(--web2-teal)}
.dg2-scene-art{display:grid;place-items:center;min-height:192px;width:100%}
.dg2-scene-art .dg-scene{transform:scale(1.42);transform-origin:center center;margin:15px auto 20px}
.dg2-scene-caption{font-weight:800;font-size:1.05rem;color:var(--web2-navy)}
.dg2-scene-sub{font-size:.73rem;color:var(--web2-muted);margin-top:3px}
.dg2-scene-detail{display:flex;gap:1rem;align-items:center;justify-content:space-around;background:rgba(255,255,255,.84);border:1px solid #d6e8e5;border-radius:14px;padding:.75rem 1rem;width:100%;margin-top:1rem}
.dg2-scene-detail div{display:flex;flex-direction:column;gap:3px;min-width:0}
.dg2-scene-detail small{font-size:.69rem;color:var(--web2-muted)}
.dg2-scene-detail strong{font-size:1rem;color:var(--web2-navy);font-variant-numeric:tabular-nums}
.dg2-scene-detail .dg2-separator{width:1px;min-width:1px;align-self:stretch;background:#dceae6}
.dg-current-wrap{margin:1.8rem 0!important}
.dg-current-head{margin-bottom:1rem!important}
.dg-current-head h2{font-size:1.58rem!important;letter-spacing:-.035em!important;color:var(--web2-navy)!important}
.dg-current-head p{font-size:.85rem!important;color:var(--web2-muted)!important}
.dg-all-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:1.1rem!important}
.dg-prediction-instruments{grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:1rem!important}
.dg-weather-card.instrument{background:linear-gradient(135deg,var(--accent-bg),#fff 82%)!important;border:1px solid var(--web2-border)!important;box-shadow:0 5px 19px rgba(22,55,63,.045)!important;min-height:180px!important;text-align:left!important;border-radius:22px!important}
.dg-weather-card.instrument::before{content:none!important;display:none!important}
.dg-weather-card.instrument .dg-weather-value{font-size:clamp(2.9rem,4vw,4.65rem)!important;font-weight:850!important;letter-spacing:-.065em!important;line-height:1.04!important}
.dg-prediction-instruments .dg-weather-card.instrument .dg-weather-value{font-size:clamp(2.45rem,3.35vw,3.95rem)!important}
.dg-weather-card.instrument .dg-weather-label{font-size:1.03rem!important;font-weight:800!important;color:var(--web2-navy)!important}
.dg-weather-card.instrument .dg-instrument-unit{font-size:clamp(.79rem,1.2vw,1.25rem)!important;white-space:nowrap}
.dg-weather-card.instrument .dg-weather-note{font-size:.81rem!important}
.st-key-dg_journey,.dg-explorer-card{border-radius:22px!important;border:1px solid var(--web2-border)!important;box-shadow:0 6px 25px rgba(22,55,63,.04)!important}
.dg-section-title{font-size:1.75rem!important;color:var(--web2-navy)!important}
.dg-section-kicker{color:var(--web2-teal)!important}
.dg-footer{color:var(--web2-muted)!important}
@media(max-width:1150px){.dg2-hero{grid-template-columns:minmax(0,1.3fr) minmax(260px,1fr)}.dg-prediction-instruments{grid-template-columns:repeat(2,minmax(0,1fr))!important}.dg-all-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
@media(max-width:760px){
 .block-container{padding:1rem .8rem 2.5rem!important}
 .st-key-dg_topbar{top:.1rem!important}
 .st-key-dg_topbar [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important}
 .st-key-dg_topbar [data-testid="stColumn"]{flex:0 0 auto!important;width:auto!important;min-width:0!important}
 .st-key-dg_topbar [data-testid="stColumn"]:nth-child(2){order:3!important;flex:1 0 100%!important;width:100%!important}
 .st-key-dg_nav_control{overflow-x:auto!important;justify-content:flex-start!important}
 .st-key-dg_nav_control [data-testid="stSegmentedControl"]{justify-content:flex-start!important;margin:0!important;min-width:max-content!important}
 .st-key-dg_nav_control button{font-size:.75rem!important;padding:.42rem .5rem!important}
 .dg-top-brand{font-size:1.3rem!important}
 .dg2-page-intro{margin:.85rem 0!important}
 .dg2-page-intro h1{font-size:1.9rem!important}
 .dg2-hero{grid-template-columns:1fr;min-height:0;border-radius:22px}
 .dg2-risk{padding:1.35rem 1.3rem}
 .dg2-risk h2{font-size:1.47rem!important}
 .dg2-number{font-size:clamp(4.8rem,15vw,6.4rem)}
 .dg2-scene-area{padding:1.2rem;gap:.35rem}
 .dg2-scene-art{min-height:160px}
 .dg2-scene-art .dg-scene{transform:scale(1.18);margin:0}
 .dg-all-grid,.dg-prediction-instruments{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:.65rem!important}
 .dg-weather-card.instrument{min-height:165px!important;padding:.95rem!important}
 .dg-weather-card.instrument .dg-weather-value,.dg-prediction-instruments .dg-weather-card.instrument .dg-weather-value{font-size:clamp(1.95rem,7vw,3.2rem)!important}
 .dg-weather-card.instrument .dg-weather-label{font-size:.84rem!important}
 .dg-weather-card.instrument .dg-instrument-foot{display:block!important}
 .dg-weather-card.instrument .dg-instrument-source{display:none}
 .dg-weather-card.instrument .dg-instrument-unit{font-size:.72rem!important}
 .dg-current-head h2{font-size:1.4rem!important}
}
@media(max-width:390px){
 .dg-all-grid,.dg-prediction-instruments{grid-template-columns:1fr!important}
 .dg-weather-card.instrument .dg-weather-value{font-size:3.3rem!important}
}
/* Public website alignment. Keep this last to supersede legacy dashboard CSS. */
[data-testid="stHeader"]{background:transparent!important;pointer-events:none}
[data-testid="stHeader"] button{pointer-events:auto}
[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style){display:none!important}
.block-container{max-width:1440px!important;padding:0 4rem 4rem!important}
.st-key-dg_topbar{position:relative!important;top:auto!important;margin:0 0 2.5rem!important;padding:1.15rem 0!important;isolation:isolate}
.st-key-dg_topbar::before{content:"";position:absolute;inset:0 calc((100% - 100vw)/2);background:#fff;z-index:-1}
.st-key-dg_topbar>div{background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important;padding:0!important;backdrop-filter:none!important}
.st-key-dg_topbar [data-testid="stColumn"]{min-width:0!important}
.dg-top-brand{font-size:1.65rem!important;gap:.5rem!important;line-height:1.1!important}
.dg-top-brand-badge{width:26px!important;flex-basis:26px!important;font-size:27px!important}
.dg-web2-brandcopy small{font-size:.61rem!important;letter-spacing:.12em!important}
.st-key-dg_nav_control,.st-key-dg_nav_control [data-testid="stSegmentedControl"]{justify-content:flex-end!important;margin-left:auto!important;margin-right:0!important}
.st-key-dg_nav_control button{border:0!important;box-shadow:none!important;border-radius:12px!important;min-width:0!important;min-height:44px!important;font-size:.9rem!important;padding:.65rem .95rem!important}
.st-key-dg_nav_control button p{font-size:inherit!important}
.dg2-page-intro{margin:0 0 2rem!important}
.dg2-page-intro h1{font-size:clamp(1.9rem,3.2vw,3rem)!important;letter-spacing:-.035em!important;margin:.9rem 0 1rem!important}
.dg2-hero{display:block;max-width:960px;border:0;border-radius:28px;box-shadow:none;background:#12313c;margin:0 0 2rem}
.dg2-risk{padding:2.1rem;background:#12313c;min-height:380px}
.dg2-number{font-size:clamp(5rem,9vw,8.1rem);letter-spacing:-.055em;margin:1.8rem 0}
.dg2-number span{font-size:1em;letter-spacing:inherit;margin-left:0}
.dg2-risk-status{border:0;background:none;border-radius:0;padding:0;color:#f5bd79!important;font-size:1rem}
.dg2-scene-area{display:none}
@media(max-width:760px){
 .block-container{padding:0 1rem 2rem!important}
 .st-key-dg_topbar{padding:1rem 0!important;margin-bottom:1.5rem!important}
 .st-key-dg_topbar [data-testid="stHorizontalBlock"]{gap:.8rem!important}
 .st-key-dg_topbar [data-testid="stColumn"]:first-child{flex:1 0 100%!important;width:100%!important}
 .dg-top-brand span:last-child{display:flex!important}
 .st-key-dg_nav_control{justify-content:flex-start!important}
 .st-key-dg_nav_control button{font-size:.78rem!important;padding:.5rem .65rem!important}
 .dg2-page-intro h1{font-size:1.9rem!important}
 .dg2-risk{padding:1.5rem;min-height:0}
 .dg2-hero{border-radius:22px}
}
</style>
"""


def _safe(value: object) -> str:
    return html.escape(str(value))


def _num(value: object) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def _short_time(raw: object) -> str:
    if not raw:
        return "—"
    try:
        date = pd.Timestamp(raw)
        return date.strftime("%d %b, %H:%M") + " WIB"
    except (ValueError, TypeError):
        return "—"


def scene_markup(now: pd.Timestamp, weather: str = "", frost: bool = False) -> str:
    from expressive_dashboard import phase_at
    phase, sky, orb = phase_at(now.hour + now.minute / 60)
    desc = weather.lower()
    condition = ("rain" if any(w in desc for w in ("hujan", "rain"))
                 else "mist" if any(w in desc for w in ("kabut", "fog", "mist"))
                 else "cloudy" if any(w in desc for w in ("awan", "cloud", "mendung"))
                 else "")
    # Visual frost is a model illustration, not proof of frost on the ground.
    if frost:
        condition = "frost"
    night = phase == "malam"
    progress = ((now.hour + now.minute / 60 - (18 if night else 6)) % 24) / 12
    progress = min(1, max(0, progress))
    x = 12 + progress * 110
    y = 42 - math.sin(progress * math.pi) * 31
    cls = f"dg-scene {condition} {'night' if night else ''}"
    return (
        f'<div class="{cls}" role="img" aria-label="Ilustrasi suasana {phase}"'
        f' style="--sky:{sky};--orb:{orb};--orb-x:{x:.0f}px;--orb-y:{y:.0f}px">'
        '<div class="sky"><div class="orb"></div></div>'
        '<div class="mountain"></div><div class="mountain front"></div>'
        '<div class="ground"></div><div class="cloud"></div></div>'
    )


def hero_markup(pred: dict, monitor: dict, result: dict, weather: str, now: pd.Timestamp) -> str:
    latest = pred.get("latest_release") or {}
    obs = monitor.get("latest_observation") or {}
    params = obs.get("parameters") or {}
    probability = _num(result.get("probability_now"))
    threshold = _num(pred.get("threshold_stacked"))
    if probability is None:
        probability = _num(latest.get("stacked_probability"))
    if probability is None:
        prob_text = "—"
        status = "Probabilitas belum tersedia"
        progress = 0
    else:
        prob_text = f"{probability * 100:.2f}"
        status = ("Melebihi ambang model" if threshold is not None and probability >= threshold
                  else "Di bawah ambang model" if threshold is not None else "Ambang belum tersedia")
        progress = max(0, min(100, probability * 100))
    target = str(pred.get("target_night_date") or "—")
    threshold_text = "—" if threshold is None else f"{threshold * 100:.2f}%"
    release_hour = _num(latest.get("hour_wib"))
    release_label = f"{int(release_hour):02d}.00 WIB" if release_hour is not None else "—"
    prediction_stale = str(pred.get("data_status") or "unknown").lower() not in ("valid", "current", "fresh")
    prediction_health = "Data prediksi perlu diperiksa" if prediction_stale else "Data prediksi tersedia"
    temp = _num(params.get("tt_air_avg"))
    temp_text = "—" if temp is None else f"{temp:.1f} °C"
    obs_text = _short_time(obs.get("time_wib"))
    phase = phase_at(now.hour + now.minute / 60)[0]
    condition = threshold is not None and probability is not None and probability >= threshold
    image = scene_markup(now, weather, condition)
    return (
        '<section class="dg2-hero" aria-label="Ringkasan prediksi frost">'
        '<div class="dg2-risk">'
        f'<div class="dg2-risk-kicker">DIENGIN · PREDIKSI FROST · { _safe(prediction_health) }</div>'
        '<h2>Potensi frost di Dataran Tinggi Dieng</h2>'
        f'<div class="dg2-date">Tanggal target: {_safe(target)}</div>'
        f'<div class="dg2-number">{_safe(prob_text)}<span>%</span></div>'
        f'<div class="dg2-risk-status">● {_safe(status)}</div>'
        f'<div class="dg2-meter" aria-label="Probabilitas model"><span style="width:{progress:.2f}%"></span></div>'
        f'<div class="dg2-risk-meta"><span>Ambang model: {_safe(threshold_text)}</span><span>Rilis: {_safe(release_label)}</span></div>'
        '<div class="dg2-risk-explain">Nilai ini adalah probabilitas model, bukan kepastian frost. '
        'Status data prediksi ditampilkan terpisah dari observasi AWS.</div></div>'
        '<div class="dg2-scene-area">'
        '<div class="dg2-scene-head">SUASANA DATARAN TINGGI DIENG · WIB</div>'
        f'<div class="dg2-scene-art">{image}</div>'
        f'<div class="dg2-scene-caption">Suasana {_safe(phase.capitalize())}</div>'
        '<div class="dg2-scene-sub">Ilustrasi berubah mengikuti waktu WIB · bukan observasi frost</div>'
        '<div class="dg2-scene-detail">'
        f'<div><small>Suhu AWS</small><strong>{_safe(temp_text)}</strong></div>'
        '<span class="dg2-separator"></span>'
        f'<div><small>Observasi terakhir</small><strong>{_safe(obs_text)}</strong></div>'
        '</div></div></section>'
    )


@st.fragment(run_every="60s")
def render_live_hero(pred: dict, monitor: dict, result: dict, weather: str = "") -> None:
    now = pd.Timestamp.now(tz="Asia/Jakarta")
    st.markdown(hero_markup(pred, monitor, result, weather, now), unsafe_allow_html=True)


def render_page_intro(title: str, subtitle: str, eyebrow: str = "DIENGIN · Frost Early Warning") -> None:
    st.markdown(
        '<div class="dg2-page-intro">'
        f'<div class="dg2-eyebrow">{_safe(eyebrow)}</div>'
        f'<h1>{_safe(title)}</h1><p>{_safe(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )
