#!/usr/bin/env python3
"""Clean Figma-style probability journey panel for DIENGIN.

Presentation only. Reuses the existing release history and chart renderer while
removing the old paired-panel/fixed-height composition.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import app_base as base

PREDICTION_CSS = r"""
<style>
.dg-pred-control-label{
  margin:0 0 .42rem;
  color:#1e2b3f;
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.96rem;
  line-height:1.35;
  font-weight:700;
}
.st-key-clean_prediction_date [data-testid="stSelectbox"]{margin:0!important;}
.st-key-clean_prediction_date [data-baseweb="select"] > div{
  min-height:48px!important;
  border-radius:14px!important;
  border-color:rgba(32,54,82,.14)!important;
  background:#fff!important;
  box-shadow:none!important;
}
.st-key-clean_prediction_date [data-baseweb="select"] span{
  font-size:.96rem!important;
  color:#1e2b3f!important;
}
.dg-pred-summary{
  display:flex;
  justify-content:flex-start;
  align-items:center;
  flex-wrap:wrap;
  gap:.55rem;
  margin:.95rem 0 1rem;
}
.dg-pred-chip{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  min-height:36px;
  padding:.4rem .76rem;
  border:1px solid rgba(32,54,82,.12);
  border-radius:999px;
  background:#f7f9fc;
  color:#526174;
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.92rem;
  line-height:1.2;
}
.dg-pred-chip b{color:#1e2b3f;font-weight:800;margin-left:.32rem;}
.st-key-clean_prediction_chart{
  margin-top:.2rem!important;
}
.st-key-clean_prediction_chart > div{
  background:#fff!important;
  border:1px solid rgba(32,54,82,.12)!important;
  border-radius:22px!important;
  padding:1.1rem 1.2rem .75rem!important;
  box-shadow:0 8px 24px rgba(25,47,78,.035)!important;
}
.st-key-clean_prediction_chart [data-testid="stVegaLiteChart"]{
  margin:0!important;
}
.dg-pred-meta{
  margin:.72rem 0 0;
  color:#6f7d91;
  font-family:"Plus Jakarta Sans",sans-serif;
  font-size:.92rem;
  line-height:1.5;
  text-align:center;
}
.st-key-clean_prediction_details{
  margin-top:.7rem!important;
}
.st-key-clean_prediction_details [data-testid="stExpander"]{
  border:1px solid rgba(32,54,82,.12)!important;
  border-radius:14px!important;
  background:#fff!important;
  overflow:hidden;
}
.st-key-clean_prediction_details [data-testid="stExpander"] summary{
  min-height:46px!important;
  font-size:.94rem!important;
}
@media(max-width:700px){
  .dg-pred-control-label{font-size:.92rem;}
  .st-key-clean_prediction_chart > div{padding:.8rem .65rem .55rem!important;}
  .dg-pred-chip{font-size:.86rem;min-height:34px;padding:.35rem .62rem;}
  .dg-pred-meta{font-size:.86rem;}
}
</style>
"""
base.CSS += PREDICTION_CSS


def _threshold_for_target(nights: pd.DataFrame, pred: dict, target: str):
    if str(pred.get("target_night_date"))[:10] == target:
        return base.probability(pred.get("threshold_stacked"))
    if not nights.empty and "tanggal_target" in nights:
        summary = nights.loc[
            nights["tanggal_target"].astype(str).str[:10] == target
        ]
        if not summary.empty:
            return base.probability(summary.iloc[-1].get("ambang_final"))
    return None


def render_prediction_history(rh, nights, pred, now):
    """Render one date control + one clean probability chart, without duplicate headings."""
    if rh.empty or "tanggal_target" not in rh:
        st.info("Riwayat rilis belum tersedia.")
        return

    dates = sorted(
        rh["tanggal_target"].dropna().astype(str).str[:10].unique(), reverse=True
    )
    if not dates:
        st.info("Tanggal target belum tersedia.")
        return

    st.markdown(
        '<div class="dg-pred-control-label">Tanggal target prediksi</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="clean_prediction_date"):
        target = st.selectbox(
            "Tanggal target prediksi",
            dates,
            format_func=base.date_label,
            key="clean_prediction_target",
            label_visibility="collapsed",
        )

    selected = rh.loc[
        rh["tanggal_target"].astype(str).str[:10] == target
    ].copy()
    threshold = _threshold_for_target(nights, pred, target)

    probs = pd.to_numeric(
        selected.get("stack_prob", pd.Series(dtype=float)), errors="coerce"
    ).dropna()
    valid_probs = probs[(probs >= 0) & (probs <= 1)]
    release_count = int(valid_probs.shape[0])
    peak = float(valid_probs.max()) if not valid_probs.empty else None
    latest = float(valid_probs.iloc[-1]) if not valid_probs.empty else None

    chips = [
        ("Ambang", base.pct(threshold)),
        ("Rilis tersedia", f"{release_count}/11"),
        ("Puncak", base.pct(peak)),
        ("Rilis terakhir", base.pct(latest)),
    ]
    st.markdown(
        '<div class="dg-pred-summary">'
        + "".join(
            f'<span class="dg-pred-chip">{base.esc(label)} <b>{base.esc(value)}</b></span>'
            for label, value in chips
        )
        + '</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="clean_prediction_chart"):
        base.draw_chart(
            selected,
            {"stack_prob": "DIENGIN"},
            "Probabilitas (%)",
            "clean_release_chart",
            True,
            threshold,
            340,
        )

    if not selected.empty:
        start = base.time_label(selected["_time"].min()) if "_time" in selected else "—"
        end = base.time_label(selected["_time"].max()) if "_time" in selected else "—"
    else:
        start, end = "—", "—"

    st.markdown(
        f'<div class="dg-pred-meta">{base.esc(start)} — {base.esc(end)} · '
        'Probabilitas per rilis DIENGIN; garis putus-putus menunjukkan ambang target.</div>',
        unsafe_allow_html=True,
    )

    with st.container(key="clean_prediction_details"):
        with st.expander("Bandingkan model"):
            base.draw_chart(
                selected,
                base.PROB_LABELS,
                "Probabilitas (%)",
                "clean_models_chart",
                True,
            )
            st.caption(
                "ANN, SVM, dan Random Forest adalah model dasar. DIENGIN menampilkan hasil stacking; "
                "nilainya bukan rata-rata sederhana."
            )

        with st.expander("Tabel rilis dan unduhan"):
            table = selected.drop(columns=["_time"], errors="ignore").copy()
            cols = [
                c
                for c in [
                    "waktu_rilis_wib",
                    "stack_prob",
                    "ann_prob",
                    "svm_prob",
                    "rf_prob",
                    "status_data_rilis",
                ]
                if c in table
            ]
            table = table[cols]
            for col in base.PROB_LABELS:
                if col in table:
                    table[col] = (
                        pd.to_numeric(table[col], errors="coerce") * 100
                    ).round(2)
            table = table.rename(
                columns={
                    **{k: v + " (%)" for k, v in base.PROB_LABELS.items()},
                    "waktu_rilis_wib": "Rilis (WIB)",
                    "status_data_rilis": "Status data",
                }
            )
            st.dataframe(table, hide_index=True, width="stretch")
            base.download_csv(selected, f"diengin_rilis_{target}.csv", "clean_release_csv")
            st.caption("CSV mempertahankan probabilitas asli pada skala 0–1.")
