from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlmodel import Session

from afr.models import Artifact, Event, Run


def import_run_jsonl(session: Session, path: str | Path) -> str:
    imported_run_id: str | None = None
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record: dict[str, Any] = json.loads(line)
            record_type = record["record_type"]
            data = record["data"]
            if record_type == "run":
                run = Run.model_validate(data)
                imported_run_id = run.id
                session.merge(run)
            elif record_type == "event":
                session.merge(Event.model_validate(data))
            elif record_type == "artifact":
                session.merge(Artifact.model_validate(data))
            else:
                raise ValueError(f"Unknown JSONL record type: {record_type}")

    if imported_run_id is None:
        raise ValueError("JSONL file did not contain a run record")

    session.commit()
    return imported_run_id
