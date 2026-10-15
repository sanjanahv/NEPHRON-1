from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.api.nephron.data.hemobp import prepare_dataset

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw" / "hemobp-v3")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "processed" / "hemobp-v3",
    )
    args = parser.parse_args()
    report = prepare_dataset(args.raw, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
