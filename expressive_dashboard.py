"""Approved DIENGIN presentation, backed exclusively by operational data."""
from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

import dashboard_features as features


CSS = """
<style>
.block-container{max-width:1240px!important;padding:2rem 2rem 3rem!important}
.dg-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:22px 0}
.dg-eyebrow{font-size:.75rem;letter-spacing:.15em;text-transform:uppercase;color:var(--dg-muted);font-weight:750}
.dg-heading h1{font-size:clamp(1.65rem,3vw,2.65rem);letter-spacing:-.055em;margin:8px 0!important;color:var(--dg-ink)}
.dg-heading p{color:var(--dg-muted);margin:0;font-size:.94rem}
.dg-hero{background:var(--dg-card)!important;animation:none!important;border:1px solid var(--dg-border);border-top:3px solid var(--dg-blue);border-radius:24px!important;box-shadow:0 12px 32px var(--dg-shadow)!important;padding:28px!important}
.dg-hero,.dg-hero *{color:var(--dg-ink)!important}
.dg-hero h1{font-size:clamp(1.5rem,2.5vw,2rem)!important;letter-spacing:-.04em}
.dg-hero p,.dg-hero-copy-note{color:var(--dg-muted)!important}
.dg-hero-kicker{color:var(--dg-blue)!important;font-size:.75rem!important;letter-spacing:.08em}
.dg-hero-score{border-left:1px solid var(--dg-border);padding-left:28px;background:transparent!important;box-shadow:none!important}
.dg-hero-score .value{font-size:clamp(5rem,8vw,6.2rem)!important;font-variant-numeric:tabular-nums;letter-spacing:-.07em}
.dg-hero-score .label,.dg-hero-score .sub{color:var(--dg-muted)!important}
.dg-current-wrap{margin:22px 0!important}.dg-current-head{text-align:left!important;margin-bottom:14px!important}
.dg-current-head h2{font-size:1.18rem!important}.dg-current-head p{font-size:.85rem!important}
.dg-weather-card{text-align:left!important;padding:20px!important;border-radius:18px!important;position:relative;overflow:hidden}
.dg-weather-value,.dg-weather-card.primary .dg-weather-value{font-size:2.65rem!important;letter-spacing:-.045em;font-variant-numeric:tabular-nums}
.dg-weather-label{font-size:.88rem!important}.dg-weather-note{font-size:.8rem!important}
.dg-weather-card::before{content:'◌';float:right;display:grid;place-items:center;width:32px;height:32px;border-radius:11px;background:#e3f3ef;color:#087f75;font-size:24px}
.dg-weather-card:nth-child(4n+1)::before{content:'♨';background:#e7f1ff;color:#397cbb}
.dg-weather-card:nth-child(4n+2)::before{content:'◉';background:#e4f4f0;color:#087f75}
.dg-weather-card:nth-child(4n+3)::before{content:'≋';background:#f0eafa;color:#8865ad}
.dg-weather-card:nth-child(4n)::before{content:'◇';background:#fff1dc;color:#9a6a27}
.dg-primary-grid{grid-template-columns:repeat(4,minmax(0,1fr))!important}.dg-secondary-line{text-align:left!important}
.dg-section{text-align:left!important}.dg-section-title{font-size:1.4rem!important}
.dg-insight-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:12px 0 20px}
.dg-insight{border:1px solid var(--dg-border);border-radius:17px;padding:18px;background:var(--dg-card);border-left:4px solid var(--accent)}
.dg-insight b{font-size:.94rem;color:var(--dg-ink)}.dg-insight p{margin:7px 0 0;font-size:.88rem;color:var(--dg-muted);line-height:1.6}
.dg-insight em{font-style:normal;display:inline-grid;place-items:center;border-radius:9px;background:var(--dg-soft);color:var(--accent);width:29px;height:29px;margin-right:8px}
.st-key-dg_journey{padding:22px;border:1px solid var(--dg-border);border-radius:20px;background:var(--dg-card);margin-bottom:22px}
.st-key-dg_journey h3{margin:0;font-size:1.3rem}.st-key-dg_journey [data-testid="stCaptionContainer"]{color:var(--dg-muted)}
.dg-hour-chart{overflow-x:auto;width:100%}.dg-hour-chart svg{display:block;width:100%;height:auto;min-width:560px}
.dg-hour-chart text{fill:var(--dg-muted);font:13px sans-serif}.dg-hour-chart line{stroke:var(--dg-grid)}
.dg-scene{width:210px;height:126px;position:relative;flex:0 0 210px;isolation:isolate}
.dg-scene .sky{position:absolute;left:27px;top:0;width:158px;height:119px;border-radius:50%;background:var(--sky);overflow:hidden}
.dg-scene .orb{position:absolute;left:var(--orb-x);top:var(--orb-y);width:27px;height:27px;border-radius:50%;background:var(--orb);box-shadow:0 0 0 9px #ffffff22}
.dg-scene.night .orb{box-shadow:inset -8px -3px 0 0 #e4ebf0;background:transparent}
.dg-scene .mountain{position:absolute;bottom:6px;width:168px;height:78px;clip-path:polygon(0 100%,28% 8%,45% 42%,66% 20%,100% 100%);background:#98bdb2;left:1px}
.dg-scene .mountain.front{width:186px;height:71px;left:25px;bottom:1px;background:#367e75;clip-path:polygon(0 100%,28% 0,48% 35%,70% 13%,100% 100%)}
.dg-scene .ground{position:absolute;bottom:0;left:9px;width:187px;height:10px;border-radius:50%;background:#c8ded5}
.dg-scene .cloud{position:absolute;top:40px;left:70px;width:76px;height:25px;border-radius:40px;background:#e3edef;box-shadow:18px 9px 0 -4px #e3edef;display:none}
.dg-scene .cloud::before{content:'';position:absolute;width:35px;height:35px;border-radius:50%;left:14px;top:-17px;background:inherit}
.dg-scene.cloudy .cloud,.dg-scene.rain .cloud,.dg-scene.mist .cloud{display:block}
.dg-scene.rain .cloud::after{content:'╱ ╱ ╱';position:absolute;top:28px;left:15px;color:#7daec2;font-size:22px}
.dg-scene.mist .ground{height:22px;bottom:15px;box-shadow:0 -15px 0 -3px #dbe8e5;background:#dbe8e5aa}
.dg-scene.frost .mountain{background:linear-gradient(145deg,#fff 30%,#d8eef5 52%,#8ab6c3 72%)}
.dg-scene.frost .mountain.front{background:linear-gradient(145deg,#fff 27%,#d5edf6 48%,#80b3c6 76%)}
.dg-scene.frost .ground{background:#f4fdff;box-shadow:0 -3px 12px #c3e8f0}
.dg-scene.frost::after{content:'❄';position:absolute;right:18px;top:66px;font-size:21px;color:#699bb2}
.dg-scene-label{font-size:.65rem!important;text-align:center;color:var(--dg-muted);margin:5px 0 0!important}
.dg-top-brand-badge{background:linear-gradient(135deg,#087f75,#38aa98)!important}
@media(max-width:760px){.block-container{padding:1rem .8rem 2rem!important}.dg-heading{gap:4px}.dg-heading h1{font-size:1.6rem}.dg-heading p{font-size:.76rem}.dg-eyebrow{font-size:.6rem;letter-spacing:.09em}.dg-scene{transform:scale(.72);transform-origin:right center;width:145px;flex-basis:145px;margin-left:-30px}.dg-scene-label{max-width:140px;margin-left:auto!important}.dg-hero{padding:22px!important;grid-template-columns:1fr!important}.dg-hero-score{border-left:0;border-top:1px solid var(--dg-border);padding:20px 0 0}.dg-hero-score .value{font-size:5.4rem!important}.dg-primary-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.dg-weather-card{padding:14px!important}.dg-weather-value,.dg-weather-card.primary .dg-weather-value{font-size:2.15rem!important}.dg-weather-card::before{float:none;margin-bottom:10px}.dg-insight-grid{grid-template-columns:1fr}.st-key-dg_journey{padding:15px}.dg-heading>div:first-child{min-width:0}.st-key-dg_topbar [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important}.st-key-dg_topbar [data-testid="stColumn"]{min-width:0!important;width:auto!important;flex:1 1 auto!important}.st-key-dg_topbar [data-testid="stColumn"]:first-child{flex:0 0 35px!important}.st-key-dg_topbar [data-testid="stColumn"]:last-child{flex:0 0 72px!important}}
@media(max-width:380px){.dg-heading h1{font-size:1.35rem}.dg-scene{transform:scale(.6);flex-basis:105px;margin-left:-55px}.dg-scene-label{max-width:105px}.st-key-dg_nav_control button{font-size:.68rem!important;padding:.3rem!important}}
@media(max-width:760px){.dg-heading>div:last-child{width:145px;flex:0 0 145px;overflow:hidden}.dg-scene{width:210px;height:126px;transform:scale(.68);transform-origin:top left;margin:0 0 -38px;flex:none}.dg-scene-label{max-width:145px;text-align:center}}
@media(max-width:380px){.dg-heading>div:last-child{width:105px;flex-basis:105px}.dg-scene{transform:scale(.5);margin:0 0 -63px}.dg-scene-label{max-width:105px}.st-key-dg_theme_selector_wrap button{width:27px!important;min-width:27px!important;max-width:27px!important}}
.st-key-dg_insight_0,.st-key-dg_insight_1,.st-key-dg_insight_2,.st-key-dg_insight_3{border:1px solid var(--dg-border);border-left:4px solid var(--accent);border-radius:16px;padding:12px 16px!important;background:var(--dg-card);margin-bottom:10px}
.st-key-dg_insight_0{--accent:#ae7c30}.st-key-dg_insight_1{--accent:#437fba}.st-key-dg_insight_2{--accent:#16897c}.st-key-dg_insight_3{--accent:#8a6baa}
[class*="st-key-dg_insight_"] button{border:0!important;padding:0!important;min-height:28px!important;justify-content:flex-start!important;background:transparent!important;color:var(--accent)!important;box-shadow:none!important}
[class*="st-key-dg_insight_"] button p{font-weight:750;font-size:.94rem}[class*="st-key-dg_insight_"] .dg-insight-text{font-size:.84rem;color:var(--dg-muted);line-height:1.55;margin:0}
.st-key-dg_lower h3{font-size:1.25rem!important;margin-bottom:12px!important}
@media(max-width:760px){.st-key-dg_lower [data-testid="stHorizontalBlock"]{flex-direction:column!important}.st-key-dg_lower [data-testid="stColumn"]{width:100%!important;flex:1 1 100%!important}}
</style>
"""


def phase_at(hour: float) -> tuple[str, str, str]:
    if 5 <= hour < 9:
        return "pagi", "linear-gradient(#f8d5ab,#edf2da)", "#edb468"
    if 9 <= hour < 15:
        return "siang", "linear-gradient(#bce4ef,#e3f3e4)", "#f0c96c"
    if 15 <= hour < 17:
        return "sore", "linear-gradient(#f6cd93,#f7e2b5)", "#eab06f"
    if 17 <= hour < 19:
        return "senja", "linear-gradient(#c0addb,#f0b39c)", "#f6b77b"
    return "malam", "linear-gradient(#293957,#627d98)", "#e4ebf0"


@st.fragment(run_every="60s")
def render_live_heading(weather: str = "", frost: bool = False):
    render_heading(pd.Timestamp.now(tz=features.WIB), weather, frost)


def render_heading(now, weather: str = "", frost: bool = False):
    phase, sky, orb = phase_at(now.hour + now.minute / 60)
    desc = weather.lower()
    condition = "rain" if any(w in desc for w in ("hujan", "rain")) else "mist" if any(w in desc for w in ("kabut", "fog", "mist")) else "cloudy" if any(w in desc for w in ("awan", "cloud", "mendung")) else ""
    if frost:
        condition = "frost"
    night = phase == "malam"
    progress = ((now.hour + now.minute / 60 - (18 if night else 6)) % 24) / 12
    progress = min(1, max(0, progress))
    x = 12 + progress * 110
    y = 42 - math.sin(progress * math.pi) * 31
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    date = f"{days[now.weekday()]}, {now.day} {months[now.month-1]} {now.year} · WIB"
    label = "Ilustrasi potensi frost model" if frost else f"Suasana {phase} · ilustrasi" 
    st.markdown(f'<div class="dg-heading"><div><div class="dg-eyebrow">Pemantauan frost · Dataran Tinggi Dieng</div><h1>Cuaca Dieng, lebih terbaca.</h1><p>{date}</p></div><div><div class="dg-scene {condition} {"night" if night else ""}" role="img" aria-label="{label}" style="--sky:{sky};--orb:{orb};--orb-x:{x:.0f}px;--orb-y:{y:.0f}px"><div class="sky"><div class="orb"></div></div><div class="mountain"></div><div class="mountain front"></div><div class="ground"></div><div class="cloud"></div></div><p class="dg-scene-label">{label}</p></div></div>', unsafe_allow_html=True)


def hourly_series(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    """Last valid observation per completed WIB hour; missing hours stay gaps.

    Right-labelled bins never move an observation into an earlier time. No
    interpolation or forward filling is performed, including missing values.
    """
    if frame.empty or key not in frame or "time" not in frame:
        return pd.DataFrame(columns=[key])
    work = frame[["time", key]].copy()
    def local_time(value):
        try:
            ts = pd.Timestamp(value)
            return ts.tz_localize(features.WIB) if ts.tzinfo is None else ts.tz_convert(features.WIB)
        except (ValueError, TypeError):
            return pd.NaT
    work["time"] = pd.to_datetime(work["time"].map(local_time))
    work[key] = pd.to_numeric(work[key], errors="coerce")
    work.loc[~work[key].map(lambda v: pd.notna(v) and math.isfinite(v)), key] = float("nan")
    work = work.dropna(subset=["time"]).sort_values("time").drop_duplicates("time", keep="last")
    if work.empty:
        return pd.DataFrame(columns=[key])
    # Samples at :00 represent that exact hour; intermediate observations appear
    # at the following completed hour. Discard an unfinished final bin.
    latest = work["time"].max().floor("h")
    result = work.set_index("time").resample("1h", closed="right", label="right").last()
    return result.loc[result.index <= latest]


def hourly_chart(series: pd.DataFrame, key: str, unit: str, label: str) -> str:
    valid = series[key].dropna() if key in series else pd.Series(dtype=float)
    if valid.empty:
        return '<p class="dg-explorer-help">Belum ada data per jam untuk parameter ini.</p>'
    count = len(series)
    width, height, left, top = max(680, count * 66), 300, 55, 38
    plot_w, plot_h = width - 90, 190
    lo, hi = float(valid.min()), float(valid.max())
    pad = max((hi-lo)*.18, 1)
    lo, hi = (0, 100) if unit == "%" and "Probabilitas" in label else (lo-pad, hi+pad)
    parts = [f'<div class="dg-hour-chart"><svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(label)} per jam, {html.escape(unit)}"><title>{html.escape(label)} · WIB · {html.escape(unit)}</title>']
    for i in range(5):
        y = top + plot_h*i/4
        value = hi - (hi-lo)*i/4
        parts.append(f'<line x1="{left}" x2="{width-35}" y1="{y}" y2="{y}"/><text x="{left-8}" y="{y+4}" text-anchor="end">{value:.0f}</text>')
    previous = None
    for i, (ts, row) in enumerate(series.iterrows()):
        x = left + plot_w * i / max(count-1, 1)
        parts.append(f'<text x="{x:.1f}" y="265" text-anchor="middle">{ts:%H:%M}</text>')
        value = row[key]
        if pd.isna(value):
            previous = None
            continue
        y = top + (hi-value)/(hi-lo)*plot_h
        if previous:
            parts.append(f'<path d="M {previous[0]:.1f} {previous[1]:.1f} L {x:.1f} {y:.1f}" fill="none" stroke="var(--dg-blue)" stroke-width="3"/>')
        tip = html.escape(f"{ts:%d/%m %H:%M} WIB · {value:.1f} {unit}")
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="var(--dg-card)" stroke="var(--dg-blue)" stroke-width="3"><title>{tip}</title></circle><text x="{x:.1f}" y="{y-12:.1f}" text-anchor="middle">{value:.1f}</text>')
        previous = x, y
    parts.append('</svg></div>')
    return ''.join(parts)


def render_journey(mh, rh, pred, *, include_models=True):
    options = (list(features.MODEL_VARS) if include_models else []) + list(features.WEATHER_VARS)
    with st.container(key="dg_journey"):
        st.markdown('### Perjalanan prediksi')
        widget_key = "dg_journey_parameter" if include_models else "dg_monitor_parameter"
        default_index = None if widget_key in st.session_state else (3 if include_models else 0)
        label = st.selectbox("Parameter grafik", options, index=default_index, key=widget_key)
        if label is None:
            return
        frame, selected = features._series_frame(mh, rh, [label])
        if label in features.MODEL_VARS and not frame.empty:
            target = pred.get("target_night_date")
            # Do not join probabilities for different target nights.
            if target is not None and "tanggal_target" in rh:
                same_night = rh[rh["tanggal_target"].astype(str).str[:10] == str(target)[:10]]
                frame, selected = features._series_frame(mh, same_night, [label])
        if not frame.empty and selected:
            key, unit = selected[label]
            series = hourly_series(frame, key).tail(13)
            st.markdown(hourly_chart(series, key, unit, label), unsafe_allow_html=True)
            if not series.empty:
                st.caption(f"{series.index.min():%d %b %Y} – {series.index.max():%d %b %Y} · WIB · {unit}")
            st.caption("Titik setiap 1 jam · nilai valid terakhir dalam jam yang berakhir pada label waktu · jam kosong menjadi jeda. Observasi terbaru tetap tersedia di kartu cuaca.")
        else:
            st.info("Riwayat parameter ini belum tersedia.")


def _select_parameter(label):
    st.session_state["dg_journey_parameter"] = label


def render_insights(monitor, pred, result):
    params = (monitor.get("latest_observation") or {}).get("parameters") or {}
    trend = monitor.get("trend_1h") or {}
    delta = features._num(result.get("probability_change"))
    temp, dew = features._num(params.get("tt_air_avg")), features._num(params.get("dew_point_c"))
    spread = None if temp is None or dew is None else temp-dew
    items = [
        ("❄", "Potensi embun beku", "Pembanding rilis belum tersedia." if delta is None else f"Berubah {delta*100:+.1f} poin persentase dari rilis sebelumnya. Potensi model belum berarti kejadian frost teramati.", "#ae7c30"),
        ("♨", "Perubahan suhu", features._trend_note(trend.get("tt_air_avg_change"), "°C") + ". Dibandingkan dengan observasi sekitar satu jam sebelumnya.", "#437fba"),
        ("◇", "Suhu & titik embun", "Titik embun belum dapat dihitung dari data valid." if spread is None else f"Selisih suhu dan titik embun {spread:.1f} °C. Selisih kecil menunjukkan udara mendekati jenuh, bukan bukti frost.", "#16897c"),
        ("≋", "Kondisi angin", features._trend_note(trend.get("ws_avg_change"), "unit AWS") + ". Baca bersama suhu dan kelembapan saat menilai kondisi lapangan.", "#8a6baa"),
    ]
    st.markdown('### Ringkasan lapangan')
    labels = ["Probabilitas Stacked / Final", "Suhu udara", "Titik embun", "Kecepatan angin"]
    for i, (icon, title, text, _) in enumerate(items):
        with st.container(key=f"dg_insight_{i}"):
            st.button(f"{icon}  {title}", key=f"dg_insight_button_{i}", on_click=_select_parameter, args=(labels[i],), help="Tampilkan parameter terkait pada grafik")
            st.markdown(f'<p class="dg-insight-text">{html.escape(text)}</p>', unsafe_allow_html=True)
