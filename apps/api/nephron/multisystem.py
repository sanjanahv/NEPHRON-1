from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean


@dataclass(frozen=True)
class LabObservation:
    observed_on: date
    hemoglobin_g_dl: float | None = None
    calcium_mg_dl: float | None = None
    phosphate_mg_dl: float | None = None
    pth_pg_ml: float | None = None


@dataclass(frozen=True)
class MultisystemSignal:
    signal_id: str
    label: str
    status: str
    latest_value: float | None
    unit: str
    trend_per_30_days: float | None
    source: str
    confidence: str
    interpretation: str


def _slope_per_30_days(points: list[tuple[date, float]]) -> float | None:
    if len(points) < 2:
        return None
    points = sorted(points)
    origin = points[0][0]
    x = [(item[0] - origin).days for item in points]
    y = [item[1] for item in points]
    x_mean, y_mean = mean(x), mean(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return None
    daily = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True)) / denominator
    return round(daily * 30, 3)


def _confidence(count: int) -> str:
    return "high" if count >= 4 else "moderate" if count >= 2 else "low"


def map_multisystem_trends(
    observations: tuple[LabObservation, ...],
    *,
    mean_pre_sbp_mmhg: float | None = None,
    mean_weight_gain_kg: float | None = None,
    measured_lv_mass_index_g_m2: float | None = None,
) -> tuple[MultisystemSignal, ...]:
    ordered = sorted(observations, key=lambda item: item.observed_on)

    hb = [(item.observed_on, item.hemoglobin_g_dl) for item in ordered if item.hemoglobin_g_dl]
    hemoglobin_latest = hb[-1][1] if hb else None
    anemia_status = (
        "attention" if hemoglobin_latest is not None and hemoglobin_latest < 10 else "stable"
        if hemoglobin_latest is not None
        else "unavailable"
    )
    anemia = MultisystemSignal(
        signal_id="anemia",
        label="Hemoglobin trajectory",
        status=anemia_status,
        latest_value=hemoglobin_latest,
        unit="g/dL",
        trend_per_30_days=_slope_per_30_days(hb),
        source="measured laboratory history",
        confidence=_confidence(len(hb)),
        interpretation=(
            "Trend context only; ESA and iron decisions require complete clinical review."
        ),
    )

    mineral_points = [
        (item.observed_on, item.calcium_mg_dl * item.phosphate_mg_dl)
        for item in ordered
        if item.calcium_mg_dl is not None and item.phosphate_mg_dl is not None
    ]
    mineral_latest = mineral_points[-1][1] if mineral_points else None
    mineral_status = (
        "attention" if mineral_latest is not None and mineral_latest > 55 else "stable"
        if mineral_latest is not None
        else "unavailable"
    )
    mineral = MultisystemSignal(
        signal_id="mineral_bone",
        label="Calcium-phosphate product",
        status=mineral_status,
        latest_value=round(mineral_latest, 2) if mineral_latest is not None else None,
        unit="mg²/dL²",
        trend_per_30_days=_slope_per_30_days(mineral_points),
        source="calculated from paired measured laboratories",
        confidence=_confidence(len(mineral_points)),
        interpretation="Context signal only; interpret with serial PTH and local CKD-MBD guidance.",
    )

    if measured_lv_mass_index_g_m2 is not None:
        cardiovascular = MultisystemSignal(
            signal_id="cardiovascular",
            label="LV mass index",
            status="measured",
            latest_value=measured_lv_mass_index_g_m2,
            unit="g/m²",
            trend_per_30_days=None,
            source="measured echocardiography",
            confidence="high",
            interpretation="Measured structure; interpretation depends on sex and imaging context.",
        )
    else:
        available = [
            value for value in (mean_pre_sbp_mmhg, mean_weight_gain_kg) if value is not None
        ]
        burden = None
        if available:
            pressure = max(0.0, ((mean_pre_sbp_mmhg or 130) - 130) / 40)
            volume = max(0.0, ((mean_weight_gain_kg or 2) - 2) / 3)
            burden = round(min(1.0, 0.6 * pressure + 0.4 * volume), 3)
        cardiovascular = MultisystemSignal(
            signal_id="cardiovascular",
            label="Cardiovascular load signal",
            status="screening" if burden is not None else "unavailable",
            latest_value=burden,
            unit="0–1 index",
            trend_per_30_days=None,
            source="modeled from blood-pressure and volume-load history",
            confidence="low" if burden is not None else "low",
            interpretation="Not an LVH estimate or diagnosis; echocardiography is required.",
        )
    return anemia, mineral, cardiovascular
