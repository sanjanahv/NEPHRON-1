from fastapi.testclient import TestClient

from apps.api.nephron.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["synthetic_only"] is True
    assert response.headers["X-Clinical-Status"] == "research-prototype"
    assert response.headers["X-Trace-ID"].startswith("nt1-")


def test_valid_trace_id_is_preserved_and_invalid_value_is_replaced() -> None:
    preserved = client.get("/health", headers={"X-Trace-ID": "demo-run_42"})
    assert preserved.headers["X-Trace-ID"] == "demo-run_42"
    replaced = client.get("/health", headers={"X-Trace-ID": "unsafe trace value"})
    assert replaced.headers["X-Trace-ID"].startswith("nt1-")


def test_system_manifest_exposes_safety_boundary() -> None:
    response = client.get("/api/v1/system/manifest")
    assert response.status_code == 200
    body = response.json()
    assert body["autonomous_machine_control"] is False
    assert body["requires_clinician_review"] is True


def test_demo_contract() -> None:
    response = client.get("/api/v1/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["patient"]["patient_id"] == "DT-042"
    assert body["parallel_futures"]
    assert "Not for clinical use" in body["disclaimer"]


def test_model_status_is_explicit() -> None:
    response = client.get("/api/v1/model/status")
    assert response.status_code == 200
    assert "available" in response.json()


def test_temporal_model_cannot_silently_enable_alarm() -> None:
    response = client.get("/api/v1/model/temporal-status")
    assert response.status_code == 200
    assert response.json()["clinical_alarm_enabled"] is False


def test_twin_calibration_contract() -> None:
    demo = client.get("/api/v1/demo").json()
    response = client.post(
        "/api/v1/twin/calibrate",
        json={
            "patient": demo["patient"],
            "history": [
                {
                    "session_date": "2026-01-01",
                    "nadir_sbp_mmhg": 86,
                    "idh_event": True,
                    "completed": True,
                },
                {
                    "session_date": "2026-01-03",
                    "nadir_sbp_mmhg": 72,
                    "idh_event": True,
                    "completed": False,
                },
            ],
            "as_of": "2026-01-02",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source_session_count"] == 1
    assert body["confidence"] == "low"
    assert body["requires_clinician_review"] is True


def test_hybrid_forecast_preserves_safety_boundary() -> None:
    demo = client.get("/api/v1/demo").json()
    response = client.post(
        "/api/v1/forecast/hybrid",
        json={
            "patient": demo["patient"],
            "prescription": demo["prescription"],
            "learned_probability": 0.62,
            "data_quality": 0.9,
            "learned_model_externally_validated": False,
            "model_artifact_sha256": "a" * 64,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hybrid_risk"]["learned_weight"] <= 0.35
    assert body["autonomous_machine_control"] is False


def test_stream_quality_endpoint_disables_missing_bp_outputs() -> None:
    response = client.post(
        "/api/v1/streams/assess",
        json={
            "age_seconds": 20,
            "sbp_mmhg": None,
            "dbp_mmhg": 70,
            "blood_flow_ml_min": 320,
            "cumulative_uf_l": 1.2,
            "target_uf_l": 3.0,
            "elapsed_minutes": 90,
            "prescribed_duration_minutes": 240,
        },
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "unavailable"
    assert "IDH forecast" in response.json()["disabled_outputs"]
