"""Nhận diện heading/list marker cấu trúc trong masked_text (TDD §11.2, C-02).

Thay `document_router` + `CLAUSE_PATTERN` cũ (`utils/text_processing.py`): không còn "router"
chọn Pipeline A/B theo tỉ lệ heading. Luôn chạy parser; không có heading đáng tin cậy thì
`segmenter` rơi về fallback paragraph (§11.3).

6 pattern (mỗi pattern neo ở đầu dòng):
  1. article   `Điều 5. Tiêu đề`
  2. decimal   `5.1 ...`, `5.1.2 ...` (sâu tối đa 4 cấp)
  3. numbered  `1. ...` / `1) ...`
  4. roman     `I. ...`, `ii) ...` (SRS OI-11: numeral La Mã hợp lệ, không phân biệt hoa/thường)
  5. lettered  `a) ...` / `a. ...`
  6. dash      `- ...`, `– ...`, `— ...`, `• ...`
  7. plus      `+ ...` — cấp CON riêng (thường nằm dưới `- ...`), CHỈ khi bật `allow_plus`
               (rules_v1.2+, D1/D2 Dev 09/11). Sửa OI-11 §2: `+` không gộp chung nhóm với `-`.

Roman vs lettered: numeral nhiều ký tự (`II`, `iv`) luôn là roman. Một ký tự trùng chữ cái
(`I`, `V`, `X`, `L`, `C`, `D`, `M` và dạng thường) mặc định là lettered như trước; chỉ thành roman
khi nối chuỗi La Mã (mục roman ngay trước có giá trị liền kề, hoặc là `I`/`i` mà phía sau có
`II`/`ii` cùng kiểu chữ) và không phải chữ cái kế tiếp của danh sách lettered ngay trước
(`h) i)`). Vì vậy `a) b) c)` vẫn là lettered, `I. II. III.` là roman.

Hàm thuần: không đụng I/O, không import api/session. Offset = Unicode code point trên
masked_text (cùng độ dài canonical_text, INV-01).

Quy tắc độ tin cậy (TDD §11.2: "chỉ thành clause riêng khi rule list đủ tin cậy"):
  - article, decimal: luôn tin cậy (trừ dạng số có dấu phân cách hàng nghìn: `2.000.000 đồng`).
  - numbered, lettered, roman, dash, plus: chỉ giữ khi nhóm anh em cùng cha có >= 2 mục; riêng
    numbered / lettered / roman còn phải đánh số liên tiếp (1,2,3 / a,b,c / I,II,III) và bắt đầu
    từ mục đầu (1 / a / I). Quy tắc này KHÔNG nới lỏng khi thêm roman và plus (OI-11 §4): nhóm đứt
    chuỗi hoặc thiếu marker bị bỏ — đây là giới hạn đã biết, không phải cấu trúc đã khôi phục.
    Mục lẻ loi nằm lại trong clause hiện tại, không tạo ranh giới.
  - Heading có `start` rơi vào trong placeholder PII (`boundary_guard` = False) bị BỎ (TDD §10.3,
    chọn "bỏ match" thay vì dời để không tạo clause rỗng).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

# v2 = v1.1 (Data Lead: `DIEU` ASCII, gạch dài —, `+` opt-in) + roman (SRS OI-11). `+` là kind PLUS riêng.
STRUCTURE_PARSER_VERSION = "structure_parser_v2"

# ---- 5 pattern (TDD §11.2). Chạy theo từng dòng; group "body" là phần sau marker. ----
_ARTICLE = re.compile(r"^[ \t]*(?:Điều|DIEU)[ \t]+(?P<num>\d+[A-Za-z]?)[ \t]*[.:\-]?[ \t]*(?P<body>.*)$", re.I)
_DECIMAL = re.compile(r"^[ \t]*(?P<num>\d+(?:\.\d+){1,3})[ \t]*[.)\-]?[ \t]+(?P<body>\S.*)$")
_NUMBERED = re.compile(r"^[ \t]*(?P<num>\d{1,3})[.)][ \t]+(?P<body>\S.*)$")
_ROMAN = re.compile(r"^[ \t]*(?P<num>[IVXLCDM]{1,15}|[ivxlcdm]{1,15})[.)][ \t]+(?P<body>\S.*)$")
_LETTERED = re.compile(r"^[ \t]*(?P<num>[a-zA-ZđĐ])[.)][ \t]+(?P<body>\S.*)$")
_DASH = re.compile(r"^[ \t]*[-–—•][ \t]+(?P<body>\S.*)$")
_PLUS = re.compile(r"^[ \t]*\+[ \t]+(?P<body>\S.*)$")
_ROMAN_VALID = re.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

ARTICLE, DECIMAL, NUMBERED, LETTERED, DASH, PLUS = "article", "decimal", "numbered", "lettered", "dash", "plus"
ROMAN = "roman"
_WEAK_KINDS = (NUMBERED, LETTERED, ROMAN, DASH, PLUS)
_AMBIGUOUS = "roman_or_letter"  # nội bộ: một ký tự vừa là chữ cái vừa là numeral La Mã

# Chữ cái liệt kê tiếng Việt (có đ giữa d và e) và dạng ASCII — chấp nhận cả hai cách đánh.
_ALPHA_VN = "abcdđeghiklmnopqrstuvxy"
_ALPHA_ASCII = "abcdefghijklmnopqrstuvwxyz"


@dataclass(frozen=True)
class HeadingMark:
    """Một marker cấu trúc được chấp nhận. `start` = vị trí ký tự đầu tiên (không phải khoảng
    trắng) của dòng chứa marker, tính trên masked_text."""

    start: int
    kind: str  # ARTICLE | DECIMAL | NUMBERED | ROMAN | LETTERED | DASH
    number: Optional[str]  # "5", "5.1", "1", "IV", "a"; None với dash
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


def roman_value(num: str) -> Optional[int]:
    """Giá trị của numeral La Mã hợp lệ (hoa hoặc thường, không trộn); None nếu không hợp lệ."""
    if not num or not (num.isupper() or num.islower()):
        return None
    upper = num.upper()
    if not _ROMAN_VALID.match(upper):
        return None
    total = 0
    for i, ch in enumerate(upper):
        value = _ROMAN_VALUES[ch]
        nxt = _ROMAN_VALUES[upper[i + 1]] if i + 1 < len(upper) else 0
        total += -value if value < nxt else value
    return total


def _resolve_ambiguous(out: list[tuple[int, str, Optional[str], int]]) -> None:
    """Quyết định roman/lettered cho marker một ký tự (xem docstring module)."""
    for idx, (start, kind, num, depth) in enumerate(out):
        if kind != _AMBIGUOUS:
            continue
        value = roman_value(num)
        prev = next((c for c in reversed(out[:idx]) if c[1] in (ROMAN, LETTERED)), None)
        is_roman = False
        if prev is not None and prev[1] == LETTERED and _letter_follows(prev[2], num):
            is_roman = False  # `h) i)`: chữ cái tiếp theo của danh sách lettered
        elif prev is not None and prev[1] == ROMAN and prev[2].isupper() == num.isupper():
            is_roman = value == roman_value(prev[2]) + 1
        elif value == 1:
            is_roman = any(c[1] == ROMAN and roman_value(c[2]) == 2 and c[2].isupper() == num.isupper()
                           for c in out[idx + 1:])
        out[idx] = (start, ROMAN if is_roman else LETTERED, num, depth)


def _candidates(text: str, allow_plus: bool = False) -> list[tuple[int, str, Optional[str], int]]:
    """Mọi dòng khớp 1 trong 7 pattern: (start, kind, number, decimal_depth); `+` chỉ khi allow_plus."""
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
        m = _ROMAN.match(line)
        if m and roman_value(m.group("num")) is not None:
            num = m.group("num")
            out.append((start, ROMAN if len(num) > 1 else _AMBIGUOUS, num, 0))
            continue
        m = _LETTERED.match(line)
        if m:
            out.append((start, LETTERED, m.group("num"), 0))
            continue
        if _DASH.match(line):
            out.append((start, DASH, None, 0))
            continue
        if allow_plus and _PLUS.match(line):
            out.append((start, PLUS, None, 0))
    _resolve_ambiguous(out)
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
    """numbered: 1,2,3...; roman: I,II,III...; lettered: a,b,c...; dash/plus: không có thứ tự."""
    if kind in (DASH, PLUS):
        return True
    if kind == ROMAN:
        values = [roman_value(n) for n in numbers if n is not None]
        return values[0] == 1 and all(b == a + 1 for a, b in zip(values, values[1:]))
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
    masked_text: str, boundary_guard: Callable[[int], bool] = lambda pos: True, *,
    allow_plus: bool = False, allowed_plus_positions: set[int] | None = None,
) -> list[HeadingMark]:
    """Trả danh sách `HeadingMark` đã chấp nhận, sắp theo `start` tăng dần.

    `boundary_guard(pos)` (xem `app.privacy.masker.boundary_guard`) phải trả False nếu `pos` nằm
    chặt bên trong một placeholder PII; marker đó bị bỏ.
    `allow_plus` bật pattern `+` (segmenter bật qua `enable_plus_lists`, rules_v1.2+);
    `allowed_plus_positions` giới hạn các vị trí `+` được nhận (cổng khối cha ≥ 160 ký tự).
    """
    cands = [c for c in _candidates(masked_text, allow_plus=allow_plus)
             if boundary_guard(c[0]) and (c[1] != PLUS or allowed_plus_positions is None
                                           or c[0] in allowed_plus_positions)]

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
