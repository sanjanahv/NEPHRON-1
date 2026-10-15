"""Download the immutable HEMOBP v3 release and verify every file.

Raw files remain ignored by Git. Provenance lives in configs/data/hemobp.v3.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "data" / "hemobp.v3.json"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "hemobp-v3"


def md5sum(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_target(output: Path, name: str) -> Path:
    if Path(name).name != name or name in {".", ".."}:
        raise ValueError(f"Unsafe dataset filename: {name!r}")
    target = (output / name).resolve()
    if output.resolve() not in target.parents:
        raise ValueError(f"Dataset target escapes output directory: {target}")
    return target


def download_file(url: str, target: Path, expected_bytes: int, expected_md5: str) -> str:
    if target.exists() and target.stat().st_size == expected_bytes:
        if md5sum(target) == expected_md5:
            return "verified-existing"

    partial = target.with_suffix(target.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "NEPHRON-1/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        actual_bytes = partial.stat().st_size
        if actual_bytes != expected_bytes:
            raise RuntimeError(
                f"Size mismatch for {target.name}: expected {expected_bytes}, got {actual_bytes}"
            )
        actual_md5 = md5sum(partial)
        if actual_md5 != expected_md5:
            raise RuntimeError(
                f"MD5 mismatch for {target.name}: expected {expected_md5}, got {actual_md5}"
            )
        partial.replace(target)
        return "downloaded-verified"
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for record in config["files"]:
        target = safe_target(args.output, record["name"])
        status = download_file(record["url"], target, record["bytes"], record["md5"])
        results.append({"file": record["name"], "status": status, "bytes": record["bytes"]})
        print(f"{record['name']}: {status} ({record['bytes']:,} bytes)")

    receipt = {
        "dataset_id": config["dataset_id"],
        "doi": config["doi"],
        "files": results,
    }
    (args.output / "download-receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
