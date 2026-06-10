# Agent Flight Recorder

Agent Flight Recorder is a local-first observability and replay layer for AI agents. It records the meaningful events in an agent run so developers can inspect, replay, evaluate, and debug behavior across model providers, tools, datasets, and runtime contracts.

The core idea is simple: treat an agent run as a trace. Each model call, tool call, retrieval step, file operation, eval, error, or human override is stored as a span-like event in SQLite and can be exported to JSONL.

## Why It Exists

Agent failures are hard to debug when prompts, tool inputs, retrieved context, eval cases, and runtime errors live in separate logs. Agent Flight Recorder keeps those records together as replayable evidence, without requiring a hosted backend or OpenTelemetry infrastructure in v1.

## Related Projects

- **AI Runtime ABI** defines contract shapes for model calls, tools, permissions, schemas, and runtime execution. This repo includes an adapter stub for attaching a runtime contract and validating events against a simple contract placeholder.
- **BigSet Local** prepares private/local datasets and eval cases. This repo includes an adapter stub for loading JSONL eval cases and attaching dataset cases as artifacts.
- **Agent Flight Recorder** records what happened during a run and turns failures into inspectable, exportable traces.

## Quickstart

```bash
pip install -e ".[dev]"
afr init
afr demo
afr runs
```

Run the API:

```bash
uvicorn afr.app:app --reload
```

## CLI Usage

```bash
afr init
afr runs
afr show RUN_ID
afr events RUN_ID
afr export RUN_ID --out trace.jsonl
afr import trace.jsonl
afr replay RUN_ID
afr demo
```

By default, the CLI uses `sqlite:///afr.db`. Override it with:

```bash
AFR_DB_URL=sqlite:///path/to/afr.db
```

## Python API

```python
from afr import Recorder

rec = Recorder(project="demo", db_url="sqlite:///afr.db")
run = rec.start_run(name="sample")

with rec.event(run.id, "model.call.started", name="call gpt"):
    ...

rec.record_event(
    run.id,
    event_type="tool.call.completed",
    name="search files",
    input_json={"query": "README"},
    output_json={"matches": ["README.md"]},
)

rec.complete_run(run.id)
```

## JSONL Export Format

Exports are newline-delimited JSON records. Each line has:

```json
{"record_type": "run|event|artifact", "data": {}}
```

The first line is the run, followed by chronological events and artifacts. This keeps traces diffable, stream-friendly, and easy to move between local databases.

## Event Types

Supported first-pass event names include:

- `run.started`, `run.completed`, `run.failed`
- `model.call.started`, `model.call.completed`
- `tool.call.started`, `tool.call.completed`
- `retrieval.started`, `retrieval.completed`
- `file.read`, `file.write`
- `human.override`
- `eval.started`, `eval.completed`
- `error`, `note`

## Replay

Replay is a dry-run reconstruction in v1. It does not call external models or tools. It returns run metadata, chronological events, failed steps, model calls, tool calls, artifacts, and eval results.

## Non-Goals For V1

- No full dashboard.
- No cloud auth.
- No hosted backend.
- No required OpenTelemetry collector or vendor infrastructure.
- No external model/tool re-execution during replay.
