from __future__ import annotations

from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class SessionObservation:
    minute: float
    sbp_mmhg: float
    dbp_mmhg: float | None = None
    uf_l_h: float | None = None
    blood_flow_ml_min: float | None = None


@dataclass(frozen=True)
class WarningExample:
    session_id: str
    minute: float
    current_sbp_mmhg: float
    current_dbp_mmhg: float | None
    sbp_change_from_baseline: float
    sbp_slope_30m: float | None
    current_uf_l_h: float | None
    current_blood_flow_ml_min: float | None
    minutes_to_event: float | None
    event_within_horizon: bool


@dataclass(frozen=True)
class AlertBudgetMetrics:
    event_sessions: int
    non_event_sessions: int
    detected_event_sessions: int
    false_alert_sessions: int
    premature_alert_sessions: int
    late_alert_sessions: int
    session_sensitivity: float
    false_alerts_per_100_sessions: float
    median_warning_minutes: float | None
    alerts_per_100_session_hours: float


def first_idh_event_minute(
    observations: tuple[SessionObservation, ...],
    *,
    nadir_threshold_mmhg: float = 90,
    drop_threshold_mmhg: float = 20,
) -> float | None:
    if not observations:
        return None
    ordered = sorted(observations, key=lambda item: item.minute)
    baseline = ordered[0].sbp_mmhg
    return next(
        (
            item.minute
            for item in ordered
            if item.sbp_mmhg < nadir_threshold_mmhg
            and baseline - item.sbp_mmhg >= drop_threshold_mmhg
        ),
        None,
    )


def _prior_slope(
    observations: list[SessionObservation],
    index: int,
    lookback_minutes: float,
) -> float | None:
    current = observations[index]
    prior = next(
        (
            item
            for item in reversed(observations[:index])
            if current.minute - item.minute >= lookback_minutes
        ),
        observations[0] if index else None,
    )
    if prior is None or current.minute == prior.minute:
        return None
    return round((current.sbp_mmhg - prior.sbp_mmhg) / (current.minute - prior.minute) * 30, 3)


def build_warning_examples(
    session_id: str,
    observations: tuple[SessionObservation, ...],
    *,
    horizon_minutes: float = 60,
    minimum_lead_minutes: float = 15,
) -> tuple[WarningExample, ...]:
    """Create prediction-time rows without using data at or after an IDH event."""
    if horizon_minutes <= minimum_lead_minutes or minimum_lead_minutes < 0:
        raise ValueError("Horizon must be greater than the non-negative minimum lead time")
    ordered = sorted(observations, key=lambda item: item.minute)
    if not ordered:
        return ()
    event_minute = first_idh_event_minute(tuple(ordered))
    baseline = ordered[0].sbp_mmhg
    examples: list[WarningExample] = []
    for index, item in enumerate(ordered):
        if event_minute is not None and item.minute >= event_minute:
            break
        minutes_to_event = event_minute - item.minute if event_minute is not None else None
        positive = (
            minutes_to_event is not None
            and minimum_lead_minutes <= minutes_to_event <= horizon_minutes
        )
        examples.append(
            WarningExample(
                session_id=session_id,
                minute=item.minute,
                current_sbp_mmhg=item.sbp_mmhg,
                current_dbp_mmhg=item.dbp_mmhg,
                sbp_change_from_baseline=round(item.sbp_mmhg - baseline, 1),
                sbp_slope_30m=_prior_slope(ordered, index, 30),
                current_uf_l_h=item.uf_l_h,
                current_blood_flow_ml_min=item.blood_flow_ml_min,
                minutes_to_event=minutes_to_event,
                event_within_horizon=positive,
            )
        )
    return tuple(examples)


def evaluate_alert_budget(
    rows: tuple[tuple[str, float, float, float | None], ...],
    *,
    threshold: float,
    session_duration_minutes: dict[str, float],
    minimum_lead_minutes: float = 15,
    horizon_minutes: float = 60,
) -> AlertBudgetMetrics:
    """Evaluate one alert maximum per session.

    Each row is ``(session_id, minute, probability, event_minute)``. Alerts at or after the event
    are ignored. Event-session lead time uses the first eligible threshold crossing.
    """
    by_session: dict[str, list[tuple[float, float, float | None]]] = {}
    for session_id, minute, probability, event_minute in rows:
        by_session.setdefault(session_id, []).append((minute, probability, event_minute))

    event_sessions = 0
    detected = 0
    false_alerts = 0
    premature_alerts = 0
    late_alerts = 0
    lead_times: list[float] = []
    alert_count = 0
    for values in by_session.values():
        ordered = sorted(values)
        event_minute = next((item[2] for item in ordered if item[2] is not None), None)
        all_alerts = [
            minute
            for minute, probability, _ in ordered
            if probability >= threshold and (event_minute is None or minute < event_minute)
        ]
        if event_minute is not None:
            event_sessions += 1
            eligible_alerts = [
                minute
                for minute in all_alerts
                if minimum_lead_minutes <= event_minute - minute <= horizon_minutes
            ]
            if eligible_alerts:
                detected += 1
                alert_count += 1
                lead_times.append(event_minute - eligible_alerts[0])
            if any(event_minute - minute > horizon_minutes for minute in all_alerts):
                premature_alerts += 1
            if any(0 < event_minute - minute < minimum_lead_minutes for minute in all_alerts):
                late_alerts += 1
        elif all_alerts:
            false_alerts += 1
            alert_count += 1

    non_event = len(by_session) - event_sessions
    total_hours = sum(session_duration_minutes.get(key, 0) for key in by_session) / 60
    return AlertBudgetMetrics(
        event_sessions=event_sessions,
        non_event_sessions=non_event,
        detected_event_sessions=detected,
        false_alert_sessions=false_alerts,
        premature_alert_sessions=premature_alerts,
        late_alert_sessions=late_alerts,
        session_sensitivity=round(detected / event_sessions, 5) if event_sessions else 0,
        false_alerts_per_100_sessions=round(100 * false_alerts / len(by_session), 3)
        if by_session
        else 0,
        median_warning_minutes=round(median(lead_times), 1) if lead_times else None,
        alerts_per_100_session_hours=round(100 * alert_count / total_hours, 3)
        if total_hours
        else 0,
    )
