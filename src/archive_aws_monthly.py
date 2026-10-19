"""Download BMKG raw Excel exports by calendar month, preserving source files."""
import argparse
import calendar
import io
import gzip
import shutil
import json
import sqlite3
from contextlib import closing
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from src.download_aws import dew_point_celsius

BASE = 'https://apiaws.bmkg.go.id/rawdata'
META = {'ID Stasiun': 'id_station', 'Nama Stasiun': 'station_name', 'Lattitude': 'latitude', 'Latitude': 'latitude', 'Longitude': 'longitude', 'Tanggal': 'datetime_utc'}


def month_url(year, month, today):
    last = min(calendar.monthrange(year, month)[1], today.day) if (year, month) == (today.year, today.month) else calendar.monthrange(year, month)[1]
    route = 'downloadaccesdata_currentyear' if year == today.year else f'downloadaccesdata_year/{year}'
    return f'{BASE}/{route}/aws/STA2285/{year}-{month:02d}-01/{year}-{month:02d}-{last:02d}'


def clean_excel(content):
    raw = pd.read_excel(io.BytesIO(content), engine='openpyxl')
    frame = raw.rename(columns=META).copy()
    if not {'id_station', 'datetime_utc'}.issubset(frame.columns):
        raise ValueError('Excel response lacks station/time headers')
    frame = frame[frame['id_station'].astype(str).eq('STA2285')].copy()
    frame['datetime_utc'] = pd.to_datetime(frame['datetime_utc'], utc=True, errors='coerce')
    invalid_times = int(frame['datetime_utc'].isna().sum())
    frame = frame.dropna(subset=['datetime_utc'])
    duplicate_count = int(frame.duplicated(['id_station', 'datetime_utc']).sum())
    frame = frame.sort_values('datetime_utc').drop_duplicates(['id_station', 'datetime_utc'], keep='last')
    metadata = {'id_station', 'station_name', 'datetime_utc'}
    for key in frame.columns:
        if key not in metadata:
            frame[key] = pd.to_numeric(frame[key], errors='coerce')
    flagged = 0
    for flag in list(frame.columns):
        if flag.endswith('_flag') and flag[:-5] in frame:
            bad = frame[flag].eq(1)
            flagged += int((bad & frame[flag[:-5]].notna()).sum())
            frame.loc[bad, flag[:-5]] = float('nan')
    if 'tt_air_avg' in frame and 'rh_avg' in frame:
        frame['dew_point_c'] = [dew_point_celsius(t, rh) for t, rh in zip(frame['tt_air_avg'], frame['rh_avg'])]
    frame['datetime_wib'] = frame['datetime_utc'].dt.tz_convert('Asia/Jakarta').map(lambda v: v.isoformat())
    frame['datetime_utc'] = frame['datetime_utc'].map(lambda v: v.isoformat())
    return frame, {'raw_rows': len(raw), 'clean_rows': len(frame), 'invalid_times': invalid_times, 'duplicate_rows': duplicate_count, 'flagged_values_removed': flagged}


def rebuild(root):
    files = sorted((root / 'observations').glob('*.csv.gz'))
    if not files:
        return 0
    data = pd.concat([pd.read_csv(p) for p in files], ignore_index=True, sort=False)
    data = data.sort_values('datetime_utc').drop_duplicates(['id_station', 'datetime_utc'], keep='last')
    data.to_csv(root / 'aws_dieng_merged.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    with closing(sqlite3.connect(root / 'aws_dieng.sqlite')) as connection:
        data.to_sql('observations', connection, if_exists='replace', index=False, chunksize=1000)
        connection.execute('CREATE UNIQUE INDEX observation_station_time ON observations(id_station, datetime_utc)')
        connection.commit()
    with open(root / 'aws_dieng.sqlite', 'rb') as source, gzip.GzipFile(str(root / 'aws_dieng.sqlite.gz'), 'wb', mtime=0) as target:
        shutil.copyfileobj(source, target)
    return len(data)


def run(root, limit=72):
    today = datetime.now(ZoneInfo('Asia/Jakarta')).date()
    for folder in ['raw', 'observations']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    path = root / 'archive_manifest.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    state.pop('days', None)
    state.pop('next_day_utc', None)
    state.update({'station': 'STA2285', 'source': 'BMKG rawdata monthly Excel', 'requested_start_utc': '2021-01-01', 'requested_start': '2021-01', 'batch': 'calendar_month'})
    state.setdefault('months_checked', {})
    months = [(year, month) for year in range(2021, today.year + 1) for month in range(1, 13) if (year, month) <= (today.year, today.month)]
    # Refresh the current month every run, then continue pending historical months.
    def needs_refresh(year, month):
        entry = state['months_checked'].get(f'{year}-{month:02d}', {})
        if entry.get('url') != month_url(year, month, today):
            return True
        if entry.get('status') not in ('downloaded', 'empty'):
            return True
        if entry.get('status') == 'empty':
            checked = datetime.fromisoformat(entry['checked_utc'])
            return entry.get('url') != month_url(year, month, today) or (datetime.now(timezone.utc) - checked).days >= 7
        return False
    pending = [(y, m) for y, m in months if needs_refresh(y, m)]
    previous = today.replace(day=1) - timedelta(days=1)
    work = list(dict.fromkeys([(today.year, today.month), (previous.year, previous.month)] + pending))[:limit]
    failure = False
    with requests.Session() as session:
        session.headers['User-Agent'] = 'DIENGIN monthly AWS archive'
        for year, month in work:
            name = f'{year}-{month:02d}'
            url = month_url(year, month, today)
            entry = {'url': url, 'checked_utc': datetime.now(timezone.utc).isoformat()}
            try:
                for attempt in range(3):
                    response = session.get(url, timeout=120)
                    if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                        break
                    time.sleep(5 * (attempt + 1))
                if response.status_code != 200 or not response.content.startswith(b'PK'):
                    raise ValueError(f'Not an Excel download: HTTP {response.status_code}')
                (root / 'raw' / f'{name}.xlsx').write_bytes(response.content)
                frame, audit = clean_excel(response.content)
                # currentyear can lag the live export. Merge the live month as
                # an additional source, with newer live records taking priority.
                if (year, month) == (today.year, today.month):
                    recent_url = url.replace('/downloadaccesdata_currentyear/', '/downloadaccesdata/')
                    recent_response = session.get(recent_url, timeout=120)
                    if recent_response.status_code != 200 or not recent_response.content.startswith(b'PK'):
                        raise ValueError('Live monthly supplement failed')
                    (root / 'raw' / f'{name}_recent.xlsx').write_bytes(recent_response.content)
                    recent, recent_audit = clean_excel(recent_response.content)
                    combined = pd.concat([frame, recent], ignore_index=True)
                    overlap = int(combined.duplicated(['id_station', 'datetime_utc']).sum())
                    frame = combined.drop_duplicates(['id_station', 'datetime_utc'], keep='last').sort_values('datetime_utc')
                    audit = {key: audit[key] + recent_audit[key] for key in audit}
                    audit['duplicate_rows'] += overlap
                    audit['clean_rows'] = len(frame)
                    entry['supplement_url'] = recent_url
                    entry['supplement_rows'] = len(recent)
                # Range endpoints in rawdata exports are UTC dates; keep WIB conversion explicit.
                times = pd.to_datetime(frame['datetime_utc'], utc=True)
                unexpected = int((times.dt.year.ne(year) | times.dt.month.ne(month)).sum())
                if unexpected:
                    raise ValueError('Source returned timestamps outside the requested UTC month')
                frame.to_csv(root / 'observations' / f'{name}.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
                entry.update(audit, status='downloaded' if len(frame) else 'empty', first_utc=frame['datetime_utc'].min() if len(frame) else None, last_utc=frame['datetime_utc'].max() if len(frame) else None)
            except Exception as error:
                entry.update(status='error', error_type=type(error).__name__)
                failure = True
            state['months_checked'][name] = entry
            state['months'] = sorted(p.name[:7] for p in (root / 'observations').glob('*.csv.gz'))
            remaining = [f'{y}-{m:02d}' for y, m in months if needs_refresh(y, m)]
            state['next_month'] = remaining[0] if remaining else None
            state['backfill_complete'] = not remaining
            state['updated_utc'] = datetime.now(timezone.utc).isoformat()
            path.write_text(json.dumps(state, indent=2))
            print(f'{name}: {entry["status"]}; rows={entry.get("clean_rows", 0)}', flush=True)
            time.sleep(1)
    state['merged_rows'] = rebuild(root)
    path.write_text(json.dumps(state, indent=2))
    if failure:
        raise SystemExit('Some monthly downloads failed; successful months were retained and failed months will be retried.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('archive'))
    parser.add_argument('--months', type=int, default=72)
    args = parser.parse_args()
    run(args.root, max(1, min(args.months, 72)))

