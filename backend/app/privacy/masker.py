"""Che PII trên toàn bộ canonical_text và tiện ích biên (TDD §10.1, §10.3). Bản đầu của C-09 (a).

Quy tắc: chạy trên TOÀN BỘ canonical_text trước segmentation; placeholder cùng độ dài theo code
point; không có bảng ánh xạ placeholder về giá trị gốc; không NER hoặc LLM; từ chỉ vai trò
(NLĐ, NSDLĐ, "Công ty" dùng như đại từ) không bị mask, chỉ mask phần giá trị sau anchor.

boundary_guard và adjust_boundary đặt ở đây tạm thời; SKELETON §5.6 đặt chúng ở
clause/segmenter.py, chuyển khi làm C-01 (b).
"""

from __future__ import annotations

from app.privacy.detector import detect
from app.privacy.pii_types import TYPE_SHORT_CODE, TYPE_TAG, MaskResult, PiiSpan, PiiType

PII_MASKING_VERSION = "pii_draft_0.2"


# ==============================================================================
# 4. MASKER VÀ BOUNDARY GUARD
# ==============================================================================


def mask_value(text: str, pii_type: PiiType) -> str:
    """Placeholder cùng độ dài với `text` (TDD §10.1): tag + '_', hoặc mã 1 chữ nếu quá ngắn."""
    n = len(text)
    tag = TYPE_TAG[pii_type]
    if n >= len(tag):
        return tag + "_" * (n - len(tag))
    return TYPE_SHORT_CODE[pii_type] * n


def mask(canonical_text: str) -> MaskResult:
    """Che PII trên toàn bộ canonical_text. len(masked_text) == len(canonical_text) (INV-01)."""
    spans = detect(canonical_text)
    pieces: list[str] = []
    cursor = 0
    for span in spans:
        pieces.append(canonical_text[cursor : span.start])
        pieces.append(mask_value(canonical_text[span.start : span.end], span.type))
        cursor = span.end
    pieces.append(canonical_text[cursor:])
    masked = "".join(pieces)
    if len(masked) != len(canonical_text):  # không dùng assert: -O sẽ bỏ qua
        raise RuntimeError("Vi phạm INV-01: độ dài masked_text khác canonical_text")
    return MaskResult(masked_text=masked, pii_spans=spans)


def boundary_guard(pos: int, pii_spans: list[PiiSpan]) -> bool:
    """TDD §10.3: False nếu start < pos < end của span nào đó (biên rơi vào trong placeholder)."""
    return not any(span.start < pos < span.end for span in pii_spans)


def adjust_boundary(pos: int, pii_spans: list[PiiSpan]) -> int:
    """Dời biên ra đầu/cuối span nếu rơi vào trong placeholder (hòa thì về đầu)."""
    for span in pii_spans:
        if span.start < pos < span.end:
            return span.start if pos - span.start <= span.end - pos else span.end
    return pos
