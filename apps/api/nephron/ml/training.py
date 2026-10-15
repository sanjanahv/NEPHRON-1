from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "label_drop20_nadir90"
NUMERIC_FEATURES = [
    "age_years",
    "diabetes",
    "weight_start_kg",
    "dry_weight_kg",
    "weight_gain_kg",
    "body_temperature_c",
    "baseline_sbp_mmhg",
    "baseline_dbp_mmhg",
    "initial_uf_l_h",
    "initial_uf_ml_kg_h",
    "initial_blood_flow_ml_min",
    "initial_dialysate_temperature_c",
    "initial_conductivity_ms_cm",
    "prior_session_count",
    "prior_idh_rate_10",
    "prior_mean_nadir_sbp_10",
    "prior_mean_sbp_drop_10",
    "previous_session_idh",
    "previous_nadir_sbp_mmhg",
]
CATEGORICAL_FEATURES = ["sex"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


@dataclass(frozen=True)
class Metrics:
    auroc: float
    auprc: float
    brier: float
    threshold: float
    sensitivity: float
    specificity: float
    precision: float
    negative_predictive_value: float
    false_alerts_per_100_sessions: float
    prevalence: float
    sessions: int


def load_split(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    frame = pd.read_csv(path, low_memory=False)
    frame["weight_gain_kg"] = frame["weight_start_kg"] - frame["dry_weight_kg"]
    frame["initial_uf_ml_kg_h"] = (
        frame["initial_uf_l_h"] * 1000 / frame["weight_start_kg"]
    )
    return frame[FEATURES], frame[TARGET].astype(int)


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


def candidate_models(seed: int = 2026) -> dict[str, Pipeline]:
    return {
        "logistic-regression": Pipeline(
            [
                ("preprocess", preprocessing()),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "lightgbm": Pipeline(
            [
                ("preprocess", preprocessing()),
                (
                    "model",
                    LGBMClassifier(
                        objective="binary",
                        n_estimators=350,
                        learning_rate=0.035,
                        num_leaves=24,
                        max_depth=7,
                        min_child_samples=80,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        reg_alpha=0.15,
                        reg_lambda=0.35,
                        class_weight="balanced",
                        random_state=seed,
                        n_jobs=-1,
                        verbosity=-1,
                    ),
                ),
            ]
        ),
    }


def operating_threshold(y_true: pd.Series, probabilities: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    candidates: list[tuple[float, float]] = []
    for index, threshold in enumerate(thresholds):
        if recall[index] < 0.80:
            continue
        denominator = 4 * precision[index] + recall[index]
        f2 = 5 * precision[index] * recall[index] / denominator if denominator else 0
        candidates.append((f2, float(threshold)))
    return max(candidates, default=(0.0, 0.5))[1]


def evaluate(y_true: pd.Series, probabilities: np.ndarray, threshold: float) -> Metrics:
    predicted = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if tp + fn else 0
    specificity = tn / (tn + fp) if tn + fp else 0
    precision = tp / (tp + fp) if tp + fp else 0
    npv = tn / (tn + fn) if tn + fn else 0
    return Metrics(
        auroc=round(float(roc_auc_score(y_true, probabilities)), 5),
        auprc=round(float(average_precision_score(y_true, probabilities)), 5),
        brier=round(float(brier_score_loss(y_true, probabilities)), 5),
        threshold=round(threshold, 5),
        sensitivity=round(sensitivity, 5),
        specificity=round(specificity, 5),
        precision=round(precision, 5),
        negative_predictive_value=round(npv, 5),
        false_alerts_per_100_sessions=round(100 * fp / len(y_true), 3),
        prevalence=round(float(np.mean(y_true)), 5),
        sessions=len(y_true),
    )


def train_and_evaluate(
    data_dir: Path,
    artifact_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    x_train, y_train = load_split(data_dir / "sessions-train.csv")
    x_validation, y_validation = load_split(data_dir / "sessions-validation.csv")
    x_test, y_test = load_split(data_dir / "sessions-test.csv")

    candidates: dict[str, dict[str, Any]] = {}
    fitted: dict[str, CalibratedClassifierCV] = {}
    for name, pipeline in candidate_models().items():
        pipeline.fit(x_train, y_train)
        calibrated = CalibratedClassifierCV(FrozenEstimator(pipeline), method="sigmoid")
        calibrated.fit(x_validation, y_validation)
        validation_probability = calibrated.predict_proba(x_validation)[:, 1]
        threshold = operating_threshold(y_validation, validation_probability)
        metrics = evaluate(y_validation, validation_probability, threshold)
        candidates[name] = {"validation": asdict(metrics)}
        fitted[name] = calibrated

    selected_name = max(candidates, key=lambda name: candidates[name]["validation"]["auprc"])
    selected = fitted[selected_name]
    threshold = candidates[selected_name]["validation"]["threshold"]
    test_probability = selected.predict_proba(x_test)[:, 1]
    test_metrics = evaluate(y_test, test_probability, threshold)
    candidates[selected_name]["test"] = asdict(test_metrics)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": selected,
        "model_name": selected_name,
        "threshold": threshold,
        "features": FEATURES,
        "target": TARGET,
        "source_doi": "10.6084/m9.figshare.6260654.v3",
    }
    joblib.dump(artifact, artifact_dir / "idh-pre-session.joblib")
    report = {
        "selected_model": selected_name,
        "selection_rule": "highest validation AUPRC after sigmoid calibration",
        "operating_rule": "validation threshold maximizing F2 subject to sensitivity >= 0.80",
        "target": TARGET,
        "target_definition": "baseline SBP drop >=20 mmHg and nadir SBP <90 mmHg",
        "target_limitation": "BP-only proxy; symptoms and interventions unavailable",
        "features": FEATURES,
        "excluded_leakage_fields": [
            "nadir_sbp_mmhg",
            "mean_sbp_mmhg",
            "sbp_drop_mmhg",
            "mean_uf_l_h",
            "mean_blood_flow_ml_min",
            "elapsed_minutes",
        ],
        "history_policy": "history features use only chronologically earlier sessions",
        "candidates": candidates,
        "data_hashes": data_hashes(data_dir),
    }
    (report_dir / "model-evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_model_card(report, report_dir / "MODEL_CARD.md")
    return report


def data_hashes(data_dir: Path) -> dict[str, str]:
    receipt = json.loads((data_dir / "validation-receipt.json").read_text(encoding="utf-8"))
    return {name: details["sha256"] for name, details in receipt["files"].items()}


def write_model_card(report: dict[str, Any], path: Path) -> None:
    selected = report["selected_model"]
    validation = report["candidates"][selected]["validation"]
    test = report["candidates"][selected]["test"]
    content = f"""# NADI-HD pre-session IDH proxy model

## Intended use

Research prototype for clinician-reviewed pre-session risk stratification. It is not a medical
device, must not control a dialysis machine, and must not be used for patient care.

## Source and target

- Source: HEMOBP v3 (`10.6084/m9.figshare.6260654.v3`)
- Target: {report['target_definition']}
- Limitation: {report['target_limitation']}
- Selected model: `{selected}`
- Calibration: sigmoid on the patient-disjoint validation partition

## Untouched patient-level test performance

| Metric | Value |
|---|---:|
| Sessions | {test['sessions']:,} |
| Prevalence | {test['prevalence']:.3f} |
| AUROC | {test['auroc']:.3f} |
| AUPRC | {test['auprc']:.3f} |
| Brier score | {test['brier']:.3f} |
| Sensitivity | {test['sensitivity']:.3f} |
| Specificity | {test['specificity']:.3f} |
| Precision | {test['precision']:.3f} |
| False alerts / 100 sessions | {test['false_alerts_per_100_sessions']:.2f} |

The decision threshold ({validation['threshold']:.4f}) was selected using validation data only.

## Known limitations

- Single-centre Taiwanese retrospective cohort; transportability to India is unproven.
- Symptoms and nursing interventions are unavailable, so the outcome is a BP-only proxy.
- Observation timing is irregular and can be influenced by clinical concern.
- The model requires prospective, multicentre, subgroup and workflow validation.
- Performance must not be transcribed into the UI without matching model/data versions.
"""
    path.write_text(content, encoding="utf-8")
