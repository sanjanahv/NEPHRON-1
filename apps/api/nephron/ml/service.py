from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from .training import FEATURES

DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[4] / "artifacts" / "models" / "idh-pre-session.joblib"
)
DEFAULT_TEMPORAL_MODEL_PATH = (
    Path(__file__).resolve().parents[4] / "artifacts" / "models" / "idh-temporal-warning.joblib"
)
DEFAULT_TEMPORAL_REPORT_PATH = (
    Path(__file__).resolve().parents[4] / "reports" / "temporal-model-evaluation.json"
)


def configured_model_path() -> Path:
    configured = os.getenv("NEPHRON_MODEL_PATH")
    return Path(configured).resolve() if configured else DEFAULT_MODEL_PATH


@lru_cache(maxsize=1)
def load_artifact() -> dict[str, Any]:
    import joblib

    path = configured_model_path()
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact is unavailable: {path}")
    artifact = joblib.load(path)
    if artifact.get("features") != FEATURES:
        raise RuntimeError("Model feature contract does not match the running API")
    return artifact


def model_status() -> dict[str, Any]:
    path = configured_model_path()
    if not path.is_file():
        return {"available": False, "reason": "artifact-not-found"}
    try:
        artifact = load_artifact()
    except Exception as exc:
        return {"available": False, "reason": type(exc).__name__}
    artifact_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "available": True,
        "artifact_sha256": artifact_hash,
        "model_name": artifact["model_name"],
        "target": artifact["target"],
        "threshold": artifact["threshold"],
        "source_doi": artifact["source_doi"],
        "clinical_status": "research-prototype",
        "autonomous_machine_control": False,
    }


def temporal_model_status() -> dict[str, Any]:
    if not DEFAULT_TEMPORAL_MODEL_PATH.is_file() or not DEFAULT_TEMPORAL_REPORT_PATH.is_file():
        return {"available": False, "clinical_alarm_enabled": False}
    report = json.loads(DEFAULT_TEMPORAL_REPORT_PATH.read_text(encoding="utf-8"))
    selected = report["selected_model"]
    test = report["candidates"][selected]["test"]
    return {
        "available": True,
        "model_name": selected,
        "artifact_sha256": hashlib.sha256(DEFAULT_TEMPORAL_MODEL_PATH.read_bytes()).hexdigest(),
        "warning_window_minutes": [15, 60],
        "test_session_sensitivity": test["session_sensitivity"],
        "test_median_warning_minutes": test["median_warning_minutes"],
        "test_false_alerts_per_100_sessions": test["false_alerts_per_100_sessions"],
        "clinical_alarm_enabled": False,
        "reason": "frozen test alert burden exceeds prototype safety gate",
        "clinical_status": "research-baseline",
    }


def predict(features: dict[str, Any]) -> dict[str, Any]:
    import pandas as pd

    artifact = load_artifact()
    frame = pd.DataFrame([{name: features.get(name) for name in artifact["features"]}])
    probability = float(artifact["model"].predict_proba(frame)[:, 1][0])
    threshold = float(artifact["threshold"])
    if probability >= max(0.5, threshold * 4):
        tier = "very-high"
    elif probability >= threshold:
        tier = "elevated"
    elif probability >= threshold / 2:
        tier = "watch"
    else:
        tier = "lower"
    return {
        "probability": round(probability, 6),
        "validation_selected_threshold": threshold,
        "screen_positive": probability >= threshold,
        "risk_tier": tier,
        "model_name": artifact["model_name"],
        "target": artifact["target"],
        "requires_clinician_review": True,
        "limitations": [
            "BP-only proxy outcome",
            "single-centre retrospective source cohort",
            "not prospectively or externally validated",
        ],
    }
