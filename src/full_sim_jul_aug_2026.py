#!/usr/bin/env python3
"""Full DIENGIN simulation for July-August 2026.

Workflow:
1) Download AWS STA2285 historical observations first (chunked <24 h per BMKG API rule).
2) Run the frozen DIENGIN v1.1 pipeline for every target morning 2026-07-01..2026-08-31.
3) Evaluate two label scenarios:
   - scrape17: the 17 Telegram/social-scraped frost dates currently documented.
   - expanded21: scrape17 + user-confirmed 23, 26, 27, 31 Aug 2026.
4) Export nightly, release-level, QC/completeness, confusion-profile, FN-vs-TP,
   and TP-vs-TN boundary diagnostics.

No model retraining and no threshold tuning are performed here.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

import download_aws as dl
import predict as pred

WIB = ZoneInfo("Asia/Jakarta")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "full_sim_jul_aug_2026"
DATA_DIR = ROOT / "data" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

TARGET_START = pd.Timestamp("2026-07-01").date()
TARGET_END = pd.Timestamp("2026-08-31").date()
EXPECTED_NIGHT_ROWS = 72

SCRAPE17 = {
    pd.Timestamp(x).date() for x in [
        "2026-07-10", "2026-07-11", "2026-07-12",
        "2026-07-15", "2026-07-16", "2026-07-17", "2026-07-18", "2026-07-19",
        "2026-07-22", "2026-07-25", "2026-07-26", "2026-07-27",
        "2026-08-06", "2026-08-07", "2026-08-12", "2026-08-13", "2026-08-18",
    ]
}
USER_CONFIRMED_EXTRA = {
    pd.Timestamp(x).date() for x in [
        "2026-08-23", "2026-08-26", "2026-08-27", "2026-08-31"
    ]
}
EXPANDED21 = SCRAPE17 | USER_CONFIRMED_EXTRA

KEY_FEATURES = [
    "tmin_now", "tmin_min_1h", "temp_drop_1h", "tmin_anom_month",
    "rh_mean_1h", "dp_depress", "dpdep_anom_month",
    "ws_mean_1h", "ws_max_1h", "rr_10min", "rr_sum_3h", "is_rain_now",
]
BASE_PROBS = ["ann_prob", "svm_prob", "rf_prob"]
RAW_PARAMS = ["tt_air_avg", "tt_air_min", "rh_avg", "ws_avg", "rr", "pp_air"]


def safe_float(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except Exception:
        return np.nan


def download_period() -> pd.DataFrame:
    # Warm-up starts at 15 WIB on the preceding day, enough for 3-h rain and 1-h features.
    start_wib = datetime.combine(TARGET_START - timedelta(days=1), time(15, 0), tzinfo=WIB)
    end_wib = datetime.combine(TARGET_END + timedelta(days=1), time(8, 0), tzinfo=WIB)
    start_utc = start_wib.astimezone(timezone.utc)
    end_utc = end_wib.astimezone(timezone.utc)

    session = requests.Session()
    session.headers.update({"User-Agent": "DIENGIN/1.0 full Jul-Aug 2026 simulation"})
    token = dl.get_token(session)

    frames = []
    chunk_audit = []
    cursor = start_utc
    chunk_id = 0
    while cursor < end_utc:
        chunk_end = min(cursor + timedelta(hours=23, minutes=50), end_utc)
        payload = dl.request_data(session, token, cursor, chunk_end)
        records = dl.flatten_payload(payload)
        frame = dl.normalize(records)
        frames.append(frame)
        chunk_audit.append({
            "chunk": chunk_id,
            "start_utc": cursor.isoformat(),
            "end_utc": chunk_end.isoformat(),
            "rows": int(len(frame)),
        })
        chunk_id += 1
        # keep boundary overlap; duplicates are removed later
        cursor = chunk_end

    aws = pd.concat(frames, ignore_index=True)
    aws = (
        aws.sort_values("datetime_utc")
        .drop_duplicates(subset=["datetime_utc"], keep="last")
        .reset_index(drop=True)
    )
    aws.to_csv(DATA_DIR / "aws_sta2285_2026-06-30_to_2026-09-01.csv", index=False)
    pd.DataFrame(chunk_audit).to_csv(OUT / "download_chunks.csv", index=False)
    return aws


def add_night_date_for_raw(aws: pd.DataFrame) -> pd.DataFrame:
    q = aws.copy()
    q["time_wib"] = pd.to_datetime(q["datetime_wib"], utc=True, errors="coerce").dt.tz_convert("Asia/Jakarta")
    q = pred.assign_night_date(q)
    return q


def completeness_by_night(raw: pd.DataFrame, model_data: pd.DataFrame) -> pd.DataFrame:
    target_dates = pd.date_range(TARGET_START, TARGET_END, freq="D").date
    rows = []
    raw_night = raw[raw["is_night"].eq(1)].copy()
    model_night = model_data[model_data["is_night"].eq(1)].copy()

    for d in target_dates:
        r = raw_night[pd.Series(raw_night["night_date"], index=raw_night.index).eq(d)]
        m = model_night[pd.Series(model_night["night_date"], index=model_night.index).eq(d)]
        row = {
            "target_date": pd.Timestamp(d),
            "raw_night_rows": int(len(r)),
            "time_completeness": min(1.0, len(r) / EXPECTED_NIGHT_ROWS),
            "rh_adapter_invalid_count": int(m.get("rh_adapter_invalid", pd.Series(False, index=m.index)).fillna(False).sum()),
        }
        for p in RAW_PARAMS:
            if p in r:
                row[f"{p}_available_frac"] = float(pd.to_numeric(r[p], errors="coerce").notna().mean()) if len(r) else np.nan
            fc = f"{p}_flag"
            if fc in r:
                f = pd.to_numeric(r[fc], errors="coerce")
                row[f"{p}_flag0_frac"] = float(f.eq(0).mean()) if len(r) else np.nan
                row[f"{p}_flag1_count"] = int(f.eq(1).sum()) if len(r) else 0
        # Post-adapter/model-QC availability
        for p in ["tt_air_avg", "tt_air_min", "rh_avg", "ws_avg", "rr", "dew_point_c"]:
            if p in m:
                row[f"postqc_{p}_available_frac"] = float(pd.to_numeric(m[p], errors="coerce").notna().mean()) if len(m) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def confusion(obs, predv):
    if pd.isna(predv):
        return "NA"
    obs = int(obs)
    predv = int(predv)
    if obs == 1 and predv == 1:
        return "TP"
    if obs == 1 and predv == 0:
        return "FN"
    if obs == 0 and predv == 1:
        return "FP"
    return "TN"


def classification_metrics(df: pd.DataFrame, obs_col: str, pred_col: str) -> dict:
    d = df[[obs_col, pred_col]].dropna().copy()
    y = d[obs_col].astype(int)
    p = d[pred_col].astype(int)
    tp = int(((y == 1) & (p == 1)).sum())
    fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum())
    tn = int(((y == 0) & (p == 0)).sum())
    def div(a, b):
        return a / b if b else np.nan
    return {
        "n": len(d), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "POD": div(tp, tp + fn), "FAR": div(fp, tp + fp),
        "CSI": div(tp, tp + fp + fn), "precision": div(tp, tp + fp),
        "F1": div(2 * tp, 2 * tp + fp + fn), "specificity": div(tn, tn + fp),
        "bias": div(tp + fp, tp + fn),
    }


def cliffs_delta(a, b):
    a = np.asarray(pd.Series(a).dropna(), dtype=float)
    b = np.asarray(pd.Series(b).dropna(), dtype=float)
    if len(a) == 0 or len(b) == 0:
        return np.nan
    gt = 0
    lt = 0
    for x in a:
        gt += int(np.sum(x > b))
        lt += int(np.sum(x < b))
    return (gt - lt) / (len(a) * len(b))


def profile_table(df: pd.DataFrame, group_col: str, features: list[str]) -> pd.DataFrame:
    rows = []
    for g, sub in df.groupby(group_col):
        for f in features:
            if f not in sub:
                continue
            s = pd.to_numeric(sub[f], errors="coerce").dropna()
            if s.empty:
                continue
            rows.append({
                "group": g, "feature": f, "n": int(len(s)),
                "min": float(s.min()), "q10": float(s.quantile(0.10)),
                "q25": float(s.quantile(0.25)), "median": float(s.median()),
                "q75": float(s.quantile(0.75)), "q90": float(s.quantile(0.90)),
                "max": float(s.max()), "mean": float(s.mean()), "std": float(s.std(ddof=1)) if len(s) > 1 else np.nan,
            })
    return pd.DataFrame(rows)


def boundary_table(df: pd.DataFrame, class_col: str, features: list[str]) -> pd.DataFrame:
    tp = df[df[class_col].eq("TP")]
    tn = df[df[class_col].eq("TN")]
    rows = []
    for f in features:
        if f not in df:
            continue
        a = pd.to_numeric(tp[f], errors="coerce").dropna()
        b = pd.to_numeric(tn[f], errors="coerce").dropna()
        if a.empty or b.empty:
            continue
        tp10, tp25, tp50, tp75, tp90 = [a.quantile(q) for q in (0.10, 0.25, 0.50, 0.75, 0.90)]
        tn10, tn25, tn50, tn75, tn90 = [b.quantile(q) for q in (0.10, 0.25, 0.50, 0.75, 0.90)]
        overlap_10_90 = max(0.0, min(tp90, tn90) - max(tp10, tn10))
        full_span = max(tp90, tn90) - min(tp10, tn10)
        overlap_ratio = overlap_10_90 / full_span if full_span > 0 else 1.0
        rows.append({
            "feature": f, "n_TP": len(a), "n_TN": len(b),
            "TP_q10": tp10, "TP_q25": tp25, "TP_median": tp50, "TP_q75": tp75, "TP_q90": tp90,
            "TN_q10": tn10, "TN_q25": tn25, "TN_median": tn50, "TN_q75": tn75, "TN_q90": tn90,
            "median_diff_TP_minus_TN": tp50 - tn50,
            "cliffs_delta_TP_vs_TN": cliffs_delta(a, b),
            "q10_q90_overlap_ratio": overlap_ratio,
            "clean_IQR_separation": bool(tp75 < tn25 or tn75 < tp25),
        })
    return pd.DataFrame(rows).sort_values("q10_q90_overlap_ratio")


def main() -> int:
    print("[1/6] Downloading AWS historical data...")
    aws = download_period()
    print("Downloaded rows:", len(aws))

    csv_path = DATA_DIR / "aws_sta2285_2026-06-30_to_2026-09-01.csv"
    pred.DATA_PATH = csv_path
    pipeline = pred.load_pipeline()
    threshold = float(pipeline["threshold"])
    config = pipeline["config"]
    feature_cols = list(config["feature_cols"])
    base_thr = config["frozen_night_thresholds"]

    print("[2/6] Running preprocessing/QC and 16-feature construction...")
    model_data, adapter_audit = pred.load_operational_aws()
    model_data, model_audit = pred.apply_model_qc(model_data, config["qc_limits"])
    model_data = pred.assign_night_date(model_data)
    featured = pred.build_features_10min(model_data, config.get("rr_mode", "cumulative"))
    featured = pred.apply_frozen_monthly_anomaly(featured, config["monthly_anomaly_reference"])

    mask = (
        featured["is_night"].eq(1)
        & pd.Series(featured["night_date"]).ge(TARGET_START)
        & pd.Series(featured["night_date"]).le(TARGET_END)
    )
    night_data = featured[mask].copy().reset_index(drop=True)

    print("[3/6] Predicting every 10 min and every release 21-07 WIB...")
    raw_matrix, imputed, scaled = pred.prepare_model_matrix(night_data, config, pipeline["scaler"])
    prediction_10min = pred.predict_10min(night_data, scaled, pipeline)
    prediction_10min["feature_missing_count"] = raw_matrix.isna().sum(axis=1).to_numpy()
    prediction_10min["feature_missing_frac"] = prediction_10min["feature_missing_count"] / len(feature_cols)
    prediction_10min["feature_missing_names"] = raw_matrix.apply(lambda r: ";".join(r.index[r.isna()].tolist()), axis=1).to_numpy()
    prediction_10min.to_csv(OUT / "prediction_10min_all.csv", index=False)

    simulated_now = pd.Timestamp(datetime.combine(TARGET_END + timedelta(days=1), time(8, 0), tzinfo=WIB))
    release = pred.build_release_table(prediction_10min, pipeline["release_hours"], simulated_now)

    # Attach source-row meteorology, quality flags, and raw-feature missingness.
    source_cols = list(dict.fromkeys(
        KEY_FEATURES + RAW_PARAMS + [f"{p}_flag" for p in RAW_PARAMS]
        + ["dew_point_c", "rh_adapter_invalid", "feature_missing_count", "feature_missing_frac", "feature_missing_names"]
    ))
    source_cols = [c for c in source_cols if c in prediction_10min.columns]
    src = prediction_10min[source_cols].copy()
    src["source_row_index"] = src.index.astype(int)
    release = release.merge(src, on="source_row_index", how="left")
    release = pred.add_stacked_probability(release, pipeline["meta"], threshold)
    release["base_prob_range"] = release[BASE_PROBS].max(axis=1) - release[BASE_PROBS].min(axis=1)
    release["base_prob_std"] = release[BASE_PROBS].std(axis=1)
    release["ann_above_own_thr"] = release["ann_prob"] >= float(base_thr["ANN"])
    release["svm_above_own_thr"] = release["svm_prob"] >= float(base_thr["SVM"])
    release["rf_above_own_thr"] = release["rf_prob"] >= float(base_thr["RF"])
    release["base_models_above_own_thr"] = release[["ann_above_own_thr", "svm_above_own_thr", "rf_above_own_thr"]].sum(axis=1)
    release.to_csv(OUT / "release_all.csv", index=False)

    nightly = pred.aggregate_night(release, threshold)
    nightly = nightly.rename(columns={"tanggal_target": "target_date", "prediksi_malam": "predicted_frost"})
    nightly["target_date"] = pd.to_datetime(nightly["target_date"])

    # Pmax release and whole-night base maxima.
    pmax_rows = []
    for d, g in release.groupby("tanggal_target"):
        valid = g.dropna(subset=["stack_prob"]).copy()
        if valid.empty:
            continue
        ix = valid["stack_prob"].idxmax()
        row = valid.loc[ix].copy()
        out = {"target_date": pd.Timestamp(d)}
        for c in BASE_PROBS + ["stack_prob", "jam_rilis_wib", "base_prob_range", "base_prob_std",
                               "feature_missing_count", "feature_missing_frac", "feature_missing_names",
                               "base_models_above_own_thr"] + KEY_FEATURES:
            if c in row.index:
                out[f"pmax_{c}"] = row[c]
        out["night_ann_max"] = safe_float(valid["ann_prob"].max())
        out["night_svm_max"] = safe_float(valid["svm_prob"].max())
        out["night_rf_max"] = safe_float(valid["rf_prob"].max())
        out["releases_above_stack_thr"] = int((valid["stack_prob"] >= threshold).sum())
        out["max_base_models_above_own_thr"] = int(valid["base_models_above_own_thr"].max())
        pmax_rows.append(out)
    pmax_df = pd.DataFrame(pmax_rows)
    nightly = nightly.merge(pmax_df, on="target_date", how="left")

    rawq = add_night_date_for_raw(aws)
    completeness = completeness_by_night(rawq, model_data)
    nightly = nightly.merge(completeness, on="target_date", how="left")

    # Labels and confusion under both scenarios.
    date_obj = nightly["target_date"].dt.date
    nightly["observed_scrape17"] = date_obj.isin(SCRAPE17).astype(int)
    nightly["observed_expanded21"] = date_obj.isin(EXPANDED21).astype(int)
    nightly["label_source"] = np.select(
        [date_obj.isin(SCRAPE17), date_obj.isin(USER_CONFIRMED_EXTRA)],
        ["scrape17", "user_confirmed_extra"],
        default="unlabeled_nonfrost",
    )
    nightly["confusion_scrape17"] = [confusion(o, p) for o, p in zip(nightly["observed_scrape17"], nightly["predicted_frost"])]
    nightly["confusion_expanded21"] = [confusion(o, p) for o, p in zip(nightly["observed_expanded21"], nightly["predicted_frost"])]
    nightly["stack_margin"] = nightly["probabilitas_maksimum"] - threshold

    # Simple diagnostic tags for expanded-scenario FNs (descriptive, not causal proof).
    nightly["fn_diagnostic_tags"] = ""
    for idx, row in nightly.iterrows():
        if row["confusion_expanded21"] != "FN":
            continue
        tags = []
        if safe_float(row.get("probabilitas_maksimum")) >= 0.20:
            tags.append("near_threshold")
        if safe_float(row.get("pmax_base_prob_range")) >= 0.50:
            tags.append("high_model_disagreement")
        if safe_float(row.get("night_ann_max")) >= float(base_thr["ANN"]):
            tags.append("ANN_strong_but_stack_suppressed")
        if safe_float(row.get("night_rf_max")) < float(base_thr["RF"]):
            tags.append("RF_never_above_own_threshold")
        if safe_float(row.get("night_svm_max")) < float(base_thr["SVM"]):
            tags.append("SVM_never_above_own_threshold")
        if safe_float(row.get("tt_air_min_flag0_frac")) < 0.80:
            tags.append("low_Tmin_flag0_completeness")
        if safe_float(row.get("tt_air_avg_flag0_frac")) < 0.80:
            tags.append("low_Tavg_flag0_completeness")
        if safe_float(row.get("rh_avg_flag0_frac")) < 0.80:
            tags.append("low_RH_flag0_completeness")
        if safe_float(row.get("pmax_feature_missing_frac")) > 0:
            tags.append("feature_imputation_at_pmax")
        nightly.at[idx, "fn_diagnostic_tags"] = ";".join(tags) if tags else "no_obvious_quality_issue"

    nightly.to_csv(OUT / "nightly_results.csv", index=False)

    print("[4/6] Building verification metrics and confusion diagnostics...")
    metrics = {
        "threshold_stacked": threshold,
        "scrape17": classification_metrics(nightly, "observed_scrape17", "predicted_frost"),
        "expanded21": classification_metrics(nightly, "observed_expanded21", "predicted_frost"),
        "notes": {
            "scrape17_dates": sorted(str(x) for x in SCRAPE17),
            "user_confirmed_extra": sorted(str(x) for x in USER_CONFIRMED_EXTRA),
            "nonfrost_definition": "All other Jul-Aug nights are treated as non-frost only relative to the current event inventory; undocumented frost may exist.",
        },
        "adapter_audit": adapter_audit,
        "model_qc_audit": model_audit,
    }
    (OUT / "verification_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    analysis_features = [
        "probabilitas_maksimum", "stack_margin", "night_ann_max", "night_svm_max", "night_rf_max",
        "pmax_ann_prob", "pmax_svm_prob", "pmax_rf_prob", "pmax_base_prob_range", "pmax_feature_missing_frac",
        "time_completeness", "tt_air_min_flag0_frac", "tt_air_avg_flag0_frac", "rh_avg_flag0_frac",
        "rh_adapter_invalid_count",
    ] + [f"pmax_{f}" for f in KEY_FEATURES]

    profiles = profile_table(nightly, "confusion_expanded21", analysis_features)
    profiles.to_csv(OUT / "confusion_profiles_expanded21.csv", index=False)

    fn = nightly[nightly["confusion_expanded21"].eq("FN")]
    tp = nightly[nightly["confusion_expanded21"].eq("TP")]
    effect_rows = []
    for f in analysis_features:
        if f not in nightly:
            continue
        a = pd.to_numeric(fn[f], errors="coerce").dropna()
        b = pd.to_numeric(tp[f], errors="coerce").dropna()
        if a.empty or b.empty:
            continue
        effect_rows.append({
            "feature": f, "n_FN": len(a), "n_TP": len(b),
            "FN_median": float(a.median()), "TP_median": float(b.median()),
            "FN_minus_TP_median": float(a.median() - b.median()),
            "cliffs_delta_FN_vs_TP": cliffs_delta(a, b),
            "abs_cliffs_delta": abs(cliffs_delta(a, b)),
        })
    effects = pd.DataFrame(effect_rows).sort_values("abs_cliffs_delta", ascending=False)
    effects.to_csv(OUT / "fn_vs_tp_effects.csv", index=False)

    boundaries = boundary_table(nightly, "confusion_expanded21", analysis_features)
    boundaries.to_csv(OUT / "tp_tn_boundaries.csv", index=False)

    fn_cols = [
        "target_date", "probabilitas_maksimum", "jam_probabilitas_maksimum_wib", "stack_margin",
        "night_ann_max", "night_svm_max", "night_rf_max",
        "pmax_ann_prob", "pmax_svm_prob", "pmax_rf_prob", "pmax_base_prob_range",
        "pmax_feature_missing_frac", "pmax_feature_missing_names",
        "tt_air_min_flag0_frac", "tt_air_avg_flag0_frac", "rh_avg_flag0_frac",
        "rh_adapter_invalid_count", "time_completeness", "fn_diagnostic_tags",
    ] + [f"pmax_{f}" for f in KEY_FEATURES]
    fn[[c for c in fn_cols if c in fn.columns]].to_csv(OUT / "false_negatives_map.csv", index=False)

    print("[5/6] Writing summary tables...")
    # Base-model pattern at pmax by confusion group.
    summary = {
        "n_target_nights": int(len(nightly)),
        "threshold": threshold,
        "metrics_scrape17": metrics["scrape17"],
        "metrics_expanded21": metrics["expanded21"],
        "FN_dates_expanded21": [d.strftime("%Y-%m-%d") for d in nightly.loc[nightly["confusion_expanded21"].eq("FN"), "target_date"]],
        "FP_dates_expanded21": [d.strftime("%Y-%m-%d") for d in nightly.loc[nightly["confusion_expanded21"].eq("FP"), "target_date"]],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("[6/6] Done")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
