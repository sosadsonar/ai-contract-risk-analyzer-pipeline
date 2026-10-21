"""DEC-20: enum trong JSON Schema phải khớp nguồn duy nhất trong code.

Nguồn: app.clause.taxonomy.CLAUSE_LABELS (nhãn clause) và app.core.enums (các enum còn lại).
Test này fail nếu ai đó sửa taxonomy mà quên schema (hoặc ngược lại).
"""

import json
from pathlib import Path

import pytest
from app.clause.taxonomy import CLAUSE_LABELS
from app.core.enums import EvidenceStatus, Severity

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "ai_pipeline" / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_clause_output_v3_label_enum_matches_taxonomy_exactly_and_in_order():
    enum = _load("clause_output_v3")["$defs"]["clause_label"]["enum"]
    assert tuple(enum) == CLAUSE_LABELS


def test_clause_output_v3_label_array_is_one_to_three_unique():
    schema = _load("clause_output_v3")
    labels = schema["properties"]["items"]["items"]["properties"]["clause_labels"]
    assert labels["minItems"] == 1
    assert labels["maxItems"] == 3
    assert labels["uniqueItems"] is True


def test_no_legacy_schema_left():
    assert not (SCHEMA_DIR / "clause_output_v2.json").exists()


@pytest.mark.parametrize("name", ["risk_output_v1"])
def test_risk_output_enums_match_code_when_schema_exists(name):
    """risk_output_v1 do Người 3 tạo (X-01 / PROGRESS T1). 
    Khi file xuất hiện, enum phải khớp code.
    """
    path = SCHEMA_DIR / f"{name}.json"
    if not path.exists():
        pytest.skip(f"{name}.json chưa có (việc của Người 3)")
    raw_schema = json.loads(path.read_text(encoding="utf-8"))
    props = raw_schema["properties"]["items"]["items"]["properties"]
    assert {x for x in props["severity"]["enum"] if x is not None} == {s.value for s in Severity}
    assert set(props["evidence_status"]["enum"]) == {e.value for e in EvidenceStatus}
