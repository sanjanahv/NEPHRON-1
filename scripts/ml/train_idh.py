from __future__ import annotations

import json
from pathlib import Path

from apps.api.nephron.ml.training import train_and_evaluate

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    report = train_and_evaluate(
        ROOT / "data" / "processed" / "hemobp-v3",
        ROOT / "artifacts" / "models",
        ROOT / "reports",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
