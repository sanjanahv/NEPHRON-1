from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from statistics import median

from .domain import PatientProfile


@dataclass(frozen=True)
class HistoricalSession:
    session_date: date
    nadir_sbp_mmhg: float
    idh_event: bool
    completed: bool = True


@dataclass(frozen=True)
class TwinCalibration:
    patient: PatientProfile
    source_session_count: int
    effective_history_weight: float
    completeness: float
    confidence: str
    latest_session_date: date | None
    audit_trace: tuple[str, ...]


def calibrate_patient_twin(
    patient: PatientProfile,
    history: tuple[HistoricalSession, ...],
    *,
    as_of: date,
    maximum_sessions: int = 10,
) -> TwinCalibration:
    """Calibrate history fields using completed sessions strictly before ``as_of``.

    Sparse history is shrunk toward the profile's existing priors. The function does not infer
    unobserved cardiac, laboratory, or treatment parameters.
    """
    eligible = sorted(
        (item for item in history if item.completed and item.session_date < as_of),
        key=lambda item: item.session_date,
    )[-maximum_sessions:]
    count = len(eligible)
    weight = count / (count + 4) if count else 0.0

    if eligible:
        observed_rate = sum(item.idh_event for item in eligible) / count
        observed_nadir = median(item.nadir_sbp_mmhg for item in eligible)
        prior_rate = (1 - weight) * patient.prior_idh_rate + weight * observed_rate
        prior_nadir = (1 - weight) * patient.prior_nadir_sbp + weight * observed_nadir
        latest = eligible[-1].session_date
    else:
        prior_rate = patient.prior_idh_rate
        prior_nadir = patient.prior_nadir_sbp
        latest = None

    completeness = min(1.0, count / maximum_sessions)
    confidence = "high" if count >= 8 else "moderate" if count >= 4 else "low"
    calibrated = replace(
        patient,
        prior_idh_rate=round(prior_rate, 4),
        prior_nadir_sbp=round(prior_nadir, 1),
    )
    trace = (
        f"Used {count} completed session(s) before {as_of.isoformat()}",
        "Limited calibration to the 10 most recent eligible sessions",
        f"Applied empirical-Bayes shrinkage weight {weight:.3f}",
        "Did not infer missing laboratory, cardiac, or prescription variables",
    )
    return TwinCalibration(
        patient=calibrated,
        source_session_count=count,
        effective_history_weight=round(weight, 3),
        completeness=round(completeness, 3),
        confidence=confidence,
        latest_session_date=latest,
        audit_trace=trace,
    )
