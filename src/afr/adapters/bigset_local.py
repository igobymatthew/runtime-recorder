from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from afr.recorder import Recorder


def load_eval_cases(path: str | Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                cases.append(json.loads(line))
    return cases


def attach_dataset_case(recorder: Recorder, run_id: str, case: dict[str, Any]) -> str:
    artifact = recorder.add_artifact(run_id, "dataset_case", content_json=case)
    return artifact.id
