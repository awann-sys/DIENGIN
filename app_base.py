#!/usr/bin/env python3
"""DIENGIN: read-only AWS and frost prediction dashboard.

Run: streamlit run app.py
Reads existing pipeline outputs; never downloads AWS data or runs the models.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
WIB = "Asia/Jakarta"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
COLORS = ["#22b8a7", "#879cf5", "#e8ad58", "#df83b5"]

# Development helper. Set True only while checking spacing/alignment locally.
# It draws 12-column guide lines and outlines the main layout blocks.
DEBUG_LAYOUT = False

MON_LABELS = {
    "tt_air_avg": "Suhu udara (°C)",
    "tt_air_min": "Suhu minimum observasi (°C)",
    "tmin_min_1h": "Suhu minimum 1 jam (°C)",
    "rh_avg": "Kelembapan (%)",
    "ws_avg": "Angin observasi",
    "ws_mean_1h": "Angin rata-rata 1 jam",
    "dew_point_c": "Titik embun (°C)",
    "rr": "Pembacaan hujan AWS (mm)",
    "pp_air": "Tekanan (hPa)",
    "wd_avg": "Arah angin (°)",
}
PROB_LABELS = {
    "stack_prob": "DIENGIN",
    "ann_prob": "ANN",
    "svm_prob": "SVM",
    "rf_prob": "Random Forest",
}

CSS = """
<style>
:root {
    --dg-space-1: 8px;
    --dg-space-2: 12px;
    --dg-space-3: 16px;
    --dg-space-4: 24px;
    --dg-space-5: 32px;
    --dg-radius: 16px;
    --dg-teal: #22b8a7;
    --dg-amber: #e8ad58;
    --dg-border: rgba(128,128,128,.22);
    --dg-soft: rgba(128,128,128,.055);
}

.block-container {
    max-width: 1540px;
    padding: 3.75rem 2rem 2rem;
}
[data-testid="stVerticalBlock"] { gap: .85rem; }
[data-testid="stHorizontalBlock"] { gap: 1.15rem; align-items: stretch; }
[data-testid="stHeadingWithActionElements"] h3 {
    font-size: 1.22rem;
    line-height: 1.3;
    padding: .2rem 0 .35rem;
    letter-spacing: -.01em;
}
[data-testid="stCaptionContainer"] p {
    font-size: .88rem;
    line-height: 1.55;
}
[data-testid="stTabs"] [role="tablist"] {
    gap: 1.65rem;
    border-bottom-color: rgba(128,128,128,.22);
}
[data-testid="stTabs"] [role="tab"] {
    font-size: .98rem;
    font-weight: 560;
    padding: .65rem 0;
}
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stDownloadButton"] button {
    min-height: 42px;
    border-radius: .72rem;
    font-size: .9rem;
}
[data-baseweb="select"] > div { min-height: 44px; }
[data-baseweb="select"] span { font-size: .93rem; }
[data-testid="stRadio"] label p { font-size: .93rem; }
[data-testid="stRadio"] [role="radiogroup"] { gap: .8rem; }

.dg-brand {
    display: flex;
    align-items: center;
    gap: .85rem;
    padding: .15rem 0 .05rem;
}
.dg-mark {
    display: grid;
    place-items: center;
    width: 46px;
    height: 46px;
    border-radius: 13px;
    background: rgba(34,184,167,.14);
    color: var(--dg-teal);
    font-size: 29px;
    flex-shrink: 0;
    box-shadow: inset 0 0 0 1px rgba(34,184,167,.10);
}
.dg-brand h1 {
    font-size: 1.72rem;
    line-height: 1.1;
    padding: 0;
    margin: 0;
    letter-spacing: .045em;
}
.dg-brand p {
    font-size: .9rem;
    line-height: 1.35;
    margin: .22rem 0 0;
    opacity: .72;
}
.dg-strip {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: .48rem 1.15rem;
    font-size: .88rem;
    padding: .42rem 0 .68rem;
}
.dg-muted { opacity: .72; }
.dg-pill {
    border-radius: 50px;
    padding: .34rem .72rem;
    font-size: .8rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: .42rem;
    border: 1px solid rgba(128,128,128,.28);
}
.dg-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    display: inline-block;
}
.dg-fresh { color: inherit; background: rgba(34,184,167,.10); }
.dg-fresh .dg-dot {
    background: var(--dg-teal);
    animation: dg-pulse 2.4s ease-in-out infinite;
}
.dg-old {
    color: inherit;
    background: rgba(232,173,88,.12);
    border-color: rgba(232,173,88,.5);
}

.dg-card {
    background: var(--dg-soft);
    border: 1px solid var(--dg-border);
    border-radius: var(--dg-radius);
    padding: 1.2rem 1.25rem;
    box-sizing: border-box;
}
.dg-forecast {
    border-top: 3px solid var(--dg-teal);
    min-height: 322px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}
.dg-forecast.alert { border-top-color: var(--dg-amber); }
.dg-forecast h2 {
    font-size: 1.28rem;
    line-height: 1.35;
    margin: .7rem 0 .28rem;
    padding: 0;
    letter-spacing: -.015em;
}
.dg-eyebrow {
    font-size: .77rem;
    font-weight: 700;
    letter-spacing: .09em;
    text-transform: uppercase;
    opacity: .72;
}
.dg-score {
    font-size: 4rem;
    font-weight: 680;
    line-height: 1.02;
    letter-spacing: -.06em;
    margin: .85rem 0 .22rem;
    font-variant-numeric: tabular-nums;
}
.dg-score small {
    font-size: 1.52rem;
    font-weight: 520;
    margin-left: .18rem;
}
.dg-meta {
    font-size: .83rem;
    line-height: 1.5;
    opacity: .76;
}
.dg-pair {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: .5rem;
    margin-top: .72rem;
    font-size: .82rem;
}
.dg-meter {
    position: relative;
    height: 8px;
    border-radius: 8px;
    background: rgba(128,128,128,.20);
    margin: 1rem 0 .38rem;
    overflow: visible;
}
.dg-fill {
    height: 8px;
    border-radius: 8px;
    background: var(--dg-teal);
    transform-origin: left center;
    animation: dg-fill-in .65s ease-out both;
}
.dg-threshold {
    position: absolute;
    width: 2px;
    height: 16px;
    top: -4px;
    background: var(--dg-amber);
    border-radius: 2px;
}

.dg-weather {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .85rem;
}
.dg-weather .dg-card {
    padding: 1rem 1.05rem;
    min-height: 138px;
    transition: transform .16s ease, border-color .16s ease, background .16s ease;
}
.dg-label-row {
    display: flex;
    align-items: center;
    gap: .5rem;
    min-height: 22px;
}
.dg-icon {
    width: 22px;
    display: inline-grid;
    place-items: center;
    font-size: 1rem;
    line-height: 1;
    opacity: .92;
}
.dg-label {
    font-size: .86rem;
    line-height: 1.35;
    opacity: .82;
    font-weight: 540;
}
.dg-value {
    font-size: 2.25rem;
    line-height: 1.15;
    font-weight: 660;
    margin: .52rem 0 .25rem;
    font-variant-numeric: tabular-nums;
    letter-spacing: -.035em;
}
.dg-unit {
    font-size: .92rem;
    font-weight: 430;
    opacity: .74;
    margin-left: .27rem;
}
.dg-delta {
    font-size: .79rem;
    line-height: 1.45;
    opacity: .71;
}
.dg-info {
    border-left: 3px solid rgba(34,184,167,.72);
    padding: .65rem .85rem;
    margin: .32rem 0;
    background: rgba(34,184,167,.065);
    font-size: .88rem;
    line-height: 1.5;
    border-radius: 0 9px 9px 0;
}
.dg-info.warn {
    border-left-color: var(--dg-amber);
    background: rgba(232,173,88,.075);
}
.dg-release-row {
    display: grid;
    grid-template-columns: repeat(11, minmax(0,1fr));
    gap: 6px;
    margin: .65rem 0;
}
.dg-release {
    text-align: center;
    border-radius: 9px;
    padding: .62rem .15rem;
    font-size: .73rem;
    line-height: 1.2;
    border: 1px solid rgba(128,128,128,.24);
}
.dg-release b {
    display: block;
    font-size: .82rem;
    margin-top: .28rem;
}
.dg-release.has {
    background: rgba(34,184,167,.10);
    border-color: rgba(34,184,167,.38);
}
.dg-release.hit {
    background: rgba(232,173,88,.13);
    border-color: var(--dg-amber);
}
.dg-summary {
    display: flex;
    gap: 1.35rem;
    flex-wrap: wrap;
    font-size: .86rem;
    margin: .5rem 0;
}
.dg-footer {
    font-size: .78rem;
    line-height: 1.45;
    opacity: .67;
    border-top: 1px solid rgba(128,128,128,.2);
    padding-top: .85rem;
    margin-top: 1rem;
}

.dg-panel-title {
    display: flex;
    align-items: center;
    gap: .5rem;
    font-size: 1.22rem;
    font-weight: 650;
    margin: .2rem 0 .35rem;
}
.dg-panel-title .dg-panel-emoji { font-size: 1.05rem; }

@keyframes dg-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(34,184,167,.25); }
    50% { box-shadow: 0 0 0 6px rgba(34,184,167,0); }
}
@keyframes dg-fill-in {
    from { transform: scaleX(.02); opacity: .35; }
    to { transform: scaleX(1); opacity: 1; }
}

@media (hover:hover) {
    .dg-weather .dg-card:hover {
        transform: translateY(-2px);
        border-color: rgba(34,184,167,.33);
        background: rgba(128,128,128,.075);
    }
}
@media (prefers-reduced-motion: reduce) {
    .dg-fresh .dg-dot, .dg-fill { animation: none !important; }
    .dg-weather .dg-card { transition: none !important; }
}

@media(max-width: 1000px) {
    .block-container { padding-left: 1.2rem; padding-right: 1.2rem; }
    .dg-weather { grid-template-columns: repeat(2, minmax(0,1fr)); }
    .dg-forecast { min-height: 0; }
}
@media(max-width: 740px) {
    .block-container { padding: 3.7rem .9rem 1.4rem; }
    [data-testid="stHorizontalBlock"] { gap: .8rem; }
    [data-testid="stTabs"] [role="tablist"] { gap: 1rem; }
    [data-testid="stTabs"] [role="tab"] { font-size: .9rem; }
    .dg-brand h1 { font-size: 1.42rem; }
    .dg-brand p { font-size: .8rem; }
    .dg-mark { width: 42px; height: 42px; font-size: 26px; }
    .dg-strip { font-size: .8rem; }
    .dg-weather { grid-template-columns: repeat(2, minmax(0,1fr)); gap: .65rem; }
    .dg-weather .dg-card { min-height: 118px; padding: .85rem; }
    .dg-score { font-size: 3.2rem; }
    .dg-value { font-size: 1.85rem; }
    .dg-release-row { grid-template-columns: repeat(6, minmax(0,1fr)); }
}
</style>
"""

DEBUG_CSS = """
<style>
.block-container {
    position: relative;
    background-image: repeating-linear-gradient(
        90deg,
        rgba(34,184,167,.00) 0,
        rgba(34,184,167,.00) calc(8.333% - 1px),
        rgba(34,184,167,.18) calc(8.333% - 1px),
        rgba(34,184,167,.18) 8.333%
    );
}
[data-testid="stHorizontalBlock"], .dg-card, .dg-weather, .dg-info,
[data-testid="stVegaLiteChart"], [data-testid="stSelectbox"], [data-testid="stRadio"] {
    outline: 1px dashed rgba(232,173,88,.55) !important;
    outline-offset: 2px;
}
</style>
"""


def esc(value):
    return html.escape(str(value), quote=True)


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def fmt(value, places=1):
    value = number(value)
    return "—" if value is None else f"{value:.{places}f}".replace(".", ",")


def probability(value):
    value = number(value)
    return value if value is not None and 0 <= value <= 1 else None


def pct(value):
    value = probability(value)
    return "—" if value is None else fmt(value * 100) + "%"


def truth(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def stamp(value):
    if value is None or str(value).strip() in {"", "null", "NaT", "nan"}:
        return pd.NaT
    try:
        dt = pd.Timestamp(value)
        if pd.isna(dt):
            return pd.NaT
        return dt.tz_localize(WIB) if dt.tzinfo is None else dt.tz_convert(WIB)
    except (ValueError, TypeError, OverflowError):
        return pd.NaT


def date_label(value):
    dt = stamp(value)
    return "—" if pd.isna(dt) else f"{dt.day:02d} {MONTHS[dt.month - 1]} {dt.year}"


def time_label(value, short=False):
    dt = stamp(value)
    if pd.isna(dt):
        return "—"
    return ("" if short else date_label(dt) + ", ") + dt.strftime("%H:%M") + " WIB"


def freshness(value, now):
    dt = stamp(value)
    if pd.isna(dt):
        return "unknown", "Waktu belum tersedia", None
    age = (now - dt).total_seconds() / 60
    if age < -5:
        return "future", "Waktu data tidak sesuai", age
    if age <= 30:
        return "current", "Data terkini", age
    if age <= 60:
        return "delayed", "Data terlambat", age
    return "stale", "Data lama", age


def age_label(age):
    if age is None or age < -5:
        return "—"
    if age < 60:
        return f"{max(0, int(age))} menit lalu"
    if age < 1440:
        return f"{age / 60:.1f}".replace(".", ",") + " jam lalu"
    return f"{int(age / 1440)} hari lalu"


@st.cache_data(max_entries=24, show_spinner=False)
def cached_file(path, modified_ns, size, kind):
    if kind == "json":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data
    return pd.read_csv(path)


def read_file(relative, kind="json"):
    path = ROOT / relative
    try:
        info = path.stat()
        if info.st_size == 0:
            return ({} if kind == "json" else pd.DataFrame()), "empty"
        return cached_file(str(path), info.st_mtime_ns, info.st_size, kind), "ok"
    except FileNotFoundError:
        return ({} if kind == "json" else pd.DataFrame()), "missing"
    except (OSError, ValueError, pd.errors.ParserError, UnicodeError):
        return ({} if kind == "json" else pd.DataFrame()), "error"


def timed_frame(frame, field):
    if frame.empty or field not in frame:
        return pd.DataFrame()
    out = frame.copy()
    out["_time"] = out[field].map(stamp)
    out = out.dropna(subset=["_time"])
    if out.empty:
        return out
    out["_time"] = pd.to_datetime(out["_time"], utc=True).dt.tz_convert(WIB)
    return out.sort_values("_time").drop_duplicates("_time", keep="last")


def window(frame, hours):
    if frame.empty:
        return frame
    return frame.loc[frame["_time"] >= frame["_time"].max() - pd.Timedelta(hours=hours)].copy()


def chart_rows(frame, fields, percent=False, gap_minutes=30):
    """Split lines across missing values and acquisition gaps; do not interpolate."""
    parts = []
    for field, label in fields.items():
        if field not in frame or frame.empty:
            continue
        values = pd.to_numeric(frame[field], errors="coerce").replace([math.inf, -math.inf], float("nan"))
        if percent:
            values = values.where(values.between(0, 1)) * 100
        valid = values.notna()
        gap = frame["_time"].diff().dt.total_seconds().div(60).gt(gap_minutes)
        segment = ((~valid) | (~valid.shift(1, fill_value=False)) | gap).cumsum()
        part = pd.DataFrame({
            "instant": frame["_time"].map(lambda dt: dt.timestamp() * 1000),
            "Waktu": frame["_time"].map(time_label),
            "Nilai": values,
            "Seri": label,
            "Segmen": label + ":" + segment.astype(str),
        }).dropna(subset=["Nilai"])
        parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def draw_chart(frame, fields, ylabel, key, percent=False, threshold=None, height=285):
    data = chart_rows(frame, fields, percent, gap_minutes=90 if percent else 30)
    if data.empty:
        st.info("Belum ada nilai valid untuk grafik ini.")
        return
    encoding = {
        "x": {
            "field": "instant",
            "type": "temporal",
            "scale": {"type": "utc"},
            "axis": {
                "title": None,
                "labelExpr": "utcFormat(toNumber(datum.value) + 25200000, '%d/%m %H:%M')",
                "labelOverlap": True,
                "tickCount": 5,
                "labelPadding": 8,
            },
        },
        "y": {
            "field": "Nilai",
            "type": "quantitative",
            "title": ylabel,
            "scale": {"domain": [0, 100], "clamp": True} if percent else {"zero": False},
            "axis": {"titlePadding": 12, "labelPadding": 6},
        },
        "color": {
            "field": "Seri",
            "type": "nominal",
            "scale": {"domain": list(fields.values()), "range": COLORS[:len(fields)]},
            "legend": {"title": None, "orient": "bottom", "labelLimit": 230, "offset": 10},
        },
        "tooltip": [
            {"field": "Waktu"},
            {"field": "Seri"},
            {"field": "Nilai", "type": "quantitative", "format": ".2f"},
        ],
    }
    layers = [
        {"mark": {"type": "line", "strokeWidth": 2.5},
         "encoding": {**encoding, "detail": {"field": "Segmen"}}},
        {"mark": {"type": "point", "filled": True, "size": 30}, "encoding": encoding},
    ]
    if probability(threshold) is not None:
        layers.append({
            "data": {"values": [{"ambang": threshold * 100}]},
            "mark": {"type": "rule", "strokeDash": [6, 4], "color": "#e8ad58", "strokeWidth": 1.6},
            "encoding": {
                "y": {"field": "ambang", "type": "quantitative"},
                "tooltip": [{"field": "ambang", "title": "Ambang (%)", "format": ".2f"}],
            },
        })
    layers[0]["params"] = [{
        "name": "zoom",
        "select": {"type": "interval", "encodings": ["x"]},
        "bind": "scales",
    }]
    spec = {
        "height": height,
        "layer": layers,
        "config": {
            "view": {"stroke": None},
            "axis": {
                "gridOpacity": .13,
                "labelFontSize": 12,
                "titleFontSize": 13,
                "titleFontWeight": 500,
            },
            "legend": {"labelFontSize": 12},
        },
    }
    st.vega_lite_chart(data, spec, width="stretch", key=key)


def delta_label(value, unit):
    value = number(value)
    if value is None:
        return "Tren 1 jam belum tersedia"
    direction = "Turun" if value < 0 else "Naik" if value > 0 else "Tetap"
    return f"{direction} {fmt(abs(value))} {unit} · ±1 jam"


def weather_card(label, value, unit="", note="", icon="•"):
    return (
        '<div class="dg-card">'
        '<div class="dg-label-row">'
        f'<span class="dg-icon" aria-hidden="true">{esc(icon)}</span>'
        f'<span class="dg-label">{esc(label)}</span>'
        '</div>'
        f'<div class="dg-value">{esc(fmt(value))}<span class="dg-unit">{esc(unit)}</span></div>'
        f'<div class="dg-delta">{esc(note)}</div>'
        '</div>'
    )


def render_weather(monitor):
    latest = monitor.get("latest_observation") or {}
    params = latest.get("parameters") or {}
    trend = monitor.get("trend_1h") or {}
    usable = monitor.get("status") == "success"
    if not usable:
        params, trend = {}, {}
    cards = [
        weather_card("Suhu udara", params.get("tt_air_avg"), "°C",
                     delta_label(trend.get("tt_air_avg_change"), "°C"), "🌡️"),
        weather_card("Minimum observasi", params.get("tt_air_min"), "°C",
                     "Minimum pada observasi terakhir", "🌡️"),
        weather_card("Kelembapan", params.get("rh_avg"), "%",
                     "Belum tersedia / tidak lolos QC" if number(params.get("rh_avg")) is None
                     else delta_label(trend.get("rh_avg_change"), "poin %"), "💧"),
        weather_card("Kecepatan angin", params.get("ws_avg"), "",
                     delta_label(trend.get("ws_avg_change"), "unit AWS"), "💨"),
        weather_card("Titik embun", params.get("dew_point_c"), "°C",
                     "Belum tersedia" if number(params.get("dew_point_c")) is None
                     else "Suhu saat udara mencapai jenuh", "💧"),
        weather_card("Pembacaan hujan", params.get("rr"), "mm",
                     "Nilai AWS · bukan intensitas per jam", "🌧️"),
    ]
    st.markdown('<div class="dg-weather">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.caption(
        f"Tekanan {fmt(params.get('pp_air'))} hPa · Arah angin {fmt(params.get('wd_avg'), 0)}° · "
        "Satuan kecepatan angin mengikuti sumber AWS."
    )


def prediction_state(pred, now):
    pmax = probability(pred.get("probability_max_so_far"))
    flag = number(pred.get("prediction_so_far"))
    valid = pred.get("status") == "success" and pmax is not None and flag in (0, 1)
    target = stamp(pred.get("target_night_date"))
    current_target = now.normalize() + (pd.Timedelta(days=1) if now.hour >= 19 else pd.Timedelta(0))
    archived = not pd.isna(target) and target.normalize() < current_target
    source_state = freshness(pred.get("latest_observation_wib"), now)[0]
    ended = not pd.isna(target) and now >= target.normalize() + pd.Timedelta(hours=7)
    if not valid:
        label = "Prediksi belum tersedia"
    elif flag == 1:
        label = "Terindikasi embun beku"
    else:
        label = "Belum terindikasi embun beku"
    status = "Arsip prediksi" if archived else "Periode rilis selesai" if ended else "Prediksi sementara"
    return {
        "valid": valid,
        "label": label,
        "status": status,
        "archived": archived,
        "source_state": source_state,
        "pmax": pmax,
        "flag": flag,
    }


def render_forecast(pred, now):
    state = prediction_state(pred, now)
    threshold = probability(pred.get("threshold_stacked"))
    release = pred.get("latest_release") or {}
    available = number(pred.get("releases_available"))
    expected = number(pred.get("releases_expected"))
    count = f"{int(available)}/{int(expected)}" if available is not None and expected else "—"
    score = fmt(state["pmax"] * 100) if state["valid"] else "—"
    latest_score = pct(release.get("stacked_probability")) if state["valid"] else "—"
    extra = " · data input lama" if state["source_state"] in {"stale", "delayed"} else ""
    alert = " alert" if state["flag"] == 1 or state["archived"] else ""
    meter = ""
    if state["valid"]:
        marker = "" if threshold is None else (
            f'<span class="dg-threshold" style="left:{threshold * 100:.4f}%"></span>'
        )
        meter = (
            f'<div class="dg-meter"><div class="dg-fill" style="width:{state["pmax"] * 100:.4f}%"></div>'
            f'{marker}</div>'
        )
    st.markdown(
        f'<div class="dg-card dg-forecast{alert}">'
        '<div class="dg-eyebrow">❄️ Prediksi embun beku</div>'
        f'<h2>{esc(state["label"])}</h2>'
        f'<div class="dg-meta">Target {esc(date_label(pred.get("target_night_date")))}</div>'
        f'<div class="dg-score">{esc(score)}<small>%</small></div>'
        f'<div class="dg-meta">Probabilitas maksimum dari rilis tersedia</div>{meter}'
        f'<div class="dg-pair"><span>Ambang <b>{esc(pct(threshold))}</b></span><span>Rilis <b>{count}</b></span></div>'
        f'<div class="dg-pair"><span>Rilis terakhir <b>{esc(latest_score)}</b></span>'
        f'<span>{esc(time_label(release.get("release_time_wib"), True))}</span></div>'
        f'<div class="dg-meta" style="margin-top:.7rem">{esc(state["status"] + extra)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def release_strip(releases, target, threshold, now):
    target_dt = stamp(target)
    if pd.isna(target_dt):
        return
    selected = (
        releases.loc[releases["tanggal_target"].astype(str).str[:10] == target_dt.date().isoformat()]
        if "tanggal_target" in releases else pd.DataFrame()
    )
    boxes = []
    for hour in [21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]:
        when = target_dt.normalize() + pd.Timedelta(hours=hour) - (
            pd.Timedelta(days=1) if hour >= 21 else pd.Timedelta(0)
        )
        rows = (
            selected.loc[pd.to_numeric(selected["jam_rilis_wib"], errors="coerce") == hour]
            if "jam_rilis_wib" in selected else pd.DataFrame()
        )
        p = probability(rows.iloc[-1].get("stack_prob")) if not rows.empty else None
        css, label = "", "Nanti" if when > now else "—"
        if p is not None:
            css = " hit" if threshold is not None and p >= threshold else " has"
            label = pct(p)
        title = f"{time_label(when)} · " + (label if p is not None else "Belum ada rilis valid")
        boxes.append(
            f'<div class="dg-release{css}" title="{esc(title)}">{hour:02d}<b>{esc(label)}</b></div>'
        )
    st.markdown('<div class="dg-release-row">' + "".join(boxes) + "</div>", unsafe_allow_html=True)
    st.caption("Jam rilis WIB · — belum tersedia · garis kuning menandai ambang pada grafik.")


def download_csv(frame, name, key):
    output = frame.drop(columns=["_time"], errors="ignore").copy()
    st.download_button(
        "↓ Unduh CSV",
        output.to_csv(index=False).encode("utf-8-sig"),
        file_name=name,
        mime="text/csv",
        key=key,
    )


def render_trend(mh):
    title, control = st.columns([1.8, 1])
    with title:
        st.markdown(
            '<div class="dg-panel-title"><span class="dg-panel-emoji">📈</span><span>Jejak cuaca</span></div>',
            unsafe_allow_html=True,
        )
    with control:
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
    subset = window(mh, hours)
    options = ["Suhu", "Kelembapan", "Angin", "Hujan AWS"]
    selected = st.radio(
        "Parameter cuaca",
        options,
        horizontal=True,
        key="weather_parameter",
        label_visibility="collapsed",
    )
    mapping = {
        "Suhu": ({"tt_air_avg": "Suhu udara", "tt_air_min": "Minimum observasi"}, "Suhu (°C)"),
        "Kelembapan": ({"rh_avg": "Kelembapan"}, "RH (%)"),
        "Angin": ({"ws_avg": "Angin observasi", "ws_mean_1h": "Rata-rata 1 jam"}, "Kecepatan · unit sumber AWS"),
        "Hujan AWS": ({"rr": "Pembacaan hujan AWS"}, "Pembacaan AWS (mm)"),
    }
    fields, ylabel = mapping[selected]
    draw_chart(subset, fields, ylabel, "weather_chart", height=300)
    st.caption(
        f"{time_label(subset['_time'].min())} — {time_label(subset['_time'].max())} · "
        f"{len(subset)} observasi tersimpan"
    )
    if selected == "Hujan AWS":
        st.caption("Pembacaan sumber belum dikonversi menjadi intensitas atau total hujan periode pilihan.")
    elif selected == "Suhu":
        values = pd.to_numeric(subset.get("tt_air_avg", pd.Series(dtype=float)), errors="coerce")
        if values.notna().any():
            st.markdown(
                f'<div class="dg-summary"><span>Terendah <b>{fmt(values.min())} °C</b></span>'
                f'<span>Rata-rata <b>{fmt(values.mean())} °C</b></span>'
                f'<span>Tertinggi <b>{fmt(values.max())} °C</b></span></div>',
                unsafe_allow_html=True,
            )
    st.caption("Geser atau zoom untuk menjelajah; klik dua kali untuk reset. Jeda data tidak disambungkan.")


def render_prediction_history(rh, nights, pred, now):
    st.markdown(
        '<div class="dg-panel-title"><span class="dg-panel-emoji">❄️</span><span>Perjalanan prediksi</span></div>',
        unsafe_allow_html=True,
    )
    if rh.empty or "tanggal_target" not in rh:
        st.info("Riwayat rilis belum tersedia.")
        return
    dates = sorted(rh["tanggal_target"].dropna().astype(str).str[:10].unique(), reverse=True)
    if not dates:
        st.info("Tanggal target belum tersedia.")
        return
    target = st.selectbox("Tanggal target prediksi", dates, format_func=date_label, key="prediction_date")
    selected = rh.loc[rh["tanggal_target"].astype(str).str[:10] == target]
    threshold = None
    if str(pred.get("target_night_date"))[:10] == target:
        threshold = probability(pred.get("threshold_stacked"))
    elif "tanggal_target" in nights:
        summary = nights.loc[nights["tanggal_target"].astype(str).str[:10] == target]
        if not summary.empty:
            threshold = probability(summary.iloc[-1].get("ambang_final"))
    release_strip(selected, target, threshold, now)
    draw_chart(selected, {"stack_prob": "DIENGIN"}, "Probabilitas (%)", "release_chart", True, threshold, 300)
    st.caption(f"Ambang target {pct(threshold)} · probabilitas per rilis, bukan observasi kejadian frost.")
    with st.expander("Bandingkan model"):
        draw_chart(selected, PROB_LABELS, "Probabilitas (%)", "models_chart", True, height=285)
        st.caption(
            "ANN, SVM, dan Random Forest adalah model dasar. DIENGIN menampilkan hasil stacking; "
            "nilainya bukan rata-rata sederhana."
        )
    with st.expander("Tabel rilis dan unduhan"):
        table = selected.drop(columns=["_time"], errors="ignore").copy()
        cols = [
            c for c in ["waktu_rilis_wib", "stack_prob", "ann_prob", "svm_prob", "rf_prob", "status_data_rilis"]
            if c in table
        ]
        table = table[cols]
        for col in PROB_LABELS:
            if col in table:
                table[col] = (pd.to_numeric(table[col], errors="coerce") * 100).round(2)
        table = table.rename(columns={
            **{k: v + " (%)" for k, v in PROB_LABELS.items()},
            "waktu_rilis_wib": "Rilis (WIB)",
            "status_data_rilis": "Status data",
        })
        st.dataframe(table, hide_index=True, width="stretch")
        download_csv(selected, f"diengin_rilis_{target}.csv", "release_csv")
        st.caption("CSV mempertahankan probabilitas asli pada skala 0–1.")


def render_explore(mh, nights):
    st.subheader("Eksplorasi observasi")
    if mh.empty:
        st.info("Belum ada arsip monitoring untuk dijelajahi.")
    else:
        first, last = mh["_time"].min().date(), mh["_time"].max().date()
        dates = st.date_input(
            "Rentang tanggal observasi (WIB)",
            (last, last),
            min_value=first,
            max_value=last,
            key="explore_dates",
        )
        if not isinstance(dates, (tuple, list)) or len(dates) != 2:
            st.info("Pilih tanggal awal dan tanggal akhir.")
        else:
            subset = mh.loc[
                (mh["_time"].dt.date >= dates[0]) & (mh["_time"].dt.date <= dates[1])
            ]
            columns = [c for c in MON_LABELS if c in mh]
            selected = st.multiselect(
                "Kolom yang ditampilkan",
                columns,
                default=[c for c in ["tt_air_avg", "tt_air_min", "rh_avg", "ws_avg"] if c in columns],
                format_func=lambda col: MON_LABELS[col],
                key="explore_columns",
            )
            st.caption(f"{len(subset)} observasi · kosong berarti data tidak tersedia, bukan nol.")
            if subset.empty:
                st.info("Tidak ada observasi tersimpan pada rentang tanggal ini.")
            else:
                table = subset[["observation_time_wib"] + selected].rename(
                    columns={"observation_time_wib": "Waktu (WIB)", **MON_LABELS}
                )
                st.dataframe(table, width="stretch", hide_index=True, height=360)
                download_csv(
                    subset[["observation_time_wib"] + selected],
                    "diengin_observasi.csv",
                    "monitoring_csv",
                )
    with st.expander("Arsip ringkasan malam"):
        if nights.empty:
            st.info("Arsip ringkasan malam belum tersedia.")
        else:
            table = nights.copy()
            if "tanggal_target" in table:
                table = table.sort_values("tanggal_target", ascending=False)
            for col in ["probabilitas_maksimum", "ambang_final"]:
                if col in table:
                    table[col] = (pd.to_numeric(table[col], errors="coerce") * 100).round(2)
            table = table.rename(columns={
                "tanggal_target": "Tanggal target",
                "jumlah_rilis_tersedia": "Rilis valid",
                "ambang_final": "Ambang (%)",
                "probabilitas_maksimum": "Maksimum (%)",
                "jam_probabilitas_maksimum_wib": "Jam maksimum (WIB)",
                "jam_pertama_melampaui_ambang_wib": "Jam pertama melampaui ambang",
                "prediksi_malam": "Indikasi (1=ya, 0=belum)",
            })
            st.dataframe(table, hide_index=True, width="stretch")
            st.caption(
                "Ringkasan mengikuti arsip pipeline dan jumlah rilisnya; sebagian malam dapat memiliki rilis tidak lengkap."
            )
            download_csv(nights, "diengin_ringkasan_malam.csv", "night_csv")


def render_info(monitor, pred, pipeline, states, now):
    left, right = st.columns(2)
    with left:
        st.subheader("Kenali angkanya")
        st.markdown(
            "**Probabilitas** menunjukkan keluaran model, bukan kepastian kejadian. "
            "Angka utama adalah probabilitas maksimum dari rilis yang tersedia untuk tanggal target.\n\n"
            "**Ambang klasifikasi** adalah batas yang digunakan model untuk menghasilkan indikasi frost. "
            "Warna penanda mengikuti ambang dari pipeline, tanpa kategori risiko tambahan.\n\n"
            "**Rilis 21–07 WIB** melintasi tengah malam. Tanggal target merujuk pada pagi akhir periode. "
            "Rilis yang hilang tetap ditandai kosong.\n\n"
            "**Suhu minimum observasi** berbeda dengan minimum harian. **Titik embun** adalah suhu "
            "ketika udara mencapai kondisi jenuh."
        )
    with right:
        st.subheader("Kualitas & pembaruan")
        st.markdown(
            "Tampilan diperiksa ulang setiap **60 detik** selama halaman terbuka; pengambilan data "
            "mengikuti pipeline terjadwal sekitar **15 menit**, dan dapat terlambat.\n\n"
            "Umur data dihitung dari waktu observasi terhadap waktu sekarang: **≤30 menit** terkini, "
            "**30–60 menit** terlambat, dan **>60 menit** data lama.\n\n"
            "Garis grafik diputus saat ada nilai hilang atau jeda monitoring lebih dari 30 menit. "
            "Nilai RH yang tidak lolos pemeriksaan kualitas tidak diganti dengan nol.\n\n"
            "Kecepatan angin ditampilkan dalam unit sumber AWS; pembacaan hujan tidak dijumlahkan "
            "menjadi akumulasi tanpa memastikan jenis pencatatannya."
        )
    station = monitor.get("station") or {}
    st.caption(
        f"Stasiun: {station.get('station_name') or '—'} · ID {station.get('station_id') or '—'} · "
        f"Elevasi {fmt(station.get('elevation_m'), 0)} m · "
        f"Koordinat {fmt(station.get('latitude'), 5)}, {fmt(station.get('longitude'), 5)}"
    )
    with st.expander("Detail operasional"):
        st.write({
            "Dashboard diperiksa (WIB)": time_label(now),
            "Monitoring diproses": time_label(monitor.get("generated_at_wib")),
            "Prediksi diproses": time_label(pred.get("generated_at_wib")),
            "Status pipeline": pipeline.get("status", "belum tersedia"),
            "Status monitoring": monitor.get("monitoring_status", "belum tersedia"),
            "Berkas": states,
        })
        if pred.get("qc"):
            st.dataframe(pd.DataFrame(pred["qc"]), width="stretch", hide_index=True)


@st.fragment(run_every="60s")
def dashboard():
    now = pd.Timestamp.now(tz=WIB)
    monitor, ms = read_file("output/monitoring_latest.json")
    pred, ps = read_file("output/prediction_latest.json")
    pipeline, ss = read_file("output/pipeline_status.json")
    monitoring_history, hs = read_file("data/history/monitoring_history.csv", "csv")
    release_history, rs = read_file("data/history/prediction_release_history.csv", "csv")
    nights, ns = read_file("data/history/prediction_night_history.csv", "csv")

    mh = timed_frame(monitoring_history, "observation_time_wib")
    rh = timed_frame(release_history, "waktu_rilis_wib")
    latest = monitor.get("latest_observation") or {}
    station = monitor.get("station") or {}
    fresh, fresh_text, age = freshness(latest.get("time_wib"), now)

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
            st.rerun()

    pill = "dg-fresh" if fresh == "current" else "dg-old"
    st.markdown(
        f'<div class="dg-strip"><span class="dg-pill {pill}"><i class="dg-dot"></i>{esc(fresh_text)}</span>'
        f'<span>{esc(station.get("station_name") or "Stasiun AWS")}</span>'
        f'<span class="dg-muted">{esc(time_label(latest.get("time_wib")))} · {esc(age_label(age))}</span></div>',
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
            '<div class="dg-info warn">' + esc(" ".join(notices)) + "</div>",
            unsafe_allow_html=True,
        )

    overview, explore, info = st.tabs(["Ringkasan", "Eksplorasi data", "Panduan & status"])

    with overview:
        forecast_col, weather_col = st.columns([1, 2.15])
        with forecast_col:
            render_forecast(pred, now)
        with weather_col:
            render_weather(monitor)
            change = number((monitor.get("trend_1h") or {}).get("tt_air_avg_change"))
            if change is not None and monitor.get("status") == "success":
                st.markdown(
                    '<div class="dg-info">' + esc(
                        f"Suhu {'turun' if change < 0 else 'naik' if change > 0 else 'tetap'} "
                        f"{fmt(abs(change))} °C dibanding referensi sekitar 1 jam sebelumnya. "
                        "Tren ini bukan konfirmasi frost."
                    ) + "</div>",
                    unsafe_allow_html=True,
                )

        weather_plot, release_plot = st.columns([1, 1])
        with weather_plot:
            render_trend(mh)
        with release_plot:
            render_prediction_history(rh, nights, pred, now)

        st.download_button(
            "↓ Simpan ringkasan",
            data=(
                f"DIENGIN\nObservasi: {time_label(latest.get('time_wib'))}\n"
                f"Status data: {fresh_text}\nTarget prediksi: {date_label(pred.get('target_night_date'))}\n"
                f"Hasil: {prediction_state(pred, now)['label']}\n"
                f"Probabilitas maksimum dari rilis tersedia: {pct(pred.get('probability_max_so_far'))}\n"
                f"Rilis terakhir: {time_label((pred.get('latest_release') or {}).get('release_time_wib'))}\n"
                "Prototipe penelitian; bukan peringatan resmi BMKG.\n"
            ).encode("utf-8"),
            file_name="diengin_ringkasan.txt",
            mime="text/plain",
            key="summary_download",
        )

    with explore:
        render_explore(mh, nights)

    with info:
        render_info(
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
        'Seluruh waktu dalam WIB. Data kosong tidak berarti nol.</div>',
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="DIENGIN · Cuaca & Frost",
        page_icon="❄️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS + (DEBUG_CSS if DEBUG_LAYOUT else ""), unsafe_allow_html=True)
    dashboard()


if __name__ == "__main__":
    main()
