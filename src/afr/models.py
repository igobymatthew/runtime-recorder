from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class RunStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class EventStatus(StrEnum):
    ok = "ok"
    error = "error"
    skipped = "skipped"


class EventType(StrEnum):
    run_started = "run.started"
    run_completed = "run.completed"
    run_failed = "run.failed"
    model_call_started = "model.call.started"
    model_call_completed = "model.call.completed"
    tool_call_started = "tool.call.started"
    tool_call_completed = "tool.call.completed"
    retrieval_started = "retrieval.started"
    retrieval_completed = "retrieval.completed"
    file_read = "file.read"
    file_write = "file.write"
    human_override = "human.override"
    eval_started = "eval.started"
    eval_completed = "eval.completed"
    error = "error"
    note = "note"


class ArtifactType(StrEnum):
    prompt = "prompt"
    completion = "completion"
    tool_input = "tool_input"
    tool_output = "tool_output"
    retrieved_doc = "retrieved_doc"
    dataset_case = "dataset_case"
    eval_result = "eval_result"
    file_snapshot = "file_snapshot"
    other = "other"


class Run(SQLModel, table=True):
    id: str = SQLField(default_factory=new_id, primary_key=True)
    name: str | None = None
    project: str | None = None
    started_at: datetime = SQLField(default_factory=now_utc, index=True)
    ended_at: datetime | None = None
    status: RunStatus = SQLField(default=RunStatus.running, index=True)
    runtime_contract_version: str | None = None
    metadata_json: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))


class Event(SQLModel, table=True):
    id: str = SQLField(default_factory=new_id, primary_key=True)
    run_id: str = SQLField(foreign_key="run.id", index=True)
    parent_event_id: str | None = SQLField(default=None, foreign_key="event.id")
    event_type: str = SQLField(index=True)
    name: str
    timestamp: datetime = SQLField(default_factory=now_utc, index=True)
    duration_ms: int | None = None
    status: EventStatus = SQLField(default=EventStatus.ok, index=True)
    input_json: dict[str, Any] | None = SQLField(default=None, sa_column=Column(JSON))
    output_json: dict[str, Any] | None = SQLField(default=None, sa_column=Column(JSON))
    error_json: dict[str, Any] | None = SQLField(default=None, sa_column=Column(JSON))
    metadata_json: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))


class Artifact(SQLModel, table=True):
    id: str = SQLField(default_factory=new_id, primary_key=True)
    run_id: str = SQLField(foreign_key="run.id", index=True)
    event_id: str | None = SQLField(default=None, foreign_key="event.id", index=True)
    artifact_type: str = SQLField(index=True)
    uri: str | None = None
    content_text: str | None = None
    content_json: dict[str, Any] | None = SQLField(default=None, sa_column=Column(JSON))
    sha256: str | None = None
    metadata_json: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = SQLField(default_factory=now_utc, index=True)


class RunCreate(BaseModel):
    name: str | None = None
    project: str | None = None
    metadata: dict[str, Any] | None = None
    runtime_contract_version: str | None = None


class EventCreate(BaseModel):
    event_type: str
    name: str
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    error_json: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    parent_event_id: str | None = None
    status: EventStatus = EventStatus.ok


class ArtifactCreate(BaseModel):
    artifact_type: ArtifactType
    event_id: str | None = None
    content_text: str | None = None
    content_json: dict[str, Any] | None = None
    uri: str | None = None
    metadata: dict[str, Any] | None = None


class ErrorPayload(BaseModel):
    error: dict[str, Any] | str


class ReplaySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run: dict[str, Any]
    events: list[dict[str, Any]]
    failed_steps: list[dict[str, Any]]
    model_calls: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    eval_results: list[dict[str, Any]]
