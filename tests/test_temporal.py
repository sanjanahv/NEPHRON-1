from apps.api.nephron.ml.temporal import (
    SessionObservation,
    build_warning_examples,
    evaluate_alert_budget,
)


def test_warning_examples_never_include_event_or_post_event_rows() -> None:
    observations = (
        SessionObservation(0, 125),
        SessionObservation(30, 116),
        SessionObservation(60, 102),
        SessionObservation(90, 88),
        SessionObservation(120, 84),
    )
    rows = build_warning_examples("s1", observations, horizon_minutes=60, minimum_lead_minutes=15)
    assert [row.minute for row in rows] == [0, 30, 60]
    assert [row.event_within_horizon for row in rows] == [False, True, True]
    assert all(row.minutes_to_event is None or row.minutes_to_event > 0 for row in rows)


def test_warning_features_use_only_current_and_prior_values() -> None:
    common = (
        SessionObservation(0, 130),
        SessionObservation(30, 120),
        SessionObservation(60, 110),
    )
    first = build_warning_examples("s1", common + (SessionObservation(90, 85),))
    second = build_warning_examples("s1", common + (SessionObservation(90, 70),))
    assert first[2].sbp_slope_30m == second[2].sbp_slope_30m
    assert first[2].current_sbp_mmhg == second[2].current_sbp_mmhg


def test_alert_budget_counts_at_most_one_alert_per_session() -> None:
    rows = (
        ("event", 30, 0.8, 90.0),
        ("event", 60, 0.9, 90.0),
        ("quiet", 30, 0.7, None),
        ("quiet", 60, 0.8, None),
        ("normal", 30, 0.1, None),
    )
    metrics = evaluate_alert_budget(
        rows,
        threshold=0.5,
        session_duration_minutes={"event": 240, "quiet": 240, "normal": 240},
    )
    assert metrics.detected_event_sessions == 1
    assert metrics.false_alert_sessions == 1
    assert metrics.median_warning_minutes == 60
    assert metrics.false_alerts_per_100_sessions == 33.333


def test_alert_budget_does_not_credit_premature_or_late_alerts() -> None:
    metrics = evaluate_alert_budget(
        (
            ("premature", 10, 0.9, 90.0),
            ("late", 80, 0.9, 90.0),
        ),
        threshold=0.5,
        session_duration_minutes={"premature": 240, "late": 240},
    )
    assert metrics.detected_event_sessions == 0
    assert metrics.premature_alert_sessions == 1
    assert metrics.late_alert_sessions == 1
    assert metrics.median_warning_minutes is None
