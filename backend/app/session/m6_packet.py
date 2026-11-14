"""Project review rows from an already assembled client result."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def review_rows_from_final_result(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return review fields; callers must keep source quotes in restricted storage."""
    if result.get("schema_version") != "final_result_v1":
        raise ValueError("M6 source must be final_result_v1")
    source = result["canonical_text"]
    rows = []
    for index, risk in enumerate(result["risks"], 1):
        start, end = risk["start_char"], risk["end_char"]
        if not 0 <= start < end <= len(source) or source[start:end] != risk["quote"]:
            raise ValueError("M6 quote does not match final source offset")
        for label in risk["risk_labels"]:
            rows.append({
                "output_id": f"{result['session_id']}::{index:04d}::{label}",
                "role": result["role"], "risk_label": label,
                "severity": risk["severity"], "explanation": risk["explanation"],
                "citation_ids": list(risk["citation_ids"]), "quote": risk["quote"],
                "start_char": start, "end_char": end,
            })
    return rows
