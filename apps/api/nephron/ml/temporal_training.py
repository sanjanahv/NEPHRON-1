from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .temporal import AlertBudgetMetrics, evaluate_alert_budget

TARGET = "event_within_horizon"
NUMERIC_FEATURES = [
    "minute",
    "current_sbp_mmhg",
    "current_dbp_mmhg",
    "sbp_change_from_baseline",
    "sbp_slope_30m",
    "current_uf_l_h",
    "current_blood_flow_ml_min",
    "age_years",
    "diabetes",
    "weight_start_kg",
    "dry_weight_kg",
    "body_temperature_c",
    "prior_session_count",
    "prior_idh_rate_10",
    "prior_mean_nadir_sbp_10",
    "previous_session_idh",
    "previous_nadir_sbp_mmhg",
]
CATEGORICAL_FEATURES = ["sex"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
LOAD_COLUMNS = ["patient_id", "session_id", "minutes_to_event", TARGET, *FEATURES]


def load_temporal(path: Path) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    frame = pd.read_csv(path, usecols=LOAD_COLUMNS, low_memory=False)
    target = frame[TARGET].astype(str).str.lower().map({"true": 1, "false": 0}).astype(int)
    context = frame[["session_id", "minute", "minutes_to_event"]].copy()
    return frame[FEATURES], target, context


def preprocessing() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [("numeric", numeric, NUMERIC_FEATURES), ("categorical", categorical, CATEGORICAL_FEATURES)]
    )


def candidates(seed: int = 2026) -> dict[str, Pipeline]:
    return {
        "temporal-logistic": Pipeline(
            [
                ("preprocess", preprocessing()),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=500,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "temporal-lightgbm": Pipeline(
            [
                ("preprocess", preprocessing()),
                (
                    "model",
                    LGBMClassifier(
                        objective="binary",
                        n_estimators=300,
                        learning_rate=0.04,
                        num_leaves=24,
                        max_depth=7,
                        min_child_samples=150,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        reg_alpha=0.2,
                        reg_lambda=0.5,
                        class_weight="balanced",
                        random_state=seed,
                        n_jobs=-1,
                        verbosity=-1,
                    ),
                ),
            ]
        ),
    }


def session_operating_threshold(
    context: pd.DataFrame,
    probabilities: np.ndarray,
    *,
    minimum_sensitivity: float = 0.80,
) -> float:
    scored = context.assign(probability=probabilities)
    scored["event"] = scored.groupby("session_id")["minutes_to_event"].transform(
        lambda values: int(values.notna().any())
    )
    timely = scored["minutes_to_event"].between(15, 60, inclusive="both")
    scored["eligible_probability"] = scored["probability"].where(
        (scored["event"] == 0) | timely
    )
    session = scored.groupby("session_id", sort=False).agg(
        maximum_probability=("eligible_probability", "max"),
        event=("event", "first"),
    )
    session["maximum_probability"] = session["maximum_probability"].fillna(0)
    thresholds = np.unique(np.quantile(session["maximum_probability"], np.linspace(0, 1, 201)))
    options: list[tuple[float, float, float]] = []
    for threshold in thresholds:
        predicted = session["maximum_probability"] >= threshold
        event = session["event"].astype(bool)
        sensitivity = float(predicted[event].mean()) if event.any() else 0.0
        false_rate = float((predicted & ~event).mean())
        if sensitivity >= minimum_sensitivity:
            options.append((false_rate, -float(threshold), float(threshold)))
    if options:
        return min(options)[2]
    return 0.5


def temporal_metrics(
    target: pd.Series,
    probabilities: np.ndarray,
    context: pd.DataFrame,
    threshold: float,
) -> dict[str, Any]:
    rows = tuple(
        (
            session_id,
            float(minute),
            float(probability),
            float(minute + lead) if pd.notna(lead) else None,
        )
        for session_id, minute, probability, lead in zip(
            context["session_id"],
            context["minute"],
            probabilities,
            context["minutes_to_event"],
            strict=True,
        )
    )
    duration = context.groupby("session_id")["minute"].max().to_dict()
    budget: AlertBudgetMetrics = evaluate_alert_budget(
        rows,
        threshold=threshold,
        session_duration_minutes=duration,
    )
    return {
        "row_auroc": round(float(roc_auc_score(target, probabilities)), 5),
        "row_auprc": round(float(average_precision_score(target, probabilities)), 5),
        "row_brier": round(float(brier_score_loss(target, probabilities)), 5),
        "threshold": round(threshold, 6),
        **asdict(budget),
    }


def train_temporal(data_dir: Path, artifact_dir: Path, report_dir: Path) -> dict[str, Any]:
    x_train, y_train, _ = load_temporal(data_dir / "temporal-train.csv")
    x_validation, y_validation, validation_context = load_temporal(
        data_dir / "temporal-validation.csv"
    )
    x_test, y_test, test_context = load_temporal(data_dir / "temporal-test.csv")

    results: dict[str, dict[str, Any]] = {}
    fitted: dict[str, CalibratedClassifierCV] = {}
    for name, pipeline in candidates().items():
        pipeline.fit(x_train, y_train)
        calibrated = CalibratedClassifierCV(FrozenEstimator(pipeline), method="sigmoid")
        calibrated.fit(x_validation, y_validation)
        probability = calibrated.predict_proba(x_validation)[:, 1]
        threshold = session_operating_threshold(validation_context, probability)
        results[name] = {
            "validation": temporal_metrics(
                y_validation, probability, validation_context, threshold
            )
        }
        fitted[name] = calibrated

    selected_name = max(results, key=lambda name: results[name]["validation"]["row_auprc"])
    selected = fitted[selected_name]
    threshold = results[selected_name]["validation"]["threshold"]
    test_probability = selected.predict_proba(x_test)[:, 1]
    results[selected_name]["test"] = temporal_metrics(
        y_test, test_probability, test_context, threshold
    )

    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": selected,
            "model_name": selected_name,
            "threshold": threshold,
            "features": FEATURES,
            "target": TARGET,
            "warning_horizon_minutes": 60,
            "minimum_lead_minutes": 15,
            "source_doi": "10.6084/m9.figshare.6260654.v3",
        },
        artifact_dir / "idh-temporal-warning.joblib",
    )
    report = {
        "selected_model": selected_name,
        "selection_rule": "highest validation row-level AUPRC after sigmoid calibration",
        "operating_rule": (
            "lowest session false-alert rate among validation thresholds with sensitivity >=0.80"
        ),
        "target": "first qualifying BP-proxy event 15 to 60 minutes ahead",
        "leakage_policy": "features stop strictly before the first qualifying event",
        "candidates": results,
    }
    (report_dir / "temporal-model-evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_temporal_model_card(report, report_dir / "TEMPORAL_MODEL_CARD.md")
    return report


def write_temporal_model_card(report: dict[str, Any], path: Path) -> None:
    selected = report["selected_model"]
    validation = report["candidates"][selected]["validation"]
    test = report["candidates"][selected]["test"]
    content = f"""# NADI-HD temporal IDH warning model

## Decision

**Research baseline only — disruptive clinical alarms are disabled.** The frozen patient-level test
result does not meet the prototype's alert-burden gate.

## Protocol

- Source: HEMOBP v3 (`10.6084/m9.figshare.6260654.v3`)
- Target: first qualifying BP-proxy event 15–60 minutes ahead
- Leakage control: features stop strictly before the first qualifying event
- Selected model: `{selected}`
- Threshold: {test['threshold']:.6f}, selected using validation sessions only

## Untouched patient-level test performance

| Metric | Value |
|---|---:|
| Event sessions | {test['event_sessions']:,} |
| Non-event sessions | {test['non_event_sessions']:,} |
| Row AUROC | {test['row_auroc']:.3f} |
| Row AUPRC | {test['row_auprc']:.3f} |
| Row Brier score | {test['row_brier']:.3f} |
| Session sensitivity | {test['session_sensitivity']:.3f} |
| Median timely warning | {test['median_warning_minutes']:.1f} min |
| False-alert sessions / 100 | {test['false_alerts_per_100_sessions']:.2f} |
| Premature-alert event sessions | {test['premature_alert_sessions']:,} |
| Late-alert event sessions | {test['late_alert_sessions']:,} |

Validation sensitivity was {validation['session_sensitivity']:.3f}; test sensitivity fell to
{test['session_sensitivity']:.3f}. The false-alert burden increased from
{validation['false_alerts_per_100_sessions']:.2f} to {test['false_alerts_per_100_sessions']:.2f} per
100 sessions. This result is not suitable for a nurse-facing alarm.

## Limitations

- BP-only proxy outcome; symptoms and interventions are unavailable.
- Observation timing is irregular and may reflect clinical concern.
- Single-centre Taiwanese retrospective cohort; external transportability is unknown.
- Repeated within-session measurements are correlated.
- Prospective workflow and alarm-fatigue evaluation is required.
"""
    path.write_text(content, encoding="utf-8")
