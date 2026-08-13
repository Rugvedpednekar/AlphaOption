import json
from dataclasses import asdict
from pathlib import Path

from app.smartapi.types import ProbeReport


def write_redacted_evidence(report: ProbeReport, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    timestamp = report.started_utc.replace(":", "-").replace("+", "_")
    path = root / f"probe-{timestamp}.json"
    path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return path
