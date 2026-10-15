from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StreamSnapshot:
    age_seconds: float
    sbp_mmhg: float | None
    dbp_mmhg: float | None
    blood_flow_ml_min: float | None
    cumulative_uf_l: float | None
    target_uf_l: float | None
    elapsed_minutes: float | None
    prescribed_duration_minutes: float | None


@dataclass(frozen=True)
class QualityAssessment:
    mode: str
    score: float
    issues: tuple[str, ...]
    disabled_outputs: tuple[str, ...]


def assess_streams(snapshot: StreamSnapshot) -> QualityAssessment:
    issues: list[str] = []
    severe = False
    missing = sum(
        value is None
        for value in (
            snapshot.sbp_mmhg,
            snapshot.dbp_mmhg,
            snapshot.blood_flow_ml_min,
            snapshot.cumulative_uf_l,
            snapshot.elapsed_minutes,
        )
    )
    if snapshot.sbp_mmhg is None:
        issues.append("Systolic blood pressure is missing")
        severe = True
    if missing:
        issues.append(f"{missing} required stream value(s) are missing")
    if snapshot.age_seconds > 300:
        issues.append("Stream is delayed by more than five minutes")
        severe = True
    elif snapshot.age_seconds > 90:
        issues.append("Stream freshness is degraded")

    if snapshot.sbp_mmhg is not None and not 30 <= snapshot.sbp_mmhg <= 250:
        issues.append("Systolic blood pressure is physiologically implausible")
        severe = True
    if snapshot.dbp_mmhg is not None and not 20 <= snapshot.dbp_mmhg <= 160:
        issues.append("Diastolic blood pressure is physiologically implausible")
        severe = True
    if (
        snapshot.sbp_mmhg is not None
        and snapshot.dbp_mmhg is not None
        and snapshot.dbp_mmhg >= snapshot.sbp_mmhg
    ):
        issues.append("Diastolic pressure is not below systolic pressure")
        severe = True
    if snapshot.blood_flow_ml_min is not None and not 0 <= snapshot.blood_flow_ml_min <= 600:
        issues.append("Blood-flow value is outside the supported range")
        severe = True
    if (
        snapshot.cumulative_uf_l is not None
        and snapshot.target_uf_l is not None
        and snapshot.cumulative_uf_l > snapshot.target_uf_l + 0.2
    ):
        issues.append("Cumulative ultrafiltration exceeds the prescribed target")
        severe = True
    if (
        snapshot.elapsed_minutes is not None
        and snapshot.prescribed_duration_minutes is not None
        and snapshot.elapsed_minutes > snapshot.prescribed_duration_minutes + 5
    ):
        issues.append("Elapsed time exceeds the prescribed duration")

    score = max(0.0, 1 - 0.12 * missing - 0.18 * len(issues) - (0.18 if severe else 0))
    if snapshot.sbp_mmhg is None or score < 0.35:
        mode = "unavailable"
        disabled = ("IDH forecast", "counterfactual ranking")
    elif severe:
        mode = "conservative"
        disabled = ("counterfactual ranking",)
    elif issues:
        mode = "caution"
        disabled = ()
    else:
        mode = "normal"
        disabled = ()
    return QualityAssessment(mode, round(score, 2), tuple(issues), disabled)
