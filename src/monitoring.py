#!/usr/bin/env python3
"""
DIENGIN - Tahap 4 v2
Monitoring AWS lokal 15-menitan.

Catatan:
- Resolusi observasi sumber tetap mengikuti AWS (umumnya 10 menit).
- Script ini tidak melakukan retraining dan tidak mengubah prediksi model.
- Quality flag dari API dipertahankan sebagai informasi audit; nilai numeriknya
  tidak ditafsirkan sebagai status baik/buruk di sini.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "aws_dieng_latest.csv"
MODEL_CONFIG_PATH = PROJECT_ROOT / "models" / "deployment_config.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LATEST_JSON = OUTPUT_DIR / "monitoring_latest.json"
SNAPSHOT_CSV = OUTPUT_DIR / "monitoring_snapshot_latest.csv"
LOG_PATH = LOG_DIR / "monitoring.log"

TIMEZONE_WIB = "Asia/Jakarta"
WIB = ZoneInfo(TIMEZONE_WIB)

CURRENT_MAX_AGE_MIN = 30
DELAYED_MAX_AGE_MIN = 60
TREND_REFERENCE_MIN = 60

DISPLAY_PARAMETERS = [
    "tt_air_avg",
    "tt_air_min",
    "rh_avg",
    "ws_avg",
    "wd_avg",
    "rr",
    "pp_air",
    "dew_point_c",
]

FLAG_COLUMNS = [
    "tt_air_avg_flag",
    "tt_air_min_flag",
    "rh_avg_flag",
    "ws_avg_flag",
    "wd_avg_flag",
    "rr_flag",
    "pp_air_flag",
]


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if pd.isna(value):
        return None
    raise TypeError(f"Tipe tidak dapat diserialisasi: {type(value)}")


def save_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )


def append_log(message: str) -> None:
    timestamp = datetime.now(WIB).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {message}\n")


def load_model_config() -> dict:
    if not MODEL_CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"Konfigurasi model tidak ditemukan: {MODEL_CONFIG_PATH}"
        )
    return json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8"))


def load_aws() -> pd.DataFrame:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Data AWS tidak ditemukan: {DATA_PATH}\n"
            "Jalankan dahulu: python src\\download_aws.py"
        )

    df = pd.read_csv(DATA_PATH)

    if "datetime_wib" not in df.columns:
        raise ValueError("Kolom datetime_wib tidak ditemukan pada data AWS.")

    df["time_wib"] = (
        pd.to_datetime(df["datetime_wib"], errors="coerce", utc=True)
        .dt.tz_convert(TIMEZONE_WIB)
    )

    for col in DISPLAY_PARAMETERS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in FLAG_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = (
        df.dropna(subset=["time_wib"])
        .sort_values("time_wib")
        .drop_duplicates(subset=["time_wib"], keep="last")
        .reset_index(drop=True)
    )

    if df.empty:
        raise RuntimeError("Data AWS kosong setelah parsing timestamp.")

    df = apply_operational_adapter(df)

    return df



def calculate_dew_point_c(temperature_c, relative_humidity):
    t = pd.to_numeric(temperature_c, errors="coerce")
    rh = pd.to_numeric(relative_humidity, errors="coerce")

    valid = t.notna() & rh.gt(0) & rh.le(110)

    gamma = pd.Series(np.nan, index=t.index, dtype=float)
    gamma.loc[valid] = (
        np.log(rh.loc[valid] / 100.0)
        + 17.625 * t.loc[valid] / (243.04 + t.loc[valid])
    )

    return 243.04 * gamma / (17.625 - gamma)


def apply_operational_adapter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Samakan input monitoring dengan adapter operasional predict.py.

    Nilai sumber tidak dibuang:
    - rh_avg_source menyimpan nilai RH asli API.
    - rh_adapter_invalid hanya menandai bahwa RH tidak dipakai oleh
      pipeline operasional DIENGIN.

    Aturan ini adalah aturan deployment DIENGIN, bukan legenda resmi
    numerik quality flag BMKG.
    """
    out = df.copy()

    out["rh_avg_source"] = out["rh_avg"]

    rh_flag = (
        pd.to_numeric(out["rh_avg_flag"], errors="coerce")
        if "rh_avg_flag" in out.columns
        else pd.Series(np.nan, index=out.index)
    )

    out["rh_adapter_invalid"] = (
        rh_flag.eq(1)
        | out["rh_avg"].lt(5)
        | out["rh_avg"].gt(110)
    )

    out.loc[out["rh_adapter_invalid"], "rh_avg"] = np.nan

    # Hitung ulang titik embun dari RH efektif agar monitoring dan predict.py konsisten.
    out["dew_point_c"] = calculate_dew_point_c(
        out["tt_air_avg"],
        out["rh_avg"],
    )

    return out


def safe_float(value):
    if pd.isna(value):
        return None
    return float(value)


def safe_int(value):
    if pd.isna(value):
        return None
    return int(value)


def parameter_qc(latest: pd.Series, qc_limits: dict) -> dict:
    """
    QC parameter yang relevan untuk model menggunakan batas frozen dari
    deployment_config.json. Parameter lain ditampilkan tanpa label QC model.
    """

    checks = {}

    mapping = {
        "tt_air_avg": ("tavg_min", "tavg_max"),
        "tt_air_min": ("tmin_min", "tmin_max"),
        "rh_avg": ("rh_min", "rh_max"),
    }

    for parameter, (low_key, high_key) in mapping.items():
        value = latest.get(parameter, np.nan)
        low = qc_limits.get(low_key)
        high = qc_limits.get(high_key)

        if pd.isna(value):
            status = "missing"
        elif low is None or high is None:
            status = "not_checked"
        elif float(low) <= float(value) <= float(high):
            status = "valid"
        else:
            status = "out_of_range"

        checks[parameter] = {
            "value": safe_float(value),
            "qc_status": status,
            "qc_min": safe_float(low) if low is not None else None,
            "qc_max": safe_float(high) if high is not None else None,
        }

    # Kecepatan angin pada konfigurasi model hanya memiliki batas bawah.
    ws = latest.get("ws_avg", np.nan)
    ws_min = qc_limits.get("ws_min")
    if pd.isna(ws):
        ws_status = "missing"
    elif ws_min is None:
        ws_status = "not_checked"
    elif float(ws) >= float(ws_min):
        ws_status = "valid"
    else:
        ws_status = "out_of_range"

    checks["ws_avg"] = {
        "value": safe_float(ws),
        "qc_status": ws_status,
        "qc_min": safe_float(ws_min) if ws_min is not None else None,
        "qc_max": None,
    }

    # Dew point hasil turunan downloader juga mengikuti batas frozen model.
    td = latest.get("dew_point_c", np.nan)
    td_min = qc_limits.get("td_min")
    td_max = qc_limits.get("td_max")
    if pd.isna(td):
        td_status = "missing"
    elif td_min is None or td_max is None:
        td_status = "not_checked"
    elif float(td_min) <= float(td) <= float(td_max):
        td_status = "valid"
    else:
        td_status = "out_of_range"

    checks["dew_point_c"] = {
        "value": safe_float(td),
        "qc_status": td_status,
        "qc_min": safe_float(td_min) if td_min is not None else None,
        "qc_max": safe_float(td_max) if td_max is not None else None,
    }

    return checks


def data_freshness(latest_time: pd.Timestamp, now_wib: pd.Timestamp) -> tuple[str, float]:
    age_minutes = (now_wib - latest_time).total_seconds() / 60.0

    # Clock skew kecil tidak langsung dianggap error.
    if age_minutes < -5:
        return "future_timestamp", float(age_minutes)
    if age_minutes <= CURRENT_MAX_AGE_MIN:
        return "current", float(age_minutes)
    if age_minutes <= DELAYED_MAX_AGE_MIN:
        return "delayed", float(age_minutes)
    return "stale", float(age_minutes)


def find_reference_row(df: pd.DataFrame, latest_time: pd.Timestamp) -> pd.Series | None:
    target = latest_time - pd.Timedelta(minutes=TREND_REFERENCE_MIN)
    candidates = df[df["time_wib"] <= target]

    if candidates.empty:
        return None

    # Ambil observasi terdekat terhadap target satu jam sebelumnya.
    idx = (candidates["time_wib"] - target).abs().idxmin()
    return candidates.loc[idx]


def build_trend(latest: pd.Series, reference: pd.Series | None) -> dict:
    if reference is None:
        return {
            "reference_available": False,
            "reference_time_wib": None,
        }

    result = {
        "reference_available": True,
        "reference_time_wib": reference["time_wib"].isoformat(),
        "reference_age_from_latest_minutes": float(
            (latest["time_wib"] - reference["time_wib"]).total_seconds() / 60.0
        ),
    }

    for col in ["tt_air_avg", "tt_air_min", "rh_avg", "ws_avg", "pp_air"]:
        if col not in latest.index:
            continue

        a = latest.get(col, np.nan)
        b = reference.get(col, np.nan)

        result[f"{col}_change"] = (
            float(a - b)
            if pd.notna(a) and pd.notna(b)
            else None
        )

    return result


def build_recent_window(df: pd.DataFrame, latest_time: pd.Timestamp) -> dict:
    start = latest_time - pd.Timedelta(minutes=60)
    recent = df[(df["time_wib"] > start) & (df["time_wib"] <= latest_time)].copy()

    interval = recent["time_wib"].diff().dt.total_seconds().div(60)

    return {
        "window_start_wib": start.isoformat(),
        "window_end_wib": latest_time.isoformat(),
        "observation_count": int(len(recent)),
        "median_interval_minutes": (
            float(interval.median()) if interval.notna().any() else None
        ),
        "maximum_interval_minutes": (
            float(interval.max()) if interval.notna().any() else None
        ),
        "tmin_min_1h": (
            safe_float(recent["tt_air_min"].min())
            if "tt_air_min" in recent.columns
            else None
        ),
        "rh_mean_1h": (
            safe_float(recent["rh_avg"].mean())
            if "rh_avg" in recent.columns
            else None
        ),
        "ws_mean_1h": (
            safe_float(recent["ws_avg"].mean())
            if "ws_avg" in recent.columns
            else None
        ),
        "ws_max_1h": (
            safe_float(recent["ws_avg"].max())
            if "ws_avg" in recent.columns
            else None
        ),
    }


def build_source_flags(latest: pd.Series) -> dict:
    """
    Flag dipublikasikan apa adanya untuk audit.
    Tidak ada interpretasi 0/1/9 di monitoring.py.
    """
    result = {}

    for col in FLAG_COLUMNS:
        if col in latest.index:
            result[col] = safe_int(latest.get(col))

    return result


def build_parameter_values(latest: pd.Series) -> dict:
    result = {}

    for col in DISPLAY_PARAMETERS:
        if col in latest.index:
            result[col] = safe_float(latest.get(col))

    return result


def station_metadata(latest: pd.Series) -> dict:
    aliases = {
        "station_id": ["id_station", "station_id"],
        "station_name": ["name_station", "station_name"],
        "latitude": ["latt_station", "latitude", "lat"],
        "longitude": ["long_station", "longitude", "lon"],
        "elevation_m": ["elv_station", "elevation", "elevation_m"],
        "city": ["nama_kota", "city"],
    }

    out = {}

    for out_key, candidates in aliases.items():
        value = None
        for col in candidates:
            if col in latest.index and pd.notna(latest.get(col)):
                value = latest.get(col)
                break

        if out_key in {"latitude", "longitude", "elevation_m"}:
            try:
                value = float(value) if value is not None else None
            except (TypeError, ValueError):
                value = None

        out[out_key] = value

    return out


def overall_monitoring_status(
    freshness: str,
    qc_checks: dict,
) -> str:
    if freshness in {"stale", "future_timestamp"}:
        return freshness

    statuses = [entry["qc_status"] for entry in qc_checks.values()]

    if any(status == "out_of_range" for status in statuses):
        return "invalid"
    if any(status == "missing" for status in statuses):
        return "partial"
    if freshness == "delayed":
        return "delayed"
    return "valid"


def make_snapshot_csv(payload: dict) -> None:
    latest = payload.get("latest_observation", {})
    params = latest.get("parameters", {})

    row = {
        "generated_at_wib": payload.get("generated_at_wib"),
        "observation_time_wib": latest.get("time_wib"),
        "data_age_minutes": latest.get("data_age_minutes"),
        "freshness_status": latest.get("freshness_status"),
        "monitoring_status": payload.get("monitoring_status"),
        **params,
    }

    pd.DataFrame([row]).to_csv(SNAPSHOT_CSV, index=False)


def main() -> int:
    now_wib = pd.Timestamp(datetime.now(WIB))

    try:
        config = load_model_config()
        df = load_aws()

        latest = df.iloc[-1]
        latest_time = latest["time_wib"]

        freshness, age_minutes = data_freshness(latest_time, now_wib)
        qc_checks = parameter_qc(latest, config.get("qc_limits", {}))
        reference = find_reference_row(df, latest_time)

        payload = {
            "status": "success",
            "generated_at_wib": now_wib.isoformat(),
            "monitoring_status": overall_monitoring_status(freshness, qc_checks),
            "station": station_metadata(latest),
            "latest_observation": {
                "time_wib": latest_time.isoformat(),
                "data_age_minutes": age_minutes,
                "freshness_status": freshness,
                "parameters": build_parameter_values(latest),
                "source_values": {
                    "rh_avg_source": safe_float(latest.get("rh_avg_source", np.nan)),
                },
                "operational_adapter": {
                    "rh_adapter_invalid": bool(latest.get("rh_adapter_invalid", False)),
                    "rh_policy": (
                        "RH tidak dipakai oleh pipeline DIENGIN bila rh_avg_flag=1, "
                        "RH<5%, atau RH>110%. Nilai sumber tetap disimpan terpisah."
                    ),
                },
                "source_quality_flags": build_source_flags(latest),
                "model_qc": qc_checks,
            },
            "trend_1h": build_trend(latest, reference),
            "recent_1h": build_recent_window(df, latest_time),
            "notes": {
                "source_flag_policy": (
                    "Quality flag API tetap disimpan apa adanya. Khusus rh_avg_flag=1, "
                    "pipeline mengikuti adapter operasional DIENGIN yang juga digunakan predict.py; "
                    "ini bukan klaim mengenai legenda resmi flag BMKG."
                ),
                "prediction_policy": (
                    "Monitoring tidak mengubah model, threshold, atau jam rilis prediksi."
                ),
            },
        }

        save_json(LATEST_JSON, payload)
        make_snapshot_csv(payload)

        print("")
        print("======================================")
        print(" DIENGIN - AWS MONITORING")
        print("======================================")
        print("Observasi   :", latest_time.isoformat())
        print("Umur data   :", f"{age_minutes:.1f} menit")
        print("Freshness   :", freshness)
        print("Status      :", payload["monitoring_status"])

        params = payload["latest_observation"]["parameters"]
        if params.get("tt_air_avg") is not None:
            print("Suhu        :", f"{params['tt_air_avg']:.2f} °C")
        if params.get("tt_air_min") is not None:
            print("Tmin        :", f"{params['tt_air_min']:.2f} °C")
        rh_invalid = payload["latest_observation"]["operational_adapter"]["rh_adapter_invalid"]
        rh_source = payload["latest_observation"]["source_values"]["rh_avg_source"]

        if params.get("rh_avg") is not None:
            print("RH          :", f"{params['rh_avg']:.2f} %")
        elif rh_invalid:
            print(
                "RH          : unavailable"
                + (
                    f" (source={rh_source:.2f} %)"
                    if rh_source is not None
                    else ""
                )
            )
        else:
            print("RH          : unavailable")

        if params.get("ws_avg") is not None:
            print("Angin       :", f"{params['ws_avg']:.2f}")

        if params.get("dew_point_c") is not None:
            print("Titik embun :", f"{params['dew_point_c']:.2f} °C")
        else:
            print("Titik embun : unavailable")

        print("Output JSON :", LATEST_JSON)
        print("Status run  : SUCCESS")

        append_log(
            "SUCCESS | "
            f"obs={latest_time.isoformat()} | "
            f"age_min={age_minutes:.1f} | "
            f"monitoring_status={payload['monitoring_status']}"
        )

        return 0

    except Exception as exc:
        payload = {
            "status": "error",
            "generated_at_wib": now_wib.isoformat(),
            "monitoring_status": "missing",
            "message": str(exc),
        }

        save_json(LATEST_JSON, payload)
        append_log(f"ERROR | {exc}")
        print(f"[DIENGIN ERROR] {exc}", file=sys.stderr)

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
