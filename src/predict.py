#!/usr/bin/env python3
"""
DIENGIN - Tahap 3
Prediction Engine lokal untuk model embun beku Dieng.

Struktur proyek yang diasumsikan:
C:\DIENGIN\
├── data\
│   └── processed\
│       └── aws_dieng_latest.csv
├── logs\
├── models\
│   ├── ann_model.keras
│   ├── svm_core.joblib
│   ├── svm_calibrator.joblib
│   ├── random_forest.joblib
│   ├── meta_probability_logistic_regression.joblib
│   ├── scaler.joblib
│   └── deployment_config.json
├── output\
└── src\
    └── predict.py

Tidak ada training ulang.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd

try:
    from tensorflow import keras
except Exception as exc:
    raise ImportError(
        "TensorFlow belum tersedia. Jalankan dari root DIENGIN:\n"
        "  py -m pip install -r models\\requirements_model.txt\n"
        "lalu ulangi: py src\\predict.py"
    ) from exc


# ============================================================
# 0. PATH DAN KONSTANTA
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

MODEL_DIR = PROJECT_ROOT / "models"
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "aws_dieng_latest.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LATEST_JSON = OUTPUT_DIR / "prediction_latest.json"
RELEASE_CSV = OUTPUT_DIR / "prediction_releases_latest.csv"
NIGHT_CSV = OUTPUT_DIR / "prediction_night_summary.csv"
QC_CSV = OUTPUT_DIR / "prediction_qc_audit.csv"
FEATURE_CSV = OUTPUT_DIR / "prediction_feature_snapshot_latest.csv"
LOG_PATH = LOG_DIR / "prediction.log"

TIMEZONE_WIB = "Asia/Jakarta"
WIB = ZoneInfo(TIMEZONE_WIB)

NIGHT_START_HOUR = 19
NIGHT_END_HOUR = 6

RAIN_NOISE_MM = 0.2
RAIN_FLAG_THRESHOLD_MM = 0.0
MAX_INFORMATION_DELAY_MINUTES = 30

BASE_PROB_COLS = ["ann_prob", "svm_prob", "rf_prob"]

EXPECTED_MODEL_FILES = [
    "ann_model.keras",
    "svm_core.joblib",
    "svm_calibrator.joblib",
    "random_forest.joblib",
    "meta_probability_logistic_regression.joblib",
    "scaler.joblib",
    "deployment_config.json",
]


# ============================================================
# 1. UTILITAS
# ============================================================

def append_log(message: str) -> None:
    timestamp = datetime.now(WIB).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {message}\n")


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if pd.isna(value):
        return None
    raise TypeError(f"Tipe tidak dapat diserialisasi: {type(value)}")


def save_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            default=json_default,
        ),
        encoding="utf-8",
    )


def check_files() -> None:
    missing_models = [
        name for name in EXPECTED_MODEL_FILES
        if not (MODEL_DIR / name).is_file()
    ]
    if missing_models:
        raise FileNotFoundError(
            "Berkas model belum lengkap di folder models: "
            + ", ".join(missing_models)
        )

    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Data AWS tidak ditemukan: {DATA_PATH}\n"
            "Jalankan dahulu: py src\\download_aws.py"
        )


# ============================================================
# 2. LOAD MODEL DEPLOYMENT v1.1
# ============================================================

def load_pipeline():
    with (MODEL_DIR / "deployment_config.json").open(
        "r", encoding="utf-8"
    ) as f:
        config = json.load(f)

    scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    svm_core = joblib.load(MODEL_DIR / "svm_core.joblib")
    svm_calibrator = joblib.load(MODEL_DIR / "svm_calibrator.joblib")
    rf_model = joblib.load(MODEL_DIR / "random_forest.joblib")
    meta_model = joblib.load(
        MODEL_DIR / "meta_probability_logistic_regression.joblib"
    )
    ann_model = keras.models.load_model(MODEL_DIR / "ann_model.keras")

    feature_cols = list(config["feature_cols"])
    if len(feature_cols) != 16:
        raise RuntimeError(
            f"Konfigurasi model harus memiliki 16 fitur, ditemukan {len(feature_cols)}."
        )

    architecture = config.get("architecture_version")
    expected_architecture = (
        "probability_only_grouped_oof_one_release_16_features_v4"
    )
    if architecture != expected_architecture:
        raise RuntimeError(
            "Arsitektur model tidak sesuai paket DIENGIN v1.1.\n"
            f"Ditemukan : {architecture}\n"
            f"Diharapkan: {expected_architecture}"
        )

    thresholds = config.get("frozen_night_thresholds", {})
    if "Stacked Ensemble" not in thresholds:
        raise KeyError(
            "Threshold 'Stacked Ensemble' tidak ditemukan di deployment_config.json."
        )

    threshold = float(thresholds["Stacked Ensemble"])
    release_hours = [
        int(x) for x in config.get(
            "release_hours_wib",
            [21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7],
        )
    ]

    return {
        "config": config,
        "scaler": scaler,
        "ann": ann_model,
        "svm_core": svm_core,
        "svm_calibrator": svm_calibrator,
        "rf": rf_model,
        "meta": meta_model,
        "threshold": threshold,
        "release_hours": release_hours,
        "feature_cols": feature_cols,
    }


# ============================================================
# 3. LOAD DATA + ADAPTER QC OPERASIONAL 2026
# ============================================================

def calculate_dew_point_c(temperature_c, relative_humidity):
    temperature = pd.to_numeric(temperature_c, errors="coerce")
    humidity = pd.to_numeric(relative_humidity, errors="coerce")

    valid = (
        temperature.notna()
        & humidity.gt(0)
        & humidity.le(110)
    )

    gamma = pd.Series(
        np.nan,
        index=temperature.index,
        dtype=float,
    )

    gamma.loc[valid] = (
        np.log(humidity.loc[valid] / 100.0)
        + 17.625
        * temperature.loc[valid]
        / (243.04 + temperature.loc[valid])
    )

    return 243.04 * gamma / (17.625 - gamma)


def load_operational_aws():
    raw = pd.read_csv(DATA_PATH)

    required = [
        "datetime_wib",
        "rr",
        "ws_avg",
        "wd_avg",
        "tt_air_avg",
        "tt_air_min",
        "rh_avg",
    ]

    missing = [
        col for col in required
        if col not in raw.columns
    ]
    if missing:
        raise ValueError(
            f"Kolom data AWS belum lengkap: {missing}"
        )

    data = raw.copy()

    # Downloader menyimpan datetime_wib dengan offset +07:00.
    # Parse via UTC agar robust, lalu kembalikan ke WIB.
    data["time_wib"] = (
        pd.to_datetime(
            data["datetime_wib"],
            errors="coerce",
            utc=True,
        )
        .dt.tz_convert(TIMEZONE_WIB)
    )

    numeric_cols = [
        "rr",
        "ws_avg",
        "wd_avg",
        "tt_air_avg",
        "tt_air_min",
        "rh_avg",
    ]

    for col in numeric_cols:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce",
        )

    invalid_time = int(data["time_wib"].isna().sum())
    duplicate_time = int(
        data["time_wib"].duplicated(keep="last").sum()
    )

    data = (
        data.dropna(subset=["time_wib"])
        .sort_values("time_wib")
        .drop_duplicates(
            subset=["time_wib"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    # Adapter implementasi 2026:
    # rh_avg_flag=1 atau RH < 5 dianggap tidak valid.
    rh_flag_invalid = pd.Series(
        False,
        index=data.index,
    )

    if "rh_avg_flag" in data.columns:
        rh_flag = pd.to_numeric(
            data["rh_avg_flag"],
            errors="coerce",
        )
        rh_flag_invalid = rh_flag.eq(1)

    rh_suspicious_low = data["rh_avg"].lt(5)
    data["rh_adapter_invalid"] = (
        rh_flag_invalid | rh_suspicious_low
    )

    data.loc[
        data["rh_adapter_invalid"],
        "rh_avg",
    ] = np.nan

    # Titik embun selalu dihitung ulang setelah adapter RH.
    data["dew_point_c"] = calculate_dew_point_c(
        data["tt_air_avg"],
        data["rh_avg"],
    )

    intervals = (
        data["time_wib"]
        .diff()
        .dt.total_seconds()
        .div(60)
    )

    audit = [
        {
            "pemeriksaan": "jumlah_baris_input",
            "nilai": int(len(raw)),
        },
        {
            "pemeriksaan": "waktu_tidak_valid",
            "nilai": invalid_time,
        },
        {
            "pemeriksaan": "waktu_duplikat_dihapus",
            "nilai": duplicate_time,
        },
        {
            "pemeriksaan": "rh_adapter_tidak_valid",
            "nilai": int(
                data["rh_adapter_invalid"].sum()
            ),
        },
        {
            "pemeriksaan": "jumlah_jeda_lebih_10_menit",
            "nilai": int(intervals.gt(10.1).sum()),
        },
        {
            "pemeriksaan": "jeda_maksimum_menit",
            "nilai": (
                float(intervals.max())
                if intervals.notna().any()
                else np.nan
            ),
        },
    ]

    return data, audit


def apply_model_qc(data, qc_limits):
    output = data.copy()
    limits = dict(qc_limits)

    flags = {
        "invalid_rh_range": (
            output["rh_avg"].lt(limits["rh_min"])
            | output["rh_avg"].gt(limits["rh_max"])
        ),
        "invalid_ws_negative": (
            output["ws_avg"].lt(limits["ws_min"])
        ),
        "invalid_tavg_range": (
            output["tt_air_avg"].lt(
                limits["tavg_min"]
            )
            | output["tt_air_avg"].gt(
                limits["tavg_max"]
            )
        ),
        "invalid_tmin_range": (
            output["tt_air_min"].lt(
                limits["tmin_min"]
            )
            | output["tt_air_min"].gt(
                limits["tmin_max"]
            )
        ),
        "invalid_td_range": (
            output["dew_point_c"].lt(
                limits["td_min"]
            )
            | output["dew_point_c"].gt(
                limits["td_max"]
            )
        ),
    }

    output.loc[
        flags["invalid_rh_range"],
        "rh_avg",
    ] = np.nan

    output.loc[
        flags["invalid_ws_negative"],
        "ws_avg",
    ] = np.nan

    output.loc[
        flags["invalid_tavg_range"],
        "tt_air_avg",
    ] = np.nan

    output.loc[
        flags["invalid_tmin_range"],
        "tt_air_min",
    ] = np.nan

    output.loc[
        flags["invalid_td_range"],
        ["dew_point_c", "rh_avg"],
    ] = np.nan

    audit = [
        {
            "pemeriksaan": f"qc_model_{name}",
            "nilai": int(
                mask.fillna(False).sum()
            ),
        }
        for name, mask in flags.items()
    ]

    return output, audit


# ============================================================
# 4. NIGHT DATE + 16 FITUR
# ============================================================

def assign_night_date(data):
    output = data.copy()

    output["hour"] = output["time_wib"].dt.hour

    output["is_night"] = (
        output["hour"].ge(NIGHT_START_HOUR)
        | output["hour"].le(NIGHT_END_HOUR)
    ).astype(int)

    output["night_date"] = (
        output["time_wib"].dt.date
    )

    evening = output["hour"].ge(
        NIGHT_START_HOUR
    )

    output.loc[
        evening,
        "night_date",
    ] = (
        output.loc[
            evening,
            "time_wib",
        ]
        + pd.Timedelta(days=1)
    ).dt.date

    return output


def rain_10min_from_rr(rr, mode="cumulative"):
    rr_numeric = pd.to_numeric(
        rr,
        errors="coerce",
    )

    if mode == "cumulative":
        valid_pair = (
            rr_numeric.notna()
            & rr_numeric.shift(1).notna()
        )
        increment = (
            rr_numeric.diff()
            .where(valid_pair)
        )
        increment = increment.where(
            increment >= 0,
            0.0,
        )

    elif mode == "increment":
        increment = rr_numeric.clip(
            lower=0.0
        )

    else:
        raise ValueError(
            "rr_mode harus 'cumulative' atau 'increment'."
        )

    return increment


def build_features_10min(data, rr_mode):
    base_data = (
        data.copy()
        .sort_values("time_wib")
        .reset_index(drop=True)
        .set_index("time_wib")
    )

    features = pd.DataFrame(
        index=base_data.index
    )

    features["tmin_now"] = (
        base_data["tt_air_min"]
    )

    features["tmin_min_1h"] = (
        base_data["tt_air_min"]
        .rolling(
            "60min",
            min_periods=1,
        )
        .min()
    )

    # Persis seperti model final:
    # 6 baris = 1 jam pada resolusi 10 menit.
    features["temp_drop_1h"] = (
        base_data["tt_air_min"].shift(6)
        - base_data["tt_air_min"]
    )

    features["rh_mean_1h"] = (
        base_data["rh_avg"]
        .rolling(
            "60min",
            min_periods=1,
        )
        .mean()
    )

    features["dp_depress"] = (
        base_data["tt_air_avg"]
        - base_data["dew_point_c"]
    )

    features["ws_mean_1h"] = (
        base_data["ws_avg"]
        .rolling(
            "60min",
            min_periods=1,
        )
        .mean()
    )

    features["ws_max_1h"] = (
        base_data["ws_avg"]
        .rolling(
            "60min",
            min_periods=1,
        )
        .max()
    )

    rr_10min = rain_10min_from_rr(
        base_data["rr"],
        mode=rr_mode,
    )

    rr_10min = rr_10min.mask(
        rr_10min.notna()
        & rr_10min.le(RAIN_NOISE_MM),
        0.0,
    )

    features["rr_10min"] = rr_10min

    features["rr_sum_3h"] = (
        rr_10min
        .rolling(
            "180min",
            min_periods=1,
        )
        .sum()
    )

    features["is_rain_now"] = np.where(
        rr_10min.notna(),
        rr_10min.gt(
            RAIN_FLAG_THRESHOLD_MM
        ).astype(float),
        np.nan,
    )

    day_of_year = (
        base_data.index.dayofyear
    )

    hour_decimal = (
        base_data.index.hour
        + base_data.index.minute / 60.0
    )

    features["doy_sin"] = np.sin(
        2 * np.pi * day_of_year / 365.25
    )

    features["doy_cos"] = np.cos(
        2 * np.pi * day_of_year / 365.25
    )

    features["hour_sin"] = np.sin(
        2 * np.pi * hour_decimal / 24.0
    )

    features["hour_cos"] = np.cos(
        2 * np.pi * hour_decimal / 24.0
    )

    return (
        base_data.reset_index()
        .merge(
            features.reset_index(),
            on="time_wib",
            how="left",
        )
    )


def normalize_month_reference(reference):
    """
    deployment_config.json memakai key JSON string.
    Ubah 1..12 menjadi integer agar pandas Series.map(month)
    bekerja seperti konfigurasi asli notebook.
    """
    return {
        int(key): float(value)
        for key, value in reference.items()
    }


def apply_frozen_monthly_anomaly(
    data,
    references,
):
    output = data.copy()

    month = output["time_wib"].dt.month

    tmin_ref = normalize_month_reference(
        references[
            "tt_air_min_monthly_median_train"
        ]
    )

    dp_ref = normalize_month_reference(
        references[
            "dp_depress_monthly_median_train"
        ]
    )

    output["tmin_anom_month"] = (
        output["tt_air_min"]
        - month.map(tmin_ref)
    )

    output["dpdep_anom_month"] = (
        output["dp_depress"]
        - month.map(dp_ref)
    )

    return output


# ============================================================
# 5. MODEL MATRIX + PROBABILITAS 10 MENIT
# ============================================================

def prepare_model_matrix(
    night_data,
    config,
    scaler,
):
    feature_cols = list(
        config["feature_cols"]
    )

    raw_matrix = (
        night_data[feature_cols]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
    )

    train_median = (
        pd.Series(
            config["train_median"],
            dtype=float,
        )
        .reindex(feature_cols)
    )

    imputed = raw_matrix.fillna(
        train_median
    )

    unresolved = (
        imputed.columns[
            imputed.isna().any()
        ].tolist()
    )

    if unresolved:
        raise ValueError(
            "Missing value belum terselesaikan: "
            f"{unresolved}"
        )

    scaled = scaler.transform(
        imputed
    )

    return (
        raw_matrix,
        imputed,
        scaled,
    )


def predict_10min(
    night_data,
    scaled,
    pipeline,
):
    output = (
        night_data
        .reset_index(drop=True)
        .copy()
    )

    # ANN
    ann_prob = np.asarray(
        pipeline["ann"].predict(
            np.asarray(
                scaled,
                dtype=np.float32,
            ),
            verbose=0,
        )
    ).reshape(-1)

    ann_prob = np.clip(
        ann_prob,
        1e-7,
        1 - 1e-7,
    )

    # SVM + Platt calibration
    decision = (
        pipeline["svm_core"]
        .decision_function(
            np.asarray(
                scaled,
                dtype=float,
            )
        )
        .reshape(-1, 1)
    )

    svm_prob = (
        pipeline["svm_calibrator"]
        .predict_proba(decision)[:, 1]
    )

    svm_prob = np.clip(
        svm_prob,
        1e-7,
        1 - 1e-7,
    )

    # Random Forest
    rf_prob = (
        pipeline["rf"]
        .predict_proba(
            np.asarray(
                scaled,
                dtype=float,
            )
        )[:, 1]
    )

    output["ann_prob"] = ann_prob
    output["svm_prob"] = svm_prob
    output["rf_prob"] = rf_prob

    return output


# ============================================================
# 6. JAM RILIS
# ============================================================

def release_timestamp(
    target_date,
    release_hour,
):
    target = pd.Timestamp(target_date)

    release_date = (
        target - pd.Timedelta(days=1)
        if int(release_hour) >= NIGHT_START_HOUR
        else target
    )

    return (
        pd.Timestamp(release_date.date())
        + pd.Timedelta(
            hours=int(release_hour)
        )
    ).tz_localize(TIMEZONE_WIB)


def build_release_table(
    prediction_10min,
    release_hours,
    now_wib,
):
    rows = []

    for (
        target_date,
        night,
    ) in prediction_10min.groupby(
        "night_date",
        sort=True,
    ):
        night = night.sort_values(
            "time_wib"
        )

        for release_hour in release_hours:
            release_time = release_timestamp(
                target_date,
                release_hour,
            )

            # DIENGIN real-time:
            # jangan membuat "prediksi" untuk waktu rilis
            # yang belum terjadi.
            if release_time > now_wib:
                continue

            available = night[
                night["time_wib"]
                < release_time
            ]

            if available.empty:
                continue

            latest = available.iloc[-1]

            delay = (
                release_time
                - latest["time_wib"]
            ).total_seconds() / 60.0

            on_time = (
                0 <= delay
                <= MAX_INFORMATION_DELAY_MINUTES
            )

            row = {
                "tanggal_target":
                    pd.Timestamp(target_date),
                "jam_rilis_wib":
                    int(release_hour),
                "waktu_rilis_wib":
                    release_time,
                "waktu_pengamatan_terakhir_wib":
                    latest["time_wib"],
                "jeda_informasi_menit":
                    float(delay),
                "status_data_rilis":
                    (
                        "tepat_waktu"
                        if on_time
                        else "terlambat"
                    ),
                "source_row_index":
                    int(latest.name),
            }

            for col in BASE_PROB_COLS:
                row[col] = (
                    float(latest[col])
                    if on_time
                    else np.nan
                )

            rows.append(row)

    release = pd.DataFrame(rows)

    if release.empty:
        return release

    order = {
        hour: index
        for index, hour
        in enumerate(release_hours)
    }

    release["_urutan_rilis"] = (
        release["jam_rilis_wib"]
        .map(order)
    )

    return (
        release
        .sort_values(
            [
                "tanggal_target",
                "_urutan_rilis",
            ]
        )
        .reset_index(drop=True)
    )


def add_stacked_probability(
    release,
    meta_model,
    threshold,
):
    if release.empty:
        return release

    output = release.copy()

    valid = (
        output[BASE_PROB_COLS]
        .notna()
        .all(axis=1)
    )

    output["stack_prob"] = np.nan

    if valid.any():
        output.loc[
            valid,
            "stack_prob",
        ] = (
            meta_model.predict_proba(
                output.loc[
                    valid,
                    BASE_PROB_COLS,
                ]
            )[:, 1]
        )

    output["indikasi_rilis"] = pd.Series(
        pd.NA,
        index=output.index,
        dtype="Int64",
    )

    output.loc[
        valid,
        "indikasi_rilis",
    ] = (
        output.loc[
            valid,
            "stack_prob",
        ]
        >= threshold
    ).astype(int)

    return output


def aggregate_night(
    release,
    threshold,
):
    if release.empty:
        return pd.DataFrame()

    rows = []

    for (
        target_date,
        night,
    ) in release.groupby(
        "tanggal_target",
        sort=True,
    ):
        valid = (
            night.dropna(
                subset=["stack_prob"]
            )
            .sort_values("_urutan_rilis")
            .copy()
        )

        row = {
            "tanggal_target":
                pd.Timestamp(target_date),
            "jumlah_rilis_tersedia":
                int(len(valid)),
            "ambang_final":
                float(threshold),
        }

        if valid.empty:
            row.update({
                "probabilitas_maksimum":
                    np.nan,
                "jam_probabilitas_maksimum_wib":
                    np.nan,
                "jam_pertama_melampaui_ambang_wib":
                    np.nan,
                "prediksi_malam":
                    pd.NA,
            })

        else:
            max_idx = (
                valid["stack_prob"]
                .idxmax()
            )

            exceed = valid[
                valid["stack_prob"]
                >= threshold
            ]

            row.update({
                "probabilitas_maksimum":
                    float(
                        valid.loc[
                            max_idx,
                            "stack_prob",
                        ]
                    ),
                "jam_probabilitas_maksimum_wib":
                    int(
                        valid.loc[
                            max_idx,
                            "jam_rilis_wib",
                        ]
                    ),
                "jam_pertama_melampaui_ambang_wib":
                    (
                        int(
                            exceed.iloc[0][
                                "jam_rilis_wib"
                            ]
                        )
                        if not exceed.empty
                        else np.nan
                    ),
                "prediksi_malam":
                    int(
                        valid[
                            "stack_prob"
                        ].max()
                        >= threshold
                    ),
            })

        rows.append(row)

    return (
        pd.DataFrame(rows)
        .sort_values("tanggal_target")
        .reset_index(drop=True)
    )


# ============================================================
# 7. OUTPUT TERBARU
# ============================================================

def next_release_time(
    target_date,
    release_hours,
    now_wib,
):
    for hour in release_hours:
        t = release_timestamp(
            target_date,
            hour,
        )
        if t > now_wib:
            return t
    return None


def build_latest_payload(
    prediction_10min,
    release,
    night_summary,
    pipeline,
    now_wib,
    quality_audit,
):
    latest_obs = (
        prediction_10min[
            "time_wib"
        ].max()
    )

    if release.empty:
        return {
            "status": "no_release_available",
            "generated_at_wib":
                now_wib.isoformat(),
            "latest_observation_wib":
                latest_obs.isoformat(),
            "threshold_stacked":
                float(
                    pipeline["threshold"]
                ),
            "message":
                "Belum ada jam rilis yang dapat dihitung dari data tersedia.",
        }

    latest_target = (
        release["tanggal_target"]
        .max()
    )

    latest_night_release = (
        release[
            release["tanggal_target"]
            .eq(latest_target)
        ]
        .sort_values("_urutan_rilis")
        .copy()
    )

    valid_release = (
        latest_night_release
        .dropna(
            subset=["stack_prob"]
        )
    )

    summary_row = (
        night_summary[
            night_summary[
                "tanggal_target"
            ].eq(latest_target)
        ]
        .iloc[-1]
    )

    latest_valid = (
        valid_release.iloc[-1]
        if not valid_release.empty
        else None
    )

    target_date_value = (
        pd.Timestamp(
            latest_target
        ).date()
    )

    next_time = next_release_time(
        target_date_value,
        pipeline["release_hours"],
        now_wib,
    )

    has_07 = (
        valid_release[
            "jam_rilis_wib"
        ].eq(7).any()
        if not valid_release.empty
        else False
    )

    data_age_minutes = (
        now_wib
        - latest_obs
    ).total_seconds() / 60.0

    if data_age_minutes <= 30:
        data_status = "current"
    elif data_age_minutes <= 60:
        data_status = "delayed"
    else:
        data_status = "stale"

    payload = {
        "status": "success",
        "architecture_version":
            pipeline["config"][
                "architecture_version"
            ],
        "generated_at_wib":
            now_wib.isoformat(),
        "target_night_date":
            target_date_value.isoformat(),
        "latest_observation_wib":
            latest_obs.isoformat(),
        "data_age_minutes":
            float(data_age_minutes),
        "data_status":
            data_status,
        "threshold_stacked":
            float(
                pipeline["threshold"]
            ),
        "releases_expected":
            int(
                len(
                    pipeline[
                        "release_hours"
                    ]
                )
            ),
        "releases_available":
            int(
                summary_row[
                    "jumlah_rilis_tersedia"
                ]
            ),
        "night_complete":
            bool(has_07),
        "probability_max_so_far":
            (
                float(
                    summary_row[
                        "probabilitas_maksimum"
                    ]
                )
                if pd.notna(
                    summary_row[
                        "probabilitas_maksimum"
                    ]
                )
                else None
            ),
        "probability_max_hour_wib":
            (
                int(
                    summary_row[
                        "jam_probabilitas_maksimum_wib"
                    ]
                )
                if pd.notna(
                    summary_row[
                        "jam_probabilitas_maksimum_wib"
                    ]
                )
                else None
            ),
        "first_threshold_exceed_hour_wib":
            (
                int(
                    summary_row[
                        "jam_pertama_melampaui_ambang_wib"
                    ]
                )
                if pd.notna(
                    summary_row[
                        "jam_pertama_melampaui_ambang_wib"
                    ]
                )
                else None
            ),
        "prediction_so_far":
            (
                int(
                    summary_row[
                        "prediksi_malam"
                    ]
                )
                if pd.notna(
                    summary_row[
                        "prediksi_malam"
                    ]
                )
                else None
            ),
        "next_release_wib":
            (
                next_time.isoformat()
                if next_time is not None
                else None
            ),
        "qc": quality_audit,
    }

    if latest_valid is not None:
        payload["latest_release"] = {
            "hour_wib":
                int(
                    latest_valid[
                        "jam_rilis_wib"
                    ]
                ),
            "release_time_wib":
                latest_valid[
                    "waktu_rilis_wib"
                ].isoformat(),
            "observation_used_wib":
                latest_valid[
                    "waktu_pengamatan_terakhir_wib"
                ].isoformat(),
            "information_delay_minutes":
                float(
                    latest_valid[
                        "jeda_informasi_menit"
                    ]
                ),
            "ann_probability":
                float(
                    latest_valid[
                        "ann_prob"
                    ]
                ),
            "svm_probability":
                float(
                    latest_valid[
                        "svm_prob"
                    ]
                ),
            "rf_probability":
                float(
                    latest_valid[
                        "rf_prob"
                    ]
                ),
            "stacked_probability":
                float(
                    latest_valid[
                        "stack_prob"
                    ]
                ),
            "threshold_exceeded":
                bool(
                    int(
                        latest_valid[
                            "indikasi_rilis"
                        ]
                    )
                ),
        }
    else:
        payload["latest_release"] = None

    return payload


def save_feature_snapshot(
    prediction_10min,
    imputed_features,
    release,
    feature_cols,
):
    if release.empty:
        return

    valid = release.dropna(
        subset=["stack_prob"]
    )

    if valid.empty:
        return

    latest = (
        valid.sort_values(
            [
                "tanggal_target",
                "_urutan_rilis",
            ]
        )
        .iloc[-1]
    )

    row_index = int(
        latest["source_row_index"]
    )

    metadata = {
        "tanggal_target":
            latest["tanggal_target"],
        "jam_rilis_wib":
            latest["jam_rilis_wib"],
        "waktu_rilis_wib":
            latest["waktu_rilis_wib"],
        "waktu_pengamatan_terakhir_wib":
            latest[
                "waktu_pengamatan_terakhir_wib"
            ],
    }

    feature_values = (
        imputed_features.iloc[
            row_index
        ][feature_cols]
        .to_dict()
    )

    row = {
        **metadata,
        **feature_values,
    }

    pd.DataFrame(
        [row]
    ).to_csv(
        FEATURE_CSV,
        index=False,
    )


# ============================================================
# 8. MAIN
# ============================================================

def main() -> int:
    now_wib = pd.Timestamp(
        datetime.now(WIB)
    )

    try:
        check_files()
        pipeline = load_pipeline()

        data, adapter_audit = (
            load_operational_aws()
        )

        data, model_audit = (
            apply_model_qc(
                data,
                pipeline["config"][
                    "qc_limits"
                ],
            )
        )

        quality_audit = (
            adapter_audit
            + model_audit
        )

        data = assign_night_date(
            data
        )

        featured = build_features_10min(
            data,
            pipeline["config"].get(
                "rr_mode",
                "cumulative",
            ),
        )

        featured = (
            apply_frozen_monthly_anomaly(
                featured,
                pipeline["config"][
                    "monthly_anomaly_reference"
                ],
            )
        )

        night_data = (
            featured[
                featured[
                    "is_night"
                ].eq(1)
            ]
            .copy()
            .reset_index(drop=True)
        )

        if night_data.empty:
            raise RuntimeError(
                "Tidak ada data malam "
                "(19:00-06:59 WIB) pada "
                "window AWS saat ini."
            )

        (
            raw_features,
            imputed_features,
            scaled,
        ) = prepare_model_matrix(
            night_data,
            pipeline["config"],
            pipeline["scaler"],
        )

        prediction_10min = (
            predict_10min(
                night_data,
                scaled,
                pipeline,
            )
        )

        release = build_release_table(
            prediction_10min,
            pipeline["release_hours"],
            now_wib,
        )

        release = (
            add_stacked_probability(
                release,
                pipeline["meta"],
                pipeline["threshold"],
            )
        )

        night_summary = (
            aggregate_night(
                release,
                pipeline["threshold"],
            )
        )

        payload = (
            build_latest_payload(
                prediction_10min,
                release,
                night_summary,
                pipeline,
                now_wib,
                quality_audit,
            )
        )

        # Simpan output
        if not release.empty:
            release_to_save = (
                release.drop(
                    columns=[
                        "_urutan_rilis"
                    ],
                    errors="ignore",
                )
            )
            release_to_save.to_csv(
                RELEASE_CSV,
                index=False,
            )

        if not night_summary.empty:
            night_summary.to_csv(
                NIGHT_CSV,
                index=False,
            )

        pd.DataFrame(
            quality_audit
        ).to_csv(
            QC_CSV,
            index=False,
        )

        save_json(
            LATEST_JSON,
            payload,
        )

        save_feature_snapshot(
            prediction_10min,
            imputed_features,
            release,
            pipeline["feature_cols"],
        )

        print("")
        print(
            "======================================"
        )
        print(
            " DIENGIN - PREDICTION ENGINE"
        )
        print(
            "======================================"
        )
        print(
            "Arsitektur :",
            pipeline["config"][
                "architecture_version"
            ],
        )
        print(
            "Ambang     :",
            f"{pipeline['threshold']:.6f}",
        )
        print(
            "Data latest:",
            payload.get(
                "latest_observation_wib"
            ),
        )
        print(
            "Target     :",
            payload.get(
                "target_night_date"
            ),
        )
        print(
            "Rilis valid:",
            payload.get(
                "releases_available"
            ),
            "/",
            payload.get(
                "releases_expected"
            ),
        )

        latest_release = (
            payload.get(
                "latest_release"
            )
        )

        if latest_release:
            print(
                "Rilis latest:",
                f"{latest_release['hour_wib']:02d}:00 WIB",
            )
            print(
                "Stack prob :",
                f"{latest_release['stacked_probability']:.6f}",
            )

        print(
            "Prob max   :",
            payload.get(
                "probability_max_so_far"
            ),
        )
        print(
            "Prediksi   :",
            payload.get(
                "prediction_so_far"
            ),
        )
        print(
            "Data status:",
            payload.get(
                "data_status"
            ),
        )
        print(
            "Output JSON:",
            LATEST_JSON,
        )
        print(
            "Status     : SUCCESS"
        )

        append_log(
            "SUCCESS | "
            f"target={payload.get('target_night_date')} | "
            f"releases={payload.get('releases_available')} | "
            f"pmax={payload.get('probability_max_so_far')} | "
            f"prediction={payload.get('prediction_so_far')}"
        )

        return 0

    except Exception as exc:
        error_payload = {
            "status": "error",
            "generated_at_wib":
                now_wib.isoformat(),
            "message": str(exc),
        }

        save_json(
            LATEST_JSON,
            error_payload,
        )

        append_log(
            f"ERROR | {exc}"
        )

        print(
            f"[DIENGIN ERROR] {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
