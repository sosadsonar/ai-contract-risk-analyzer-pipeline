"""Assembler: ghép clause upstream + câu trả lời LLM (risk_output_v2) thành risk_merged_v1."""

import copy

import pytest
from app.integrations.risk_assembler import (
    AssemblerContext,
    RiskAssemblerError,
    assemble_risk_output,
)

TEXT = "A" * 10 + "B" * 20 + "C" * 15


def _upstream():
    return [
        {
            "clause_id": "cl_0001", "clause_number": "1", "start_char": 0, "end_char": 10,
            "original_text": "A" * 10, "clause_labels": ["WORKING_CONDITIONS"],
        },
        {
            "clause_id": "cl_0002", "clause_number": "2",
            "span": {"start_char": 10, "end_char": 30},
            "original_text": "B" * 20, "clause_labels": ["TRAINING"],
        },
        {
            "clause_id": "cl_0003", "clause_number": None, "start_char": 30, "end_char": 45,
            "original_text": "C" * 15, "clause_labels": ["OTHER"],
        },
    ]


def _item(cid, **kw):
    base = {
        "clause_id": cid,
        "basis_type": "LEGAL_VIOLATION",
        "risk_labels": ["DEPOSIT_DOCUMENT_HELD"],
        "citation_ids": ["BLLD2019:art17"],
        "evidence_status": "SUPPORTED",
        "explanation": "Điều khoản trái quy định về giữ giấy tờ của người lao động.",
    }
    base.update(kw)
    return base


def _ai(*items):
    return {"schema_version": "risk_output_v2", "items": list(items)}


def _ctx(role="EMPLOYEE", citations=None):
    if citations is None:
        citations = [{"citation_id": "BLLD2019:art17"}, {"citation_id": "BLLD2019:art26"}]
    return AssemblerContext(
        session_id="s1", role=role, clause_stage={"prompt_version": "c1"},
        citations=citations, model_id="m", prompt_version="risk_prompt_v1",
    )


def test_happy_path_flat_span_pins_from_ctx_and_only_used_citations():
    res = assemble_risk_output(_upstream(), _ai(_item("cl_0002")), _ctx(), canonical_text=TEXT)
    m = res.merged
    assert m["schema_version"] == "risk_merged_v1"
    assert (m["model_id"], m["prompt_version"]) == ("m", "risk_prompt_v1")
    assert m["risk_taxonomy_version"] == "risk_taxonomy_v01"
    assert m["citations"] == [{"citation_id": "BLLD2019:art17"}]
    c = m["clauses"][0]
    assert (c["start_char"], c["end_char"], c["original_text"]) == (10, 30, "B" * 20)
    assert "span" not in c and not any(k.startswith("_") for k in c)
    assert c["severity"] == "HIGH"
    assert res.diagnostics == {"need_review": [], "labels_dropped": []}


def test_risk_basis_is_one_to_one_with_risk_labels():
    ai = _ai(
        _item(
            "cl_0001",
            basis_type="AMBIGUOUS",
            risk_labels=["PROBATION", "CONTRACT_TERM_TYPE"],
        )
    )
    c = assemble_risk_output(_upstream(), ai, _ctx()).merged["clauses"][0]
    assert c["risk_labels"] == ["PROBATION", "CONTRACT_TERM_TYPE"]
    assert c["risk_basis"] == [
        {"label": "PROBATION", "basis_type": "AMBIGUOUS"},
        {"label": "CONTRACT_TERM_TYPE", "basis_type": "AMBIGUOUS"},
    ]
    assert "basis_type" not in c


def test_no_risk_gives_empty_clauses():
    res = assemble_risk_output(_upstream(), _ai(), _ctx())
    assert res.merged["clauses"] == [] and res.merged["citations"] == []


def test_output_follows_upstream_order_not_llm_order():
    ai = _ai(_item("cl_0003"), _item("cl_0001"))
    res = assemble_risk_output(_upstream(), ai, _ctx())
    assert [c["clause_id"] for c in res.merged["clauses"]] == ["cl_0001", "cl_0003"]


def test_inputs_are_not_mutated():
    up, ai = _upstream(), _ai(_item("cl_0001", basis_type="UNFAVORABLE"))
    up0, ai0 = copy.deepcopy(up), copy.deepcopy(ai)
    assemble_risk_output(up, ai, _ctx())
    assert up == up0 and ai == ai0


def test_severity_comes_from_table_and_ignores_any_llm_value():
    # TRAINING_COMMITMENT + LV + EMPLOYEE = HIGH; trường severity thừa từ LLM bị bỏ qua
    ai = _ai(_item("cl_0002", risk_labels=["TRAINING_COMMITMENT"], severity="LOW"))
    res = assemble_risk_output(_upstream(), ai, _ctx())
    assert res.merged["clauses"][0]["severity"] == "HIGH"


def test_role_changes_the_table_severity():
    ai = _ai(_item("cl_0001", risk_labels=["BONUS_BENEFITS"]))
    emp = assemble_risk_output(_upstream(), ai, _ctx("EMPLOYEE")).merged["clauses"][0]
    er = assemble_risk_output(_upstream(), ai, _ctx("EMPLOYER")).merged["clauses"][0]
    assert (emp["severity"], er["severity"]) == ("MEDIUM", "HIGH")


def test_dash_cell_drops_clause_and_flags_need_review():
    # SOCIAL_INSURANCE + UNFAVORABLE là '-' cho cả hai vai trò
    bad = _item("cl_0001", basis_type="UNFAVORABLE", risk_labels=["SOCIAL_INSURANCE"])
    res = assemble_risk_output(_upstream(), _ai(bad, _item("cl_0002")), _ctx())
    assert [c["clause_id"] for c in res.merged["clauses"]] == ["cl_0002"]
    assert res.diagnostics["need_review"][0]["clause_id"] == "cl_0001"


def test_dash_label_removed_but_valid_label_kept():
    item = _item(
        "cl_0001", basis_type="UNFAVORABLE", risk_labels=["PROBATION", "BONUS_BENEFITS"]
    )
    res = assemble_risk_output(_upstream(), _ai(item), _ctx("EMPLOYER"))
    clause = res.merged["clauses"][0]
    assert clause["risk_labels"] == ["BONUS_BENEFITS"]
    assert clause["risk_basis"] == [{"label": "BONUS_BENEFITS", "basis_type": "UNFAVORABLE"}]
    assert res.diagnostics["labels_dropped"][0]["labels"] == ["PROBATION"]
    assert res.diagnostics["need_review"] == []


def test_insufficient_evidence_keeps_null_severity_and_no_citations():
    ai = _ai(_item("cl_0001", evidence_status="INSUFFICIENT_EVIDENCE", citation_ids=[]))
    c = assemble_risk_output(_upstream(), ai, _ctx()).merged["clauses"][0]
    assert c["severity"] is None and c["citation_ids"] == []


@pytest.mark.parametrize(
    "ai",
    [
        _ai(_item("cl_9999")),  # clause lạ
        _ai(_item("cl_0001"), _item("cl_0001")),  # trùng
        _ai(_item("cl_0001", citation_ids=[])),  # SUPPORTED không citation
        _ai(_item("cl_0001", evidence_status="INSUFFICIENT_EVIDENCE")),  # còn citation
        _ai(_item("cl_0001", citation_ids=["BLLD2019:art99"])),  # citation chưa resolve
        _ai(_item("cl_0001", risk_labels=["NOT_A_LABEL"])),  # nhãn ngoài taxonomy
        _ai(_item("cl_0001", basis_type="BAD")),
        _ai(_item("cl_0001", explanation="  ")),
        {"schema_version": "risk_output_v1", "items": []},
    ],
)
def test_invalid_ai_output_raises(ai):
    with pytest.raises(RiskAssemblerError):
        assemble_risk_output(_upstream(), ai, _ctx())


def test_invalid_role_raises():
    with pytest.raises(RiskAssemblerError):
        assemble_risk_output(_upstream(), _ai(), _ctx("ADMIN"))


def test_broken_upstream_raises():
    dup = _upstream() + [_upstream()[0]]
    with pytest.raises(RiskAssemblerError):
        assemble_risk_output(dup, _ai(), _ctx())
    no_text = _upstream()
    del no_text[0]["original_text"]
    with pytest.raises(RiskAssemblerError):
        assemble_risk_output(no_text, _ai(), _ctx())


def test_canonical_text_mismatch_raises_inv03():
    with pytest.raises(RiskAssemblerError):
        assemble_risk_output(_upstream(), _ai(), _ctx(), canonical_text="X" * 45)
