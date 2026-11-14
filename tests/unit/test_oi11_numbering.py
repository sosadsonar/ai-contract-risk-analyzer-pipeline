"""SRS OI-11 (decision_SRS_OI-11_v3): DOCX numbering → canonical text → structure_parser.

Expected text ở đây được viết tay theo cách Word hiển thị cho các fixture TỔNG HỢP. Điều kiện
đóng OI-11 vẫn cần fixture DOCX thực do N2 cung cấp và đối chiếu (OPEN_ISSUES_HANDLE_v4 §6.4);
file này chỉ khóa hợp đồng extractor ↔ parser và hai regression P2 của review N4.
"""

import pytest
from app.clause.segmenter import segment
from app.clause.structure_parser import (
    DASH,
    LETTERED,
    NUMBERED,
    ROMAN,
    STRUCTURE_PARSER_VERSION,
    parse_structure,
    roman_value,
)
from app.document.canonicalizer import canonicalize
from app.document.docx_extractor import extract_docx
from app.document.extractor import DOCX_EXTRACTION_VERSION, extract
from app.privacy.masker import mask
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# ---------------------------------------------------------------- helpers


def _el(tag, **attrs):
    element = OxmlElement(f"w:{tag}")
    for key, value in attrs.items():
        element.set(qn(f"w:{key}"), str(value))
    return element


def _level(index, fmt, text, start=1, restart=None):
    level = _el("lvl", ilvl=index)
    level.append(_el("start", val=start))
    level.append(_el("numFmt", val=fmt))
    if restart is not None:
        level.append(_el("lvlRestart", val=restart))
    level.append(_el("lvlText", val=text))
    return level


def _numbering(doc, levels, overrides=()):
    """Thêm abstractNum + num; overrides = [(ilvl, lvl_element|None, start_override|None)]."""
    root = doc.part.numbering_part.element
    abstract_id = max(int(e.get(qn("w:abstractNumId"))) for e in root.findall(qn("w:abstractNum"))) + 1
    num_id = max(int(e.get(qn("w:numId"))) for e in root.findall(qn("w:num"))) + 1
    abstract = _el("abstractNum", abstractNumId=abstract_id)
    for level in levels:
        abstract.append(level)
    # abstractNum phải đứng trước mọi w:num trong numbering.xml
    first_num = root.find(qn("w:num"))
    if first_num is not None:
        first_num.addprevious(abstract)
    else:
        root.append(abstract)
    num = _el("num", numId=num_id)
    num.append(_el("abstractNumId", val=abstract_id))
    for ilvl, lvl, start in overrides:
        override = _el("lvlOverride", ilvl=ilvl)
        if start is not None:
            override.append(_el("startOverride", val=start))
        if lvl is not None:
            override.append(lvl)
        num.append(override)
    root.append(num)
    return num_id


def _item(doc, text, num_id, ilvl):
    paragraph = doc.add_paragraph(text)
    num_pr = _el("numPr")
    num_pr.append(_el("ilvl", val=ilvl))
    num_pr.append(_el("numId", val=num_id))
    paragraph._p.get_or_add_pPr().append(num_pr)
    return paragraph


class _Canonical:
    def __init__(self, text):
        self.canonical_text = text


def _extract(doc, tmp_path, name="f.docx"):
    """DOCX → canonical text (bỏ quality gate độ dài tối thiểu vì fixture ngắn có chủ ý)."""
    path = tmp_path / name
    doc.save(path)
    return _Canonical(canonicalize(extract_docx(path)))


def test_full_extract_path_uses_v2(tmp_path):
    doc = Document()
    doc.add_paragraph("Hợp đồng lao động giữa người lao động và người sử dụng lao động. " * 3)
    path = tmp_path / "full.docx"
    doc.save(path)
    assert extract(path, "docx").extraction_version == "extract_docx_v2"


# ---------------------------------------------------------------- parser


def test_versions_bumped_for_changed_canonical_and_parser():
    assert DOCX_EXTRACTION_VERSION == "extract_docx_v2"
    assert STRUCTURE_PARSER_VERSION == "structure_parser_v2"


@pytest.mark.parametrize("num,value", [("I", 1), ("iv", 4), ("IX", 9), ("XIV", 14), ("MCMXC", 1990),
                                       ("IIII", None), ("VX", None), ("Iv", None), ("", None)])
def test_roman_value(num, value):
    assert roman_value(num) == value


def test_roman_sequence_recognised_separately_from_letters():
    marks = parse_structure("I. Chung\nII. Tiền lương\nIII. Thời giờ\nIV. Chấm dứt")
    assert [(m.kind, m.number) for m in marks] == [(ROMAN, "I"), (ROMAN, "II"), (ROMAN, "III"), (ROMAN, "IV")]
    marks = parse_structure("i) một\nii) hai")
    assert [m.kind for m in marks] == [ROMAN, ROMAN]


def test_letters_that_look_roman_stay_lettered():
    marks = parse_structure("a) một\nb) hai\nc) ba\nd) bốn")
    assert [m.kind for m in marks] == [LETTERED] * 4
    marks = parse_structure("g) bảy\nh) tám\ni) chín\nk) mười")  # bắt đầu không phải a → bỏ cả nhóm
    assert marks == []


def test_plus_bullet_is_dash_variant():
    marks = parse_structure("+ Lương cơ bản\n+ Phụ cấp\n- Thưởng\n• Khác")
    assert {m.kind for m in marks} == {DASH} and len(marks) == 4


@pytest.mark.parametrize("text", [
    "I. Chỉ một mục La Mã",          # singleton
    "I. Một\nIII. Ba",               # đứt chuỗi
    "II. Hai\nIII. Ba",              # không bắt đầu từ I
    "+ Chỉ một dòng cộng",            # singleton dash
    "1. Một\n3. Ba",                 # numbered đứt chuỗi (giữ quy tắc cũ)
])
def test_weak_group_limits_unchanged(text):
    assert parse_structure(text) == []


def test_roman_parent_child_levels():
    marks = parse_structure("I. Chung\n1. Một\n2. Hai\nII. Riêng\n1. Ba\n2. Bốn")
    assert [(m.kind, m.level, m.parent_index) for m in marks] == [
        (ROMAN, 1, None), (NUMBERED, 2, 0), (NUMBERED, 2, 0),
        (ROMAN, 1, None), (NUMBERED, 2, 3), (NUMBERED, 2, 3)]


# ---------------------------------------------------------------- extractor regressions (P2)


def test_regression_effective_level_override_used_in_placeholder(tmp_path):
    """(a) lvlOverride thay w:lvl: cả level hiện tại lẫn %N tham chiếu phải dùng format override."""
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    override_lvl0 = _level(0, "upperRoman", "%1.")
    num_id = _numbering(doc, [_level(0, "decimal", "%1."), _level(1, "lowerLetter", "%1.%2)")],
                        overrides=[(0, override_lvl0, None)])
    _item(doc, "Quy định chung", num_id, 0)
    _item(doc, "Phạm vi", num_id, 1)
    _item(doc, "Tiền lương", num_id, 0)
    text = _extract(doc, tmp_path).canonical_text
    assert text == "HỢP ĐỒNG LAO ĐỘNG\nI. Quy định chung\nI.a) Phạm vi\nII. Tiền lương"


def test_regression_lvl_restart_zero_does_not_reset(tmp_path):
    """(b) lvlRestart=0: cấp con KHÔNG đánh lại khi cấp cha tăng."""
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    num_id = _numbering(doc, [_level(0, "upperRoman", "%1."), _level(1, "decimal", "%2.", restart=0)])
    for ilvl, text in ((0, "Chung"), (1, "Một"), (1, "Hai"), (0, "Riêng"), (1, "Ba")):
        _item(doc, text, num_id, ilvl)
    text = _extract(doc, tmp_path).canonical_text
    assert text == "HỢP ĐỒNG LAO ĐỘNG\nI. Chung\n1. Một\n2. Hai\nII. Riêng\n3. Ba"


def test_default_restart_still_resets_children(tmp_path):
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    num_id = _numbering(doc, [_level(0, "upperRoman", "%1."), _level(1, "decimal", "%2.")])
    for ilvl, text in ((0, "Chung"), (1, "Một"), (1, "Hai"), (0, "Riêng"), (1, "Ba")):
        _item(doc, text, num_id, ilvl)
    assert _extract(doc, tmp_path).canonical_text.endswith("II. Riêng\n1. Ba")


# ---------------------------------------------------------------- fixtures tối thiểu §3


def test_multilevel_list_extraction_then_parser(tmp_path):
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    num_id = _numbering(doc, [_level(0, "upperRoman", "%1."), _level(1, "decimal", "%2."),
                              _level(2, "lowerLetter", "%3)")])
    for ilvl, text in ((0, "Công việc"), (1, "Chức danh chuyên viên"), (2, "Báo cáo tuần"),
                       (2, "Báo cáo tháng"), (1, "Địa điểm làm việc"), (0, "Tiền lương"),
                       (1, "Mức lương chính"), (1, "Phụ cấp")):
        _item(doc, text, num_id, ilvl)
    text = _extract(doc, tmp_path).canonical_text
    assert text == ("HỢP ĐỒNG LAO ĐỘNG\nI. Công việc\n1. Chức danh chuyên viên\na) Báo cáo tuần\n"
                    "b) Báo cáo tháng\n2. Địa điểm làm việc\nII. Tiền lương\n1. Mức lương chính\n2. Phụ cấp")
    marks = parse_structure(text)
    assert [(m.kind, m.number, m.level, m.parent_index) for m in marks] == [
        (ROMAN, "I", 1, None), (NUMBERED, "1", 2, 0), (LETTERED, "a", 3, 1), (LETTERED, "b", 3, 1),
        (NUMBERED, "2", 2, 0), (ROMAN, "II", 1, None), (NUMBERED, "1", 2, 5), (NUMBERED, "2", 2, 5)]


@pytest.mark.parametrize("symbol,expected", [("-", "-"), ("–", "–"), ("", "•"), ("•", "•"), ("+", "+")])
def test_bullet_formats_materialized_and_parsed(tmp_path, symbol, expected):
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    num_id = _numbering(doc, [_level(0, "bullet", symbol)])
    _item(doc, "Lương cơ bản", num_id, 0)
    _item(doc, "Phụ cấp ăn trưa", num_id, 0)
    text = _extract(doc, tmp_path).canonical_text
    assert text == f"HỢP ĐỒNG LAO ĐỘNG\n{expected} Lương cơ bản\n{expected} Phụ cấp ăn trưa"
    assert [m.kind for m in parse_structure(text)] == [DASH, DASH]


def test_typed_numbering_kept_verbatim(tmp_path):
    doc = Document()
    for line in ("HỢP ĐỒNG LAO ĐỘNG", "Điều 1. Công việc", "1) Chức danh", "2) Địa điểm",
                 "I. Phần chung", "II. Phần riêng", "+ Lương", "+ Thưởng"):
        doc.add_paragraph(line)
    text = _extract(doc, tmp_path).canonical_text
    assert text == "HỢP ĐỒNG LAO ĐỘNG\nĐiều 1. Công việc\n1) Chức danh\n2) Địa điểm\nI. Phần chung\nII. Phần riêng\n+ Lương\n+ Thưởng"


def test_mixed_automatic_and_typed_marker_not_duplicated_or_lost(tmp_path):
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    num_id = _numbering(doc, [_level(0, "decimal", "%1.")])
    _item(doc, "Công việc", num_id, 0)            # tự động → "1. "
    _item(doc, "2. Tiền lương", num_id, 0)         # tự động + gõ tay trùng → không nhân đôi
    _item(doc, "Thời giờ", num_id, 0)              # vẫn đếm tiếp → "3. "
    doc.add_paragraph("4. Điều khoản gõ tay")       # gõ tay thuần
    text = _extract(doc, tmp_path).canonical_text
    assert text == "HỢP ĐỒNG LAO ĐỘNG\n1. Công việc\n2. Tiền lương\n3. Thời giờ\n4. Điều khoản gõ tay"
    assert "2. 2." not in text
    assert [m.number for m in parse_structure(text)] == ["1", "2", "3", "4"]


def test_unsupported_format_not_guessed_and_group_limit_detected(tmp_path):
    """Format ngoài phạm vi không được materialize; nhóm còn lại đứt chuỗi → parser bỏ (giới hạn §4)."""
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    num_ok = _numbering(doc, [_level(0, "decimal", "%1.")])
    num_bad = _numbering(doc, [_level(0, "ordinalText", "%1.")])
    _item(doc, "Công việc", num_ok, 0)
    _item(doc, "Mục định dạng lạ", num_bad, 0)
    _item(doc, "Tiền lương", num_ok, 0)
    text = _extract(doc, tmp_path).canonical_text
    assert text == "HỢP ĐỒNG LAO ĐỘNG\n1. Công việc\nMục định dạng lạ\n2. Tiền lương"
    single = Document()
    single.add_paragraph("HỢP ĐỒNG LAO ĐỘNG")
    num_single = _numbering(single, [_level(0, "upperRoman", "%1.")])
    _item(single, "Mục duy nhất", num_single, 0)
    single_text = _extract(single, tmp_path, "single.docx").canonical_text
    assert single_text.endswith("I. Mục duy nhất")
    assert parse_structure(single_text) == []  # singleton: giới hạn được phát hiện, không coi là cấu trúc


def test_spans_after_materialized_marker_point_to_canonical_substring(tmp_path):
    doc = Document()
    doc.add_paragraph("HỢP ĐỒNG LAO ĐỘNG 📄")  # non-BMP để kiểm offset code point
    num_id = _numbering(doc, [_level(0, "upperRoman", "%1.")])
    _item(doc, "Công việc: chuyên viên phân tích dữ liệu theo phân công.", num_id, 0)
    _item(doc, "Tiền lương: trả theo tháng bằng chuyển khoản.", num_id, 0)
    canonical = _extract(doc, tmp_path).canonical_text
    masking = mask(canonical)
    result = segment(canonical, masking.masked_text, masking.pii_spans)
    texts = [canonical[c.start_char:c.end_char] for c in result.clauses]
    assert any(t.startswith("II. Tiền lương") for t in texts)
    for clause in result.clauses:
        assert canonical[clause.start_char:clause.end_char] == clause.original_text
