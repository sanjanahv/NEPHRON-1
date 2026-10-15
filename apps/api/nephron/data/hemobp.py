from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MISSING = {"", "NA", "N/A", "null", "None"}


def pseudonymize_patient(raw_patient_id: str) -> str:
    digest = hashlib.sha256(f"nephron-hemobp-v1:{raw_patient_id}".encode()).hexdigest()
    return f"HBP-{digest[:16]}"


def patient_split(patient_id: str) -> str:
    """Stable 70/15/15 patient-level partition independent of row order."""
    bucket = int(hashlib.sha256(f"split-v1:{patient_id}".encode()).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def as_float(value: str | None) -> float | None:
    if value is None or value.strip() in MISSING:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def date_part(value: str | None) -> str | None:
    if value is None or value.strip() in MISSING or len(value) < 10:
        return None
    candidate = value[:10]
    try:
        return datetime.strptime(candidate, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


@dataclass
class SessionAggregate:
    raw_patient_id: str
    date: str
    observations: int = 0
    baseline_elapsed: float = math.inf
    baseline_sbp: float | None = None
    baseline_dbp: float | None = None
    initial_uf: float | None = None
    initial_blood_flow: float | None = None
    initial_dialysate_temperature: float | None = None
    initial_conductivity: float | None = None
    nadir_sbp: float = math.inf
    sbp_sum: float = 0.0
    dbp_sum: float = 0.0
    dbp_count: int = 0
    uf_sum: float = 0.0
    uf_count: int = 0
    max_uf: float | None = None
    blood_flow_sum: float = 0.0
    blood_flow_count: int = 0
    dialysate_temperature_sum: float = 0.0
    dialysate_temperature_count: int = 0
    conductivity_sum: float = 0.0
    conductivity_count: int = 0
    max_elapsed: float = 0.0

    def add(self, row: dict[str, str], quality: Counter[str]) -> None:
        sbp = as_float(row.get("sbp"))
        dbp = as_float(row.get("dbp"))
        elapsed = as_float(row.get("time"))
        if sbp is None or not 30 <= sbp <= 250:
            quality["invalid_sbp"] += 1
            return
        if elapsed is None or not 0 <= elapsed <= 600:
            quality["invalid_elapsed_time"] += 1
            return

        self.observations += 1
        self.sbp_sum += sbp
        self.nadir_sbp = min(self.nadir_sbp, sbp)
        self.max_elapsed = max(self.max_elapsed, elapsed)
        if elapsed < self.baseline_elapsed:
            self.baseline_elapsed = elapsed
            self.baseline_sbp = sbp
            self.baseline_dbp = dbp if dbp is not None and 20 <= dbp <= 160 else None
            self.initial_uf = as_float(row.get("uf"))
            self.initial_blood_flow = as_float(row.get("blood_flow"))
            self.initial_dialysate_temperature = as_float(row.get("dia_temp_value"))
            self.initial_conductivity = as_float(row.get("conductivity"))
        self.dbp_sum, self.dbp_count, _ = self._bounded_accumulate(
            self.dbp_sum, self.dbp_count, None, dbp, 20, 160, "invalid_dbp", quality
        )
        self.uf_sum, self.uf_count, self.max_uf = self._bounded_accumulate(
            self.uf_sum,
            self.uf_count,
            self.max_uf,
            as_float(row.get("uf")),
            0,
            5,
            "invalid_uf",
            quality,
        )
        self.blood_flow_sum, self.blood_flow_count, _ = self._bounded_accumulate(
            self.blood_flow_sum,
            self.blood_flow_count,
            None,
            as_float(row.get("blood_flow")),
            0,
            600,
            "invalid_blood_flow",
            quality,
        )
        (
            self.dialysate_temperature_sum,
            self.dialysate_temperature_count,
            _,
        ) = self._bounded_accumulate(
            self.dialysate_temperature_sum,
            self.dialysate_temperature_count,
            None,
            as_float(row.get("dia_temp_value")),
            30,
            42,
            "invalid_dialysate_temperature",
            quality,
        )
        self.conductivity_sum, self.conductivity_count, _ = self._bounded_accumulate(
            self.conductivity_sum,
            self.conductivity_count,
            None,
            as_float(row.get("conductivity")),
            10,
            20,
            "invalid_conductivity",
            quality,
        )

    @staticmethod
    def _bounded_accumulate(
        running_sum: float,
        count: int,
        running_max: float | None,
        value: float | None,
        minimum: float,
        maximum: float,
        counter: str,
        quality: Counter[str],
    ) -> tuple[float, int, float | None]:
        if value is None or not minimum <= value <= maximum:
            quality[counter] += 1
            return running_sum, count, running_max
        maximum_value = value if running_max is None else max(running_max, value)
        return running_sum + value, count + 1, maximum_value


def safe_mean(total: float, count: int) -> float | None:
    return round(total / count, 3) if count else None


def load_patients(path: Path, quality: Counter[str]) -> dict[str, dict[str, Any]]:
    patients: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            raw_id = row["pid"]
            birth_year = as_float(row.get("birthday"))
            patients[raw_id] = {
                "patient_id": pseudonymize_patient(raw_id),
                "sex": row.get("gender") or None,
                "birth_year": int(birth_year) if birth_year else None,
                "diabetes": int(as_float(row.get("DM")) or 0),
            }
            quality["patient_rows"] += 1
    return patients


def load_session_context(
    path: Path,
    quality: Counter[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    sessions: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            quality["session_context_rows"] += 1
            session_date = date_part(row.get("keyindate"))
            if session_date is None:
                quality["session_context_missing_date"] += 1
                continue
            key = (row["pid"], session_date)
            candidate = {
                "weight_start_kg": as_float(row.get("weightstart")),
                "weight_end_kg": as_float(row.get("weightend")),
                "dry_weight_kg": as_float(row.get("dryweight")),
                "body_temperature_c": as_float(row.get("temperature")),
                "dialysis_start": row.get("dialysisstart"),
                "dialysis_end": row.get("dialysisend"),
            }
            if key in sessions:
                quality["duplicate_session_context_key"] += 1
                existing_score = sum(value is not None for value in sessions[key].values())
                candidate_score = sum(value is not None for value in candidate.values())
                if candidate_score <= existing_score:
                    continue
            sessions[key] = candidate
    return sessions


def aggregate_observations(
    path: Path,
    quality: Counter[str],
) -> dict[tuple[str, str], SessionAggregate]:
    sessions: dict[tuple[str, str], SessionAggregate] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            quality["observation_rows"] += 1
            session_date = date_part(row.get("datatime"))
            if session_date is None:
                quality["observation_missing_date"] += 1
                continue
            key = (row["pid"], session_date)
            aggregate = sessions.setdefault(key, SessionAggregate(row["pid"], session_date))
            aggregate.add(row, quality)
    return sessions


def build_session_row(
    aggregate: SessionAggregate,
    patient: dict[str, Any],
    context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if aggregate.baseline_sbp is None or not aggregate.observations:
        return None
    baseline_sbp = aggregate.baseline_sbp
    nadir_sbp = aggregate.nadir_sbp
    patient_id = patient["patient_id"]
    session_id = f"{patient_id}-{aggregate.date}"
    context = context or {}
    weight_start = context.get("weight_start_kg")
    weight_end = context.get("weight_end_kg")
    age = None
    if patient.get("birth_year"):
        age = int(aggregate.date[:4]) - patient["birth_year"]
    drop = baseline_sbp - nadir_sbp
    return {
        "patient_id": patient_id,
        "session_id": session_id,
        "split": patient_split(patient_id),
        "session_date": aggregate.date,
        "age_years": age,
        "sex": patient.get("sex"),
        "diabetes": patient.get("diabetes"),
        "observations": aggregate.observations,
        "weight_start_kg": weight_start,
        "weight_end_kg": weight_end,
        "dry_weight_kg": context.get("dry_weight_kg"),
        "fluid_removed_kg": (
            round(weight_start - weight_end, 3)
            if weight_start is not None and weight_end is not None
            else None
        ),
        "body_temperature_c": context.get("body_temperature_c"),
        "baseline_sbp_mmhg": baseline_sbp,
        "baseline_dbp_mmhg": aggregate.baseline_dbp,
        "nadir_sbp_mmhg": nadir_sbp,
        "mean_sbp_mmhg": safe_mean(aggregate.sbp_sum, aggregate.observations),
        "mean_dbp_mmhg": safe_mean(aggregate.dbp_sum, aggregate.dbp_count),
        "mean_uf_l_h": safe_mean(aggregate.uf_sum, aggregate.uf_count),
        "max_uf_l_h": round(aggregate.max_uf, 3) if aggregate.max_uf is not None else None,
        "mean_blood_flow_ml_min": safe_mean(
            aggregate.blood_flow_sum, aggregate.blood_flow_count
        ),
        "mean_dialysate_temperature_c": safe_mean(
            aggregate.dialysate_temperature_sum,
            aggregate.dialysate_temperature_count,
        ),
        "mean_conductivity_ms_cm": safe_mean(
            aggregate.conductivity_sum, aggregate.conductivity_count
        ),
        "initial_uf_l_h": aggregate.initial_uf,
        "initial_blood_flow_ml_min": aggregate.initial_blood_flow,
        "initial_dialysate_temperature_c": aggregate.initial_dialysate_temperature,
        "initial_conductivity_ms_cm": aggregate.initial_conductivity,
        "elapsed_minutes": round(aggregate.max_elapsed, 1),
        "sbp_drop_mmhg": round(drop, 1),
        "label_nadir90": int(nadir_sbp < 90),
        "label_drop20_nadir90": int(drop >= 20 and nadir_sbp < 90),
    }


def add_prior_history(rows: list[dict[str, Any]], window: int = 10) -> None:
    """Attach history available strictly before each session."""
    current_patient: str | None = None
    history: list[dict[str, Any]] = []
    for row in rows:
        if row["patient_id"] != current_patient:
            current_patient = row["patient_id"]
            history = []
        recent = history[-window:]
        row["prior_session_count"] = len(history)
        row["prior_idh_rate_10"] = (
            round(sum(item["label_drop20_nadir90"] for item in recent) / len(recent), 4)
            if recent
            else None
        )
        row["prior_mean_nadir_sbp_10"] = (
            round(sum(item["nadir_sbp_mmhg"] for item in recent) / len(recent), 3)
            if recent
            else None
        )
        row["prior_mean_sbp_drop_10"] = (
            round(sum(item["sbp_drop_mmhg"] for item in recent) / len(recent), 3)
            if recent
            else None
        )
        row["previous_session_idh"] = recent[-1]["label_drop20_nadir90"] if recent else None
        row["previous_nadir_sbp_mmhg"] = recent[-1]["nadir_sbp_mmhg"] if recent else None
        history.append(row)


def prepare_dataset(raw_dir: Path, output_dir: Path) -> dict[str, Any]:
    quality: Counter[str] = Counter()
    patients = load_patients(raw_dir / "idp.csv", quality)
    contexts = load_session_context(raw_dir / "d1.csv", quality)
    observations = aggregate_observations(raw_dir / "vip.csv", quality)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for key, aggregate in observations.items():
        patient = patients.get(aggregate.raw_patient_id)
        if patient is None:
            quality["session_missing_patient"] += 1
            continue
        context = contexts.get(key)
        if context is None:
            quality["observation_session_missing_context"] += 1
            continue
        row = build_session_row(aggregate, patient, context)
        if row is not None:
            rows.append(row)

    rows.sort(key=lambda item: (item["patient_id"], item["session_date"]))
    add_prior_history(rows)
    fieldnames = list(rows[0]) if rows else []
    for split in ("all", "train", "validation", "test"):
        target = output_dir / f"sessions-{split}.csv"
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(row for row in rows if split == "all" or row["split"] == split)

    split_patients = {
        split: sorted({row["patient_id"] for row in rows if row["split"] == split})
        for split in ("train", "validation", "test")
    }
    (output_dir / "patient-splits.json").write_text(
        json.dumps(split_patients, indent=2) + "\n", encoding="utf-8"
    )
    split_counts = Counter(row["split"] for row in rows)
    label_counts = Counter((row["split"], row["label_drop20_nadir90"]) for row in rows)
    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_dataset": "HEMOBP v3",
        "source_doi": "10.6084/m9.figshare.6260654.v3",
        "label_definition": "baseline SBP drop >=20 mmHg and nadir SBP <90 mmHg",
        "label_limitation": "BP-only proxy; symptoms and nursing interventions are unavailable",
        "patients": len({row["patient_id"] for row in rows}),
        "sessions": len(rows),
        "session_counts_by_split": dict(split_counts),
        "positive_sessions_by_split": {
            split: label_counts[(split, 1)] for split in ("train", "validation", "test")
        },
        "quality_counters": dict(sorted(quality.items())),
    }
    (output_dir / "quality-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report
