#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_STATUS = OUTPUT_DIR / "pipeline_status.json"
PIPELINE_LOG = LOG_DIR / "pipeline.log"

WIB = ZoneInfo("Asia/Jakarta")

STAGES = [
    ("download", SRC_DIR / "download_aws.py"),
    ("monitoring", SRC_DIR / "monitoring.py"),
    ("prediction", SRC_DIR / "predict.py"),
    ("history", SRC_DIR / "history.py"),
]


def now_iso():
    return datetime.now(WIB).isoformat()


def append_log(message):
    with PIPELINE_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{now_iso()} | {message}\n")


def save_status(payload):
    PIPELINE_STATUS.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def run_stage(name, script_path):
    if not script_path.is_file():
        return {
            "name": name,
            "status": "error",
            "returncode": None,
            "message": f"Script tidak ditemukan: {script_path}",
        }

    print("")
    print("======================================")
    print(f" DIENGIN - {name.upper()}")
    print("======================================")

    started = now_iso()
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    stage = {
        "name": name,
        "script": str(script_path),
        "status": "success" if result.returncode == 0 else "error",
        "returncode": int(result.returncode),
        "started_at_wib": started,
        "finished_at_wib": now_iso(),
    }

    if result.returncode != 0:
        stage["message"] = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Tahap gagal tanpa pesan."
        )

    return stage


def main():
    payload = {
        "status": "running",
        "started_at_wib": now_iso(),
        "finished_at_wib": None,
        "python_executable": sys.executable,
        "stages": [],
    }

    save_status(payload)
    append_log(f"PIPELINE START | python={sys.executable}")

    print("")
    print("######################################")
    print(" DIENGIN - MAIN PIPELINE v2")
    print("######################################")
    print("Python :", sys.executable)

    for name, script_path in STAGES:
        stage = run_stage(name, script_path)
        payload["stages"].append(stage)

        if stage["status"] != "success":
            payload["status"] = "error"
            payload["failed_stage"] = name
            payload["finished_at_wib"] = now_iso()
            save_status(payload)
            append_log(f"PIPELINE ERROR | stage={name}")
            print("")
            print("######################################")
            print(" DIENGIN - PIPELINE FAILED")
            print("######################################")
            print("Tahap gagal :", name)
            return 1

        save_status(payload)
        append_log(f"STAGE SUCCESS | {name}")

    payload["status"] = "success"
    payload["finished_at_wib"] = now_iso()
    save_status(payload)
    append_log("PIPELINE SUCCESS")

    print("")
    print("######################################")
    print(" DIENGIN - PIPELINE SUCCESS")
    print("######################################")
    print("Download    : SUCCESS")
    print("Monitoring  : SUCCESS")
    print("Prediction  : SUCCESS")
    print("History     : SUCCESS")
    print("Status JSON :", PIPELINE_STATUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
