from __future__ import annotations

import re
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .counterfactual import generate_parallel_futures
from .demo import meera_baseline, meera_profile
from .hybrid import fuse_risk
from .memory import SessionMemory
from .ml.service import model_status, predict, temporal_model_status
from .multisystem import map_multisystem_trends
from .quality import assess_streams
from .risk import forecast_session
from .schemas import (
    CompletedSessionInput,
    ForecastRequest,
    HybridForecastRequest,
    ModelRiskInput,
    MultisystemRequest,
    ParallelFuturesRequest,
    StreamSnapshotInput,
    TwinCalibrationRequest,
)
from .serialization import candidate_dict, forecast_dict
from .twin import calibrate_patient_twin

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Synthetic-data clinical simulation API. This proof of concept is not for diagnosis "
        "or treatment."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Trace-ID"],
)
session_memory = SessionMemory(settings.session_memory_path)

TRACE_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@app.middleware("http")
async def attach_trace_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    supplied = request.headers.get("X-Trace-ID", "")
    trace_id = supplied if TRACE_PATTERN.fullmatch(supplied) else f"nt1-{uuid4().hex[:20]}"
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Clinical-Status"] = "research-prototype"
    return response


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "version": settings.app_version, "synthetic_only": True}


@app.get("/api/v1/system/manifest")
def system_manifest() -> dict[str, object]:
    return {
        "product": settings.app_name,
        "api_version": settings.app_version,
        "clinical_status": "research-prototype",
        "demo_data": "synthetic",
        "model_development_data": "HEMOBP v3 / CC BY 4.0",
        "source_doi": "10.6084/m9.figshare.6260654.v3",
        "autonomous_machine_control": False,
        "requires_clinician_review": True,
        "claims_policy": "display only frozen, version-matched evaluation results",
    }


@app.get("/api/v1/demo")
def demo() -> dict[str, object]:
    patient = meera_profile()
    prescription = meera_baseline()
    forecast = forecast_session(patient, prescription)
    candidates = generate_parallel_futures(patient, prescription)
    return {
        "patient": patient.__dict__,
        "prescription": prescription.__dict__,
        "forecast": forecast_dict(forecast),
        "parallel_futures": [candidate_dict(candidate) for candidate in candidates],
        "disclaimer": "Synthetic demonstration data. Not for clinical use.",
    }


@app.post("/api/v1/forecast")
def forecast(request: ForecastRequest) -> dict[str, object]:
    result = forecast_session(
        request.patient.to_domain(),
        request.prescription.to_domain(),
        request.data_quality,
    )
    return forecast_dict(result)


@app.post("/api/v1/forecast/hybrid")
def hybrid_forecast(request: HybridForecastRequest) -> dict[str, object]:
    simulation = forecast_session(
        request.patient.to_domain(),
        request.prescription.to_domain(),
        request.data_quality,
    )
    hybrid = fuse_risk(
        simulation.peak_idh_risk,
        request.learned_probability,
        data_quality=request.data_quality,
        learned_model_externally_validated=request.learned_model_externally_validated,
    )
    return {
        "simulation": forecast_dict(simulation),
        "hybrid_risk": hybrid.__dict__,
        "model_artifact_sha256": request.model_artifact_sha256,
        "requires_clinician_review": True,
        "autonomous_machine_control": False,
    }


@app.post("/api/v1/parallel-futures")
def parallel_futures(request: ParallelFuturesRequest) -> dict[str, object]:
    candidates = generate_parallel_futures(
        request.patient.to_domain(),
        request.prescription.to_domain(),
        request.minimum_kt_v,
    )
    return {
        "simulated": len(candidates),
        "feasible": sum(candidate.feasible for candidate in candidates),
        "candidates": [candidate_dict(candidate) for candidate in candidates],
        "requires_clinician_review": True,
    }


@app.post("/api/v1/twin/calibrate")
def calibrate_twin(request: TwinCalibrationRequest) -> dict[str, object]:
    calibration = calibrate_patient_twin(
        request.patient.to_domain(),
        tuple(item.to_domain() for item in request.history),
        as_of=request.as_of,
    )
    return {
        "patient": calibration.patient.__dict__,
        "source_session_count": calibration.source_session_count,
        "effective_history_weight": calibration.effective_history_weight,
        "completeness": calibration.completeness,
        "confidence": calibration.confidence,
        "latest_session_date": (
            calibration.latest_session_date.isoformat()
            if calibration.latest_session_date is not None
            else None
        ),
        "audit_trace": calibration.audit_trace,
        "requires_clinician_review": True,
    }


@app.post("/api/v1/multisystem/map")
def multisystem_map(request: MultisystemRequest) -> dict[str, object]:
    signals = map_multisystem_trends(
        tuple(item.to_domain() for item in request.observations),
        mean_pre_sbp_mmhg=request.mean_pre_sbp_mmhg,
        mean_weight_gain_kg=request.mean_weight_gain_kg,
        measured_lv_mass_index_g_m2=request.measured_lv_mass_index_g_m2,
    )
    return {
        "signals": [signal.__dict__ for signal in signals],
        "causality_warning": (
            "Associations and burden signals do not establish causality or a diagnosis."
        ),
        "requires_clinician_review": True,
    }


@app.post("/api/v1/sessions/completed", status_code=201)
def record_completed_session(request: CompletedSessionInput) -> dict[str, object]:
    try:
        session_memory.record(request.to_domain())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "recorded": True,
        "session_id": request.session_id,
        "patient_id": request.patient_id,
        "recalibration": session_memory.comparison(request.patient_id),
    }


@app.get("/api/v1/patients/{patient_id}/session-memory")
def patient_session_memory(patient_id: str) -> dict[str, object]:
    if not 1 <= len(patient_id) <= 64:
        raise HTTPException(status_code=422, detail="Invalid patient identifier")
    return session_memory.comparison(patient_id)


@app.post("/api/v1/streams/assess")
def assess_stream_quality(request: StreamSnapshotInput) -> dict[str, object]:
    assessment = assess_streams(request.to_domain())
    return {
        **assessment.__dict__,
        "requires_clinician_review": assessment.mode != "normal",
    }


@app.get("/api/v1/model/status")
def get_model_status() -> dict[str, object]:
    return model_status()


@app.get("/api/v1/model/temporal-status")
def get_temporal_model_status() -> dict[str, object]:
    return temporal_model_status()


@app.post("/api/v1/model/predict")
def predict_model_risk(request: ModelRiskInput) -> dict[str, object]:
    return predict(request.model_dump())
