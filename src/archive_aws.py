"""Resumable BMKG observation archive. No model predictions are backfilled."""
from __future__ import annotations
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import requests
from src.download_aws import get_token, request_data, flatten_payload, normalize


def store_months(frame, root):
    if frame.empty:
        return 0
    frame = frame.copy()
    frame['datetime_utc'] = pd.to_datetime(frame['datetime_utc'], utc=True)
    frame['datetime_wib'] = frame['datetime_utc'].dt.tz_convert('Asia/Jakarta').map(lambda v: v.isoformat())
    frame['datetime_utc'] = frame['datetime_utc'].map(lambda v: v.isoformat())
    folder = root / 'observations'
    folder.mkdir(parents=True, exist_ok=True)
    for month, rows in frame.groupby(frame['datetime_wib'].str[:7]):
        target = folder / f'{month}.csv.gz'
        old = pd.read_csv(target) if target.exists() else pd.DataFrame()
        combined = pd.concat([old, rows], ignore_index=True).drop_duplicates(['id_station', 'datetime_utc'], keep='last').sort_values('datetime_utc')
        combined.to_csv(target, index=False, compression={'method': 'gzip', 'mtime': 0})
    return len(frame)


def download_day(session, token, day, root):
    # UTC days; downloader splits year boundaries if needed. Never >24h/request.
    end = min(day + timedelta(days=1) - timedelta(seconds=1), datetime.now(timezone.utc))
    payload = request_data(session, token, day, end)
    records = flatten_payload(payload)
    if not records:
        return 0
    frame = normalize(records)
    times = pd.to_datetime(frame['datetime_utc'], utc=True)
    return store_months(frame[(times >= day) & (times <= end)], root)


def run(root, limit):
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / 'archive_manifest.json'
    state = json.loads(manifest.read_text()) if manifest.exists() else {'station': 'STA2285', 'requested_start_utc': '2020-01-01', 'next_day_utc': '2020-01-01', 'days': {}}
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    with requests.Session() as session:
        token = get_token(session)
        # Update recent observations independently of historical progress.
        for day in [today - timedelta(days=1), today]:
            count = download_day(session, token, day, root)
            state['days'][day.date().isoformat()] = {'rows_received': count, 'checked_utc': datetime.now(timezone.utc).isoformat()}
            time.sleep(2)
        cursor = datetime.fromisoformat(state['next_day_utc']).replace(tzinfo=timezone.utc)
        for _ in range(limit):
            if cursor >= today:
                break
            count = download_day(session, token, cursor, root)
            state['days'][cursor.date().isoformat()] = {'rows_received': count, 'checked_utc': datetime.now(timezone.utc).isoformat()}
            cursor += timedelta(days=1)
            state['next_day_utc'] = cursor.date().isoformat()
            # Checkpoint only successful API responses; empty days stay explicit.
            state['updated_utc'] = datetime.now(timezone.utc).isoformat()
            manifest.write_text(json.dumps(state, indent=2))
            print(f'Archive checked through {cursor.date()}; rows received: {count}', flush=True)
            time.sleep(2)
    state['updated_utc'] = datetime.now(timezone.utc).isoformat()
    state['backfill_complete'] = cursor >= today
    state['months'] = sorted(p.stem.replace('.csv', '') for p in (root / 'observations').glob('*.csv.gz'))
    manifest.write_text(json.dumps(state, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('archive'))
    parser.add_argument('--days', type=int, default=30)
    args = parser.parse_args()
    try:
        run(args.root, max(1, min(args.days, 60)))
    except Exception:
        # API URLs/payloads can contain credentials. Never print raw exceptions.
        raise SystemExit('AWS archive failed: check API access, credentials and historical availability. Progress already saved will be retained.') from None

