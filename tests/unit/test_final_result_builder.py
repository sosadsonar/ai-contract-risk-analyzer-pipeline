"""Final client envelope is assembled after masked provider work."""

import pytest
from app.session.final_result import build_final_result_v1, resolve_app_commit

_PINS = {
    "extraction_version": "caller_canonical_v1",
    "clause_taxonomy_version": "clause_taxonomy_v03",
    "risk_taxonomy_version": "risk_taxonomy_v01",
    "severity_rubric_version": "severity_v01",
    "corpus_version": "legal_corpus_2026-10-12",
    "data_graph_version": "legal_graph_2026-10-12",
    "clause_prompt_version": "clause_prompt_v1",
    "risk_prompt_version": "risk_prompt_v1",
    "model_id": "fake-model",
    "temperature": 0.0,
    "app_commit": "test-commit",
}


def _inputs():
    text = "Điều khoản chưa rõ."
    clauses = [{"clause_id": "cl_0001", "start_char": 0,
                "end_char": len(text), "original_text": text,
                "clause_labels": ["COMPENSATION_BENEFITS"]}]
    merged = {"clauses": [{**clauses[0], "risk_labels": ["UNILATERAL_CHANGE"],
                           "risk_basis": [{"label": "UNILATERAL_CHANGE",
                                           "basis_type": "AMBIGUOUS"}],
                           "severity": "MEDIUM", "explanation": "Điều khoản cần làm rõ.",
                           "evidence_status": "SUPPORTED", "citation_ids": ["LAW:1"]}],
              "citations": [{"citation_id": "LAW:1", "document_name": "Law",
                             "article": "1", "content": "Public provision"}]}
    return text, clauses, merged


def test_final_result_has_exact_envelope_and_source_offsets():
    text, clauses, merged = _inputs()
    result = build_final_result_v1(
        session_id="session-1", role="EMPLOYEE", analysis_date="2026-11-13",
        canonical_text=text, clauses=clauses, merged=merged,
        related_clause_ids={"cl_0001": []}, version_pins=_PINS,
    )
    assert result["schema_version"] == "final_result_v1"
    assert result["offset_unit"] == "unicode_code_point"
    assert result["status"] == "COMPLETED"
    assert set(result) == {"schema_version", "offset_unit", "session_id", "role",
                           "status", "analysis_date", "canonical_text", "clauses",
                           "risks", "citations", "disclaimer", "data_notice",
                           "version_pins"}
    assert result["clauses"] == clauses
    assert len(result["version_pins"]) == 11
    assert result["risks"][0]["quote"] == text
    assert result["risks"][0]["start_char"] == 0
    assert result["risks"][0]["end_char"] == len(text)
    assert result["risks"][0]["risk_basis"] == [
        {"label": "UNILATERAL_CHANGE", "basis_type": "AMBIGUOUS"}]


def test_final_result_rejects_offset_mismatch_and_unpinned_model():
    text, clauses, merged = _inputs()
    clauses[0]["end_char"] -= 1
    with pytest.raises(ValueError, match="offset"):
        build_final_result_v1(
            session_id="session-1", role="EMPLOYEE", analysis_date="2026-11-13",
            canonical_text=text, clauses=clauses, merged=merged,
            related_clause_ids={}, version_pins=_PINS,
        )
    clauses[0]["end_char"] += 1
    with pytest.raises(ValueError, match="version"):
        build_final_result_v1(
            session_id="session-1", role="EMPLOYEE", analysis_date="2026-11-13",
            canonical_text=text, clauses=clauses, merged=merged,
            related_clause_ids={}, version_pins={k: v for k, v in _PINS.items()
                                                  if k != "model_id"},
        )


def test_app_commit_uses_environment_then_git_then_no_git_fallback(monkeypatch, tmp_path):
    env_sha = "a" * 40
    monkeypatch.setenv("APP_COMMIT", env_sha)
    assert resolve_app_commit(repo_root=tmp_path) == env_sha
    monkeypatch.delenv("APP_COMMIT")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr("app.session.final_result.subprocess.run", lambda *args, **kwargs:
                        type("Result", (), {"returncode": 0, "stdout": "B" * 40})())
    assert resolve_app_commit(repo_root=repo) == "b" * 40
    assert resolve_app_commit(repo_root=tmp_path) == "dev-unpinned"
