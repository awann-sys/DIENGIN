#!/usr/bin/env python3
"""DIENGIN operational Streamlit entrypoint.

Uses the dashboard/UI code from app.py, but reads operational JSON/CSV
straight from the runtime branch so AWS/prediction history can refresh
without waiting for a Streamlit redeploy.

Also adds the rule-based EWS narrative layer and the centered dashboard
composition.
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pandas as pd
import streamlit as st

import app
import centered_dashboard
from ews_narrative import build_ews_narrative, render_ews_narrative

RUNTIME_RAW_BASE = "https://raw.githubusercontent.com/awann-sys/DIENGIN/runtime/"
_original_read_file = app.base.read_file
_original_render_weather = app.base.render_weather


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


def render_weather_with_ews(monitor):
    """Render centered weather cards, then the automatic EWS explanation."""
    _original_render_weather(monitor)

    try:
        pred, _ = read_operational_file("output/prediction_latest.json")
        release_history, _ = read_operational_file(
            "data/history/prediction_release_history.csv",
            "csv",
        )
        release_history = app.base.timed_frame(
            release_history,
            "waktu_rilis_wib",
        )

        try:
            bmkg_payload, _ = app.get_bmkg_forecast()
        except Exception:
            bmkg_payload = {}

        result = build_ews_narrative(
            monitor=monitor,
            pred=pred,
            release_history=release_history,
            bmkg_payload=bmkg_payload,
            now=pd.Timestamp.now(tz=app.base.WIB),
        )
        render_ews_narrative(result)
    except Exception as exc:
        # Narrative is explanatory only; it must never break the core dashboard.
        st.caption(f"Analisis otomatis EWS sementara belum tersedia ({type(exc).__name__}).")


# app_base resolves these globals at runtime. Core data/model behavior stays
# unchanged while the presentation becomes live, centered, and narrative-aware.
app.base.read_file = read_operational_file
app.base.render_weather = render_weather_with_ews
app.base.dashboard = centered_dashboard.dashboard


if __name__ == "__main__":
    app.base.main()
