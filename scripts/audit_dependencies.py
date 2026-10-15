from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path

DIRECT_DEPENDENCIES = (
    "fastapi",
    "pydantic",
    "uvicorn",
    "joblib",
    "lightgbm",
    "numpy",
    "pandas",
    "scikit-learn",
    "httpx",
    "pytest",
    "pytest-cov",
    "ruff",
)


def audit() -> dict[str, object]:
    packages = []
    unresolved = []
    for name in DIRECT_DEPENDENCIES:
        try:
            package_metadata = metadata(name)
            license_name = (
                package_metadata.get("License-Expression")
                or package_metadata.get("License")
                or next(
                    (
                        classifier.removeprefix("License :: ")
                        for classifier in package_metadata.get_all("Classifier", [])
                        if classifier.startswith("License :: ")
                    ),
                    "UNKNOWN",
                )
            )
            packages.append(
                {
                    "name": name,
                    "version": version(name),
                    "license": license_name.strip(),
                    "homepage": package_metadata.get("Home-page")
                    or package_metadata.get("Project-URL"),
                }
            )
            if license_name.strip() == "UNKNOWN":
                unresolved.append(name)
        except PackageNotFoundError:
            unresolved.append(name)
            packages.append({"name": name, "installed": False, "license": "UNKNOWN"})
    return {
        "scope": "declared direct runtime, ML, and development dependencies",
        "packages": packages,
        "unresolved": unresolved,
        "distribution_approved": not unresolved,
    }


if __name__ == "__main__":
    report = audit()
    target = Path("reports/dependency-licenses.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["unresolved"] else 0)
