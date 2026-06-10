from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import typer

from afr.db import init_db
from afr.evals import contains_required_terms
from afr.recorder import Recorder

app = typer.Typer(help="Agent Flight Recorder local CLI.")


def _recorder() -> Recorder:
    return Recorder(db_url=os.getenv("AFR_DB_URL", "sqlite:///afr.db"))


@app.command()
def init() -> None:
    """Create local SQLite tables."""
    init_db()
    typer.echo("Initialized Agent Flight Recorder database.")


@app.command()
def runs(limit: int = 50) -> None:
    """List recent runs."""
    for run in _recorder().list_runs(limit=limit):
        typer.echo(f"{run.id}\t{run.status}\t{run.project or '-'}\t{run.name or '-'}")


@app.command()
def show(run_id: str) -> None:
    """Show one run."""
    run = _recorder().get_run(run_id)
    typer.echo(json.dumps(run.model_dump(mode="json"), indent=2))


@app.command()
def events(run_id: str) -> None:
    """List events for a run."""
    for event in _recorder().get_events(run_id):
        typer.echo(f"{event.timestamp.isoformat()}\t{event.status}\t{event.event_type}\t{event.name}")


@app.command()
def export(run_id: str, out: Annotated[Path, typer.Option("--out", "-o")]) -> None:
    """Export a run to JSONL."""
    path = _recorder().export_run_jsonl(run_id, out)
    typer.echo(str(path))


@app.command(name="import")
def import_trace(path: Path) -> None:
    """Import a JSONL trace."""
    run_id = _recorder().import_run_jsonl(path)
    typer.echo(run_id)


@app.command()
def replay(run_id: str) -> None:
    """Print a dry-run replay summary."""
    summary = _recorder().replay(run_id)
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def demo() -> None:
    """Create a sample local agent trace."""
    rec = _recorder()
    run = rec.start_run(name="demo agent run", project="demo", metadata={"source": "afr demo"})
    model_start = rec.record_event(
        run.id,
        "model.call.started",
        name="draft answer",
        input_json={
            "model": "example-model",
            "messages": [{"role": "user", "content": "Summarize AFR"}],
        },
    )
    rec.add_artifact(run.id, "prompt", event_id=model_start.id, content_text="Summarize AFR")
    rec.record_event(
        run.id,
        "model.call.completed",
        name="draft answer completed",
        output_json={"content": "Agent Flight Recorder records agent traces locally."},
        parent_event_id=model_start.id,
    )
    rec.record_event(
        run.id,
        "tool.call.completed",
        name="search local files",
        input_json={"query": "agent trace"},
        output_json={"matches": ["README.md"]},
    )
    retrieval = rec.record_event(
        run.id,
        "retrieval.completed",
        name="retrieve docs",
        output_json={"documents": [{"id": "doc-1", "score": 0.92}]},
    )
    rec.add_artifact(
        run.id,
        "retrieved_doc",
        event_id=retrieval.id,
        content_json={"id": "doc-1", "text": "Runs are traces; events are span-like records."},
    )
    eval_result: dict[str, Any] = contains_required_terms(
        ["trace", "events"], "Runs are traces and events are records."
    )
    rec.add_artifact(run.id, "eval_result", content_json=eval_result)
    rec.complete_run(run.id)
    typer.echo(run.id)


if __name__ == "__main__":
    app()
