from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RiskBand(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class PatientProfile:
    patient_id: str
    age_years: int
    sex: str
    pre_weight_kg: float
    dry_weight_kg: float
    pre_sbp_mmhg: float
    pre_dbp_mmhg: float
    urea_pre_mg_dl: float
    urea_post_mg_dl: float | None = None
    prior_idh_rate: float = 0.0
    prior_nadir_sbp: float = 105.0
    diabetes: bool = False
    cardiac_disease: bool = False
    hemoglobin_g_dl: float = 10.5
    albumin_g_dl: float = 3.8

    @property
    def interdialytic_weight_gain_kg(self) -> float:
        return max(0.0, self.pre_weight_kg - self.dry_weight_kg)


@dataclass(frozen=True)
class Prescription:
    duration_minutes: int
    blood_flow_ml_min: float
    dialysate_flow_ml_min: float
    ultrafiltration_l: float
    dialysate_temperature_c: float = 36.5
    dialyzer_koa_ml_min: float = 700.0

    def uf_rate_ml_kg_h(self, weight_kg: float) -> float:
        if weight_kg <= 0 or self.duration_minutes <= 0:
            raise ValueError("Weight and duration must be positive")
        return self.ultrafiltration_l * 1000 / weight_kg / (self.duration_minutes / 60)


@dataclass(frozen=True)
class TimePoint:
    minute: int
    sbp_mmhg: float
    dbp_mmhg: float
    plasma_volume_change_pct: float
    estimated_cardiac_output_l_min: float
    cumulative_uf_l: float
    urea_mg_dl: float
    idh_risk: float
    confidence_low_sbp: float
    confidence_high_sbp: float


@dataclass(frozen=True)
class Adequacy:
    urr_pct: float
    sp_kt_v: float
    effective_clearance_ml_min: float


@dataclass(frozen=True)
class Forecast:
    points: tuple[TimePoint, ...]
    peak_idh_risk: float
    warning_minute: int | None
    risk_band: RiskBand
    adequacy: Adequacy
    data_quality: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
