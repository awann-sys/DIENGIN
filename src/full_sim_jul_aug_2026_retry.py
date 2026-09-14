#!/usr/bin/env python3
"""Retry wrapper for the full Jul-Aug simulation with token refresh."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pandas as pd
import requests

import download_aws as dl
import full_sim_jul_aug_2026 as sim


def download_period_refresh() -> pd.DataFrame:
    start_wib = datetime.combine(
        sim.TARGET_START - timedelta(days=1), time(15, 0), tzinfo=sim.WIB
    )
    end_wib = datetime.combine(
        sim.TARGET_END + timedelta(days=1), time(8, 0), tzinfo=sim.WIB
    )
    start_utc = start_wib.astimezone(timezone.utc)
    end_utc = end_wib.astimezone(timezone.utc)

    session = requests.Session()
    session.headers.update({"User-Agent": "DIENGIN/1.0 full Jul-Aug 2026 simulation"})
    token = dl.get_token(session)

    frames = []
    audit = []
    cursor = start_utc
    chunk_id = 0

    while cursor < end_utc:
        chunk_end = min(cursor + timedelta(hours=23, minutes=50), end_utc)

        # The AWS token can expire during a 2-month historical pull.
        # Refresh proactively every 8 chunks and once more on an expiry response.
        if chunk_id > 0 and chunk_id % 8 == 0:
            token = dl.get_token(session)

        try:
            payload = dl.request_data(session, token, cursor, chunk_end)
        except RuntimeError as exc:
            if "Token sudah expired" not in str(exc):
                raise
            token = dl.get_token(session)
            payload = dl.request_data(session, token, cursor, chunk_end)

        records = dl.flatten_payload(payload)
        frame = dl.normalize(records)
        frames.append(frame)
        audit.append({
            "chunk": chunk_id,
            "start_utc": cursor.isoformat(),
            "end_utc": chunk_end.isoformat(),
            "rows": int(len(frame)),
        })
        print(f"Downloaded chunk {chunk_id:02d}: {cursor} -> {chunk_end}, rows={len(frame)}", flush=True)
        chunk_id += 1
        cursor = chunk_end

    aws = pd.concat(frames, ignore_index=True)
    aws = (
        aws.sort_values("datetime_utc")
        .drop_duplicates(subset=["datetime_utc"], keep="last")
        .reset_index(drop=True)
    )
    aws.to_csv(
        sim.DATA_DIR / "aws_sta2285_2026-06-30_to_2026-09-01.csv", index=False
    )
    pd.DataFrame(audit).to_csv(sim.OUT / "download_chunks.csv", index=False)
    return aws


sim.download_period = download_period_refresh

if __name__ == "__main__":
    raise SystemExit(sim.main())
