"""Verify monthly AWS responses against a known nonempty daily request."""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from src.download_aws import get_token, request_data, flatten_payload, normalize
from src.archive_aws import store_months


def fetch_window(session, token, start, end, root):
    payload = request_data(session, token, start.astimezone(timezone.utc), end.astimezone(timezone.utc))
    rows = flatten_payload(payload)
    if not rows:
        return {'rows': 0, 'first_wib': None, 'last_wib': None}, set()
    frame = normalize(rows)
    dates = pd.to_datetime(frame['datetime_utc'], utc=True)
    frame = frame[dates.between(start, end)]
    store_months(frame, root)
    keys = set(pd.to_datetime(frame['datetime_utc'], utc=True).map(lambda t: t.isoformat()))
    local = pd.to_datetime(frame['datetime_utc'], utc=True).dt.tz_convert('Asia/Jakarta')
    return {'rows': len(frame), 'first_wib': local.min().isoformat() if len(frame) else None, 'last_wib': local.max().isoformat() if len(frame) else None, 'days_returned': int(local.dt.date.nunique())}, keys


def main():
    root = Path('archive')
    zone = ZoneInfo('Asia/Jakarta')
    now = datetime.now(zone)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'results': {}}
    with requests.Session() as session:
        token = get_token(session)
        tests = [
            ('current_month', month_start, now),
            ('reference_day', day_start, day_start + timedelta(days=1) - timedelta(seconds=1)),
            ('january_2020', datetime(2020, 1, 1, tzinfo=zone), datetime(2020, 2, 1, tzinfo=zone) - timedelta(seconds=1)),
        ]
        keys = {}
        for label, start, end in tests:
            try:
                result, keys[label] = fetch_window(session, token, start, end, root)
                report['results'][label] = {'request_start_wib': start.isoformat(), 'request_end_wib': end.isoformat(), 'status': 'ok', **result}
            except Exception as error:
                detail = str(error)
                for secret in [token, os.getenv('AWS_API_USERNAME'), os.getenv('AWS_API_PASSWORD')]:
                    if secret:
                        detail = detail.replace(secret, '[redacted]')
                detail = re.sub(r'https?://\S+', '[URL redacted]', detail)
                report['results'][label] = {'status': 'error', 'error_type': type(error).__name__, 'detail': detail[:240]}
            (root / 'monthly_probe.json').write_text(json.dumps(report, indent=2))
        reference = keys.get('reference_day', set())
        report['monthly_contains_reference_day'] = bool(reference) and reference.issubset(keys.get('current_month', set()))
        report['note'] = 'Empty responses alone do not verify monthly support or historical absence; inspect timestamps and the reference-day comparison.'
        (root / 'monthly_probe.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Monthly probe failed before results; verify credentials and API connectivity.') from None

