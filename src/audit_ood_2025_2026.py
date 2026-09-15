#!/usr/bin/env python3
"""Audit DIENGIN model behaviour on 2025 replay and selected 2026 frost nights.

Audit-only: no retraining and no operational output overwrite.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree
from sklearn.metrics import brier_score_loss, confusion_matrix, log_loss, roc_auc_score

import download_aws as dl
import predict as pred

WIB = ZoneInfo("Asia/Jakarta")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT = PROJECT_ROOT / "output" / "ood_audit_2025_2026"
DATA_OUT = PROJECT_ROOT / "data" / "audit"
OUT.mkdir(parents=True, exist_ok=True)
DATA_OUT.mkdir(parents=True, exist_ok=True)

FROST_2025 = {
    pd.Timestamp(x).date()
    for x in [
        "2025-04-28", "2025-07-10", "2025-07-11", "2025-07-12",
        "2025-07-18", "2025-07-19", "2025-07-20", "2025-07-21",
        "2025-07-27", "2025-07-30",
    ]
}
FROST_2026_SELECTED = [
    pd.Timestamp(x).date()
    for x in [
        "2026-08-23", "2026-08-26", "2026-08-27", "2026-08-31",
        "2026-09-01", "2026-09-06", "2026-09-15",
    ]
]

NOTEBOOK_EXPECTED = {
    "ANN": {"N": 363, "Events": 10, "TP": 5, "FP": 16, "FN": 5, "TN": 337,
            "Brier": 0.249053, "BSS": -8.295219, "LogLoss": 0.739060, "AUC": 0.930312},
    "SVM": {"N": 363, "Events": 10, "TP": 8, "FP": 14, "FN": 2, "TN": 339,
            "Brier": 0.014325, "BSS": 0.465362, "LogLoss": 0.067421, "AUC": 0.978754},
    "RF": {"N": 363, "Events": 10, "TP": 7, "FP": 5, "FN": 3, "TN": 348,
           "Brier": 0.013130, "BSS": 0.509964, "LogLoss": 0.050462, "AUC": 0.985411},
    "Stacked Ensemble": {"N": 363, "Events": 10, "TP": 7, "FP": 3, "FN": 3, "TN": 350,
                         "Brier": 0.013705, "BSS": 0.488491, "LogLoss": 0.061639, "AUC": 0.971671},
}
MODEL_COLS = {
    "ANN": "ann_prob", "SVM": "svm_prob", "RF": "rf_prob",
    "Stacked Ensemble": "stack_prob",
}


def json_default(v):
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if pd.isna(v):
        return None
    return str(v)


def request_retry(session, token, start, end, label, attempts=5):
    current = token
    for attempt in range(1, attempts + 1):
        try:
            return dl.request_data(session, current, start, end), current
        except Exception as exc:
            if attempt == attempts:
                raise RuntimeError(f"request failed {label}: {exc}") from exc
            wait = min(attempt * 3, 12)
            print(f"WARN {label} attempt={attempt}: {exc}; retry {wait}s")
            time.sleep(wait)
            try:
                current = dl.get_token(session)
            except Exception:
                pass


def download_utc_days(session, token, first_day, last_day):
    records, failures = [], []
    day = pd.Timestamp(first_day).date()
    last = pd.Timestamp(last_day).date()
    n = 0
    while day <= last:
        start = datetime.combine(day, dtime(0, 0), tzinfo=timezone.utc)
        end = datetime.combine(day, dtime(23, 50), tzinfo=timezone.utc)
        try:
            payload, token = request_retry(session, token, start, end, day.isoformat())
            records.extend(dl.flatten_payload(payload))
        except Exception as exc:
            failures.append({"day": day.isoformat(), "error": str(exc)})
            print("ERROR", day, exc)
        n += 1
        if n % 30 == 0:
            print(f"days={n}, records={len(records)}, failures={len(failures)}")
        time.sleep(0.05)
        day += timedelta(days=1)
    return records, failures, token


def download_target_window(session, token, target):
    start_wib = datetime.combine(target - timedelta(days=1), dtime(15, 0), tzinfo=WIB)
    end_wib = datetime.combine(target, dtime(8, 0), tzinfo=WIB)
    payload, token = request_retry(
        session, token, start_wib.astimezone(timezone.utc),
        end_wib.astimezone(timezone.utc), target.isoformat()
    )
    return dl.normalize(dl.flatten_payload(payload)), token


def pipeline_frame(aws, pipeline, year=None):
    path = DATA_OUT / "_audit_input.csv"
    aws.to_csv(path, index=False)
    pred.DATA_PATH = path
    data, adapter_audit = pred.load_operational_aws()
    data, model_audit = pred.apply_model_qc(data, pipeline["config"]["qc_limits"])
    data = pred.assign_night_date(data)
    feat = pred.build_features_10min(data, pipeline["config"].get("rr_mode", "cumulative"))
    feat = pred.apply_frozen_monthly_anomaly(feat, pipeline["config"]["monthly_anomaly_reference"])
    night = feat[feat["is_night"].eq(1)].copy().reset_index(drop=True)
    if year is not None:
        yy = pd.to_datetime(pd.Series(night["night_date"])).dt.year.to_numpy()
        night = night.loc[yy == int(year)].copy().reset_index(drop=True)
    raw, imp, scaled = pred.prepare_model_matrix(night, pipeline["config"], pipeline["scaler"])
    prediction = pred.predict_10min(night, scaled, pipeline)
    return night, raw, imp, np.asarray(scaled, float), prediction, adapter_audit + model_audit


def release_with_features(night, raw, imp, scaled, prediction, pipeline, now_wib):
    release = pred.build_release_table(prediction, pipeline["release_hours"], now_wib)
    release = pred.add_stacked_probability(release, pipeline["meta"], pipeline["threshold"])
    rows = []
    for _, r in release.iterrows():
        idx = int(r["source_row_index"])
        row = r.drop(labels=["_urutan_rilis"], errors="ignore").to_dict()
        src = night.iloc[idx]
        for c in ["tt_air_avg", "tt_air_min", "rh_avg", "ws_avg"]:
            row[c] = src.get(c, np.nan)
        row["n_missing_raw_features"] = int(raw.iloc[idx].isna().sum())
        for j, f in enumerate(pipeline["feature_cols"]):
            row[f"raw__{f}"] = raw.iloc[idx][f]
            row[f"imp__{f}"] = imp.iloc[idx][f]
            row[f"z__{f}"] = float(scaled[idx, j])
        rows.append(row)
    return pd.DataFrame(rows)


def add_geometry(release, pipeline):
    if release.empty:
        return release
    zcols = [f"z__{f}" for f in pipeline["feature_cols"]]
    X = release[zcols].to_numpy(float)
    absx = np.abs(X)
    out = release.copy()
    out["z_abs_max"] = absx.max(axis=1)
    out["z_abs_mean"] = absx.mean(axis=1)
    out["z_count_gt3"] = (absx > 3).sum(axis=1)
    out["z_count_gt5"] = (absx > 5).sum(axis=1)

    svm = pipeline["svm_core"]
    svtree = cKDTree(np.asarray(svm.support_vectors_, float))
    d, _ = svtree.query(X, k=1)
    gamma = float(getattr(svm, "_gamma", 1.0 / X.shape[1]))
    out["svm_nearest_support_distance"] = d
    out["svm_max_support_kernel"] = np.exp(-gamma * d * d)

    rf = pipeline["rf"]
    supports = np.empty((len(X), len(rf.estimators_)), dtype=np.float32)
    for j, tree in enumerate(rf.estimators_):
        leaf = tree.apply(X)
        supports[:, j] = tree.tree_.n_node_samples[leaf]
    out["rf_leaf_support_mean"] = supports.mean(axis=1)
    out["rf_leaf_support_median"] = np.median(supports, axis=1)
    out["rf_leaf_support_p10"] = np.quantile(supports, 0.10, axis=1)
    out["rf_leaf_fraction_support_le5"] = (supports <= 5).mean(axis=1)
    return out


def err(actual, predicted):
    return {(1, 1): "TP", (0, 1): "FP", (1, 0): "FN", (0, 0): "TN"}[(int(actual), int(predicted))]


def aggregate_nights(release, pipeline, frost_dates):
    rows = []
    thresholds = pipeline["config"]["frozen_night_thresholds"]
    for night_date, g in release.groupby("tanggal_target", sort=True):
        date = pd.Timestamp(night_date).date()
        actual = int(date in frost_dates)
        row = {"night_date": date.isoformat(), "actual_frost": actual, "n_releases": int(len(g))}
        for model, col in MODEL_COLS.items():
            vals = pd.to_numeric(g[col], errors="coerce")
            if vals.notna().any():
                idx = vals.idxmax()
                pmax = float(vals.loc[idx])
                hour = int(g.loc[idx, "jam_rilis_wib"])
            else:
                pmax, hour = np.nan, np.nan
            threshold = float(thresholds[model])
            prediction = int(pmax >= threshold) if np.isfinite(pmax) else np.nan
            slug = model.lower().replace(" ", "_")
            row[f"{slug}_pmax"] = pmax
            row[f"{slug}_pmax_hour"] = hour
            row[f"{slug}_threshold"] = threshold
            row[f"{slug}_prediction"] = prediction
            row[f"{slug}_error"] = err(actual, prediction) if np.isfinite(prediction) else "NA"
        rows.append(row)
    return pd.DataFrame(rows)


def score_nights(nights, pipeline):
    y = nights["actual_frost"].to_numpy(int)
    clim = float(pipeline["config"]["train_night_climatology"])
    reference_brier = float(np.mean((y - clim) ** 2))
    rows = []
    for model in MODEL_COLS:
        slug = model.lower().replace(" ", "_")
        p = nights[f"{slug}_pmax"].to_numpy(float)
        c = nights[f"{slug}_prediction"].to_numpy(int)
        valid = np.isfinite(p)
        yy = y[valid]
        pp = np.clip(p[valid], 1e-7, 1 - 1e-7)
        cc = c[valid]
        tn, fp, fn, tp = confusion_matrix(yy, cc, labels=[0, 1]).ravel()
        bs = brier_score_loss(yy, pp)
        rows.append({
            "Model": model, "N": len(yy), "Events": int(yy.sum()),
            "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
            "Brier": float(bs),
            "BSS": float(1 - bs / reference_brier) if reference_brier else np.nan,
            "LogLoss": float(log_loss(yy, pp, labels=[0, 1])),
            "AUC": float(roc_auc_score(yy, pp)) if np.unique(yy).size == 2 else np.nan,
        })
    return pd.DataFrame(rows)


def compare_notebook(replay):
    rows = []
    for _, r in replay.iterrows():
        exp = NOTEBOOK_EXPECTED[r["Model"]]
        out = {"Model": r["Model"]}
        for key in ["N", "Events", "TP", "FP", "FN", "TN", "Brier", "BSS", "LogLoss", "AUC"]:
            out[f"notebook_{key}"] = exp[key]
            out[f"replay_{key}"] = r[key]
            out[f"delta_{key}"] = float(r[key]) - float(exp[key])
        rows.append(out)
    return pd.DataFrame(rows)


def group_probability_summary(nights):
    cols = ["ann_pmax", "svm_pmax", "rf_pmax", "stacked_ensemble_pmax"]
    rows = []
    for et, g in nights.groupby("stacked_ensemble_error"):
        row = {"stack_error_type": et, "N": len(g), "frost_nights": int(g["actual_frost"].sum())}
        for c in cols:
            x = pd.to_numeric(g[c], errors="coerce")
            for s, v in {"mean": x.mean(), "median": x.median(), "min": x.min(),
                         "p25": x.quantile(.25), "p75": x.quantile(.75), "max": x.max()}.items():
                row[f"{c}_{s}"] = v
        rows.append(row)
    return pd.DataFrame(rows)


def feature_neighbours(release25, release26):
    zcols = [c for c in release25.columns if c.startswith("z__")]
    X25 = release25[zcols].to_numpy(float)
    tree = cKDTree(X25)
    selfd, _ = tree.query(X25, k=2)
    loo = selfd[:, 1]
    d26, i26 = tree.query(release26[zcols].to_numpy(float), k=1)
    out = release26.copy()
    out["nearest_2025_release_distance"] = d26
    out["nearest_2025_release_percentile"] = [(loo <= d).mean() * 100 for d in d26]
    out["nearest_2025_release_target"] = [
        pd.Timestamp(release25.iloc[int(i)]["tanggal_target"]).date().isoformat() for i in i26
    ]
    out["nearest_2025_release_hour"] = [int(release25.iloc[int(i)]["jam_rilis_wib"]) for i in i26]
    out["nearest_2025_release_actual_frost"] = [int(release25.iloc[int(i)]["actual_frost"]) for i in i26]
    return out


def probability_neighbours(n25, n26):
    cols = ["ann_pmax", "svm_pmax", "rf_pmax", "stacked_ensemble_pmax"]
    X = n25[cols].to_numpy(float)
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1
    Z = (X - mu) / sd
    tree = cKDTree(Z)
    selfd, _ = tree.query(Z, k=2)
    loo = selfd[:, 1]
    d, idx = tree.query((n26[cols].to_numpy(float) - mu) / sd, k=1)
    out = n26.copy()
    out["nearest_2025_probability_distance"] = d
    out["nearest_2025_probability_percentile"] = [(loo <= x).mean() * 100 for x in d]
    out["nearest_2025_probability_night"] = [n25.iloc[int(i)]["night_date"] for i in idx]
    out["nearest_2025_probability_error"] = [n25.iloc[int(i)]["stacked_ensemble_error"] for i in idx]
    out["nearest_2025_probability_actual_frost"] = [int(n25.iloc[int(i)]["actual_frost"]) for i in idx]
    return out


def percentile(series, value):
    x = pd.to_numeric(series, errors="coerce").dropna().to_numpy(float)
    return float((x <= value).mean() * 100) if len(x) and np.isfinite(value) else np.nan


def main():
    pipeline = pred.load_pipeline()
    session = requests.Session()
    session.headers.update({"User-Agent": "DIENGIN/1.0 OOD audit 2025-2026"})
    token = dl.get_token(session)

    print("Download 2025 replay...")
    rec25, failures25, token = download_utc_days(session, token, "2024-12-31", "2025-12-31")
    if failures25:
        pd.DataFrame(failures25).to_csv(OUT / "download_failures_2025.csv", index=False)
    aws25 = dl.normalize(rec25)
    aws25.to_csv(DATA_OUT / "aws_api_replay_2025.csv", index=False)

    n25, raw25, imp25, sc25, p25, qc25 = pipeline_frame(aws25, pipeline, 2025)
    rel25 = release_with_features(
        n25, raw25, imp25, sc25, p25, pipeline,
        pd.Timestamp("2026-01-01 12:00:00", tz=WIB),
    )
    rel25 = add_geometry(rel25, pipeline)
    rel25["actual_frost"] = [int(pd.Timestamp(x).date() in FROST_2025) for x in rel25["tanggal_target"]]
    nights25 = aggregate_nights(rel25, pipeline, FROST_2025)
    metrics25 = score_nights(nights25, pipeline)
    parity25 = compare_notebook(metrics25)
    groups25 = group_probability_summary(nights25)

    rel25.to_csv(OUT / "release_diagnostics_2025_api_replay.csv", index=False)
    nights25.to_csv(OUT / "night_predictions_2025_api_replay.csv", index=False)
    metrics25.to_csv(OUT / "metrics_2025_api_replay.csv", index=False)
    parity25.to_csv(OUT / "notebook_expected_vs_api_replay.csv", index=False)
    groups25.to_csv(OUT / "probability_by_stacked_error_type_2025.csv", index=False)
    pd.DataFrame(qc25).to_csv(OUT / "qc_2025_api_replay.csv", index=False)

    rel26_list, n26_list, qc26_rows = [], [], []
    for target in FROST_2026_SELECTED:
        print("Download 2026", target)
        aws26, token = download_target_window(session, token, target)
        n26, _, _, _, _, qc26 = pipeline_frame(aws26, pipeline, 2026)
        n26 = n26[pd.Series(n26["night_date"]).eq(target)].copy().reset_index(drop=True)
        raw26, imp26, sc26 = pred.prepare_model_matrix(n26, pipeline["config"], pipeline["scaler"])
        p26 = pred.predict_10min(n26, sc26, pipeline)
        rel26 = release_with_features(
            n26, raw26, imp26, np.asarray(sc26, float), p26, pipeline,
            pd.Timestamp(datetime.combine(target, dtime(8, 0), tzinfo=WIB)),
        )
        rel26 = add_geometry(rel26, pipeline)
        rel26["actual_frost"] = 1
        rel26["target_date_text"] = target.isoformat()
        rel26_list.append(rel26)
        n26_list.append(aggregate_nights(rel26, pipeline, {target}))
        qc26_rows.extend({"target_date": target.isoformat(), **q} for q in qc26)

    rel26 = pd.concat(rel26_list, ignore_index=True)
    nights26 = pd.concat(n26_list, ignore_index=True)
    rel26 = feature_neighbours(rel25, rel26)
    nights26 = probability_neighbours(nights25, nights26)

    diagnostic_cols = [
        "z_abs_max", "z_abs_mean", "z_count_gt3", "z_count_gt5",
        "svm_nearest_support_distance", "rf_leaf_support_mean",
        "rf_leaf_support_median", "rf_leaf_fraction_support_le5",
    ]
    for c in diagnostic_cols:
        rel26[f"pct_vs_2025__{c}"] = [percentile(rel25[c], v) for v in rel26[c]]

    key_rows = []
    for target, g in rel26.groupby("target_date_text"):
        for selector, pcol in [("stack_max_release", "stack_prob"), ("ann_max_release", "ann_prob")]:
            gg = g.dropna(subset=[pcol])
            r = gg.loc[gg[pcol].idxmax()]
            row = {
                "target_date": target, "selector": selector,
                "release_hour": int(r["jam_rilis_wib"]),
                "ann_prob": r["ann_prob"], "svm_prob": r["svm_prob"],
                "rf_prob": r["rf_prob"], "stack_prob": r["stack_prob"],
                "tt_air_avg": r["tt_air_avg"], "tt_air_min": r["tt_air_min"],
                "rh_avg": r["rh_avg"], "ws_avg": r["ws_avg"],
                "n_missing_raw_features": int(r["n_missing_raw_features"]),
                "z_abs_max": r["z_abs_max"], "z_count_gt3": int(r["z_count_gt3"]),
                "svm_nearest_support_distance": r["svm_nearest_support_distance"],
                "svm_max_support_kernel": r["svm_max_support_kernel"],
                "rf_leaf_support_median": r["rf_leaf_support_median"],
                "rf_leaf_fraction_support_le5": r["rf_leaf_fraction_support_le5"],
                "nearest_2025_release_distance": r["nearest_2025_release_distance"],
                "nearest_2025_release_percentile": r["nearest_2025_release_percentile"],
                "nearest_2025_release_target": r["nearest_2025_release_target"],
                "nearest_2025_release_hour": int(r["nearest_2025_release_hour"]),
                "nearest_2025_release_actual_frost": int(r["nearest_2025_release_actual_frost"]),
            }
            for c in diagnostic_cols:
                row[f"pct_vs_2025__{c}"] = r[f"pct_vs_2025__{c}"]
            key_rows.append(row)
    key26 = pd.DataFrame(key_rows)

    rel26.to_csv(OUT / "release_diagnostics_selected_2026.csv", index=False)
    nights26.to_csv(OUT / "night_probability_neighbours_selected_2026.csv", index=False)
    key26.to_csv(OUT / "selected_2026_key_release_diagnostics.csv", index=False)
    pd.DataFrame(qc26_rows).to_csv(OUT / "qc_selected_2026.csv", index=False)

    exact = True
    for _, r in parity25.iterrows():
        for k in ["N", "Events", "TP", "FP", "FN", "TN"]:
            exact &= int(round(r[f"delta_{k}"])) == 0

    stackkey = key26[key26["selector"].eq("stack_max_release")].copy()
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "notebook_expected_nights_2025": 363,
        "api_replay_nights_2025": int(len(nights25)),
        "api_replay_download_failed_days": int(len(failures25)),
        "exact_2025_confusion_parity_with_notebook": bool(exact),
        "selected_2026_dates": [x.isoformat() for x in FROST_2026_SELECTED],
        "feature_space_ood95_stackmax_dates": stackkey.loc[
            stackkey["nearest_2025_release_percentile"] >= 95, "target_date"
        ].tolist(),
        "threshold_stacked": float(pipeline["threshold"]),
    }
    (OUT / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8"
    )

    print("\n=== NOTEBOOK vs 2025 API REPLAY ===")
    print(parity25.to_string(index=False))
    print("\n=== 2025 STACK ERROR GROUPS ===")
    print(groups25.to_string(index=False))
    print("\n=== 2026 NIGHT PROBABILITY NEIGHBOURS ===")
    print(nights26.to_string(index=False))
    print("\n=== 2026 KEY RELEASE DIAGNOSTICS ===")
    print(key26.to_string(index=False))
    print("\nSUMMARY")
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
