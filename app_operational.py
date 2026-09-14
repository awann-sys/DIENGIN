#!/usr/bin/env python3
"""DIENGIN operational Streamlit entrypoint.

Uses the dashboard/UI code from app.py, but reads operational JSON/CSV
straight from the runtime branch so AWS/prediction history can refresh
without waiting for a Streamlit redeploy.
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pandas as pd
import streamlit as st

import app

RUNTIME_RAW_BASE = "https://raw.githubusercontent.com/awann-sys/DIENGIN/runtime/"
_original_read_file = app.base.read_file


@st.cache_data(ttl=45, show_spinner=False)
def _read_runtime(relative: str, kind: str = "json"):
    url = RUNTIME_RAW_BASE + relative.lstrip("/")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DIENGIN/1.0 (+https://github.com/awann-sys/DIENGIN)",
            "Accept": "application/json,text/csv,text/plain,*/*",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        text = response.read().decode("utf-8")
    if not text.strip():
        return ({} if kind == "json" else pd.DataFrame()), "empty"
    if kind == "json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data, "ok"
    return pd.read_csv(io.StringIO(text)), "ok"


def read_operational_file(relative: str, kind: str = "json"):
    """Prefer live runtime-branch data; fall back to checked-out files."""
    try:
        return _read_runtime(relative, kind)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        pd.errors.ParserError,
    ):
        return _original_read_file(relative, kind)


# app.dashboard resolves base.read_file at runtime, so this keeps the
# approved UI while making the data source operational/live.
app.base.read_file = read_operational_file


if __name__ == "__main__":
    app.base.main()
