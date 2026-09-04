#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
HISTORY_DIR = PROJECT_ROOT / "data" / "history"
LOG_DIR = PROJECT_ROOT / "logs"

HISTORY_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

MONITORING_LATEST = OUTPUT_DIR / "monitoring_latest.json"
RELEASE_LATEST = OUTPUT_DIR / "prediction_releases_latest.csv"
NIGHT_LATEST = OUTPUT_DIR / "prediction_night_summary.csv"

MONITORING_HISTORY = HISTORY_DIR / "monitoring_history.csv"
RELEASE_HISTORY = HISTORY_DIR / "prediction_release_history.csv"
NIGHT_HISTORY = HISTORY_DIR / "prediction_night_history.csv"

STATUS_PATH = OUTPUT_DIR / "history_status.json"
LOG_PATH = LOG_DIR / "history.log"

WIB = ZoneInfo("Asia/Jakarta")


def now_iso():
    return datetime.now(WIB).isoformat()


def append_log(message):
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{now_iso()} | {message}\n")


def save_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_existing(path):
    if not path.is_file() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def upsert_csv(incoming, destination, key_cols, sort_cols=None):
    if incoming.empty:
        existing = read_existing(destination)
        return {"incoming_rows": 0, "stored_rows": int(len(existing)), "changed": False}

    missing = [c for c in key_cols if c not in incoming.columns]
    if missing:
        raise ValueError(f"Key history tidak ditemukan: {missing}")

    existing = read_existing(destination)
    combined = (
        pd.concat([existing, incoming], ignore_index=True, sort=False)
        if not existing.empty
        else incoming.copy()
    )

    combined = combined.drop_duplicates(subset=key_cols, keep="last")

    if sort_cols:
        cols = [c for c in sort_cols if c in combined.columns]
        if cols:
            combined = combined.sort_values(cols)

    combined = combined.reset_index(drop=True)
    combined.to_csv(destination, index=False)

    return {
        "incoming_rows": int(len(incoming)),
        "rows_before": int(len(existing)),
        "stored_rows": int(len(combined)),
        "changed": True,
    }


def flatten_monitoring(payload):
    if payload.get("status") != "success":
        return pd.DataFrame()

    latest = payload.get("latest_observation") or {}
    obs_time = latest.get("time_wib")
    if not obs_time:
        return pd.DataFrame()

    params = latest.get("parameters") or {}
    source_values = latest.get("source_values") or {}
    adapter = latest.get("operational_adapter") or {}
    trend = payload.get("trend_1h") or {}
    recent = payload.get("recent_1h") or {}
    station = payload.get("station") or {}
    flags = latest.get("source_quality_flags") or {}

    row = {
        "observation_time_wib": obs_time,
        "generated_at_wib": payload.get("generated_at_wib"),
        "monitoring_status": payload.get("monitoring_status"),
        "freshness_status": latest.get("freshness_status"),
        "data_age_minutes": latest.get("data_age_minutes"),
        "station_id": station.get("station_id"),
        "station_name": station.get("station_name"),
        "latitude": station.get("latitude"),
        "longitude": station.get("longitude"),
        "elevation_m": station.get("elevation_m"),
        "city": station.get("city"),
        "tt_air_avg": params.get("tt_air_avg"),
        "tt_air_min": params.get("tt_air_min"),
        "rh_avg": params.get("rh_avg"),
        "rh_avg_source": source_values.get("rh_avg_source"),
        "rh_adapter_invalid": adapter.get("rh_adapter_invalid"),
        "ws_avg": params.get("ws_avg"),
        "wd_avg": params.get("wd_avg"),
        "rr": params.get("rr"),
        "pp_air": params.get("pp_air"),
        "dew_point_c": params.get("dew_point_c"),
        "temp_change_1h": trend.get("tt_air_avg_change"),
        "tmin_change_1h": trend.get("tt_air_min_change"),
        "rh_change_1h": trend.get("rh_avg_change"),
        "ws_change_1h": trend.get("ws_avg_change"),
        "pressure_change_1h": trend.get("pp_air_change"),
        "recent_1h_observation_count": recent.get("observation_count"),
        "recent_1h_median_interval_minutes": recent.get("median_interval_minutes"),
        "recent_1h_maximum_interval_minutes": recent.get("maximum_interval_minutes"),
        "tmin_min_1h": recent.get("tmin_min_1h"),
        "rh_mean_1h": recent.get("rh_mean_1h"),
        "ws_mean_1h": recent.get("ws_mean_1h"),
        "ws_max_1h": recent.get("ws_max_1h"),
    }

    row.update(flags)
    return pd.DataFrame([row])


def archive_monitoring():
    if not MONITORING_LATEST.is_file():
        return {"status": "skipped", "reason": "monitoring_latest.json belum ada"}

    payload = json.loads(MONITORING_LATEST.read_text(encoding="utf-8"))
    incoming = flatten_monitoring(payload)

    if incoming.empty:
        return {"status": "skipped", "reason": "monitoring_latest tidak valid"}

    result = upsert_csv(
        incoming,
        MONITORING_HISTORY,
        ["observation_time_wib"],
        ["observation_time_wib"],
    )
    return {"status": "success", **result}


def archive_release():
    if not RELEASE_LATEST.is_file():
        return {"status": "skipped", "reason": "prediction_releases_latest.csv belum ada"}

    incoming = pd.read_csv(RELEASE_LATEST)
    if incoming.empty:
        return {"status": "skipped", "reason": "prediction_releases_latest.csv kosong"}

    keys = [c for c in ["tanggal_target", "jam_rilis_wib", "waktu_rilis_wib"] if c in incoming.columns]
    if len(keys) < 2:
        raise ValueError("Key rilis tidak cukup.")

    result = upsert_csv(
        incoming,
        RELEASE_HISTORY,
        keys,
        ["tanggal_target", "waktu_rilis_wib", "jam_rilis_wib"],
    )
    return {"status": "success", **result}


def archive_night():
    if not NIGHT_LATEST.is_file():
        return {"status": "skipped", "reason": "prediction_night_summary.csv belum ada"}

    incoming = pd.read_csv(NIGHT_LATEST)
    if incoming.empty:
        return {"status": "skipped", "reason": "prediction_night_summary.csv kosong"}

    if "tanggal_target" not in incoming.columns:
        raise ValueError("Kolom tanggal_target tidak ditemukan.")

    result = upsert_csv(
        incoming,
        NIGHT_HISTORY,
        ["tanggal_target"],
        ["tanggal_target"],
    )
    return {"status": "success", **result}


def main():
    generated = now_iso()

    try:
        results = {
            "monitoring": archive_monitoring(),
            "prediction_release": archive_release(),
            "prediction_night": archive_night(),
        }

        payload = {
            "status": "success",
            "generated_at_wib": generated,
            "history_dir": str(HISTORY_DIR),
            "results": results,
        }
        save_json(STATUS_PATH, payload)

        print("")
        print("======================================")
        print(" DIENGIN - HISTORY STORAGE")
        print("======================================")

        for name, result in results.items():
            extra = f" | stored={result.get('stored_rows')}" if result.get("stored_rows") is not None else ""
            print(f"{name:18s}: {result.get('status','unknown').upper()}{extra}")

        print("History dir :", HISTORY_DIR)
        print("Status run  : SUCCESS")

        append_log(
            "SUCCESS | "
            + " | ".join(f"{k}={v.get('status')}" for k, v in results.items())
        )
        return 0

    except Exception as exc:
        save_json(
            STATUS_PATH,
            {
                "status": "error",
                "generated_at_wib": generated,
                "message": str(exc),
            },
        )
        append_log(f"ERROR | {exc}")
        print(f"[DIENGIN ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
