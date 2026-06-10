from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from afr.models import Artifact, Event, ReplaySummary, Run


def _dump(value: Run | Event | Artifact) -> dict[str, Any]:
    return value.model_dump(mode="json")


def replay_run(session: Session, run_id: str) -> ReplaySummary:
    run = session.get(Run, run_id)
    if run is None:
        raise ValueError(f"Run not found: {run_id}")

    events = session.exec(
        select(Event).where(Event.run_id == run_id).order_by(Event.timestamp, Event.id)
    ).all()
    artifacts = session.exec(
        select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.created_at, Artifact.id)
    ).all()

    return ReplaySummary(
        run=_dump(run),
        events=[_dump(event) for event in events],
        failed_steps=[
            _dump(event) for event in events if event.status == "error" or event.error_json
        ],
        model_calls=[
            _dump(event) for event in events if event.event_type.startswith("model.call.")
        ],
        tool_calls=[_dump(event) for event in events if event.event_type.startswith("tool.call.")],
        artifacts=[_dump(artifact) for artifact in artifacts],
        eval_results=[
            _dump(artifact) for artifact in artifacts if artifact.artifact_type == "eval_result"
        ],
    )
