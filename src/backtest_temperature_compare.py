#!/usr/bin/env python3
"""Experimental DIENGIN temperature-feature compatibility backtest.

Compares two feature modes for one historical frost morning:
1) current
   - exact operational DIENGIN temperature features.
2) tmin_fallback_tavg_trend
   - tmin_now uses AWS tt_air_min when available, otherwise tt_air_avg.
   - tmin_min_1h uses the effective Tmin above.
   - temp_drop_1h uses tt_air_avg change over ~60 minutes, falling back to
     effective Tmin only when tt_air_avg is missing.
   - tmin_anom_month uses the effective Tmin.

This script NEVER retrains models and does not overwrite operational outputs.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

import download_aws as dl
import predict as pred

WIB = ZoneInfo("Asia/Jakarta")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODES = ("current", "tmin_fallback_tavg_trend")
LAG_TOLERANCE = pd.Timedelta(minutes=11)


def json_default(value):
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def safe_float(value):
    return None if pd.isna(value) else float(value)


def robust_one_hour_lag(time_series, value_series):
    """Return value near exactly T-60 min and diagnostic lag error."""
    left = pd.DataFrame({
        "row_id": np.arange(len(time_series), dtype=int),
        "time_wib": pd.Series(time_series).reset_index(drop=True),
        "value_now": pd.to_numeric(value_series, errors="coerce").reset_index(drop=True),
    })
    left["target_time"] = left["time_wib"] - pd.Timedelta(hours=1)

    right = pd.DataFrame({
        "past_time": pd.Series(time_series).reset_index(drop=True),
        "value_past": pd.to_numeric(value_series, errors="coerce").reset_index(drop=True),
    }).dropna(subset=["past_time"]).sort_values("past_time")

    matched = pd.merge_asof(
        left.sort_values("target_time"),
        right,
        left_on="target_time",
        right_on="past_time",
        direction="nearest",
        tolerance=LAG_TOLERANCE,
    ).sort_values("row_id")

    lag_error_minutes = (
        (matched["past_time"] - matched["target_time"])
        .dt.total_seconds()
        .abs()
        .div(60.0)
    )
    return (
        matched["value_past"].reset_index(drop=True),
        lag_error_minutes.reset_index(drop=True),
    )


def build_features_mode(data, config, mode):
    featured = pred.build_features_10min(
        data, config.get("rr_mode", "cumulative")
    )

    if mode == "current":
        featured = pred.apply_frozen_monthly_anomaly(
            featured, config["monthly_anomaly_reference"]
        )
        featured["temperature_feature_mode"] = mode
        featured["tmin_source"] = np.where(
            pd.to_numeric(featured["tt_air_min"], errors="coerce").notna(),
            "tt_air_min",
            "missing",
        )
        featured["temp_trend_source"] = "tt_air_min_shift6"
        featured["tmin_change_1h_diag"] = (
            pd.to_numeric(featured["tt_air_min"], errors="coerce").shift(6)
            - pd.to_numeric(featured["tt_air_min"], errors="coerce")
        )
        featured["temp_drop_lag_error_minutes"] = np.where(
            featured["temp_drop_1h"].notna(), 0.0, np.nan
        )
        return featured

    if mode != "tmin_fallback_tavg_trend":
        raise ValueError(f"Mode temperatur tidak dikenal: {mode}")

    work = data.copy().sort_values("time_wib").reset_index(drop=True)
    tmin_raw = pd.to_numeric(work["tt_air_min"], errors="coerce")
    tavg_raw = pd.to_numeric(work["tt_air_avg"], errors="coerce")

    # User-requested hierarchy: trust AWS minimum when present;
    # use ordinary air temperature only as a fallback when Tmin is missing.
    tmin_effective = tmin_raw.combine_first(tavg_raw)
    temp_trend = tavg_raw.combine_first(tmin_effective)

    work_indexed = work.set_index("time_wib")
    effective_indexed = pd.Series(
        tmin_effective.to_numpy(),
        index=work_indexed.index,
        dtype=float,
    )
    tmin_min_1h = (
        effective_indexed.rolling("60min", min_periods=1).min().reset_index(drop=True)
    )

    temp_past, temp_lag_error = robust_one_hour_lag(
        work["time_wib"], temp_trend
    )
    tmin_past, _ = robust_one_hour_lag(
        work["time_wib"], tmin_effective
    )

    # Cooling is positive when the current air temperature is lower than ~1h ago.
    temp_drop_1h = temp_past - temp_trend.reset_index(drop=True)
    tmin_change_diag = tmin_past - tmin_effective.reset_index(drop=True)

    # build_features_10min preserves row/time ordering after sorting.
    featured = featured.sort_values("time_wib").reset_index(drop=True)
    featured["tmin_now"] = tmin_effective.reset_index(drop=True)
    featured["tmin_min_1h"] = tmin_min_1h
    featured["temp_drop_1h"] = temp_drop_1h
    featured["tmin_change_1h_diag"] = tmin_change_diag
    featured["temp_drop_lag_error_minutes"] = temp_lag_error

    tmin_ref = pred.normalize_month_reference(
        config["monthly_anomaly_reference"]["tt_air_min_monthly_median_train"]
    )
    dp_ref = pred.normalize_month_reference(
        config["monthly_anomaly_reference"]["dp_depress_monthly_median_train"]
    )
    month = featured["time_wib"].dt.month
    featured["tmin_anom_month"] = (
        featured["tmin_now"] - month.map(tmin_ref)
    )
    featured["dpdep_anom_month"] = (
        featured["dp_depress"] - month.map(dp_ref)
    )

    featured["temperature_feature_mode"] = mode
    featured["tmin_source"] = np.where(
        tmin_raw.notna(),
        "tt_air_min",
        np.where(tavg_raw.notna(), "tt_air_avg_fallback", "missing"),
    )
    featured["temp_trend_source"] = np.where(
        tavg_raw.notna(), "tt_air_avg", "tmin_effective_fallback"
    )
    return featured


def release_feature_table(release, prediction_10min, feature_cols):
    rows = []
    if release.empty:
        return pd.DataFrame()

    extra = [
        "tt_air_avg", "tt_air_min", "rh_avg", "ws_avg",
        "tmin_change_1h_diag", "temp_drop_lag_error_minutes",
        "temperature_feature_mode", "tmin_source", "temp_trend_source",
    ]

    for _, rel in release.iterrows():
        row = rel.drop(labels=["_urutan_rilis"], errors="ignore").to_dict()
        idx = int(rel["source_row_index"])
        src = prediction_10min.iloc[idx]
        for col in list(feature_cols) + extra:
            if col in src.index:
                row[col] = src[col]
        rows.append(row)

    return pd.DataFrame(rows)


def run_mode(data, pipeline, target_date, mode, root_out):
    featured = build_features_mode(data, pipeline["config"], mode)

    night_data = featured[
        featured["is_night"].eq(1)
        & pd.Series(featured["night_date"]).eq(target_date)
    ].copy().reset_index(drop=True)

    if night_data.empty:
        raise RuntimeError(
            f"Tidak ada data malam target {target_date.isoformat()} mode={mode}."
        )

    raw_matrix, imputed_features, scaled = pred.prepare_model_matrix(
        night_data, pipeline["config"], pipeline["scaler"]
    )
    prediction_10min = pred.predict_10min(night_data, scaled, pipeline)

    simulated_now = pd.Timestamp(
        datetime.combine(target_date, time(8, 0), tzinfo=WIB)
    )
    release = pred.build_release_table(
        prediction_10min, pipeline["release_hours"], simulated_now
    )
    release = pred.add_stacked_probability(
        release, pipeline["meta"], pipeline["threshold"]
    )
    night_summary = pred.aggregate_night(release, pipeline["threshold"])

    mode_out = root_out / mode
    mode_out.mkdir(parents=True, exist_ok=True)

    release_save = release.drop(columns=["_urutan_rilis"], errors="ignore")
    release_save.to_csv(mode_out / "release_probabilities.csv", index=False)
    night_summary.to_csv(mode_out / "night_summary.csv", index=False)
    prediction_10min.to_csv(mode_out / "prediction_10min.csv", index=False)
    raw_matrix.to_csv(mode_out / "model_input_raw.csv", index=False)
    imputed_features.to_csv(mode_out / "model_input_imputed.csv", index=False)

    release_diag = release_feature_table(
        release, prediction_10min, pipeline["feature_cols"]
    )
    release_diag.to_csv(mode_out / "release_features.csv", index=False)

    summary_row = night_summary.iloc[-1] if not night_summary.empty else None
    valid = release.dropna(subset=["stack_prob"]).copy()
    exceed = valid[valid["stack_prob"] >= pipeline["threshold"]]
    first_exceed = int(exceed.iloc[0]["jam_rilis_wib"]) if not exceed.empty else None

    base_max = {}
    base_max_hours = {}
    for col in pred.BASE_PROB_COLS:
        if valid.empty or valid[col].dropna().empty:
            base_max[col] = None
            base_max_hours[col] = None
            continue
        idx = valid[col].idxmax()
        base_max[col] = float(valid.loc[idx, col])
        base_max_hours[col] = int(valid.loc[idx, "jam_rilis_wib"])

    feature_missing = raw_matrix.isna().sum()
    imputed_cells = int(raw_matrix.isna().sum().sum())

    result = {
        "target_date": target_date.isoformat(),
        "observed_frost": int(os.getenv("BACKTEST_OBSERVED_FROST", "1")),
        "temperature_feature_mode": mode,
        "threshold_stacked": float(pipeline["threshold"]),
        "night_rows": int(len(night_data)),
        "releases_valid": int(len(valid)),
        "probability_max": (
            safe_float(summary_row["probabilitas_maksimum"])
            if summary_row is not None else None
        ),
        "probability_max_hour_wib": (
            int(summary_row["jam_probabilitas_maksimum_wib"])
            if summary_row is not None
            and pd.notna(summary_row["jam_probabilitas_maksimum_wib"])
            else None
        ),
        "first_threshold_exceed_hour_wib": first_exceed,
        "predicted_frost": (
            int(summary_row["prediksi_malam"])
            if summary_row is not None and pd.notna(summary_row["prediksi_malam"])
            else None
        ),
        "ann_probability_max": base_max.get("ann_prob"),
        "ann_probability_max_hour_wib": base_max_hours.get("ann_prob"),
        "svm_probability_max": base_max.get("svm_prob"),
        "svm_probability_max_hour_wib": base_max_hours.get("svm_prob"),
        "rf_probability_max": base_max.get("rf_prob"),
        "rf_probability_max_hour_wib": base_max_hours.get("rf_prob"),
        "tmin_min_c": safe_float(pd.to_numeric(night_data["tmin_now"], errors="coerce").min()),
        "temp_drop_1h_max_c": safe_float(pd.to_numeric(night_data["temp_drop_1h"], errors="coerce").max()),
        "temp_drop_1h_min_c": safe_float(pd.to_numeric(night_data["temp_drop_1h"], errors="coerce").min()),
        "tmin_fallback_rows": int((night_data["tmin_source"] == "tt_air_avg_fallback").sum()),
        "imputed_model_cells": imputed_cells,
        "missing_by_feature": {k: int(v) for k, v in feature_missing.items()},
    }
    obs = result["observed_frost"]
    pred_cls = result["predicted_frost"]
    if pred_cls is None:
        result["verification"] = "NO_VALID_PREDICTION"
    elif obs == 1:
        result["verification"] = "HIT" if pred_cls == 1 else "MISS"
    else:
        result["verification"] = "CORRECT_NEGATIVE" if pred_cls == 0 else "FALSE_ALARM"

    (mode_out / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )
    return result


def main() -> int:
    target_str = os.getenv("BACKTEST_TARGET_DATE", "2026-09-15").strip()
    target_date = pd.Timestamp(target_str).date()

    start_wib = datetime.combine(
        target_date - pd.Timedelta(days=1), time(15, 0), tzinfo=WIB
    )
    end_wib = datetime.combine(target_date, time(8, 0), tzinfo=WIB)
    start_utc = start_wib.astimezone(timezone.utc)
    end_utc = end_wib.astimezone(timezone.utc)

    root_out = PROJECT_ROOT / "output" / f"temperature_compare_{target_date.isoformat()}"
    root_out.mkdir(parents=True, exist_ok=True)
    data_dir = PROJECT_ROOT / "data" / "backtest"
    data_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "DIENGIN/1.0 temperature compatibility backtest"})
    token = dl.get_token(session)
    payload = dl.request_data(session, token, start_utc, end_utc)

    (root_out / "aws_raw.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    records = dl.flatten_payload(payload)
    aws = dl.normalize(records)
    aws_csv = data_dir / f"aws_{target_date.isoformat()}.csv"
    aws.to_csv(aws_csv, index=False)

    pred.DATA_PATH = aws_csv
    pipeline = pred.load_pipeline()

    data, adapter_audit = pred.load_operational_aws()
    data, model_audit = pred.apply_model_qc(
        data, pipeline["config"]["qc_limits"]
    )
    pd.DataFrame(adapter_audit + model_audit).to_csv(
        root_out / "qc_audit.csv", index=False
    )
    data = pred.assign_night_date(data)

    results = [
        run_mode(data, pipeline, target_date, mode, root_out)
        for mode in MODES
    ]

    compare = pd.DataFrame(results)
    compare.to_csv(root_out / "comparison.csv", index=False)

    current = results[0]
    corrected = results[1]
    delta = {
        "target_date": target_date.isoformat(),
        "current_stack_pmax": current["probability_max"],
        "corrected_stack_pmax": corrected["probability_max"],
        "delta_stack_pmax": (
            corrected["probability_max"] - current["probability_max"]
            if current["probability_max"] is not None
            and corrected["probability_max"] is not None
            else None
        ),
        "current_prediction": current["predicted_frost"],
        "corrected_prediction": corrected["predicted_frost"],
        "current_verification": current["verification"],
        "corrected_verification": corrected["verification"],
        "current_ann_pmax": current["ann_probability_max"],
        "corrected_ann_pmax": corrected["ann_probability_max"],
        "current_svm_pmax": current["svm_probability_max"],
        "corrected_svm_pmax": corrected["svm_probability_max"],
        "current_rf_pmax": current["rf_probability_max"],
        "corrected_rf_pmax": corrected["rf_probability_max"],
        "corrected_tmin_fallback_rows": corrected["tmin_fallback_rows"],
    }
    (root_out / "comparison_delta.json").write_text(
        json.dumps(delta, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )

    print("======================================")
    print(" DIENGIN TEMPERATURE COMPATIBILITY TEST")
    print("======================================")
    print("Target:", target_date.isoformat())
    print("AWS rows:", len(aws))
    print("Threshold:", f"{pipeline['threshold']:.6f}")
    for result in results:
        print(
            result["temperature_feature_mode"],
            "| pmax=", result["probability_max"],
            "| pred=", result["predicted_frost"],
            "|", result["verification"],
            "| ANN=", result["ann_probability_max"],
            "| SVM=", result["svm_probability_max"],
            "| RF=", result["rf_probability_max"],
        )
    print("Delta stack pmax:", delta["delta_stack_pmax"])
    print("Output:", root_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
