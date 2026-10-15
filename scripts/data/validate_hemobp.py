from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(output: Path) -> dict[str, object]:
    partitions = json.loads((output / "patient-splits.json").read_text(encoding="utf-8"))
    split_sets = {name: set(values) for name, values in partitions.items()}
    if not split_sets["train"].isdisjoint(split_sets["validation"]):
        raise RuntimeError("Patient leakage between train and validation")
    if not split_sets["train"].isdisjoint(split_sets["test"]):
        raise RuntimeError("Patient leakage between train and test")
    if not split_sets["validation"].isdisjoint(split_sets["test"]):
        raise RuntimeError("Patient leakage between validation and test")

    counts: Counter[str] = Counter()
    session_ids: set[str] = set()
    files: dict[str, dict[str, object]] = {}
    for split in ("train", "validation", "test"):
        path = output / f"sessions-{split}.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                counts[f"{split}_rows"] += 1
                counts[f"{split}_positive"] += int(row["label_drop20_nadir90"])
                if row["split"] != split:
                    raise RuntimeError(f"Incorrect split value in {path.name}")
                if row["patient_id"] not in split_sets[split]:
                    raise RuntimeError(f"Patient assigned outside {split} partition")
                if row["session_id"] in session_ids:
                    raise RuntimeError(f"Duplicate session identifier: {row['session_id']}")
                session_ids.add(row["session_id"])
                baseline = float(row["baseline_sbp_mmhg"])
                nadir = float(row["nadir_sbp_mmhg"])
                if not 30 <= nadir <= baseline <= 250:
                    raise RuntimeError(f"Invalid BP relationship in {row['session_id']}")
        files[path.name] = {"bytes": path.stat().st_size, "sha256": sha256sum(path)}

    total_rows = sum(counts[f"{split}_rows"] for split in ("train", "validation", "test"))
    if total_rows != len(session_ids):
        raise RuntimeError("Session count does not reconcile")
    report = {
        "validated_at_utc": datetime.now(UTC).isoformat(),
        "status": "passed",
        "patients_by_split": {name: len(values) for name, values in split_sets.items()},
        "sessions_by_split": {
            split: counts[f"{split}_rows"] for split in ("train", "validation", "test")
        },
        "positive_sessions_by_split": {
            split: counts[f"{split}_positive"] for split in ("train", "validation", "test")
        },
        "patient_partitions_disjoint": True,
        "session_identifiers_unique": True,
        "files": files,
    }
    (output / "validation-receipt.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "processed" / "hemobp-v3",
    )
    args = parser.parse_args()
    print(json.dumps(validate(args.output), indent=2))


if __name__ == "__main__":
    main()
