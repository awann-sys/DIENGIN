#!/usr/bin/env python3
"""One-off / reusable historical DIENGIN backtest for a target frost morning.

Default target: 2026-08-23. The script downloads the historical AWS window
from BMKG using the same repository secrets/credentials as the operational
pipeline, runs the frozen DIENGIN v1.1 models without retraining, and writes
release-by-release and nightly summary outputs under output/backtest_<date>/.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

import download_aws as dl
import predict as pred

WIB = ZoneInfo("Asia/Jakarta")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def json_default(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def main() -> int:
    target_str = os.getenv("BACKTEST_TARGET_DATE", "2026-08-23").strip()
    target_date = pd.Timestamp(target_str).date()

    # Six hours before first release gives ample history for the 3-hour
    # rainfall feature and 1-hour rolling features. End after the 07 WIB release.
    start_wib = datetime.combine(
        target_date - pd.Timedelta(days=1), time(15, 0), tzinfo=WIB
    )
    end_wib = datetime.combine(target_date, time(8, 0), tzinfo=WIB)
    start_utc = start_wib.astimezone(timezone.utc)
    end_utc = end_wib.astimezone(timezone.utc)

    out_dir = PROJECT_ROOT / "output" / f"backtest_{target_date.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = PROJECT_ROOT / "data" / "backtest"
    data_dir.mkdir(parents=True, exist_ok=True)

    raw_json = out_dir / "aws_raw.json"
    aws_csv = data_dir / f"aws_{target_date.isoformat()}.csv"

    session = requests.Session()
    session.headers.update({"User-Agent": "DIENGIN/1.0 historical backtest"})
    token = dl.get_token(session)
    payload = dl.request_data(session, token, start_utc, end_utc)
    raw_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    records = dl.flatten_payload(payload)
    aws = dl.normalize(records)
    aws.to_csv(aws_csv, index=False)

    # Point prediction module to the historical file only for this process.
    pred.DATA_PATH = aws_csv
    pipeline = pred.load_pipeline()

    data, adapter_audit = pred.load_operational_aws()
    data, model_audit = pred.apply_model_qc(
        data, pipeline["config"]["qc_limits"]
    )
    quality_audit = adapter_audit + model_audit

    data = pred.assign_night_date(data)
    featured = pred.build_features_10min(
        data, pipeline["config"].get("rr_mode", "cumulative")
    )
    featured = pred.apply_frozen_monthly_anomaly(
        featured, pipeline["config"]["monthly_anomaly_reference"]
    )

    night_data = featured[
        featured["is_night"].eq(1)
        & pd.Series(featured["night_date"]).eq(target_date)
    ].copy().reset_index(drop=True)

    if night_data.empty:
        raise RuntimeError(
            f"Tidak ada data malam untuk target {target_date.isoformat()}."
        )

    _, imputed_features, scaled = pred.prepare_model_matrix(
        night_data, pipeline["config"], pipeline["scaler"]
    )
    prediction_10min = pred.predict_10min(night_data, scaled, pipeline)

    # Simulate the completed target morning, after the 07 WIB release.
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

    release_save = release.drop(columns=["_urutan_rilis"], errors="ignore")
    release_save.to_csv(out_dir / "release_probabilities.csv", index=False)
    night_summary.to_csv(out_dir / "night_summary.csv", index=False)
    pd.DataFrame(quality_audit).to_csv(out_dir / "qc_audit.csv", index=False)
    prediction_10min.to_csv(out_dir / "prediction_10min.csv", index=False)

    # Observational descriptors for context; user supplied observed frost = 1.
    tmin_obs = pd.to_numeric(night_data["tt_air_min"], errors="coerce")
    rh_obs = pd.to_numeric(night_data["rh_avg"], errors="coerce")
    ws_obs = pd.to_numeric(night_data["ws_avg"], errors="coerce")

    summary_row = night_summary.iloc[-1] if not night_summary.empty else None
    valid_rel = release.dropna(subset=["stack_prob"]).copy()
    first_exceed = None
    if not valid_rel.empty:
        exceed = valid_rel[valid_rel["stack_prob"] >= pipeline["threshold"]]
        if not exceed.empty:
            first_exceed = int(exceed.iloc[0]["jam_rilis_wib"])

    result = {
        "target_date": target_date.isoformat(),
        "observed_frost": 1,
        "station_id": dl.STATION_ID,
        "data_window_wib": {
            "start": start_wib.isoformat(),
            "end": end_wib.isoformat(),
        },
        "aws_rows": int(len(aws)),
        "night_rows": int(len(night_data)),
        "threshold_stacked": float(pipeline["threshold"]),
        "releases_expected": int(len(pipeline["release_hours"])),
        "releases_valid": int(len(valid_rel)),
        "probability_max": (
            float(summary_row["probabilitas_maksimum"])
            if summary_row is not None and pd.notna(summary_row["probabilitas_maksimum"])
            else None
        ),
        "probability_max_hour_wib": (
            int(summary_row["jam_probabilitas_maksimum_wib"])
            if summary_row is not None and pd.notna(summary_row["jam_probabilitas_maksimum_wib"])
            else None
        ),
        "first_threshold_exceed_hour_wib": first_exceed,
        "predicted_frost": (
            int(summary_row["prediksi_malam"])
            if summary_row is not None and pd.notna(summary_row["prediksi_malam"])
            else None
        ),
        "verification": (
            "HIT" if summary_row is not None and int(summary_row["prediksi_malam"]) == 1
            else "MISS"
        ) if summary_row is not None and pd.notna(summary_row["prediksi_malam"]) else "NO_VALID_PREDICTION",
        "observed_night": {
            "tmin_min_c": float(tmin_obs.min()) if tmin_obs.notna().any() else None,
            "rh_mean_pct": float(rh_obs.mean()) if rh_obs.notna().any() else None,
            "ws_mean": float(ws_obs.mean()) if ws_obs.notna().any() else None,
        },
    }

    (out_dir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )

    print("======================================")
    print(" DIENGIN HISTORICAL BACKTEST")
    print("======================================")
    print("Target        :", target_date.isoformat())
    print("AWS rows      :", len(aws))
    print("Night rows    :", len(night_data))
    print("Threshold     :", f"{pipeline['threshold']:.6f}")
    print("Valid releases:", len(valid_rel), "/", len(pipeline["release_hours"]))
    print("Pmax          :", result["probability_max"])
    print("Pmax hour     :", result["probability_max_hour_wib"])
    print("First exceed  :", result["first_threshold_exceed_hour_wib"])
    print("Prediction    :", result["predicted_frost"])
    print("Observed frost: 1")
    print("Verification  :", result["verification"])
    print("Output        :", out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
