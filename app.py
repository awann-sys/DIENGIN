#!/usr/bin/env python3
"""DIENGIN Streamlit entrypoint.

The production app is started from this file. It keeps BMKG forecast support,
reads live operational outputs from the runtime branch when available, and
renders the current three-tab DIENGIN dashboard from nav_dashboard.py.
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pandas as pd
import streamlit as st

# Keep the existing visual base/tokens available to the redesigned dashboard.
import app_ui  # noqa: F401
import app_base as base

BMKG_ADM4 = "33.04.16.2008"
BMKG_API_URL = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={BMKG_ADM4}"
RUNTIME_RAW_BASE = "https://raw.githubusercontent.com/awann-sys/DIENGIN/runtime/"

BMKG_CSS = r"""
<style>
.dg-bmkg-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.9rem;margin:.75rem 0 .95rem}
.dg-bmkg-card{border:1px solid rgba(128,128,128,.22);border-radius:14px;padding:1rem 1.1rem;background:rgba(128,128,128,.045);min-height:160px}
.dg-bmkg-time{font-size:.86rem;font-weight:500;opacity:.7;margin-bottom:.48rem}
.dg-bmkg-weather{font-size:1.2rem;font-weight:680;line-height:1.32;min-height:50px;display:flex;align-items:flex-start}
.dg-bmkg-weather .emoji{font-size:1.55rem;line-height:1;margin-right:.42rem;flex-shrink:0}
.dg-bmkg-temp{font-size:2.2rem;font-weight:700;line-height:1.05;letter-spacing:-.03em;margin:.56rem 0 .32rem}
.dg-bmkg-meta{font-size:.88rem;line-height:1.55;opacity:.8}
.dg-bmkg-hero{border-left:3px solid #22b8a7;background:rgba(34,184,167,.065);border-radius:0 12px 12px 0;padding:1rem 1.08rem;margin:.55rem 0 1rem;font-size:.94rem;line-height:1.6}
.dg-bmkg-hero strong{font-size:1.18rem}.dg-bmkg-source{font-size:.82rem;opacity:.72;margin-top:.65rem}
@media(max-width:1000px){.dg-bmkg-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.dg-bmkg-grid{grid-template-columns:1fr}.dg-bmkg-weather{font-size:1.08rem}.dg-bmkg-temp{font-size:2rem}}
</style>
"""
base.CSS += BMKG_CSS


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_bmkg_forecast():
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
    parsed = []
    for row in rows:
        ts = base.stamp(row.get("local_datetime"))
        if not pd.isna(ts):
            parsed.append((ts, row))
    parsed.sort(key=lambda item: item[0])
    return parsed


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
    payload, status = get_bmkg_forecast()
    if status != "ok":
        st.warning("Data prakiraan BMKG sedang tidak dapat diambil. Coba beberapa saat lagi.")
        st.caption("Sumber data: BMKG · API Prakiraan Cuaca Terbuka")
        return

    location = payload.get("lokasi") or {}
    parsed = flatten_bmkg_rows(payload)
    if not parsed:
        st.info("Respons BMKG diterima, tetapi detail prakiraan belum tersedia.")
        return

    village = location.get("desa") or "Dieng Kulon"
    district = location.get("kecamatan") or "—"
    regency = location.get("kotkab") or "—"
    province = location.get("provinsi") or "—"
    st.caption(f"{village} · {district} · {regency} · {province}")

    next_pair = next((item for item in parsed if item[0] >= now), parsed[0])
    dt, row = next_pair
    desc = row.get("weather_desc") or "Cuaca"
    st.markdown(
        '<div class="dg-bmkg-hero">'
        f'<strong>{bmkg_weather_emoji(desc)} {base.esc(desc)}</strong> · '
        f'{base.esc(base.date_label(dt))}, {dt.strftime("%H:%M")} WIB<br>'
        f'Suhu <b>{base.esc(base.fmt(row.get("t"), 0))} °C</b> · '
        f'RH <b>{base.esc(base.fmt(row.get("hu"), 0))}%</b> · '
        f'Angin <b>{base.esc(base.fmt(row.get("ws"), 1))} km/jam</b> dari '
        f'{base.esc(row.get("wd") or "—")}'
        '</div>',
        unsafe_allow_html=True,
    )

    grouped = {}
    for ts, item in parsed:
        grouped.setdefault(ts.date(), []).append((ts, item))
    dates = list(grouped)[:3]
    tabs = st.tabs([base.date_label(pd.Timestamp(day, tz=base.WIB)) for day in dates])
    for tab, day in zip(tabs, dates):
        with tab:
            cards = []
            for ts, item in grouped[day]:
                weather = item.get("weather_desc") or "—"
                cards.append(
                    '<div class="dg-bmkg-card">'
                    f'<div class="dg-bmkg-time">{ts.strftime("%H:%M")} WIB</div>'
                    f'<div class="dg-bmkg-weather"><span class="emoji">{bmkg_weather_emoji(weather)}</span>{base.esc(weather)}</div>'
                    f'<div class="dg-bmkg-temp">{base.esc(base.fmt(item.get("t"), 0))}°C</div>'
                    f'<div class="dg-bmkg-meta">RH {base.esc(base.fmt(item.get("hu"), 0))}% · '
                    f'Angin {base.esc(base.fmt(item.get("ws"), 1))} km/jam<br>'
                    f'Dari {base.esc(item.get("wd") or "—")} · '
                    f'Jarak pandang {base.esc(item.get("vs_text") or "—")}</div>'
                    '</div>'
                )
            st.markdown('<div class="dg-bmkg-grid">' + "".join(cards) + '</div>', unsafe_allow_html=True)

    analysis = base.stamp(parsed[0][1].get("analysis_date"))
    analysis_text = base.time_label(analysis) if not pd.isna(analysis) else "—"
    st.markdown(
        f'<div class="dg-bmkg-source">Sumber data: BMKG · ADM4 {BMKG_ADM4} · '
        f'Waktu produksi data: {base.esc(analysis_text)}</div>',
        unsafe_allow_html=True,
    )


# Keep one stable local reader. app.py can be imported again by nav_dashboard
# while Streamlit executes this file as __main__.
if not hasattr(base, "_diengin_original_read_file"):
    base._diengin_original_read_file = base.read_file
_original_read_file = base._diengin_original_read_file


@st.cache_data(ttl=45, show_spinner=False)
def _read_runtime(relative: str, kind: str = "json"):
    url = RUNTIME_RAW_BASE + relative.lstrip("/")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DIENGIN/1.0 (+https://github.com/awann-sys/DIENGIN)",
            "Accept": "application/json,text/csv,text/plain,*/*",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        text = response.read().decode("utf-8")
    if not text.strip():
        return ({} if kind == "json" else pd.DataFrame()), "empty"
    if kind == "json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data, "ok"
    return pd.read_csv(io.StringIO(text)), "ok"


def read_operational_file(relative: str, kind: str = "json"):
    try:
        return _read_runtime(relative, kind)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        pd.errors.ParserError,
    ):
        return _original_read_file(relative, kind)


base.read_file = read_operational_file


if __name__ == "__main__":
    # Import after all helpers above are defined. nav_dashboard imports `app`
    # for BMKG helpers, so doing this under the main guard avoids circular init.
    import nav_dashboard

    base.dashboard = nav_dashboard.dashboard
    base.main()
