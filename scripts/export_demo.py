from __future__ import annotations

import json
from pathlib import Path

from apps.api.nephron.counterfactual import generate_parallel_futures
from apps.api.nephron.demo import meera_baseline, meera_profile
from apps.api.nephron.risk import forecast_session
from apps.api.nephron.serialization import candidate_dict, forecast_dict


def export(path: Path) -> None:
    patient = meera_profile()
    prescription = meera_baseline()
    forecast = forecast_session(patient, prescription)
    payload = {
        "fixture_version": "1.0.0",
        "product": "NADI-HD",
        "patient": patient.__dict__,
        "prescription": prescription.__dict__,
        "forecast": forecast_dict(forecast),
        "parallel_futures": [
            candidate_dict(candidate)
            for candidate in generate_parallel_futures(patient, prescription)
        ],
        "disclaimer": "Synthetic demonstration data. Not for clinical use.",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export(Path("dist/demo-fixture.json"))
