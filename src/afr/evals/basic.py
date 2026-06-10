from __future__ import annotations

from typing import Any

from jsonschema import ValidationError, validate


def exact_match(expected: Any, actual: Any) -> dict[str, Any]:
    passed = expected == actual
    return {"passed": passed, "expected": expected, "actual": actual}


def contains_required_terms(required_terms: list[str], actual_text: str) -> dict[str, Any]:
    missing = [term for term in required_terms if term.lower() not in actual_text.lower()]
    return {"passed": not missing, "required_terms": required_terms, "missing_terms": missing}


def json_schema_valid(schema: dict[str, Any], data: Any) -> dict[str, Any]:
    try:
        validate(instance=data, schema=schema)
    except ValidationError as exc:
        return {"passed": False, "error": exc.message}
    return {"passed": True}
