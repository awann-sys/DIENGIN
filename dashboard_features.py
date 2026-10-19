#!/usr/bin/env python3
"""Focused dashboard features for the DIENGIN operational UI.

This module provides:
- hierarchical current-weather cards for the Prediction page;
- full parameter cards for Monitoring;
- user-configurable multi-variable charts with independent auto-scaling;
- on-demand AWS BMKG historical requests and CSV download.

The frost probability itself is never modified here.
"""
from __future__ import annotations

import html
import io
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

WIB = "Asia/Jakarta"
AWS_API_BASE = "https://apiaws.bmkg.go.id"
AWS_LOGIN_URL = f"{AWS_API_BASE}/auth/login"
AWS_DATA_URL = f"{AWS_API_BASE}/getdata"
AWS_STATION_ID = "STA2285"

WEATHER_VARS = {
    "Suhu udara": ("tt_air_avg", "°C"),
    "Suhu minimum AWS": ("tt_air_min", "°C"),
    "Kelembapan relatif": ("rh_avg", "%"),
    "Kecepatan angin": ("ws_avg", "unit AWS"),
    "Curah / pembacaan hujan": ("rr", "mm"),
    "Tekanan udara": ("pp_air", "hPa"),
    "Titik embun": ("dew_point_c", "°C"),
    "Arah angin": ("wd_avg", "°"),
    "Suhu maksimum AWS": ("tt_air_max", "°C"),
    "Angin maksimum AWS": ("ws_max", "unit AWS"),
    "Radiasi rata-rata AWS": ("sr_avg", "unit AWS"),
    "Radiasi maksimum AWS": ("sr_max", "unit AWS"),
}
MODEL_VARS = {
    "Probabilitas ANN": ("ann_prob", "%"),
    "Probabilitas SVM": ("svm_prob", "%"),
    "Probabilitas Random Forest": ("rf_prob", "%"),
    "Probabilitas Stacked / Final": ("stack_prob", "%"),
}

CARD_CSS = r"""
<style>
.dg-current-wrap{margin:2rem 0 1.65rem}
.dg-current-head{text-align:center;margin-bottom:1.25rem}
.dg-current-head h2{margin:0;font:800 2rem/1.2 'Plus Jakarta Sans',sans-serif;color:var(--dg-ink)}
.dg-current-head p{margin:.45rem 0 0;color:var(--dg-muted);font-size:1rem}
.dg-primary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-bottom:1rem}
.dg-secondary-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}
.dg-weather-card{background:#fff;border:1px solid var(--dg-border);border-radius:20px;padding:1.25rem 1.3rem;text-align:center;min-width:0}
.dg-weather-card.primary{min-height:180px;display:flex;flex-direction:column;justify-content:center}
.dg-weather-label{font-weight:750;color:var(--dg-ink);font-size:1rem}
.dg-weather-value{font:800 2.45rem/1.1 'Plus Jakarta Sans',sans-serif;letter-spacing:-.035em;color:var(--dg-ink);margin:.55rem 0 .35rem}
.dg-weather-card.primary .dg-weather-value{font-size:3rem}
.dg-weather-note{font-size:.9rem;line-height:1.45;color:var(--dg-muted)}
.dg-secondary-line{margin:.95rem 0 0;text-align:center;color:var(--dg-muted);font-size:.94rem;line-height:1.6}
.dg-all-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem;margin:1rem 0 1.5rem}
.dg-all-grid .dg-weather-card{min-height:150px;display:flex;flex-direction:column;justify-content:center}
.dg-explorer-card{background:#fff;border:1px solid var(--dg-border);border-radius:20px;padding:1rem 1rem 1.1rem;margin:.7rem 0 1rem}
.dg-scale-legend{display:flex;flex-wrap:wrap;gap:.45rem .7rem;margin:.35rem 0 .7rem;color:var(--dg-muted);font-size:.82rem}
.dg-scale-chip{border:1px solid var(--dg-border);border-radius:999px;padding:.3rem .55rem;background:#fafcff}
.dg-svg-wrap{width:100%;overflow-x:auto}
.dg-svg-wrap svg{width:100%;min-width:700px;height:auto;display:block}
.dg-explorer-help{font-size:.84rem;color:var(--dg-muted);margin:.25rem 0 .7rem}
@media(max-width:900px){.dg-all-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){
 .dg-primary-grid{grid-template-columns:1fr}.dg-secondary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .dg-secondary-grid .dg-weather-card:last-child{grid-column:1/-1}.dg-all-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .dg-current-head h2{font-size:1.65rem}.dg-weather-card.primary .dg-weather-value{font-size:2.55rem}
}

.dg-prediction-instruments{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem;margin:1rem 0 1.4rem}
.dg-prediction-instruments .dg-weather-card.instrument{min-height:200px}
@media(max-width:1050px){.dg-prediction-instruments{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.dg-prediction-instruments{grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem}.dg-prediction-instruments .dg-weather-card.instrument{min-height:165px}}
@media(max-width:380px){.dg-prediction-instruments{grid-template-columns:1fr}}
/* DIENGIN Weather Instruments v2 — scoped to current cards only */
.dg-all-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.1rem}
.dg-all-grid .dg-weather-card{min-height:190px}
.dg-weather-card.instrument{position:relative;display:flex;flex-direction:column;text-align:left;justify-content:space-between;gap:1.25rem;padding:1.35rem 1.5rem;border:1px solid var(--dg-border);background:linear-gradient(135deg,var(--accent-bg),var(--dg-card,#fff) 75%);border-radius:22px}
.dg-instrument-top{display:flex;align-items:center;justify-content:space-between;gap:.5rem}
.dg-instrument-icon{color:var(--accent);font-size:1.75rem;line-height:1}
.dg-weather-card.instrument .dg-weather-label{font-size:1.12rem;line-height:1.25;text-align:left}
.dg-instrument-reading{display:flex;align-items:baseline;gap:.42rem;min-width:0;white-space:nowrap}
.dg-weather-card.instrument .dg-weather-value{font-size:clamp(2.65rem,3.2vw,4rem);margin:0;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.055em}
.dg-instrument-unit{font-size:clamp(.86rem,1.2vw,1.3rem);font-weight:700;color:var(--dg-muted)}
.dg-instrument-foot{display:flex;align-items:center;justify-content:space-between;gap:.5rem;padding-top:.75rem;border-top:1px solid var(--dg-border)}
.dg-weather-card.instrument .dg-weather-note{font-size:.85rem;line-height:1.4;text-align:left}
.dg-instrument-source{font-size:.76rem;color:var(--dg-muted);white-space:nowrap}
.dg-current-wrap .dg-all-grid{margin-top:1.2rem}
@media(max-width:1050px){.dg-all-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.dg-all-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem}.dg-weather-card.instrument{padding:.9rem;min-height:155px;gap:.75rem}.dg-weather-card.instrument .dg-weather-label{font-size:.86rem}.dg-weather-card.instrument .dg-weather-value{font-size:clamp(1.65rem,7.3vw,2.5rem)}.dg-instrument-unit{font-size:.72rem}.dg-instrument-foot{align-items:flex-start;flex-direction:column}.dg-instrument-source{display:none}}
@media(max-width:380px){.dg-all-grid{grid-template-columns:1fr}.dg-weather-card.instrument .dg-weather-value{font-size:3.1rem}}
</style>
"""


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _fmt(value: Any, digits: int = 1) -> str:
    number = _num(value)
    if number is None:
        return "—"
    return f"{number:.{digits}f}".replace(".", ",")


def _observation_label(value: Any) -> str:
    """Readable timestamp in WIB; unknown times are never inferred."""
    try:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp):
            return "waktu tidak tersedia"
        stamp = stamp.tz_localize(WIB) if stamp.tzinfo is None else stamp.tz_convert(WIB)
        months = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")
        return f"{stamp.day} {months[stamp.month-1]} {stamp.year}, {stamp:%H.%M} WIB"
    except (ValueError, TypeError, OverflowError):
        return "waktu tidak tersedia"


def _trend_note(value: Any, unit: str) -> str:
    change = _num(value)
    if change is None:
        return "Tren ±1 jam belum tersedia"
    if abs(change) < 0.05:
        return "→ relatif stabil"
    arrow = "↑" if change > 0 else "↓"
    return f"{arrow} {_fmt(abs(change))} {unit} / ±1 jam"


def _card(label: str, value: Any, unit: str = "", note: str = "", primary: bool = False) -> str:
    unit_html = f" <span style='font-size:.48em;color:var(--dg-muted)'>{html.escape(unit)}</span>" if unit else ""
    return (
        f'<div class="dg-weather-card{" primary" if primary else ""}">'
        f'<div class="dg-weather-label">{html.escape(label)}</div>'
        f'<div class="dg-weather-value">{html.escape(_fmt(value))}{unit_html}</div>'
        f'<div class="dg-weather-note">{html.escape(note)}</div>'
        '</div>'
    )


def _night_minimum(history: pd.DataFrame | None, now: pd.Timestamp) -> tuple[float | None, str]:
    if history is None or history.empty or "tt_air_avg" not in history:
        return None, "Belum tersedia"
    frame = history.copy()
    if "_time" not in frame:
        source = "observation_time_wib" if "observation_time_wib" in frame else None
        if source is None:
            return None, "Belum tersedia"
        frame["_time"] = pd.to_datetime(frame[source], errors="coerce")
    times = pd.to_datetime(frame["_time"], errors="coerce")
    if getattr(times.dt, "tz", None) is None:
        times = times.dt.tz_localize(WIB, nonexistent="NaT", ambiguous="NaT")
    else:
        times = times.dt.tz_convert(WIB)
    local_now = now.tz_convert(WIB) if now.tzinfo else now.tz_localize(WIB)
    start_date = local_now.date() if local_now.hour >= 19 else (local_now - pd.Timedelta(days=1)).date()
    start = pd.Timestamp(start_date, tz=WIB) + pd.Timedelta(hours=19)
    mask = (times >= start) & (times <= local_now)
    work = frame.loc[mask].copy()
    work["_time_local"] = times.loc[mask]
    work["tt_air_avg"] = pd.to_numeric(work["tt_air_avg"], errors="coerce")
    work = work.dropna(subset=["tt_air_avg", "_time_local"])
    if work.empty:
        return None, "Belum tersedia"
    idx = work["tt_air_avg"].idxmin()
    return float(work.loc[idx, "tt_air_avg"]), f"Tercatat {work.loc[idx, '_time_local'].strftime('%H:%M')} WIB"


def render_prediction_weather(monitor: dict, history: pd.DataFrame | None, now: pd.Timestamp) -> None:
    st.markdown(CARD_CSS, unsafe_allow_html=True)
    latest = monitor.get("latest_observation") or {}
    p = latest.get("parameters") or {}
    trend = monitor.get("trend_1h") or {}
    low, low_note = _night_minimum(history, now)
    rh = _num(p.get("rh_avg"))
    rh_note = "Tidak tersedia / tidak lolos QC" if rh is None else _trend_note(trend.get("rh_avg_change"), "poin %")
    rain = _num(p.get("rr"))
    rain_note = "Tidak ada hujan" if rain == 0 else "Pembacaan AWS terbaru" if rain is not None else "Belum tersedia"
    obs_time = _observation_label(latest.get("time_wib"))
    station = (monitor.get("station") or {}).get("station_name") or "AWS Batur Dieng"

    cards = [
        ("Suhu terkini", p.get("tt_air_avg"), "°C", _trend_note(trend.get("tt_air_avg_change"), "°C"), "tt_air_avg"),
        ("Kelembapan relatif", p.get("rh_avg"), "%", rh_note, "rh_avg"),
        ("Kecepatan angin", p.get("ws_avg"), "unit AWS", _trend_note(trend.get("ws_avg_change"), "unit AWS"), "ws_avg"),
        ("Titik embun", p.get("dew_point_c"), "°C", "Dihitung dari suhu dan RH", "dew_point_c"),
    ]
    html_block = (
        '<section class="dg-current-wrap"><div class="dg-current-head">'
        '<h2>Kondisi Cuaca Terkini</h2>'
        f'<p>{html.escape(str(station))} · observasi {html.escape(str(obs_time))}</p></div>'
        '<div class="dg-prediction-instruments">'
        + ''.join(_instrument_card(*item) for item in cards)
        + '</div>'
        f'<div class="dg-secondary-line">Minimum malam ini {_fmt(low)} °C · {html.escape(low_note)} · Hujan {_fmt(rain)} mm · Tekanan {_fmt(p.get("pp_air"))} hPa</div>'
        '</section>'
    )
    st.markdown(html_block, unsafe_allow_html=True)



INSTRUMENT_STYLES = {
    "tt_air_avg": ("🌡", "#C36C46", "#FFF3ED"),
    "tt_air_min": ("❄", "#4B90B4", "#EDF7FC"),
    "rh_avg": ("💧", "#337FC3", "#EEF7FF"),
    "ws_avg": ("≋", "#218B7E", "#EAF8F2"),
    "wd_avg": ("↗", "#6785B0", "#F0F3FA"),
    "rr": ("☂", "#478BC0", "#EFF7FE"),
    "pp_air": ("◉", "#836CC0", "#F4F0FC"),
    "dew_point_c": ("◇", "#478F91", "#EDF8F7"),
    "tt_air_max": ("☀", "#CA8544", "#FFF6ED"),
    "ws_max": ("≋", "#218B7E", "#EAF8F2"),
    "sr_avg": ("☀", "#B78B32", "#FFF9EA"),
    "sr_max": ("☀", "#B78B32", "#FFF9EA"),
}


def _instrument_card(label: str, value: Any, unit: str, note: str, key: str) -> str:
    icon, accent, bg = INSTRUMENT_STYLES[key]
    observed = _num(value)
    number = _fmt(value, 2 if key in {"tt_air_avg", "tt_air_min", "tt_air_max", "ws_avg", "ws_max", "dew_point_c", "pp_air"} else 1)
    value_text = number if observed is not None else "—"
    unit_text = html.escape(unit) if observed is not None else ""
    return (
        f'<div class="dg-weather-card instrument" style="--accent:{accent};--accent-bg:{bg}">'
        f'<div class="dg-instrument-top"><span class="dg-weather-label">{html.escape(label)}</span>'
        f'<span class="dg-instrument-icon" aria-hidden="true">{icon}</span></div>'
        f'<div class="dg-instrument-reading"><span class="dg-weather-value">{html.escape(value_text)}</span>'
        f'<span class="dg-instrument-unit">{unit_text}</span></div>'
        f'<div class="dg-instrument-foot"><span class="dg-weather-note">{html.escape(note)}</span>'
        '<span class="dg-instrument-source">AWS Batur</span></div></div>'
    )

def render_monitoring_cards(monitor: dict) -> None:
    st.markdown(CARD_CSS, unsafe_allow_html=True)
    latest = monitor.get("latest_observation") or {}
    p = latest.get("parameters") or {}
    trend = monitor.get("trend_1h") or {}
    station = (monitor.get("station") or {}).get("station_name") or "AWS Batur Dieng"
    obs_time = latest.get("time_wib") or "—"
    values = [
        ("Suhu udara", p.get("tt_air_avg"), "°C", _trend_note(trend.get("tt_air_avg_change"), "°C")),
        ("Suhu minimum AWS", p.get("tt_air_min"), "°C", "Nilai minimum dari field AWS"),
        ("Kelembapan relatif", p.get("rh_avg"), "%", _trend_note(trend.get("rh_avg_change"), "poin %")),
        ("Kecepatan angin", p.get("ws_avg"), "", _trend_note(trend.get("ws_avg_change"), "unit AWS")),
        ("Arah angin", p.get("wd_avg"), "°", "Observasi terbaru"),
        ("Curah / pembacaan hujan", p.get("rr"), "mm", "Observasi terbaru"),
        ("Tekanan udara", p.get("pp_air"), "hPa", "Observasi terbaru"),
        ("Titik embun", p.get("dew_point_c"), "°C", "Dihitung dari suhu dan RH"),
        ("Suhu maksimum AWS", p.get("tt_air_max"), "°C", "Nilai maksimum dari field AWS"),
        ("Angin maksimum AWS", p.get("ws_max"), "unit AWS", "Satuan mengikuti sumber AWS"),
        ("Radiasi rata-rata AWS", p.get("sr_avg"), "unit AWS", "Satuan mengikuti sumber AWS"),
        ("Radiasi maksimum AWS", p.get("sr_max"), "unit AWS", "Satuan mengikuti sumber AWS"),
    ]
    st.markdown(
        '<section class="dg-current-wrap"><div class="dg-current-head"><h2>Monitoring AWS</h2>'
        f'<p>{html.escape(str(station))} · observasi {html.escape(str(obs_time))}</p></div>'
        '<div class="dg-all-grid">' + ''.join(_instrument_card(*item, key) for item, key in zip(values, ["tt_air_avg", "tt_air_min", "rh_avg", "ws_avg", "wd_avg", "rr", "pp_air", "dew_point_c", "tt_air_max", "ws_max", "sr_avg", "sr_max"])) + '</div></section>',
        unsafe_allow_html=True,
    )


def _series_frame(mh: pd.DataFrame | None, rh: pd.DataFrame | None, labels: list[str]) -> tuple[pd.DataFrame, dict[str, tuple[str, str]]]:
    selected: dict[str, tuple[str, str]] = {}
    weather_labels = [x for x in labels if x in WEATHER_VARS]
    model_labels = [x for x in labels if x in MODEL_VARS]
    frames = []
    if weather_labels and mh is not None and not mh.empty:
        time_col = "_time" if "_time" in mh else "observation_time_wib"
        cols = [time_col] + [WEATHER_VARS[x][0] for x in weather_labels if WEATHER_VARS[x][0] in mh]
        w = mh[cols].copy()
        w = w.rename(columns={time_col: "time"})
        for label in weather_labels:
            key, unit = WEATHER_VARS[label]
            if key in w:
                selected[label] = (key, unit)
        frames.append(w)
    if model_labels and rh is not None and not rh.empty:
        time_col = "_time" if "_time" in rh else "waktu_rilis_wib"
        cols = [time_col] + [MODEL_VARS[x][0] for x in model_labels if MODEL_VARS[x][0] in rh]
        r = rh[cols].copy().rename(columns={time_col: "time"})
        for label in model_labels:
            key, unit = MODEL_VARS[label]
            if key in r:
                r[key] = pd.to_numeric(r[key], errors="coerce") * 100.0
                selected[label] = (key, unit)
        frames.append(r)
    if not frames:
        return pd.DataFrame(), selected
    merged = pd.concat(frames, ignore_index=True, sort=False)
    merged["time"] = pd.to_datetime(merged["time"], errors="coerce")
    merged = merged.dropna(subset=["time"]).sort_values("time")
    return merged, selected


def _svg_chart(frame: pd.DataFrame, selected: dict[str, tuple[str, str]]) -> str:
    width, height = 1100, 390
    left, right, top, bottom = 70, 30, 35, 65
    plot_w, plot_h = width-left-right, height-top-bottom
    if frame.empty or not selected:
        return '<div class="dg-explorer-help">Belum ada data yang dapat digrafikkan.</div>'
    t = pd.to_datetime(frame["time"], errors="coerce")
    t0, t1 = t.min(), t.max()
    span = max((t1 - t0).total_seconds(), 1.0)
    palette = ["#2878F0", "#20A4B9", "#7A68D1", "#D47A2F", "#4B9B57", "#B45576", "#6D7B8D", "#9A6A2F"]
    parts = [f'<div class="dg-svg-wrap"><svg viewBox="0 0 {width} {height}" role="img" aria-label="Grafik eksplorasi data">']
    for i in range(5):
        y = top + plot_h*i/4
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#E8EDF4" stroke-width="1"/>')
    legend = []
    for idx, (label, (key, unit)) in enumerate(selected.items()):
        if key not in frame:
            continue
        values = pd.to_numeric(frame[key], errors="coerce")
        valid = values.dropna()
        if valid.empty:
            continue
        vmin, vmax = float(valid.min()), float(valid.max())
        if math.isclose(vmin, vmax):
            pad = max(abs(vmin)*0.05, 1.0)
            lo, hi = vmin-pad, vmax+pad
        else:
            pad = (vmax-vmin)*0.08
            lo, hi = vmin-pad, vmax+pad
        color = palette[idx % len(palette)]
        pts = []
        for row_i, value in values.items():
            if pd.isna(value):
                continue
            ts = pd.Timestamp(frame.loc[row_i, "time"])
            x = left + ((ts-t0).total_seconds()/span)*plot_w
            y = top + (1-(float(value)-lo)/(hi-lo))*plot_h
            pts.append((x, y, ts, float(value)))
        if len(pts) >= 2:
            point_text = " ".join(f"{x:.1f},{y:.1f}" for x,y,_,_ in pts)
            parts.append(f'<polyline points="{point_text}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')
        for x,y,ts,val in pts:
            tip = html.escape(f"{ts.strftime('%d/%m %H:%M')} · {label}: {val:.2f} {unit}")
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.1" fill="{color}"><title>{tip}</title></circle>')
        legend.append(f'<span class="dg-scale-chip"><b>{html.escape(label)}</b> · {_fmt(vmin)}–{_fmt(vmax)} {html.escape(unit)}</span>')
    ticks = 6
    for i in range(ticks):
        ratio = i/(ticks-1)
        ts = t0 + (t1-t0)*ratio
        x = left + plot_w*ratio
        parts.append(f'<text x="{x:.1f}" y="{height-28}" text-anchor="middle" font-size="13" fill="#6F7D91">{ts.strftime("%d/%m %H")}</text>')
    parts.append('</svg></div>')
    return '<div class="dg-scale-legend">' + ''.join(legend) + '</div>' + ''.join(parts)


def render_custom_explorer(mh: pd.DataFrame | None, rh: pd.DataFrame | None = None, *, key_prefix: str, include_models: bool = True, default_labels: list[str] | None = None, allow_download: bool = False) -> None:
    st.markdown(CARD_CSS, unsafe_allow_html=True)
    options = list(WEATHER_VARS) + (list(MODEL_VARS) if include_models else [])
    count_key = f"{key_prefix}_chart_count"
    if count_key not in st.session_state:
        st.session_state[count_key] = 1
    st.caption("Setiap variabel memakai auto-scale independen agar arah naik-turun tetap terlihat meskipun satuannya berbeda.")
    for i in range(st.session_state[count_key]):
        with st.container(key=f"{key_prefix}_chart_{i}"):
            default = default_labels if i == 0 and default_labels else ([options[0]] if options else [])
            selected_labels = st.multiselect(
                "Variabel",
                options,
                default=[x for x in default if x in options],
                key=f"{key_prefix}_vars_{i}",
                placeholder="Pilih satu atau beberapa variabel",
            )
            frame, selected = _series_frame(mh, rh, selected_labels)
            if not frame.empty:
                min_t, max_t = frame["time"].min(), frame["time"].max()
                c1, c2 = st.columns(2)
                with c1:
                    start_date = st.date_input("Dari", value=min_t.date(), key=f"{key_prefix}_from_{i}")
                with c2:
                    end_date = st.date_input("Sampai", value=max_t.date(), key=f"{key_prefix}_to_{i}")
                start = pd.Timestamp(start_date)
                end = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
                local_time = pd.to_datetime(frame["time"], errors="coerce")
                if getattr(local_time.dt, "tz", None) is not None:
                    start = start.tz_localize(WIB)
                    end = end.tz_localize(WIB)
                frame = frame[(local_time >= start) & (local_time <= end)].copy()
            st.markdown('<div class="dg-explorer-card">' + _svg_chart(frame, selected) + '</div>', unsafe_allow_html=True)
            if allow_download and not frame.empty:
                st.download_button(
                    "↓ Unduh data grafik (CSV)",
                    data=frame.to_csv(index=False).encode("utf-8"),
                    file_name=f"diengin_{key_prefix}_grafik_{i+1}.csv",
                    mime="text/csv",
                    key=f"{key_prefix}_download_{i}",
                )
            if i > 0 and st.button("Hapus grafik", key=f"{key_prefix}_remove_{i}"):
                st.session_state[count_key] = max(1, st.session_state[count_key]-1)
                st.rerun()
    if st.button("＋ Tambah grafik", key=f"{key_prefix}_add"):
        st.session_state[count_key] += 1
        st.rerun()


def _secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def _api_token() -> str:
    token = _secret("AWS_API_TOKEN")
    if token:
        return token
    username, password = _secret("AWS_API_USERNAME"), _secret("AWS_API_PASSWORD")
    if not username or not password:
        raise RuntimeError("Kredensial AWS BMKG belum tersedia pada deployment dashboard.")
    query = urllib.parse.urlencode({"username": username, "password": password})
    req = urllib.request.Request(AWS_LOGIN_URL + "?" + query, method="POST", headers={"User-Agent":"DIENGIN/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "sukses" or not payload.get("token"):
        raise RuntimeError("Login AWS BMKG gagal.")
    return str(payload["token"])


def _flatten_payload(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    def walk(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            if "tanggal" in obj and "id_station" in obj:
                records.append(obj)
            else:
                for key in ("data", "result", "results"):
                    if key in obj:
                        walk(obj[key])
    walk(payload)
    return records


def _dew_point(temp: float, rh: float) -> float:
    if pd.isna(temp) or pd.isna(rh) or rh <= 0 or rh > 100:
        return math.nan
    a, b = 17.625, 243.04
    gamma = math.log(rh/100.0) + (a*temp)/(b+temp)
    return (b*gamma)/(a-gamma)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_aws_history(start_wib_iso: str, end_wib_iso: str) -> pd.DataFrame:
    start_wib, end_wib = pd.Timestamp(start_wib_iso), pd.Timestamp(end_wib_iso)
    if start_wib.tzinfo is None:
        start_wib = start_wib.tz_localize(WIB)
    if end_wib.tzinfo is None:
        end_wib = end_wib.tz_localize(WIB)
    if end_wib <= start_wib:
        raise ValueError("Waktu akhir harus setelah waktu awal.")
    if end_wib - start_wib > pd.Timedelta(days=31):
        raise ValueError("Satu permintaan dibatasi maksimum 31 hari agar tetap ringan.")
    token = _api_token()
    start_utc, end_utc = start_wib.tz_convert("UTC"), end_wib.tz_convert("UTC")
    cursor = start_utc
    payloads = []
    while cursor < end_utc:
        chunk_end = min(cursor + pd.Timedelta(hours=23, minutes=50), end_utc)
        params = urllib.parse.urlencode({
            "token": token,
            "filter": "*",
            "tgl_mulai": cursor.strftime("%Y-%m-%d %H:%M:%S"),
            "tgl_selesai": chunk_end.strftime("%Y-%m-%d %H:%M:%S"),
            "tipe_station": "aws",
            "id_station": AWS_STATION_ID,
        })
        req = urllib.request.Request(AWS_DATA_URL + "?" + params, headers={"User-Agent":"DIENGIN/1.0"})
        with urllib.request.urlopen(req, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, dict) and payload.get("status") == "gagal":
            raise RuntimeError(str(payload.get("message") or "Request AWS ditolak."))
        payloads.append(payload)
        cursor = chunk_end + pd.Timedelta(seconds=1)
    records = []
    for payload in payloads:
        records.extend(_flatten_payload(payload))
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df = df[df.get("id_station", "").astype(str).eq(AWS_STATION_ID)].copy()
    dt = pd.to_datetime(df.get("tanggal"), utc=True, errors="coerce")
    df["_time"] = dt.dt.tz_convert(WIB)
    for col in ["rr","ws_avg","wd_avg","tt_air_avg","tt_air_min","rh_avg","pp_air","tt_air_max","ws_max","sr_avg","sr_max"]:
        if col not in df:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["dew_point_c"] = [_dew_point(t, r) for t,r in zip(df["tt_air_avg"], df["rh_avg"])]
    df = df[df['_time'].between(start_wib, end_wib)]
    return df.dropna(subset=["_time"]).sort_values("_time").drop_duplicates("_time", keep="last").reset_index(drop=True)


def render_interactive_chart(series, key, unit, label):
    import altair as alt
    if series.empty or key not in series or series[key].dropna().empty:
        st.info('Belum ada data valid pada rentang ini.')
        return
    data = series[[key]].copy()
    # Plot wall-clock WIB on a UTC scale so browser timezone cannot shift labels.
    local = pd.DatetimeIndex(data.index)
    if local.tz is not None:
        local = local.tz_convert(WIB).tz_localize(None)
    data['wib'] = local.tz_localize('UTC').as_unit('ms').asi8
    data['Waktu WIB'] = local.strftime('%d/%m/%Y %H:%M')
    gap = pd.Series(local, index=data.index).diff().gt(pd.Timedelta(hours=1))
    data['segment'] = (data[key].isna() | gap).cumsum()
    data = data.dropna(subset=[key]).reset_index(drop=True)
    base = alt.Chart(data).encode(
        x=alt.X('wib:T', title='Waktu (WIB)', scale=alt.Scale(type='utc'), axis=alt.Axis(format='%d/%m %H:%M', labelOverlap=True)),
        y=alt.Y(f'{key}:Q', title=f'{label} ({unit})', scale=alt.Scale(domain=[0, 100]) if 'Probabilitas' in label else alt.Scale(zero=False)),
        tooltip=[alt.Tooltip('Waktu WIB:N'), alt.Tooltip(f'{key}:Q', title=f'{label} ({unit})', format='.2f')],
    )
    chart = base.mark_line(color='#48BDB4', strokeWidth=2.5).encode(detail='segment:N') + base.mark_circle(color='#48BDB4', size=35)
    from theme_controller import current_theme
    dark = current_theme() == 'dark'
    chart = chart.properties(height=330, background='transparent').interactive().configure_view(stroke=None).configure_axis(
        labelColor='#B5C4D6' if dark else '#60757C', titleColor='#EDF4FF' if dark else '#172E37',
        gridColor='#29394E' if dark else '#E5ECF5', domain=False, tickCount=6,
    )
    st.altair_chart(chart, use_container_width=True, theme=None)
    st.caption('Arahkan ke titik untuk detail. Gulir untuk zoom; geser untuk menjelajah. Jam tanpa data tetap menjadi jeda.')


@st.cache_data(ttl=900, show_spinner=False)
def fetch_stored_aws_archive(start_iso, end_iso):
    import gzip
    start, end = pd.Timestamp(start_iso), pd.Timestamp(end_iso)
    if end <= start or end - start > pd.Timedelta(days=31):
        raise ValueError('Pilih rentang valid maksimum 31 hari.')
    frames = []
    for month in pd.period_range(start.tz_convert('UTC').tz_localize(None).to_period('M'), end.tz_convert('UTC').tz_localize(None).to_period('M'), freq='M'):
        url = f'https://raw.githubusercontent.com/awann-sys/DIENGIN/aws-archive/observations/{month}.csv.gz'
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                frames.append(pd.read_csv(io.BytesIO(gzip.decompress(response.read()))))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    if not frames:
        return pd.DataFrame()
    data = pd.concat(frames, ignore_index=True)
    data['_time'] = pd.to_datetime(data['datetime_utc'], utc=True).dt.tz_convert(WIB)
    for col in list(data.columns):
        if col.endswith('_flag') and col[:-5] in data:
            data.loc[pd.to_numeric(data[col], errors='coerce').eq(1), col[:-5]] = float('nan')
    return data[data['_time'].between(start, end)].sort_values('_time').drop_duplicates('_time')


def render_on_demand_monitoring_explorer() -> None:
    st.subheader("Eksplorasi Data AWS")
    st.caption("Pilih rentang tanggal dan jam. Data baru diminta dari AWS BMKG setelah tombol Muat Data ditekan.")
    source = st.selectbox('Sumber histori', ['Arsip tersimpan', 'Ambil langsung dari BMKG'], key='aws_history_source')
    st.caption('Arsip bulanan mulai 2021; hasil mengikuti ketersediaan rekaman BMKG. Permintaan dibatasi 31 hari.')
    now = pd.Timestamp.now(tz=WIB).floor("10min")
    default_start = now - pd.Timedelta(hours=12)
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Tanggal mulai", value=default_start.date(), key="aws_req_start_date")
        start_time = st.time_input("Jam mulai", value=default_start.time(), key="aws_req_start_time")
    with c2:
        end_date = st.date_input("Tanggal selesai", value=now.date(), key="aws_req_end_date")
        end_time = st.time_input("Jam selesai", value=now.time(), key="aws_req_end_time")
    if st.button("Muat Data", type="primary", key="aws_req_load"):
        start = pd.Timestamp(datetime.combine(start_date, start_time), tz=WIB)
        end = pd.Timestamp(datetime.combine(end_date, end_time), tz=WIB)
        try:
            with st.spinner("Mengunduh data AWS BMKG…"):
                reader = fetch_stored_aws_archive if source == 'Arsip tersimpan' else fetch_aws_history
                st.session_state["aws_requested_history"] = reader(start.isoformat(), end.isoformat())
            st.session_state["aws_requested_range"] = (start, end)
        except (ValueError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
            st.session_state.pop('aws_requested_history', None)
            st.error('Data belum dapat dimuat. Periksa rentang (maksimal 31 hari), ketersediaan arsip, serta kredensial AWS BMKG pada deployment.')
    frame = st.session_state.get("aws_requested_history")
    if isinstance(frame, pd.DataFrame):
        if frame.empty:
            st.info("Request berhasil, tetapi tidak ada observasi pada rentang tersebut.")
            return
        st.success(f"{len(frame):,} observasi berhasil dimuat.")
        loaded_start, loaded_end = st.session_state['aws_requested_range']
        st.caption(f'Rentang yang dimuat: {loaded_start:%d/%m/%Y %H:%M} – {loaded_end:%d/%m/%Y %H:%M} WIB. Ubah tanggal lalu tekan Muat Data untuk memperbarui hasil.')
        selected_label = st.selectbox('Parameter data unduhan', list(WEATHER_VARS), key='aws_download_parameter')
        field, unit = WEATHER_VARS[selected_label]
        if field in frame:
            render_interactive_chart(frame.set_index('_time')[[field]], field, unit, selected_label)
        with st.expander('Tampilkan observasi yang diunduh'):
            st.dataframe(frame, hide_index=True, use_container_width=True)
        st.download_button(
            "↓ Unduh data AWS (CSV)",
            data=frame.to_csv(index=False).encode("utf-8"),
            file_name=f"diengin_aws_{loaded_start:%Y%m%d_%H%M}_{loaded_end:%Y%m%d_%H%M}.csv",
            mime="text/csv",
            key="aws_req_download",
        )
        render_custom_explorer(frame, None, key_prefix="monitor_requested", include_models=False, default_labels=["Suhu udara", "Kelembapan relatif"], allow_download=True)

