from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from .domain import PatientProfile, Prescription
from .memory import CompletedSession
from .multisystem import LabObservation
from .quality import StreamSnapshot
from .twin import HistoricalSession


class PatientInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: str = Field(min_length=1, max_length=64)
    age_years: int = Field(ge=18, le=110)
    sex: str
    pre_weight_kg: float = Field(gt=25, lt=250)
    dry_weight_kg: float = Field(gt=25, lt=250)
    pre_sbp_mmhg: float = Field(gt=60, lt=260)
    pre_dbp_mmhg: float = Field(gt=30, lt=160)
    urea_pre_mg_dl: float = Field(gt=1, lt=500)
    urea_post_mg_dl: float | None = Field(default=None, gt=1, lt=500)
    prior_idh_rate: float = Field(default=0, ge=0, le=1)
    prior_nadir_sbp: float = Field(default=105, gt=40, lt=220)
    diabetes: bool = False
    cardiac_disease: bool = False
    hemoglobin_g_dl: float = Field(default=10.5, gt=3, lt=25)
    albumin_g_dl: float = Field(default=3.8, gt=1, lt=7)

    def to_domain(self) -> PatientProfile:
        return PatientProfile(**self.model_dump())


class PrescriptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_minutes: int = Field(ge=120, le=360)
    blood_flow_ml_min: float = Field(ge=150, le=500)
    dialysate_flow_ml_min: float = Field(ge=300, le=800)
    ultrafiltration_l: float = Field(ge=0, le=8)
    dialysate_temperature_c: float = Field(default=36.5, ge=34, le=38)
    dialyzer_koa_ml_min: float = Field(default=700, ge=200, le=1600)

    def to_domain(self) -> Prescription:
        return Prescription(**self.model_dump())


class ForecastRequest(BaseModel):
    patient: PatientInput
    prescription: PrescriptionInput
    data_quality: float = Field(default=0.94, ge=0, le=1)


class HybridForecastRequest(ForecastRequest):
    learned_probability: float = Field(ge=0, le=1)
    learned_model_externally_validated: bool = False
    model_artifact_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")


class ParallelFuturesRequest(BaseModel):
    patient: PatientInput
    prescription: PrescriptionInput
    minimum_kt_v: float = Field(default=1.2, ge=0.5, le=2.5)


class HistoricalSessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_date: date
    nadir_sbp_mmhg: float = Field(ge=30, le=250)
    idh_event: bool
    completed: bool = True

    def to_domain(self) -> HistoricalSession:
        return HistoricalSession(**self.model_dump())


class TwinCalibrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient: PatientInput
    history: list[HistoricalSessionInput] = Field(default_factory=list, max_length=100)
    as_of: date


class LabObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_on: date
    hemoglobin_g_dl: float | None = Field(default=None, gt=3, lt=25)
    calcium_mg_dl: float | None = Field(default=None, gt=2, lt=20)
    phosphate_mg_dl: float | None = Field(default=None, gt=0.5, lt=20)
    pth_pg_ml: float | None = Field(default=None, ge=0, lt=10000)

    def to_domain(self) -> LabObservation:
        return LabObservation(**self.model_dump())


class MultisystemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[LabObservationInput] = Field(default_factory=list, max_length=100)
    mean_pre_sbp_mmhg: float | None = Field(default=None, ge=60, le=260)
    mean_weight_gain_kg: float | None = Field(default=None, ge=0, le=20)
    measured_lv_mass_index_g_m2: float | None = Field(default=None, gt=20, lt=500)


class CompletedSessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=80)
    patient_id: str = Field(min_length=1, max_length=64)
    session_date: date
    nadir_sbp_mmhg: float = Field(ge=30, le=250)
    idh_event: bool
    actual_uf_l: float = Field(ge=0, le=8)
    duration_minutes: int = Field(ge=60, le=480)
    delivered_kt_v: float | None = Field(default=None, ge=0, le=5)
    predicted_nadir_sbp_mmhg: float | None = Field(default=None, ge=30, le=250)
    predicted_kt_v: float | None = Field(default=None, ge=0, le=5)

    def to_domain(self) -> CompletedSession:
        payload = self.model_dump()
        payload["session_date"] = self.session_date.isoformat()
        return CompletedSession(**payload)


class StreamSnapshotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_seconds: float = Field(ge=0, le=86400)
    sbp_mmhg: float | None = None
    dbp_mmhg: float | None = None
    blood_flow_ml_min: float | None = None
    cumulative_uf_l: float | None = None
    target_uf_l: float | None = None
    elapsed_minutes: float | None = None
    prescribed_duration_minutes: float | None = None

    def to_domain(self) -> StreamSnapshot:
        return StreamSnapshot(**self.model_dump())


class ModelRiskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_years: float | None = Field(default=None, ge=18, le=110)
    diabetes: int = Field(ge=0, le=1)
    weight_start_kg: float | None = Field(default=None, gt=25, lt=250)
    dry_weight_kg: float | None = Field(default=None, gt=25, lt=250)
    weight_gain_kg: float | None = Field(default=None, ge=-5, le=20)
    body_temperature_c: float | None = Field(default=None, ge=30, le=43)
    baseline_sbp_mmhg: float | None = Field(default=None, ge=30, le=250)
    baseline_dbp_mmhg: float | None = Field(default=None, ge=20, le=160)
    initial_uf_l_h: float | None = Field(default=None, ge=0, le=5)
    initial_uf_ml_kg_h: float | None = Field(default=None, ge=0, le=50)
    initial_blood_flow_ml_min: float | None = Field(default=None, ge=0, le=600)
    initial_dialysate_temperature_c: float | None = Field(default=None, ge=30, le=42)
    initial_conductivity_ms_cm: float | None = Field(default=None, ge=10, le=20)
    prior_session_count: int = Field(default=0, ge=0)
    prior_idh_rate_10: float | None = Field(default=None, ge=0, le=1)
    prior_mean_nadir_sbp_10: float | None = Field(default=None, ge=30, le=250)
    prior_mean_sbp_drop_10: float | None = Field(default=None, ge=-100, le=200)
    previous_session_idh: int | None = Field(default=None, ge=0, le=1)
    previous_nadir_sbp_mmhg: float | None = Field(default=None, ge=30, le=250)
    sex: str | None = None
