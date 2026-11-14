"""Fixed FR-06 scope decisions and Unicode title-window boundaries."""

import json
import unicodedata
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.document.scope_precheck import ScopeDecision, precheck

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/extraction/scope_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_labor_scope_fixed_positive_and_negative_cases(case):
    original = case["text"]
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=case.get("title_scan_chars", 1000))
    decision = precheck(original, cfg)
    assert isinstance(decision, ScopeDecision)
    assert decision.accept is case["accept"]
    if case["id"] == "deep-body-title-mention":
        assert "strong_title" not in decision.signals


def test_title_window_uses_code_points_before_normalizing_and_folding():
    title = "Hợp đồng lao động"
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=len(title))
    inside = title + "\nTiền lương."
    outside = "📄" + title + "\nTiền lương."
    assert precheck(inside, cfg).accept is True
    assert precheck(outside, cfg).accept is False
    assert "strong_title" not in precheck(outside, cfg).signals


def test_default_title_window_excludes_deep_body_mentions():
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=1000)
    body = "Báo cáo thống kê\n" + "Số liệu năm trước. " * 70
    decision = precheck(body + "Ví dụ về hợp đồng lao động. Lương tối thiểu.", cfg)
    assert decision.accept is False
    assert "strong_title" not in decision.signals


def test_precheck_uses_normalized_copy_without_changing_nfd_text():
    text = unicodedata.normalize("NFD", "HỢP ĐỒNG LAO ĐỘNG\nTiền lương")
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=1000)
    assert precheck(text, cfg).accept is True
    assert text != unicodedata.normalize("NFC", text)


def test_employment_groups_cap_at_three_points():
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=1000)
    decision = precheck("Hợp đồng lao động\nLương, thời giờ làm việc, công việc, thời hạn.", cfg)
    assert decision.score == 6
    assert len([signal for signal in decision.signals if signal.startswith("employment:")]) == 4


def test_one_party_term_alone_does_not_gain_pair_points():
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=1000)
    decision = precheck("Người lao động nhận lương.", cfg)
    assert decision.score == 1
    assert decision.accept is False


def test_scope_rule_version_is_v2():
    from app.document.scope_precheck import SCOPE_RULE_VERSION
    assert SCOPE_RULE_VERSION == "scope_rules_v2"


@pytest.mark.parametrize("title", ["PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG", "Nội quy lao động", "QUY CHẾ LƯƠNG",
                                   "Thỏa ước lao động tập thể", "Biên bản thanh lý", "Quyết định tuyển dụng",
                                   "Hợp đồng khoán việc", "Hợp đồng thuê khoán"])
def test_negative_title_prefix_rejects_even_with_both_parties(title):
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=1000)
    text = f"{title}\nNgười lao động và người sử dụng lao động thỏa thuận tiền lương, công việc.\nĐiều 1. a\nĐiều 2. b"
    decision = precheck(text, cfg)
    assert decision.accept is False and decision.signals == ["negative_title"]


def test_negative_title_checks_first_non_empty_line_only():
    cfg = SimpleNamespace(SCOPE_TITLE_SCAN_CHARS=1000)
    text = "\n\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nHỢP ĐỒNG LAO ĐỘNG\nPhụ lục kèm theo.\nNgười lao động nhận lương."
    assert precheck(text, cfg).accept is True
