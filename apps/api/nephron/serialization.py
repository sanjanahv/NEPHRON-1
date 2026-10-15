from dataclasses import asdict
from typing import Any

from .counterfactual import Candidate
from .domain import Forecast


def forecast_dict(forecast: Forecast) -> dict[str, Any]:
    payload = asdict(forecast)
    payload["risk_band"] = forecast.risk_band.value
    return payload


def candidate_dict(candidate: Candidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "prescription": asdict(candidate.prescription),
        "forecast": forecast_dict(candidate.forecast),
        "feasible": candidate.feasible,
        "rejection_reasons": candidate.rejection_reasons,
        "comparison": {
            "peak_risk_delta": candidate.peak_risk_delta,
            "kt_v_delta": candidate.kt_v_delta,
            "nadir_sbp_mmhg": candidate.nadir_sbp_mmhg,
            "uncertainty_mmhg": candidate.uncertainty_mmhg,
            "on_safety_adequacy_frontier": candidate.on_safety_adequacy_frontier,
        },
        "decision_trace": candidate.decision_trace,
    }
