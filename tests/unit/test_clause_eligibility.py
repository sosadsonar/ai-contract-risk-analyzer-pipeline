from app.ai.clause_adapter import masked_items_from_segmentation
from app.clause.eligibility import is_eligible_clause_for_classification, source_position_metadata
from app.clause.segmenter import ClauseStructure, SegmentationResult, SegmentedClause


def test_source_only_eligibility():
    assert not is_eligible_clause_for_classification("Điều 1: Nghĩa vụ", {})
    assert not is_eligible_clause_for_classification("ĐẠI DIỆN BÊN A", {})
    assert not is_eligible_clause_for_classification("Nhóm công việc:\nCác việc sau:", {})
    assert not is_eligible_clause_for_classification(
        "Bên A có trách nhiệm trả lương", {"before_first_article": True})
    assert is_eligible_clause_for_classification("Bên A có trách nhiệm trả lương", {})


def test_ascii_dieu_heading_and_first_article_position():
    assert not is_eligible_clause_for_classification("DIEU 1: Nghĩa vụ", {})
    clauses = [
        SegmentedClause("cl_0001", "Thông tin hai bên", 0, 17, ClauseStructure(1, None, None)),
        SegmentedClause("cl_0002", "DIEU 1. Công việc", 18, 35, ClauseStructure(1, "1", None)),
    ]
    positions = source_position_metadata(clauses)
    assert positions[0]["before_first_article"] is True
    assert positions[1]["before_first_article"] is False


def test_adapter_excludes_preamble_and_heading_without_changing_partition():
    parts = ["HỢP ĐỒNG LAO ĐỘNG", "Điều 1: Tiền lương", "Bên A trả lương đúng hạn"]
    source = "\n".join(parts)
    spans = []
    offset = 0
    for index, part in enumerate(parts, 1):
        spans.append(SegmentedClause(f"cl_{index:04d}", part, offset, offset + len(part),
                                     ClauseStructure(1, None, None)))
        offset += len(part) + 1
    result = SegmentationResult(spans)
    items = masked_items_from_segmentation(result, source)
    assert [item.clause_id for item in items] == ["cl_0003"]
    assert len(result.clauses) == 3
