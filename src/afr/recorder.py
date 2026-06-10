from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from afr.db import init_db, make_engine
from afr.exporters import export_run_jsonl as export_run_jsonl_with_session
from afr.importers import import_run_jsonl as import_run_jsonl_with_session
from afr.models import Artifact, ArtifactType, Event, EventStatus, Run, RunStatus
from afr.replay import replay_run


def _now() -> datetime:
    return datetime.now(UTC)


def _error_payload(error: Any) -> dict[str, Any]:
    if isinstance(error, dict):
        return error
    if isinstance(error, BaseException):
        return {"type": type(error).__name__, "message": str(error)}
    return {"message": str(error)}


def _sha256_for(content_text: str | None, content_json: dict[str, Any] | None) -> str | None:
    if content_text is None and content_json is None:
        return None
    payload = content_text if content_text is not None else json.dumps(content_json, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Recorder:
    def __init__(self, project: str | None = None, db_url: str = "sqlite:///afr.db") -> None:
        self.project = project
        self.db_url = db_url
        self.engine: Engine = make_engine(db_url)
        init_db(self.engine)

    def start_run(
        self,
        name: str | None = None,
        project: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Run:
        run = Run(name=name, project=project or self.project, metadata_json=metadata or {})
        with Session(self.engine) as session:
            session.add(run)
            session.commit()
            session.refresh(run)
            self.record_event(run.id, "run.started", name="run started", metadata=metadata)
            return run

    def complete_run(self, run_id: str, metadata: dict[str, Any] | None = None) -> Run:
        with Session(self.engine) as session:
            run = self._require_run(session, run_id)
            run.status = RunStatus.completed
            run.ended_at = _now()
            if metadata:
                run.metadata_json = {**run.metadata_json, **metadata}
            session.add(run)
            session.commit()
            session.refresh(run)
        self.record_event(run_id, "run.completed", name="run completed", metadata=metadata)
        return self.get_run(run_id)

    def fail_run(self, run_id: str, error: Any) -> Run:
        payload = _error_payload(error)
        with Session(self.engine) as session:
            run = self._require_run(session, run_id)
            run.status = RunStatus.failed
            run.ended_at = _now()
            session.add(run)
            session.commit()
        self.record_event(
            run_id, "run.failed", name="run failed", error_json=payload, status="error"
        )
        return self.get_run(run_id)

    def record_event(
        self,
        run_id: str,
        event_type: str,
        name: str,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        error_json: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        parent_event_id: str | None = None,
        status: str | EventStatus = EventStatus.ok,
    ) -> Event:
        with Session(self.engine) as session:
            self._require_run(session, run_id)
            event = Event(
                run_id=run_id,
                parent_event_id=parent_event_id,
                event_type=event_type,
                name=name,
                input_json=input_json,
                output_json=output_json,
                error_json=error_json,
                metadata_json=metadata or {},
                status=EventStatus(status),
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    @contextmanager
    def event(
        self,
        run_id: str,
        event_type: str,
        name: str,
        input_json: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        parent_event_id: str | None = None,
    ) -> Iterator[Event]:
        started = self.record_event(
            run_id,
            event_type,
            name,
            input_json=input_json,
            metadata=metadata,
            parent_event_id=parent_event_id,
        )
        begin = _now()
        try:
            yield started
        except Exception as exc:
            duration_ms = int((_now() - begin).total_seconds() * 1000)
            self.record_event(
                run_id,
                _completed_event_type(event_type),
                name=f"{name} failed",
                error_json=_error_payload(exc),
                metadata={"duration_ms": duration_ms},
                parent_event_id=started.id,
                status=EventStatus.error,
            )
            raise
        else:
            duration_ms = int((_now() - begin).total_seconds() * 1000)
            self.record_event(
                run_id,
                _completed_event_type(event_type),
                name=f"{name} completed",
                metadata={"duration_ms": duration_ms},
                parent_event_id=started.id,
            )

    def add_artifact(
        self,
        run_id: str,
        artifact_type: str | ArtifactType,
        event_id: str | None = None,
        content_text: str | None = None,
        content_json: dict[str, Any] | None = None,
        uri: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        with Session(self.engine) as session:
            self._require_run(session, run_id)
            artifact = Artifact(
                run_id=run_id,
                event_id=event_id,
                artifact_type=str(artifact_type),
                content_text=content_text,
                content_json=content_json,
                uri=uri,
                metadata_json=metadata or {},
                sha256=_sha256_for(content_text, content_json),
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            return artifact

    def get_run(self, run_id: str) -> Run:
        with Session(self.engine) as session:
            run = self._require_run(session, run_id)
            session.expunge(run)
            return run

    def list_runs(self, limit: int = 50) -> list[Run]:
        with Session(self.engine) as session:
            runs = session.exec(select(Run).order_by(Run.started_at.desc()).limit(limit)).all()
            for run in runs:
                session.expunge(run)
            return list(runs)

    def get_events(self, run_id: str) -> list[Event]:
        with Session(self.engine) as session:
            self._require_run(session, run_id)
            events = session.exec(
                select(Event).where(Event.run_id == run_id).order_by(Event.timestamp, Event.id)
            ).all()
            for event in events:
                session.expunge(event)
            return list(events)

    def export_run_jsonl(self, run_id: str, path: str | Path) -> Path:
        with Session(self.engine) as session:
            return export_run_jsonl_with_session(session, run_id, path)

    def import_run_jsonl(self, path: str | Path) -> str:
        with Session(self.engine) as session:
            return import_run_jsonl_with_session(session, path)

    def replay(self, run_id: str) -> dict[str, Any]:
        with Session(self.engine) as session:
            return replay_run(session, run_id).model_dump(mode="json")

    @staticmethod
    def _require_run(session: Session, run_id: str) -> Run:
        run = session.get(Run, run_id)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")
        return run


def _completed_event_type(event_type: str) -> str:
    if event_type.endswith(".started"):
        return f"{event_type.removesuffix('.started')}.completed"
    return event_type
