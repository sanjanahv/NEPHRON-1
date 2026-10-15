from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path("data/processed/hemobp-v3")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    splits = json.loads((data_dir / "patient-splits.json").read_text(encoding="utf-8"))
    patient_sets = {name: set(values) for name, values in splits.items()}
    report: dict[str, Any] = {"generated_at_utc": datetime.now(UTC).isoformat(), "files": {}}
    observed_patients: dict[str, set[str]] = {}

    for split in ("train", "validation", "test"):
        path = data_dir / f"temporal-{split}.csv"
        rows = positives = event_rows = 0
        patients: set[str] = set()
        sessions: set[str] = set()
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                rows += 1
                patient = row["patient_id"]
                if patient not in patient_sets[split]:
                    raise ValueError(f"Patient split violation in {path.name}: {patient}")
                patients.add(patient)
                sessions.add(row["session_id"])
                lead = float(row["minutes_to_event"]) if row["minutes_to_event"] else None
                positive = row["event_within_horizon"].lower() == "true"
                positives += int(positive)
                event_rows += int(lead is not None)
                if lead is not None and lead <= 0:
                    raise ValueError(f"Post-event row in {path.name}: {row['session_id']}")
                if positive and (lead is None or not 15 <= lead <= 60):
                    raise ValueError(f"Invalid positive horizon in {path.name}")
        observed_patients[split] = patients
        report["files"][path.name] = {
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
            "rows": rows,
            "sessions": len(sessions),
            "patients": len(patients),
            "positive_rows": positives,
            "pre_event_rows": event_rows,
        }

    if observed_patients["train"] & observed_patients["validation"]:
        raise ValueError("Train and validation patients overlap")
    if observed_patients["train"] & observed_patients["test"]:
        raise ValueError("Train and test patients overlap")
    if observed_patients["validation"] & observed_patients["test"]:
        raise ValueError("Validation and test patients overlap")
    report["checks"] = {
        "patient_disjoint": True,
        "no_post_event_rows": True,
        "positive_lead_window_minutes": [15, 60],
    }
    (data_dir / "temporal-validation-receipt.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
