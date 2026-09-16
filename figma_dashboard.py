#!/usr/bin/env python3
"""Figma-aligned operational dashboard for DIENGIN.

This module keeps all model/QC/runtime behavior in the existing DIENGIN
modules. It only changes presentation and screen composition.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

import app
import centered_dashboard as ui
from ews_narrative import build_ews_narrative, render_ews_narrative

base = app.base

FIGMA_AWS_CSS = r"""
<style>
.dg-aws-current{
  margin:2.2rem 0 1.8rem;
}
.dg-aws-head{
  text-align:center;
  margin:0 0 1.55rem;
}
.dg-aws-head h2{
  margin:0;
  color:var(--dg-ink);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:2.25rem;
  line-height:1.2;
  font-weight:800;
  letter-spacing:-.035em;
}
.dg-aws-head p{
  margin:.55rem 0 0;
  color:var(--dg-muted);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:1.125rem;
  line-height:1.5;
}
.dg-aws-grid{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:1.5rem;
}
.dg-aws-card{
  min-height:220px;
  box-sizing:border-box;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  gap:.5rem;
  padding:1.125rem 1.5rem;
  background:#fff;
  border:1px solid var(--dg-border);
  border-radius:22px;
  text-align:center;
  box-shadow:0 6px 18px rgba(25,47,78,.025);
}
.dg-aws-icon{
  width:40px;
  height:40px;
  display:grid;
  place-items:center;
  border-radius:12px;
  color:var(--dg-blue);
  background:rgba(57,182,234,.07);
  font-size:1.3rem;
  line-height:1;
}
.dg-aws-card.temp .dg-aws-icon,
.dg-aws-card.wind .dg-aws-icon{
  background:#fff;
}
.dg-aws-label{
  width:100%;
  color:var(--dg-ink);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:1.125rem;
  line-height:1.35;
  font-weight:700;
  text-align:center;
}
.dg-aws-value-row{
  min-height:64px;
  width:100%;
  display:flex;
  align-items:center;
  justify-content:center;
  gap:.42rem;
  white-space:nowrap;
  font-variant-numeric:tabular-nums;
}
.dg-aws-value{
  color:var(--dg-ink);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:3.25rem;
  line-height:1;
  font-weight:800;
  letter-spacing:-.045em;
}
.dg-aws-unit{
  color:var(--dg-muted);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:1.25rem;
  line-height:1;
  font-weight:650;
}
.dg-aws-note{
  width:100%;
  color:var(--dg-muted);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:1rem;
  line-height:1.45;
  text-align:center;
}
.dg-aws-foot{
  margin:1.2rem 0 0;
  color:var(--dg-muted);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:1rem;
  line-height:1.55;
  text-align:center;
}
.dg-aws-station{
  margin-top:.35rem;
  color:var(--dg-muted);
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.94rem;
  line-height:1.45;
  text-align:center;
}
@media(max-width:900px){
  .dg-aws-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
  .dg-aws-head h2{font-size:2rem;}
}
@media(max-width:620px){
  .dg-aws-current{margin:1.5rem 0 1.2rem;}
  .dg-aws-grid{grid-template-columns:1fr;gap:.85rem;}
  .dg-aws-card{min-height:190px;padding:1rem 1rem;}
  .dg-aws-head h2{font-size:1.7rem;}
  .dg-aws-head p{font-size:1rem;}
  .dg-aws-value{font-size:2.8rem;}
  .dg-aws-label{font-size:1.06rem;}
  .dg-aws-note{font-size:.95rem;}
}
</style>
"""
base.CSS += FIGMA_AWS_CSS


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _fmt_id(value, digits=1):
    number = _num(value)
    if number is None:
        return "—"
    return f"{number:.{digits}f}".replace(".", ",")


def _trend_note(change, unit):
    value = _num(change)
    if value is None:
        return "Perubahan ±1 jam belum tersedia"
    if abs(value) < 0.05:
        return f"Tetap {_fmt_id(abs(value))} {unit} · ±1 jam"
    direction = "Naik" if value > 0 else "Turun"
    return f"{direction} {_fmt_id(abs(value))} {unit} · ±1 jam"


def _aws_card(label, value, unit, note, icon, css=""):
    return (
        f'<div class="dg-aws-card {css}">'
        f'<div class="dg-aws-icon" aria-hidden="true">{base.esc(icon)}</div>'
        f'<div class="dg-aws-label">{base.esc(label)}</div>'
        '<div class="dg-aws-value-row">'
        f'<span class="dg-aws-value">{base.esc(_fmt_id(value))}</span>'
        + (f'<span class="dg-aws-unit">{base.esc(unit)}</span>' if unit else "")
        + '</div>'
        f'<div class="dg-aws-note">{base.esc(note)}</div>'
        '</div>'
    )


def render_aws_current_conditions(monitor):
    latest = monitor.get("latest_observation") or {}
    params = latest.get("parameters") or {}
    trend = monitor.get("trend_1h") or {}
    station = monitor.get("station") or {}
    usable = monitor.get("status") == "success"
    if not usable:
        params, trend = {}, {}

    rh = _num(params.get("rh_avg"))
    rh_note = (
        "Belum tersedia / tidak lolos QC"
        if rh is None
        else _trend_note(trend.get("rh_avg_change"), "poin %")
    )

    dew = _num(params.get("dew_point_c"))
    dew_note = "Belum tersedia" if dew is None else "Suhu saat udara mencapai jenuh"

    cards = [
        _aws_card(
            "Suhu udara",
            params.get("tt_air_avg"),
            "°C",
            _trend_note(trend.get("tt_air_avg_change"), "°C"),
            "🌡",
            "temp",
        ),
        _aws_card(
            "Minimum observasi",
            params.get("tt_air_min"),
            "°C",
            "Minimum pada observasi terakhir",
            "🌡",
            "temp",
        ),
        _aws_card("Kelembapan", params.get("rh_avg"), "%", rh_note, "💧"),
        _aws_card(
            "Kecepatan angin",
            params.get("ws_avg"),
            "",
            _trend_note(trend.get("ws_avg_change"), "unit AWS"),
            "💨",
            "wind",
        ),
        _aws_card("Titik embun", params.get("dew_point_c"), "°C", dew_note, "💧"),
        _aws_card(
            "Pembacaan hujan",
            params.get("rr"),
            "mm",
            "Nilai AWS · bukan intensitas per jam",
            "🌧",
        ),
    ]

    pressure = _fmt_id(params.get("pp_air"))
    direction = _fmt_id(params.get("wd_avg"), 0)
    station_name = station.get("station_name") or "AWS Batur Dieng"

    st.markdown(
        '<section class="dg-aws-current">'
        '<div class="dg-aws-head">'
        '<h2>Kondisi Cuaca Terkini</h2>'
        '<p>Observasi AWS terbaru sebagai konteks perkembangan potensi frost.</p>'
        '</div>'
        '<div class="dg-aws-grid">'
        + "".join(cards)
        + '</div>'
        f'<div class="dg-aws-foot">Tekanan {base.esc(pressure)} hPa · '
        f'Arah angin {base.esc(direction)}° · '
        'Satuan kecepatan angin mengikuti sumber AWS.</div>'
        f'<div class="dg-aws-station">Sumber observasi: {base.esc(station_name)}</div>'
        '</section>',
        unsafe_allow_html=True,
    )


def _render_ews(monitor, pred, rh, now):
    try:
        try:
            bmkg_payload, _ = app.get_bmkg_forecast()
        except Exception:
            bmkg_payload = {}
        result = build_ews_narrative(
            monitor=monitor,
            pred=pred,
            release_history=rh,
            bmkg_payload=bmkg_payload,
            now=now,
        )
        render_ews_narrative(result)
    except Exception as exc:
        st.caption(
            f"Analisis otomatis EWS sementara belum tersedia ({type(exc).__name__})."
        )


def dashboard() -> None:
    now = pd.Timestamp.now(tz=base.WIB)
    monitor, ms = base.read_file("output/monitoring_latest.json")
    pred, ps = base.read_file("output/prediction_latest.json")
    pipeline, ss = base.read_file("output/pipeline_status.json")
    monitoring_history, hs = base.read_file("data/history/monitoring_history.csv", "csv")
    release_history, rs = base.read_file(
        "data/history/prediction_release_history.csv", "csv"
    )
    nights, ns = base.read_file("data/history/prediction_night_history.csv", "csv")

    mh = base.timed_frame(monitoring_history, "observation_time_wib")
    rh = base.timed_frame(release_history, "waktu_rilis_wib")
    latest_obs = monitor.get("latest_observation") or {}
    latest_release = pred.get("latest_release") or {}
    fresh, fresh_text, _ = base.freshness(latest_obs.get("time_wib"), now)

    st.markdown(
        '<div class="dg-framer-nav">'
        '<div class="dg-brand-mini"><span class="dg-brand-badge">❄</span>'
        '<span>DIENGIN</span></div>'
        '<div class="dg-nav-center"><span class="dg-nav-active">Prediksi</span>'
        '<span>Prospek BMKG</span><span>Monitoring</span></div>'
        '<div class="dg-place">⌖ Dieng Plateau</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    p_now = ui._prob(latest_release.get("stacked_probability"))
    selected = ui._selected_releases(rh, pred.get("target_night_date"))
    p_prev = None
    if not selected.empty and "stack_prob" in selected:
        probs = [
            p
            for p in pd.to_numeric(selected["stack_prob"], errors="coerce").tolist()
            if ui._prob(p) is not None
        ]
        if p_now is not None and probs and abs(probs[-1] - p_now) < 1e-9 and len(probs) >= 2:
            p_prev = probs[-2]
        elif probs:
            p_prev = probs[-1]

    threshold = ui._prob(pred.get("threshold_stacked"))
    hero_title, hero_text = ui._hero_copy(p_now, p_prev, threshold)
    hour = _num(latest_release.get("hour_wib"))
    update_text = (
        f"RILIS {int(hour):02d}.00 WIB" if hour is not None else "PEMBARUAN TERBARU"
    )
    freshness_text = fresh_text.upper() if fresh_text else "STATUS DATA"
    temp = _num((latest_obs.get("parameters") or {}).get("tt_air_avg"))
    temp_text = "—" if temp is None else f"{temp:.1f}°C"
    prob_text = "—" if p_now is None else f"{p_now * 100:.0f}%"

    st.markdown(
        '<div class="dg-hero">'
        '<div>'
        f'<div class="dg-hero-kicker">DIENG · {base.esc(update_text)} · '
        f'{base.esc(freshness_text)}</div>'
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

    # Figma master: monitoring AWS sits directly below the primary blue hero.
    render_aws_current_conditions(monitor)

    notices = []
    if ms != "ok" or monitor.get("status") != "success":
        notices.append("Monitoring belum tersedia sepenuhnya.")
    elif fresh in {"stale", "future", "delayed"}:
        notices.append(
            "Perhatikan waktu observasi karena data belum sepenuhnya menggambarkan kondisi terbaru."
        )
    if monitor.get("monitoring_status") in {"partial", "invalid"}:
        notices.append(
            "Sebagian parameter tidak tersedia atau tidak lolos pemeriksaan kualitas."
        )
    if pipeline and pipeline.get("status") not in {"success", None}:
        notices.append("Pembaruan sistem terakhir belum berhasil.")
    if notices:
        st.markdown(
            '<div class="dg-info warn">'
            + base.esc(" ".join(notices))
            + "</div>",
            unsafe_allow_html=True,
        )

    overview, bmkg_tab, explore, info = st.tabs(
        ["Prediksi", "Prospek BMKG", "Eksplorasi data", "Panduan & status"]
    )

    with overview:
        ui._section(
            "PREDIKSI PER JAM",
            "Bagaimana potensi frost berkembang malam ini?",
            "Setiap kartu menunjukkan probabilitas pada satu rilis DIENGIN. "
            "Geser horizontal untuk melihat seluruh jam.",
        )
        ui._render_hourly_cards(rh, pred)

        ui._section(
            "PROSPEK KONDISI",
            "Apa yang mendukung atau melemahkan perkembangan potensi?",
            "Ringkasan ini menggabungkan trajectory probabilitas, AWS aktual, "
            "dan konteks prakiraan BMKG tanpa mengubah output model.",
        )
        ui._render_prospect_cards(monitor, pred, rh, now)

        ui._section(
            "ANALISIS EWS",
            "Analisis otomatis perkembangan potensi",
            "Narasi berbasis aturan menggunakan probabilitas DIENGIN, AWS aktual, "
            "dan konteks prakiraan BMKG.",
        )
        _render_ews(monitor, pred, rh, now)

        ui._section(
            "GRAFIK",
            "Perjalanan probabilitas",
            "Grafik rilis per jam tetap tersedia untuk melihat pola perkembangan "
            "secara lebih rinci.",
        )
        base.render_prediction_history(rh, nights, pred, now)

        ui._section(
            "OBSERVASI",
            "Jejak cuaca",
            "Bandingkan perubahan suhu, kelembapan, angin, dan hujan dengan "
            "perkembangan probabilitas.",
        )
        base.render_trend(mh)

    with bmkg_tab:
        ui._section(
            "PROSPEK BMKG",
            "Prakiraan cuaca Dieng",
            "Prakiraan BMKG menjadi konteks prospek dan tidak mengubah probabilitas "
            "frost DIENGIN.",
        )
        app.render_bmkg_forecast(now)

    with explore:
        ui._section("DATA", "Eksplorasi data")
        base.render_explore(mh, nights)

    with info:
        ui._section("SISTEM", "Panduan & status")
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
        '<div class="dg-footer">DIENGIN · Prototipe penelitian, bukan peringatan '
        'resmi BMKG. Prakiraan cuaca pada tab Prospek BMKG bersumber dari BMKG. '
        'Seluruh waktu dalam WIB.</div>',
        unsafe_allow_html=True,
    )
