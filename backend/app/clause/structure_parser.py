"""Nhận diện heading/list marker cấu trúc trong masked_text (TDD §11.2, C-02).

Thay `document_router` + `CLAUSE_PATTERN` cũ (`utils/text_processing.py`): không còn "router"
chọn Pipeline A/B theo tỉ lệ heading. Luôn chạy parser; không có heading đáng tin cậy thì
`segmenter` rơi về fallback paragraph (§11.3).

5 pattern (mỗi pattern neo ở đầu dòng):
  1. article   `Điều 5. Tiêu đề`
  2. decimal   `5.1 ...`, `5.1.2 ...` (sâu tối đa 4 cấp)
  3. numbered  `1. ...` / `1) ...`
  4. lettered  `a) ...` / `a. ...`
  5. dash      `- ...`, `– ...`, `• ...`

Hàm thuần: không đụng I/O, không import api/session. Offset = Unicode code point trên
masked_text (cùng độ dài canonical_text, INV-01).

Quy tắc độ tin cậy (TDD §11.2: "chỉ thành clause riêng khi rule list đủ tin cậy"):
  - article, decimal: luôn tin cậy (trừ dạng số có dấu phân cách hàng nghìn: `2.000.000 đồng`).
  - numbered, lettered, dash: chỉ giữ khi nhóm anh em cùng cha có >= 2 mục; riêng numbered /
    lettered còn phải đánh số liên tiếp (1,2,3 / a,b,c) và bắt đầu từ mục đầu (1 / a).
    Mục lẻ loi nằm lại trong clause hiện tại, không tạo ranh giới.
  - Heading có `start` rơi vào trong placeholder PII (`boundary_guard` = False) bị BỎ (TDD §10.3,
    chọn "bỏ match" thay vì dời để không tạo clause rỗng).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

STRUCTURE_PARSER_VERSION = "structure_parser_v1"

# ---- 5 pattern (TDD §11.2). Chạy theo từng dòng; group "body" là phần sau marker. ----
_ARTICLE = re.compile(r"^[ \t]*Điều[ \t]+(?P<num>\d+[A-Za-z]?)[ \t]*[.:\-]?[ \t]*(?P<body>.*)$")
_DECIMAL = re.compile(r"^[ \t]*(?P<num>\d+(?:\.\d+){1,3})[ \t]*[.)\-]?[ \t]+(?P<body>\S.*)$")
_NUMBERED = re.compile(r"^[ \t]*(?P<num>\d{1,3})[.)][ \t]+(?P<body>\S.*)$")
_LETTERED = re.compile(r"^[ \t]*(?P<num>[a-zA-ZđĐ])[.)][ \t]+(?P<body>\S.*)$")
_DASH = re.compile(r"^[ \t]*[-–•][ \t]+(?P<body>\S.*)$")

ARTICLE, DECIMAL, NUMBERED, LETTERED, DASH = "article", "decimal", "numbered", "lettered", "dash"
_WEAK_KINDS = (NUMBERED, LETTERED, DASH)

# Chữ cái liệt kê tiếng Việt (có đ giữa d và e) và dạng ASCII — chấp nhận cả hai cách đánh.
_ALPHA_VN = "abcdđeghiklmnopqrstuvxy"
_ALPHA_ASCII = "abcdefghijklmnopqrstuvwxyz"


@dataclass(frozen=True)
class HeadingMark:
    """Một marker cấu trúc được chấp nhận. `start` = vị trí ký tự đầu tiên (không phải khoảng
    trắng) của dòng chứa marker, tính trên masked_text."""

    start: int
    kind: str  # ARTICLE | DECIMAL | NUMBERED | LETTERED | DASH
    number: Optional[str]  # "5", "5.1", "1", "a"; None với dash
    level: int  # 1 = cấp cao nhất
    parent_index: Optional[int]  # chỉ số của mark cha trong danh sách kết quả; None nếu gốc


def _line_start_iter(text: str):
    """Yield (offset_đầu_dòng, nội_dung_dòng) không gồm '\\n'."""
    pos = 0
    for line in text.split("\n"):
        yield pos, line
        pos += len(line) + 1


def _is_thousands_number(num: str) -> bool:
    """`2.000.000`, `1.500`: mọi nhóm sau dấu chấm đầu gồm đúng 3 chữ số → là số tiền, không phải
    số điều khoản. (`5.100` cũng bị loại: chấp nhận đánh đổi, khoản đánh số 3 chữ số là hiếm.)"""
    groups = num.split(".")
    return all(len(g) == 3 and g.isdigit() for g in groups[1:])


def _candidates(text: str) -> list[tuple[int, str, Optional[str], int]]:
    """Mọi dòng khớp 1 trong 5 pattern: (start, kind, number, decimal_depth)."""
    out: list[tuple[int, str, Optional[str], int]] = []
    for line_start, line in _line_start_iter(text):
        stripped = line.lstrip(" \t")
        if not stripped:
            continue
        start = line_start + (len(line) - len(stripped))
        m = _ARTICLE.match(line)
        if m:
            out.append((start, ARTICLE, m.group("num"), 0))
            continue
        m = _DECIMAL.match(line)
        if m:
            num = m.group("num")
            if not _is_thousands_number(num):
                out.append((start, DECIMAL, num, num.count(".")))
                continue
        m = _NUMBERED.match(line)
        if m:
            out.append((start, NUMBERED, m.group("num"), 0))
            continue
        m = _LETTERED.match(line)
        if m:
            out.append((start, LETTERED, m.group("num"), 0))
            continue
        if _DASH.match(line):
            out.append((start, DASH, None, 0))
    return out


def _style_key(kind: str, depth: int) -> str:
    return f"{kind}{depth}" if kind == DECIMAL else kind


def _assign_levels(
    cands: list[tuple[int, str, Optional[str], int]],
) -> list[tuple[int, Optional[int]]]:
    """Gán (level, parent_index) bằng stack theo "kiểu" marker.

    - Article luôn reset stack (level 1).
    - Marker có kiểu đã nằm trong stack ⇒ anh em của nó: pop về đó, cùng level, cùng cha.
    - Kiểu mới ⇒ con của đỉnh stack (level = đỉnh + 1). Stack rỗng ⇒ level 1.
    """
    stack: list[tuple[str, int, int]] = []  # (style, level, index)
    result: list[tuple[int, Optional[int]]] = []
    for idx, (_, kind, _, depth) in enumerate(cands):
        key = _style_key(kind, depth)
        if kind == ARTICLE:
            stack.clear()
        else:
            for pos in range(len(stack) - 1, -1, -1):
                if stack[pos][0] == key:
                    del stack[pos:]
                    break
        if stack:
            level, parent = stack[-1][1] + 1, stack[-1][2]
        else:
            level, parent = 1, None
        stack.append((key, level, idx))
        result.append((level, parent))
    return result


def _letter_follows(prev: str, cur: str) -> bool:
    p, c = prev.lower(), cur.lower()
    return any(
        alpha.find(p) >= 0 and alpha.find(c) == alpha.find(p) + 1
        for alpha in (_ALPHA_VN, _ALPHA_ASCII)
    )


def _sequence_ok(kind: str, numbers: list[Optional[str]]) -> bool:
    """numbered: 1,2,3...; lettered: a,b,c...; dash: không có thứ tự."""
    if kind == DASH:
        return True
    if kind == NUMBERED:
        nums = [int(n) for n in numbers if n is not None]
        return nums[0] == 1 and all(b == a + 1 for a, b in zip(nums, nums[1:]))
    letters = [n for n in numbers if n is not None]
    pairs = zip(letters, letters[1:])
    return letters[0].lower() == "a" and all(_letter_follows(a, b) for a, b in pairs)


def _drop_unreliable(cands, assigned) -> set[int]:
    """Chỉ số các marker yếu thuộc nhóm không đủ tin cậy (<2 mục hoặc sai thứ tự)."""
    groups: dict[tuple[str, Optional[int]], list[int]] = {}
    for idx, ((_, kind, _, _), (_, parent)) in enumerate(zip(cands, assigned)):
        if kind in _WEAK_KINDS:
            groups.setdefault((kind, parent), []).append(idx)
    bad: set[int] = set()
    for (kind, _parent), members in groups.items():
        # Một nhóm có thể gồm nhiều "lượt" cùng cha (vd. a) b) ... rồi cha mới); tách lượt khi
        # số quay về đầu — đơn giản hóa: kiểm toàn nhóm theo thứ tự xuất hiện.
        if len(members) < 2 or not _sequence_ok(kind, [cands[i][2] for i in members]):
            bad.update(members)
    return bad


def parse_structure(
    masked_text: str, boundary_guard: Callable[[int], bool] = lambda pos: True
) -> list[HeadingMark]:
    """Trả danh sách `HeadingMark` đã chấp nhận, sắp theo `start` tăng dần.

    `boundary_guard(pos)` (xem `app.privacy.masker.boundary_guard`) phải trả False nếu `pos` nằm
    chặt bên trong một placeholder PII; marker đó bị bỏ.
    """
    cands = [c for c in _candidates(masked_text) if boundary_guard(c[0])]

    # Lặp tới khi ổn định: bỏ nhóm yếu có thể làm đổi cha của các marker còn lại.
    for _ in range(len(cands) + 1):
        assigned = _assign_levels(cands)
        bad = _drop_unreliable(cands, assigned)
        if not bad:
            break
        cands = [c for i, c in enumerate(cands) if i not in bad]
    else:  # pragma: no cover — mỗi vòng bỏ ≥1 phần tử nên không thể tới đây
        assigned = _assign_levels(cands)

    return [
        HeadingMark(start=s, kind=k, number=n, level=lv, parent_index=p)
        for (s, k, n, _), (lv, p) in zip(cands, assigned)
    ]
