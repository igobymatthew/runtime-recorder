from __future__ import annotations

from typing import Any

from afr.models import Event
from afr.recorder import Recorder


def attach_contract(recorder: Recorder, run_id: str, contract_json: dict[str, Any]) -> str:
    artifact = recorder.add_artifact(
        run_id,
        "other",
        content_json=contract_json,
        metadata={"adapter": "ai-runtime-abi", "kind": "runtime_contract"},
    )
    return artifact.id


def validate_event_against_contract(
    event: Event | dict[str, Any], contract_json: dict[str, Any]
) -> bool:
    # First-pass placeholder: keep the integration point obvious without embedding ABI rules yet.
    event_type = event.event_type if isinstance(event, Event) else event.get("event_type")
    allowed_event_types = contract_json.get("allowed_event_types")
    if allowed_event_types is None:
        return True
    return event_type in allowed_event_types
