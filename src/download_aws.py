#!/usr/bin/env python3
"""
DIENGIN - Tahap 2
Downloader AWS BMKG untuk STA2285 (Dieng) - v3

Pipeline operasional mengunduh Excel bulanan dari endpoint rawdata AWS Center
menggunakan route downloadaccesdata_year, lalu menormalisasi observasi terbaru
untuk monitoring dan prediksi.

Catatan:
- Jalur operasional ini tidak memerlukan AWS API token.
- Stasiun DIENGIN tetap AWS Batur STA2285. ID 160010 pada contoh lama adalah
  AWS Tambi, jadi tidak dipakai untuk masukan model Batur.
"""

from __future__ import annotations

import calendar
import io
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

API_BASE = "https://apiaws.bmkg.go.id"
LOGIN_URL = f"{API_BASE}/auth/login"
DATA_URL = f"{API_BASE}/getdata"

STATION_ID = "STA2285"
STATION_TYPE = "aws"
RAW_BASE = "https://apiaws.bmkg.go.id/rawdata"

# Parameter yang digunakan pipeline DIENGIN
PARAMETERS = [
    "rr",
    "ws_avg",
    "wd_avg",
    "tt_air_avg",
    "tt_air_min",
    "rh_avg",
    "pp_air",
    "tt_air_max",
    "ws_max",
    "sr_avg",
    "sr_max",
]

# Struktur proyek:
# C:/DIENGIN/
# ├── src/download_aws.py
# ├── data/raw/
# ├── data/processed/
# ├── output/
# └── logs/
#
# File ini berada di src/, sehingga PROJECT_ROOT adalah parent dari src/.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
STATUS_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
STATUS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

RAW_EXPORT_PATH = RAW_DIR / f"aws_{STATION_ID}_raw_latest.csv"
CSV_PATH = PROCESSED_DIR / "aws_dieng_latest.csv"
STATUS_PATH = STATUS_DIR / "aws_ingestion_status.json"
LOG_PATH = LOG_DIR / "aws_ingestion.log"

REQUEST_TIMEOUT = 60


def get_token(session: requests.Session) -> str:
    """Gunakan token environment jika ada; jika tidak, login resmi."""
    token = os.getenv("AWS_API_TOKEN", "").strip()
    if token:
        return token

    username = os.getenv("AWS_API_USERNAME", "").strip()
    password = os.getenv("AWS_API_PASSWORD", "").strip()

    if not username or not password:
        raise RuntimeError(
            "Kredensial belum tersedia. Set AWS_API_TOKEN atau "
            "AWS_API_USERNAME dan AWS_API_PASSWORD sebagai environment variable."
        )

    # BMKG documents POST with username/password as query parameters.
    # Never propagate requests.HTTPError: its string includes the full URL
    # (and therefore the credentials) into logs and status JSON.
    retryable = {429, 500, 502, 503, 504}
    pauses = (5, 15)
    for attempt in range(3):
        try:
            response = session.post(
                LOGIN_URL,
                params={"username": username, "password": password},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            if attempt < 2:
                time.sleep(pauses[attempt])
                continue
            raise RuntimeError(
                "Login AWS BMKG gagal karena masalah koneksi setelah 3 percobaan."
            ) from None

        code = response.status_code
        if code in retryable:
            if attempt < 2:
                time.sleep(pauses[attempt])
                continue
            raise RuntimeError(
                f"Login AWS BMKG HTTP {code} setelah 3 percobaan; "
                "endpoint kemungkinan sedang bermasalah atau membatasi akses."
            )

        if code >= 400:
            raise RuntimeError(
                f"Login AWS BMKG HTTP {code}; cek akses API dan kredensial. "
                "URL autentikasi sengaja tidak ditampilkan."
            )

        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError("Respons login AWS BMKG bukan JSON yang valid.") from None

        if not isinstance(payload, dict) or payload.get("status") != "sukses" or not payload.get("token"):
            raise RuntimeError(
                "Login AWS BMKG tidak berhasil; periksa izin akun/token melalui pengelola API."
            )

        return str(payload["token"]).strip()

    raise RuntimeError("Login AWS BMKG gagal setelah 3 percobaan.")


def utc_request_window() -> tuple[datetime, datetime]:
    """
    Ambil rolling 23 jam 50 menit.
    Dipilih <24 jam agar tidak menyentuh batas maksimum API.
    """
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(hours=23, minutes=50)
    return start, end


def fmt_api_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def request_data(
    session: requests.Session,
    token: str,
    start: datetime,
    end: datetime,
) -> Any:
    """
    Request data resmi /getdata.

    Jika rolling window melintasi pergantian tahun, pecah request karena
    dokumentasi API mensyaratkan tahun tgl_mulai dan tgl_selesai sama.
    """
    windows: list[tuple[datetime, datetime]] = []

    if start.year == end.year:
        windows.append((start, end))
    else:
        end_first = datetime(
            start.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc
        )
        start_second = datetime(
            end.year, 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )
        windows.extend([(start, end_first), (start_second, end)])

    collected: list[Any] = []

    for win_start, win_end in windows:
        params = {
            "token": token,
            "filter": "*",
            "tgl_mulai": fmt_api_datetime(win_start),
            "tgl_selesai": fmt_api_datetime(win_end),
            "tipe_station": STATION_TYPE,
            "id_station": STATION_ID,
        }

        try:
            response = session.get(
                DATA_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            raise RuntimeError("Gagal menghubungi API data AWS BMKG.") from None
        if response.status_code >= 400:
            raise RuntimeError(
                f"API data AWS BMKG HTTP {response.status_code}. "
                "URL yang mengandung token tidak dicatat."
            )

        payload = response.json()

        if isinstance(payload, dict) and payload.get("status") == "gagal":
            raise RuntimeError(
                f"API AWS menolak request: {payload.get('message', payload)}"
            )

        collected.append(payload)

    if len(collected) == 1:
        return collected[0]

    return collected



def raw_month_url(year: int, month: int, today) -> str:
    """Build the year-scoped raw Excel URL using BMKG's downloadaccesdata_year route."""
    first = f"{year}-{month:02d}-01"
    month_last = calendar.monthrange(year, month)[1]
    last_day = min(month_last, today.day) if (year, month) == (today.year, today.month) else month_last
    last = f"{year}-{month:02d}-{last_day:02d}"
    return (
        f"{RAW_BASE}/downloadaccesdata_year/{year}/"
        f"{STATION_TYPE}/{STATION_ID}/{first}/{last}"
    )


def fetch_raw_excel(session: requests.Session, url: str) -> bytes:
    """Download an Excel export without logging response URLs or page contents."""
    retryable = {429, 500, 502, 503, 504}
    response = None
    for attempt in range(3):
        try:
            response = session.get(url, timeout=120)
        except requests.RequestException:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError("Gagal menghubungi endpoint rawdata AWS BMKG.") from None
        if response.status_code not in retryable or attempt == 2:
            break
        time.sleep(5 * (attempt + 1))

    if response is None or response.status_code != 200:
        code = response.status_code if response is not None else "unknown"
        raise RuntimeError(f"Unduhan rawdata AWS BMKG gagal: HTTP {code}.")
    if not response.content.startswith(b"PK"):
        raise RuntimeError(
            "Endpoint rawdata tidak mengembalikan file Excel. "
            "Kemungkinan akses endpoint memerlukan sesi atau sedang ditolak."
        )
    return response.content


def raw_excel_to_frame(content: bytes) -> pd.DataFrame:
    """Convert BMKG raw Excel headers to the fields expected by normalize()."""
    raw = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    aliases = {
        "ID Stasiun": "id_station",
        "id_stasiun": "id_station",
        "Nama Stasiun": "name_station",
        "Lattitude": "latt_station",
        "Latitude": "latt_station",
        "Longitude": "long_station",
        "Tanggal": "tanggal",
    }
    frame = raw.rename(columns=aliases).copy()
    if not {"id_station", "tanggal"}.issubset(frame.columns):
        raise RuntimeError(
            "File Excel rawdata tidak memuat kolom ID Stasiun dan Tanggal."
        )
    frame["id_station"] = frame["id_station"].astype(str).str.strip()
    frame = frame[frame["id_station"].eq(STATION_ID)].copy()
    return frame


def request_raw_export(
    session: requests.Session,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    """Download raw Excel by month and return only the recent rolling window."""
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    if end <= start:
        raise ValueError("Waktu akhir harus setelah waktu mulai.")

    today = end.date()
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month == 13:
            month, year = 1, year + 1

    frames = []
    for year, month in months:
        url = raw_month_url(year, month, today)
        content = fetch_raw_excel(session, url)
        (RAW_DIR / f"aws_{STATION_ID}_{year}-{month:02d}_raw.xlsx").write_bytes(content)
        frames.append(raw_excel_to_frame(content))

    if not frames:
        raise RuntimeError("Endpoint rawdata tidak menghasilkan file untuk rentang ini.")

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["_time_utc"] = pd.to_datetime(combined["tanggal"], utc=True, errors="coerce")
    combined = combined.dropna(subset=["_time_utc"])
    combined = (
        combined.drop_duplicates(["id_station", "_time_utc"], keep="last")
        .sort_values("_time_utc")
    )
    combined = combined[combined["_time_utc"].between(start, end)].copy()
    return combined.drop(columns=["_time_utc"]).reset_index(drop=True)


def flatten_payload(payload: Any) -> list[dict[str, Any]]:
    """
    API dapat mengembalikan list, object tunggal, atau wrapper.
    Fungsi ini mengekstrak record secara defensif.
    """
    records: list[dict[str, Any]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                walk(item)
            return

        if not isinstance(obj, dict):
            return

        # Record observasi dikenali dari timestamp + id stasiun.
        if "tanggal" in obj and "id_station" in obj:
            records.append(obj)
            return

        # Wrapper umum jika API mengubah struktur.
        for key in ("data", "result", "results"):
            if key in obj:
                walk(obj[key])

    walk(payload)
    return records


def dew_point_celsius(temp_c: float, rh_pct: float) -> float:
    """
    Magnus approximation.
    Hanya untuk membentuk kolom dew_point_c yang digunakan pipeline DIENGIN.
    """
    if pd.isna(temp_c) or pd.isna(rh_pct):
        return math.nan

    if rh_pct <= 0 or rh_pct > 100:
        return math.nan

    a = 17.625
    b = 243.04

    gamma = math.log(rh_pct / 100.0) + (a * temp_c) / (b + temp_c)
    return (b * gamma) / (a - gamma)


def normalize(records: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Normalisasi respons API tanpa membuang metadata quality flag BMKG.

    Prinsip Tahap 2:
    - nilai observasi disimpan apa adanya;
    - flag kualitas dari API ikut disimpan;
    - keputusan apakah flag tertentu harus dijadikan NaN untuk MODEL
      dilakukan pada Tahap 3 (preprocessing/prediction engine), bukan di sini.
    """
    if not records:
        raise RuntimeError(
            f"Tidak ada record yang diterima untuk stasiun {STATION_ID}."
        )

    df = pd.DataFrame(records)

    required_meta = ["tanggal", "id_station"]
    missing_meta = [c for c in required_meta if c not in df.columns]
    if missing_meta:
        raise RuntimeError(
            f"Respons API tidak memiliki kolom wajib: {missing_meta}"
        )

    # Pastikan benar-benar hanya STA2285.
    df = df[df["id_station"].astype(str) == STATION_ID].copy()

    if df.empty:
        raise RuntimeError(
            f"Respons API tidak memuat record untuk {STATION_ID}."
        )

    # Schema stabil untuk parameter + flag.
    for col in PARAMETERS:
        if col not in df.columns:
            df[col] = pd.NA

        flag_col = f"{col}_flag"
        if flag_col not in df.columns:
            df[flag_col] = pd.NA

    # API AWS Center memberi timestamp +00 (UTC).
    dt_utc = pd.to_datetime(df["tanggal"], utc=True, errors="coerce")
    df["datetime_utc"] = dt_utc
    df["datetime_wib"] = dt_utc.dt.tz_convert("Asia/Jakarta")

    for col in PARAMETERS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[f"{col}_flag"] = pd.to_numeric(
            df[f"{col}_flag"], errors="coerce"
        )

    # Dew point turunan. Nilai RH <= 0 menghasilkan NaN.
    df["dew_point_c"] = [
        dew_point_celsius(t, rh)
        for t, rh in zip(df["tt_air_avg"], df["rh_avg"])
    ]

    # Metadata
    keep = [
        "datetime_wib",
        "datetime_utc",
        "id_station",
        "name_station",
        "latt_station",
        "long_station",
        "elv_station",
        "nama_kota",
    ]

    # Parameter + flag disimpan berdampingan.
    for col in PARAMETERS:
        keep.extend([col, f"{col}_flag"])

    keep.append("dew_point_c")

    keep = [c for c in keep if c in df.columns]

    out = df[keep].copy()

    out = (
        out.dropna(subset=["datetime_utc"])
        .sort_values("datetime_utc")
        .drop_duplicates(subset=["datetime_utc"], keep="last")
        .reset_index(drop=True)
    )

    return out

def write_status(
    status: str,
    message: str,
    rows: int = 0,
    latest_utc: str | None = None,
    latest_wib: str | None = None,
) -> None:
    payload = {
        "status": status,
        "message": message,
        "station_id": STATION_ID,
        "station_type": STATION_TYPE,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "latest_observation_utc": latest_utc,
        "latest_observation_wib": latest_wib,
    }

    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )



def append_log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {message}\n")


def main() -> int:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "DIENGIN/1.0 (AWS monitoring and frost prediction)"
        }
    )

    try:
        start, end = utc_request_window()

        raw_export = request_raw_export(session, start, end)
        if raw_export.empty:
            raise RuntimeError(
                f"Tidak ada observasi {STATION_ID} pada rentang rolling terakhir."
            )

        RAW_EXPORT_PATH.write_text(
            raw_export.to_csv(index=False),
            encoding="utf-8",
        )

        df = normalize(raw_export.to_dict(orient="records"))
        observed = pd.to_datetime(df["datetime_utc"], utc=True, errors="coerce")
        df = df.loc[observed.between(start, end)].copy()
        if df.empty:
            raise RuntimeError(
                f"Tidak ada observasi valid {STATION_ID} pada rentang rolling terakhir."
            )
        df.to_csv(CSV_PATH, index=False)

        latest = df.iloc[-1]

        latest_utc = str(latest["datetime_utc"])
        latest_wib = str(latest["datetime_wib"])

        write_status(
            status="success",
            message="Data AWS Dieng berhasil diperbarui.",
            rows=len(df),
            latest_utc=latest_utc,
            latest_wib=latest_wib,
        )

        print("======================================")
        print(" DIENGIN - AWS INGESTION")
        print("======================================")
        print(f"Station       : {STATION_ID}")
        print(f"Jumlah data   : {len(df)}")
        print(f"Terbaru UTC   : {latest_utc}")
        print(f"Terbaru WIB   : {latest_wib}")
        print(f"CSV           : {CSV_PATH}")
        print(f"Raw JSON      : {RAW_JSON_PATH}")

        # Ringkasan flag untuk audit operasional.
        print("")
        print("Quality flag summary:")
        for p in PARAMETERS:
            fc = f"{p}_flag"
            if fc in df.columns:
                vc = df[fc].value_counts(dropna=False).to_dict()
                print(f"  {p:12} : {vc}")

        print("Status        : SUCCESS")
        append_log(f"SUCCESS | station={STATION_ID} | rows={len(df)} | latest_wib={latest_wib}")

        return 0

    except Exception as exc:
        write_status(
            status="error",
            message=str(exc),
        )

        append_log(f"ERROR | station={STATION_ID} | {exc}")
        print(f"[DIENGIN ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
