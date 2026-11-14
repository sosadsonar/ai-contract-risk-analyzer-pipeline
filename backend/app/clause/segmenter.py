"""Clause segmentation v1 — luật + fallback paragraph (TDD §11, C-01 (a)).

Thay phần "cắt" của `clause_extraction_service.py` cũ (LLM cắt trên text chưa che + `_locate_span`):
segmentation là hàm THUẦN, local, chạy trên `masked_text`, KHÔNG gọi LLM, KHÔNG str.find.

Bất biến (AI_CONTEXT §3):
  INV-02  canonical_text[start_char:end_char] == original_text
  INV-03  các clause là partition KHÔNG chồng lấn; không ranh giới nào nằm trong placeholder PII;
          <= MAX_CLAUSES (150) clause, ngược lại ValidationReject("TOO_MANY_CLAUSES")
  INV-04  offset = Unicode code point (Python str index); canonical đã NFC,
          len(masked) == len(canonical)

"Partition" ở đây nghĩa là: các span sắp theo start, `end_i <= start_{i+1}`, mỗi span đã cắt bỏ
khoảng trắng đầu/cuối, và mọi ký tự khác khoảng trắng của văn bản đều thuộc đúng 1 clause
(không có "lỗ" chứa chữ). Khoảng trắng giữa hai clause không thuộc clause nào.

Quy tắc (TDD §11.2–11.3):
  - Mọi heading được chấp nhận (`structure_parser`) kết thúc clause trước đó, dù là cha hay con.
    Vì vậy clause "Điều 5" chỉ gồm tiêu đề + lời dẫn trước `5.1`.
  - Phần trước heading đầu tiên (quốc hiệu, thông tin các bên...) và toàn bộ văn bản nếu không có
    heading: tách theo paragraph. Paragraph < SHORT_PARAGRAPH_CHARS được gộp vào paragraph kế bên.
    Không tách giữa một dòng khi không có marker.
  - Clause > LONG_CLAUSE_CHARS giữ nguyên, ghi warning (không tách ngữ nghĩa bằng LLM).

`structure.parent_clause_id` lấy từ `structure_parser` (cha nằm trước con). Heading bị bỏ do nằm
trong placeholder không làm mất cha: cha là mark được chấp nhận gần nhất theo stack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.clause.structure_parser import HeadingMark, parse_structure
from app.domain.errors import ValidationReject
from app.privacy.pii_types import PiiSpan

SEGMENTATION_VERSION = "rules_v1.1"
PLUS_SEGMENTATION_VERSION = "rules_v1.2"
BLANK_PARAGRAPH_SEGMENTATION_VERSION = "rules_v1.3"
SEGMENTATION_SCHEMA_VERSION = "segmentation_v1"
OFFSET_UNIT = "unicode_code_point"

MAX_CLAUSES = 150  # SRS/TDD; cấu hình hóa ở core/config khi N4 dựng Settings
SHORT_PARAGRAPH_CHARS = 40  # TDD §11.3
LONG_CLAUSE_CHARS = 4000  # TDD §11.3

_BLANK_LINE = re.compile(r"\n[ \t]*\n")


def boundary_guard(pos: int, pii_spans: list[PiiSpan]) -> bool:
    """[TDD §10.3] False nếu start < pos < end của bất kỳ span PII (biên rơi vào trong placeholder).

    X-20 (N1, W4): cài đặt gốc nằm ở đây theo SKELETON §5.6. `app.privacy.masker` re-export lại
    để test/mã của N3 không phải đổi import. Hàm thuần, chỉ cần danh sách span viết tay để test.
    """
    return not any(span.start < pos < span.end for span in pii_spans)


def adjust_boundary(pos: int, pii_spans: list[PiiSpan]) -> int:
    """Dời biên ra đầu/cuối span nếu rơi vào trong placeholder (hòa thì về đầu)."""
    for span in pii_spans:
        if span.start < pos < span.end:
            return span.start if pos - span.start <= span.end - pos else span.end
    return pos


@dataclass(frozen=True)
class ClauseStructure:
    level: int
    number: Optional[str]
    parent_clause_id: Optional[str]


@dataclass(frozen=True)
class SegmentedClause:
    clause_id: str
    original_text: str
    start_char: int
    end_char: int
    structure: ClauseStructure


@dataclass(frozen=True)
class SegmentationResult:
    clauses: list[SegmentedClause]
    warnings: list[str] = field(default_factory=list)
    segmentation_version: str = SEGMENTATION_VERSION

    def to_dict(self) -> dict:
        """Dạng `segmentation_v1` (TDD §11.4)."""
        return {
            "schema_version": SEGMENTATION_SCHEMA_VERSION,
            "segmentation_version": self.segmentation_version,
            "offset_unit": OFFSET_UNIT,
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "original_text": c.original_text,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    "structure": {
                        "level": c.structure.level,
                        "number": c.structure.number,
                        "parent_clause_id": c.structure.parent_clause_id,
                    },
                }
                for c in self.clauses
            ],
        }


# ---------------------------------------------------------------------------------------------
# Helpers trên khoảng [lo, hi) của masked_text
# ---------------------------------------------------------------------------------------------


def _trim(text: str, lo: int, hi: int) -> Optional[tuple[int, int]]:
    """Cắt khoảng trắng đầu/cuối; None nếu rỗng."""
    while lo < hi and text[lo].isspace():
        lo += 1
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return (lo, hi) if lo < hi else None


def _paragraph_blocks(text: str, lo: int, hi: int) -> list[tuple[int, int]]:
    """Tách [lo,hi) thành khối paragraph (đã trim).

    Có dòng trống ⇒ tách theo dòng trống; không có ⇒ mỗi dòng không rỗng là một khối
    (không bao giờ cắt giữa một dòng).
    """
    region = text[lo:hi]
    spans: list[tuple[int, int]] = []
    if _BLANK_LINE.search(region):
        cursor = 0
        for m in _BLANK_LINE.finditer(region):
            spans.append((cursor, m.start()))
            cursor = m.end()
        spans.append((cursor, len(region)))
    else:
        cursor = 0
        for line in region.split("\n"):
            spans.append((cursor, cursor + len(line)))
            cursor += len(line) + 1
    out = []
    for a, b in spans:
        t = _trim(text, lo + a, lo + b)
        if t:
            out.append(t)
    return out


def _merge_short(text: str, blocks: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Gộp khối < SHORT_PARAGRAPH_CHARS vào khối kế tiếp (khối cuối: gộp vào khối trước).

    Gộp = span liền từ đầu khối trước tới cuối khối sau (gồm cả khoảng trắng ở giữa), vẫn là
    substring liền mạch nên INV-02 giữ nguyên.
    """
    merged: list[list[int]] = []
    carry: Optional[list[int]] = None
    for a, b in blocks:
        cur = [a, b]
        if carry is not None:
            cur = [carry[0], b]
            carry = None
        if cur[1] - cur[0] < SHORT_PARAGRAPH_CHARS:
            carry = cur
            continue
        merged.append(cur)
    if carry is not None:
        if merged:
            merged[-1][1] = carry[1]
        else:
            merged.append(carry)
    return [(a, b) for a, b in merged]


def _paragraph_clauses(text: str, lo: int, hi: int) -> list[tuple[int, int]]:
    return _merge_short(text, _paragraph_blocks(text, lo, hi))


def _split_blank_line_tail(text: str, lo: int, hi: int) -> list[tuple[int, int]]:
    """Split a marked clause only before a substantial independent blank-line paragraph.

    A single newline (including a wrapped dash item) is never a boundary here.
    The following first line must be a complete sentence of at least 60 characters.
    """
    cuts = [lo]
    for match in _BLANK_LINE.finditer(text, lo, hi):
        after = match.end()
        first_line = text[after:hi].split("\n", 1)[0].strip()
        if (len(first_line) >= 60 and first_line[0].isupper()
                and first_line.endswith(".") and not re.fullmatch(r"[.\s]+", first_line)):
            cuts.append(match.start())
    cuts.append(hi)
    return [span for a, b in zip(cuts, cuts[1:]) if (span := _trim(text, a, b))]


# ---------------------------------------------------------------------------------------------
# segment()
# ---------------------------------------------------------------------------------------------


def segment(
    canonical_text: str,
    masked_text: str,
    pii_spans: list[PiiSpan],
    *,
    max_clauses: int = MAX_CLAUSES,
    enable_plus_lists: bool = False,
    enable_blank_line_paragraphs: bool = False,
) -> SegmentationResult:
    """Cắt hợp đồng thành clause. Chạy trên `masked_text`, span tính trên `canonical_text`.

    `enable_plus_lists` chỉ dùng cho candidate D1 Dev; mặc định giữ rules_v1.1.

    Raises:
        ValueError: `len(masked_text) != len(canonical_text)` (vi phạm INV-01 từ bước che PII).
        ValidationReject("TOO_MANY_CLAUSES"): vượt `max_clauses`.
    """
    if len(masked_text) != len(canonical_text):
        raise ValueError("masked_text và canonical_text phải cùng độ dài (INV-01)")

    n = len(masked_text)
    guard = lambda pos: boundary_guard(pos, pii_spans)  # noqa: E731
    allowed_plus_positions = None
    if enable_plus_lists:
        baseline = segment(canonical_text, masked_text, pii_spans, max_clauses=max_clauses)
        # The parent block is the unsplit rules_v1.1 segment on the same source.
        allowed_plus_positions = {
            c.start_char + match.start() + len(match.group()) - len(match.group().lstrip(" \t"))
            for c in baseline.clauses if c.end_char - c.start_char >= 160
            for match in re.finditer(r"(?m)^[ \t]*\+[ \t]+\S", masked_text[c.start_char:c.end_char])
        }
    marks: list[HeadingMark] = parse_structure(
        masked_text, guard, allow_plus=enable_plus_lists,
        allowed_plus_positions=allowed_plus_positions)

    # (start, end, mark_index | None): None = vùng paragraph không thuộc heading nào.
    pieces: list[tuple[int, int, Optional[int]]] = []

    first = marks[0].start if marks else n
    for a, b in _paragraph_clauses(masked_text, 0, first):
        pieces.append((a, b, None))

    for i, mark in enumerate(marks):
        nxt = marks[i + 1].start if i + 1 < len(marks) else n
        t = _trim(masked_text, mark.start, nxt)
        if t:  # luôn có (mark.start trỏ vào ký tự không phải khoảng trắng) — phòng thủ
            pieces.append((t[0], t[1], i))

    if enable_blank_line_paragraphs:
        split_pieces: list[tuple[int, int, Optional[int]]] = []
        for a, b, mi in pieces:
            for index, (start, end) in enumerate(_split_blank_line_tail(masked_text, a, b)):
                split_pieces.append((start, end, mi if index == 0 else None))
        pieces = split_pieces

    # Ranh giới an toàn với PII: placeholder không chứa khoảng trắng nên trim không cắt vào trong,
    # nhưng kiểm lại và nới ra mép span (không bao giờ thu hẹp để không mất chữ khỏi partition).
    fixed: list[tuple[int, int, Optional[int]]] = []
    for a, b, mi in pieces:
        for span in pii_spans:
            if span.start < b < span.end:
                b = span.end
            if span.start < a < span.end:
                a = span.start
        fixed.append((a, b, mi))
    pieces = fixed

    if len(pieces) > max_clauses:
        raise ValidationReject("TOO_MANY_CLAUSES", f"{len(pieces)} > {max_clauses}")

    # Gán id + cha. clause_id theo start_char tăng dần (pieces đã theo thứ tự văn bản).
    ids = [f"cl_{i + 1:04d}" for i in range(len(pieces))]
    mark_to_clause = {mi: ids[ci] for ci, (_, _, mi) in enumerate(pieces) if mi is not None}

    warnings: list[str] = []
    clauses: list[SegmentedClause] = []
    for ci, (a, b, mi) in enumerate(pieces):
        if mi is None:
            structure = ClauseStructure(level=1, number=None, parent_clause_id=None)
        else:
            mark = marks[mi]
            parent = (
                mark_to_clause.get(mark.parent_index) if mark.parent_index is not None else None
            )
            structure = ClauseStructure(
                level=mark.level, number=mark.number, parent_clause_id=parent
            )
        if b - a > LONG_CLAUSE_CHARS:
            warnings.append(f"{ids[ci]}: dài {b - a} > {LONG_CLAUSE_CHARS} ký tự (giữ nguyên)")
        clauses.append(
            SegmentedClause(
                clause_id=ids[ci],
                original_text=canonical_text[a:b],
                start_char=a,
                end_char=b,
                structure=structure,
            )
        )

    _assert_invariants(canonical_text, clauses, pii_spans)
    version = (BLANK_PARAGRAPH_SEGMENTATION_VERSION if enable_blank_line_paragraphs
               else PLUS_SEGMENTATION_VERSION if enable_plus_lists else SEGMENTATION_VERSION)
    return SegmentationResult(clauses=clauses, warnings=warnings, segmentation_version=version)


def _assert_invariants(text: str, clauses: list[SegmentedClause], pii_spans: list[PiiSpan]) -> None:
    """Kiểm INV-02/03 trước khi trả ra; lỗi = bug của segmenter (không phải lỗi người dùng).

    Dùng `raise` thay `assert` để `python -O` không bỏ qua.
    """
    prev_end = 0
    for c in clauses:
        if text[c.start_char : c.end_char] != c.original_text:
            raise RuntimeError(f"INV-02: {c.clause_id} original_text lệch canonical")
        if c.start_char < prev_end or c.end_char <= c.start_char:
            raise RuntimeError(f"INV-03: {c.clause_id} chồng lấn hoặc rỗng")
        if not boundary_guard(c.start_char, pii_spans) or not boundary_guard(c.end_char, pii_spans):
            raise RuntimeError(f"INV-03: {c.clause_id} có ranh giới trong placeholder PII")
        prev_end = c.end_char
