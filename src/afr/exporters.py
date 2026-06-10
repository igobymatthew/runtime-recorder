from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from afr.models import Artifact, Event, Run


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def model_dump(obj: Run | Event | Artifact) -> dict[str, Any]:
    data = obj.model_dump(mode="json")
    data.pop("run", None)
    data.pop("event", None)
    data.pop("events", None)
    data.pop("artifacts", None)
    return data


def export_run_jsonl(session: Session, run_id: str, path: str | Path) -> Path:
    run = session.get(Run, run_id)
    if run is None:
        raise ValueError(f"Run not found: {run_id}")

    events = session.exec(
        select(Event).where(Event.run_id == run_id).order_by(Event.timestamp, Event.id)
    ).all()
    artifacts = session.exec(
        select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.created_at, Artifact.id)
    ).all()

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps({"record_type": "run", "data": model_dump(run)}, default=_json_default)
        )
        handle.write("\n")
        for event in events:
            handle.write(
                json.dumps(
                    {"record_type": "event", "data": model_dump(event)}, default=_json_default
                )
            )
            handle.write("\n")
        for artifact in artifacts:
            handle.write(
                json.dumps(
                    {"record_type": "artifact", "data": model_dump(artifact)}, default=_json_default
                )
            )
            handle.write("\n")
    return output
