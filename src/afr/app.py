from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from afr.db import get_session, init_db
from afr.exporters import export_run_jsonl
from afr.models import (
    Artifact,
    ArtifactCreate,
    ErrorPayload,
    Event,
    EventCreate,
    Run,
    RunCreate,
    RunStatus,
)
from afr.recorder import _error_payload

app = FastAPI(title="Agent Flight Recorder", version="0.1.0")
SessionDep = Annotated[Session, Depends(get_session)]


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/runs")
def create_run(payload: RunCreate, session: SessionDep) -> Run:
    run = Run(
        name=payload.name,
        project=payload.project,
        metadata_json=payload.metadata or {},
        runtime_contract_version=payload.runtime_contract_version,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    session.add(Event(run_id=run.id, event_type="run.started", name="run started"))
    session.commit()
    return run


@app.get("/runs")
def list_runs(session: SessionDep, limit: int = 50) -> list[Run]:
    return list(session.exec(select(Run).order_by(Run.started_at.desc()).limit(limit)).all())


@app.get("/runs/{run_id}")
def get_run(run_id: str, session: SessionDep) -> Run:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/runs/{run_id}/complete")
def complete_run(run_id: str, session: SessionDep) -> Run:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = RunStatus.completed
    run.ended_at = datetime.now(UTC)
    session.add(run)
    session.add(Event(run_id=run_id, event_type="run.completed", name="run completed"))
    session.commit()
    session.refresh(run)
    return run


@app.post("/runs/{run_id}/fail")
def fail_run(run_id: str, payload: ErrorPayload, session: SessionDep) -> Run:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = RunStatus.failed
    run.ended_at = datetime.now(UTC)
    session.add(run)
    session.add(
        Event(
            run_id=run_id,
            event_type="run.failed",
            name="run failed",
            status="error",
            error_json=_error_payload(payload.error),
        )
    )
    session.commit()
    session.refresh(run)
    return run


@app.post("/runs/{run_id}/events")
def create_event(run_id: str, payload: EventCreate, session: SessionDep) -> Event:
    if session.get(Run, run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    event = Event(
        run_id=run_id,
        event_type=payload.event_type,
        name=payload.name,
        input_json=payload.input_json,
        output_json=payload.output_json,
        error_json=payload.error_json,
        metadata_json=payload.metadata or {},
        parent_event_id=payload.parent_event_id,
        status=payload.status,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@app.get("/runs/{run_id}/events")
def list_events(run_id: str, session: SessionDep) -> list[Event]:
    if session.get(Run, run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return list(
        session.exec(select(Event).where(Event.run_id == run_id).order_by(Event.timestamp)).all()
    )


@app.post("/runs/{run_id}/artifacts")
def create_artifact(
    run_id: str, payload: ArtifactCreate, session: SessionDep
) -> Artifact:
    if session.get(Run, run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    artifact = Artifact(
        run_id=run_id,
        event_id=payload.event_id,
        artifact_type=payload.artifact_type,
        content_text=payload.content_text,
        content_json=payload.content_json,
        uri=payload.uri,
        metadata_json=payload.metadata or {},
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return artifact


@app.get("/runs/{run_id}/export")
def export_run(run_id: str, session: SessionDep) -> PlainTextResponse:
    path = export_run_jsonl(session, run_id, f"/tmp/{run_id}.jsonl")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="application/x-ndjson")
