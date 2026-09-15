#!/usr/bin/env python3
"""Rule-based DIENGIN EWS narrative engine.

Operational principles:
- Frost probability always comes from the DIENGIN model.
- AWS observations explain the current development.
- BMKG forecast is context only and never modifies model probability.
- RH is intentionally not used by this narrative engine.
- Nightly TP/FP logic is not used for operational narration.
"""
from __future__ import annotations

import html
import math
from typing import Any

import pandas as pd

WIB = "Asia/Jakarta"


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _prob(value: Any) -> float | None:
    out = _num(value)
    return out if out is not None and 0 <= out <= 1 else None


def _stamp(value: Any) -> pd.Timestamp:
    if value is None or value == "":
        return pd.NaT
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return pd.NaT
    if pd.isna(ts):
        return pd.NaT
    return ts.tz_localize(WIB) if ts.tzinfo is None else ts.tz_convert(WIB)


def _target_date(value: Any) -> str | None:
    try:
        return pd.Timestamp(value).date().isoformat()
    except Exception:
        text = str(value or "")
        return text[:10] if len(text) >= 10 else None


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _fmt(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _sequence(release_history: pd.DataFrame | None, target: Any) -> pd.DataFrame:
    if release_history is None or release_history.empty or "stack_prob" not in release_history:
        return pd.DataFrame()
    target_text = _target_date(target)
    if not target_text:
        return pd.DataFrame()

    frame = release_history.copy()
    if "tanggal_target" in frame:
        frame = frame.loc[frame["tanggal_target"].astype(str).str[:10].eq(target_text)].copy()
    frame["stack_prob"] = pd.to_numeric(frame["stack_prob"], errors="coerce")
    frame = frame.loc[frame["stack_prob"].between(0, 1, inclusive="both")].copy()
    if frame.empty:
        return frame

    if "_time" in frame:
        frame = frame.sort_values("_time")
    elif "waktu_rilis_wib" in frame:
        frame["__time"] = frame["waktu_rilis_wib"].map(_stamp)
        frame = frame.sort_values("__time")
    elif "jam_rilis_wib" in frame:
        order = {21: 0, 22: 1, 23: 2, 0: 3, 1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10}
        frame["__order"] = pd.to_numeric(frame["jam_rilis_wib"], errors="coerce").map(order)
        frame = frame.sort_values("__order")
    return frame.reset_index(drop=True)


def _trajectory(probabilities: list[float]) -> tuple[str, str]:
    """Describe probability development; never classify the whole night."""
    if not probabilities:
        return "BELUM_TERSEDIA", "Belum ada rilis probabilitas yang valid."
    if len(probabilities) == 1:
        return "RILIS_PERTAMA", "Baru satu rilis tersedia sehingga arah perkembangan belum dapat dinilai."

    recent = probabilities[-3:]
    diffs = [b - a for a, b in zip(recent[:-1], recent[1:])]
    latest_delta = probabilities[-1] - probabilities[-2]

    if len(recent) == 3 and all(d >= 0.02 for d in diffs):
        return "MENINGKAT_BERTAHAP", "Probabilitas meningkat secara bertahap dalam tiga rilis terakhir."
    if len(recent) == 3 and all(d <= -0.02 for d in diffs):
        return "MENURUN_BERTAHAP", "Probabilitas menurun secara bertahap dalam tiga rilis terakhir."
    if latest_delta >= 0.10:
        return "MENINGKAT_KUAT", "Probabilitas meningkat cukup kuat dibanding rilis sebelumnya."
    if latest_delta >= 0.03:
        return "MENINGKAT", "Probabilitas meningkat dibanding rilis sebelumnya."
    if latest_delta <= -0.10:
        return "MENURUN_KUAT", "Probabilitas menurun cukup kuat dibanding rilis sebelumnya."
    if latest_delta <= -0.03:
        return "MENURUN", "Probabilitas menurun dibanding rilis sebelumnya."
    return "RELATIF_STABIL", "Probabilitas relatif stabil atau hanya berubah kecil dibanding rilis sebelumnya."


def _next_bmkg(payload: dict | None, now: pd.Timestamp) -> dict | None:
    if not isinstance(payload, dict):
        return None
    rows: list[tuple[pd.Timestamp, dict]] = []
    for block in payload.get("data") or []:
        if not isinstance(block, dict):
            continue
        for daily in block.get("cuaca") or []:
            if not isinstance(daily, list):
                continue
            for row in daily:
                if not isinstance(row, dict):
                    continue
                dt = _stamp(row.get("local_datetime"))
                if not pd.isna(dt):
                    rows.append((dt, row))
    if not rows:
        return None
    rows.sort(key=lambda item: item[0])
    future = [item for item in rows if item[0] >= now]
    dt, row = future[0] if future else rows[-1]
    return {
        "time": dt,
        "weather": row.get("weather_desc") or row.get("weather_desc_en") or "—",
        "temperature": _num(row.get("t")),
        "wind": _num(row.get("ws")),
        "wind_direction": row.get("wd") or "—",
    }


def build_ews_narrative(
    monitor: dict | None,
    pred: dict | None,
    release_history: pd.DataFrame | None,
    bmkg_payload: dict | None,
    now: pd.Timestamp | None = None,
) -> dict:
    monitor = monitor if isinstance(monitor, dict) else {}
    pred = pred if isinstance(pred, dict) else {}
    now = _stamp(now if now is not None else pd.Timestamp.now(tz=WIB))

    latest_release = pred.get("latest_release") or {}
    p_now = _prob(latest_release.get("stacked_probability"))
    releases = _sequence(release_history, pred.get("target_night_date"))
    probs = [float(v) for v in releases["stack_prob"].tolist()] if not releases.empty else []

    if p_now is not None:
        if not probs or abs(probs[-1] - p_now) > 1e-9:
            probs.append(p_now)
    elif probs:
        p_now = probs[-1]

    p_prev = probs[-2] if len(probs) >= 2 else None
    delta_p = p_now - p_prev if p_now is not None and p_prev is not None else None
    trajectory_code, trajectory_text = _trajectory(probs)

    release_hour = _num(latest_release.get("hour_wib"))
    release_hour = int(release_hour) if release_hour is not None else None
    threshold = _prob(pred.get("threshold_stacked"))

    if p_now is None:
        headline = "Analisis EWS belum tersedia"
    elif threshold is not None and p_now >= threshold:
        if delta_p is not None and delta_p <= -0.03:
            headline = "Potensi masih terpantau, tetapi mulai melemah"
        elif delta_p is not None and delta_p >= 0.03:
            headline = "Potensi meningkat pada rilis terbaru"
        else:
            headline = "Potensi masih terpantau pada rilis terbaru"
    elif p_prev is not None and threshold is not None and p_prev >= threshold > p_now:
        headline = "Potensi menurun pada rilis terbaru"
    elif delta_p is not None and delta_p >= 0.03:
        headline = "Potensi sedang meningkat"
    elif delta_p is not None and delta_p <= -0.03:
        headline = "Potensi sedang melemah"
    else:
        headline = "Potensi saat ini relatif rendah"

    sentences: list[str] = []
    if p_now is not None:
        release_text = f" pada rilis {release_hour:02d} WIB" if release_hour is not None else ""
        if delta_p is None:
            sentences.append(f"Probabilitas frost{release_text} sebesar {_pct(p_now)}.")
        else:
            direction = "naik" if delta_p > 0 else "turun" if delta_p < 0 else "tetap"
            sentences.append(
                f"Probabilitas frost{release_text} sebesar {_pct(p_now)}, {direction} "
                f"{abs(delta_p) * 100:.0f} poin persentase dari rilis sebelumnya ({_pct(p_prev)})."
            )
        sentences.append(trajectory_text)

    latest_obs = monitor.get("latest_observation") or {}
    params = latest_obs.get("parameters") or {}
    trend = monitor.get("trend_1h") or {}
    temp_now = _num(params.get("tt_air_avg"))
    temp_delta = _num(trend.get("tt_air_avg_change"))

    if temp_now is not None:
        if temp_delta is None:
            sentences.append(f"Suhu udara aktual tercatat {_fmt(temp_now)} °C.")
        elif temp_delta <= -0.3:
            sentences.append(
                f"Suhu udara aktual {_fmt(temp_now)} °C dan turun {_fmt(abs(temp_delta))} °C "
                "dibanding sekitar satu jam sebelumnya."
            )
        elif temp_delta >= 0.3:
            sentences.append(
                f"Suhu udara aktual {_fmt(temp_now)} °C dan naik {_fmt(abs(temp_delta))} °C "
                "dibanding sekitar satu jam sebelumnya."
            )
        else:
            sentences.append(
                f"Suhu udara aktual {_fmt(temp_now)} °C dan relatif stabil dibanding sekitar satu jam sebelumnya."
            )

    if delta_p is not None and temp_delta is not None:
        if delta_p >= 0.03 and temp_delta <= -0.3:
            sentences.append("Kenaikan probabilitas berlangsung bersamaan dengan penurunan suhu udara aktual.")
        elif delta_p <= -0.03 and temp_delta >= 0.3:
            sentences.append("Penurunan probabilitas berlangsung bersamaan dengan kenaikan suhu udara aktual.")
        elif abs(delta_p) >= 0.03 and abs(temp_delta) >= 0.3:
            sentences.append(
                "Perubahan probabilitas dan suhu belum menunjukkan arah yang sama, sehingga rilis berikutnya tetap perlu dipantau."
            )

    bmkg = _next_bmkg(bmkg_payload, now)
    bmkg_weather = None
    if bmkg is not None:
        bmkg_weather = str(bmkg["weather"])
        parts = [f"Prakiraan BMKG untuk {bmkg['time'].strftime('%H:%M')} WIB menunjukkan {bmkg_weather}"]
        if bmkg["temperature"] is not None:
            parts.append(f"suhu sekitar {_fmt(bmkg['temperature'], 0)} °C")
        if bmkg["wind"] is not None:
            parts.append(f"angin {_fmt(bmkg['wind'])} km/jam dari {bmkg['wind_direction']}")
        sentences.append(", ".join(parts) + ".")
    else:
        sentences.append("Konteks prakiraan BMKG belum tersedia pada pembaruan ini.")

    return {
        "available": p_now is not None,
        "headline": headline,
        "narrative": " ".join(sentences),
        "probability_now": p_now,
        "probability_previous": p_prev,
        "probability_change": delta_p,
        "trajectory_code": trajectory_code,
        "temperature_now_c": temp_now,
        "temperature_change_1h_c": temp_delta,
        "bmkg_weather": bmkg_weather,
        "model_note": (
            "Probabilitas berasal dari model DIENGIN. AWS digunakan untuk menjelaskan perkembangan kondisi aktual; "
            "prakiraan BMKG hanya menjadi konteks prospek dan tidak mengubah probabilitas. "
            "RH tidak digunakan oleh mesin narasi ini."
        ),
    }


def render_ews_narrative(result: dict) -> None:
    import streamlit as st

    headline = html.escape(str(result.get("headline") or "Analisis EWS"))
    narrative = html.escape(str(result.get("narrative") or "Belum ada data yang cukup untuk analisis otomatis."))
    note = html.escape(str(result.get("model_note") or ""))

    chips = []
    p_now = _prob(result.get("probability_now"))
    delta = _num(result.get("probability_change"))
    temp = _num(result.get("temperature_now_c"))
    if p_now is not None:
        chips.append(f"Probabilitas <b>{html.escape(_pct(p_now))}</b>")
    if delta is not None:
        sign = "+" if delta > 0 else ""
        chips.append(f"Δ rilis <b>{sign}{delta * 100:.0f} poin</b>")
    if temp is not None:
        chips.append(f"Suhu <b>{html.escape(_fmt(temp))} °C</b>")
    if result.get("bmkg_weather"):
        chips.append(f"BMKG <b>{html.escape(str(result['bmkg_weather']))}</b>")
    chip_html = "".join(f'<span class="dg-ews-chip">{item}</span>' for item in chips)

    st.markdown(
        """
        <style>
        .dg-ews-auto{border:1px solid rgba(128,128,128,.22);border-left:4px solid #22b8a7;
          border-radius:14px;padding:1rem 1.1rem;margin:.8rem 0 .25rem;background:rgba(34,184,167,.055)}
        .dg-ews-auto .eyebrow{font-size:.76rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.7}
        .dg-ews-auto h3{margin:.35rem 0 .5rem;padding:0;font-size:1.14rem;line-height:1.35}
        .dg-ews-auto p{margin:0;line-height:1.6;font-size:.9rem}
        .dg-ews-chips{display:flex;flex-wrap:wrap;gap:.42rem;margin:.7rem 0 .55rem}
        .dg-ews-chip{border:1px solid rgba(128,128,128,.22);border-radius:999px;padding:.27rem .56rem;
          font-size:.76rem;background:rgba(128,128,128,.06)}
        .dg-ews-note{opacity:.64;font-size:.74rem!important;margin-top:.6rem!important}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="dg-ews-auto">'
        '<div class="eyebrow">📝 Analisis otomatis EWS</div>'
        f'<h3>{headline}</h3><p>{narrative}</p>'
        f'<div class="dg-ews-chips">{chip_html}</div>'
        f'<p class="dg-ews-note">{note}</p></div>',
        unsafe_allow_html=True,
    )
