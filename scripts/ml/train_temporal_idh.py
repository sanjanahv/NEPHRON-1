from __future__ import annotations

from pathlib import Path

from apps.api.nephron.ml.temporal_training import train_temporal

ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    result = train_temporal(
        ROOT / "data" / "processed" / "hemobp-v3",
        ROOT / "artifacts" / "models",
        ROOT / "reports",
    )
    selected = result["selected_model"]
    print(selected, result["candidates"][selected])
