import numpy as np
import pandas as pd

from apps.api.nephron.ml.training import evaluate, operating_threshold


def test_operating_threshold_targets_high_recall() -> None:
    target = pd.Series([0, 0, 0, 1, 1])
    probabilities = np.array([0.05, 0.2, 0.4, 0.55, 0.9])
    threshold = operating_threshold(target, probabilities)
    metrics = evaluate(target, probabilities, threshold)
    assert metrics.sensitivity >= 0.8


def test_evaluation_reports_false_alert_rate() -> None:
    target = pd.Series([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.8, 0.7, 0.9])
    metrics = evaluate(target, probabilities, 0.5)
    assert metrics.false_alerts_per_100_sessions == 25.0
    assert metrics.sensitivity == 1.0
