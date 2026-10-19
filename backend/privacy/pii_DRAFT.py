"""
Module che dữ liệu nhạy cảm (Privacy & PII Masking)
Tuân thủ:
- domain/models.py: PiiSpan [TDD §6.2-6.4]
- privacy/pii_types.py: PiiType, TYPE_TAG, TYPE_SHORT_CODE [TDD §10.1]
- privacy/detector.py: detect() [TDD §10.2]
- privacy/masker.py: mask_value(), mask() [TDD §10.1, §10.2]
- clause/segmenter.py: boundary_guard() [TDD §10.3]
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Set


# ==============================================================================
# 1. DOMAIN MODELS & PII TYPES (domain/models.py & privacy/pii_types.py)
# ==============================================================================

class PiiType(str, Enum):
    """Các loại thông tin định danh cá nhân theo TDD §10.1."""
    PERSON_NAME = "PERSON_NAME"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    NATIONAL_ID_OR_PASSPORT = "NATIONAL_ID_OR_PASSPORT"
    RESIDENTIAL_ADDRESS = "RESIDENTIAL_ADDRESS"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    LEGAL_ENTITY = "LEGAL_ENTITY"


@dataclass(frozen=True)
class PiiSpan:
    """Span vị trí PII trên văn bản chuẩn hóa (domain/models.py)."""
    type: PiiType
    start: int
    end: int


@dataclass(frozen=True)
class MaskResult:
    """Kết quả che giấu PII (privacy/masker.py). Không lưu bảng ánh xạ ngược."""
    masked_text: str
    pii_spans: List[PiiSpan]


# Tag ưu tiên (ASCII tag) và Short code theo TDD §10.1
TYPE_TAG: Dict[PiiType, str] = {
    PiiType.PERSON_NAME: "<NAME>",
    PiiType.DATE_OF_BIRTH: "<DOB>",
    PiiType.NATIONAL_ID_OR_PASSPORT: "<ID>",
    PiiType.RESIDENTIAL_ADDRESS: "<ADDR>",
    PiiType.PHONE: "<PHONE>",
    PiiType.EMAIL: "<EMAIL>",
    PiiType.BANK_ACCOUNT: "<BANK>",
    PiiType.LEGAL_ENTITY: "<ORG>",
}

TYPE_SHORT_CODE: Dict[PiiType, str] = {
    PiiType.PERSON_NAME: "N",
    PiiType.DATE_OF_BIRTH: "D",
    PiiType.NATIONAL_ID_OR_PASSPORT: "I",
    PiiType.RESIDENTIAL_ADDRESS: "R",
    PiiType.PHONE: "P",
    PiiType.EMAIL: "E",
    PiiType.BANK_ACCOUNT: "B",
    PiiType.LEGAL_ENTITY: "O",
}


# ==============================================================================
# 2. REGEX PATTERNS, ANCHORS & PRESERVE-LIST (privacy/detector.py)
# ==============================================================================

# 2.1 Nhóm Regex High-precision (Độ chính xác cao - quét trước)
REGEX_HIGH_PRECISION: Dict[PiiType, re.Pattern] = {
    # Email
    PiiType.EMAIL: re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),

    # Số điện thoại (10 chữ số VN hoặc có mã quốc gia +84)
    PiiType.PHONE: re.compile(
        r"(?:\+84|84|0)[35789](?:[.\s-]?\d{2}){4}\b"
    ),

    # CCCD (12 chữ số) hoặc Hộ chiếu (1 chữ cái + 7-8 số)
    PiiType.NATIONAL_ID_OR_PASSPORT: re.compile(
        r"\b(?:0(?:0[1-9]|[1-8]\d|9[0-6])[0-3]\d{8}|[A-Z]\d{7,8})\b"
    ),

    # Số tài khoản ngân hàng (Anchor: STK, Số tài khoản...) -> Group 1: anchor, Group 2: STK
    PiiType.BANK_ACCOUNT: re.compile(
        r"(?i)(\b(?:stk|số\s+tài\s+khoản|số\s+tk|tài\s+khoản\s+ngân\s+hàng)\s*[:：\s]\s*)([0-9]{8,16})\b"
    ),

    # Ngày sinh: Bắt buộc anchor (ngày sinh/sinh ngày/DOB) -> Group 1: anchor, Group 2: DOB
    PiiType.DATE_OF_BIRTH: re.compile(
        r"(?i)(\b(?:ngày\s+sinh|sinh\s+ngày|d\.?o\.?b)\s*[:：\s]\s*)((?:0[1-9]|[12]\d|3[01])[/\-.](?:0[1-9]|1[0-2])[/\-.](?:19\d{2}|20\d{2}))\b"
    ),

    # Địa chỉ cư trú: Bắt buộc anchor -> Group 1: anchor, Group 2: Address
    PiiType.RESIDENTIAL_ADDRESS: re.compile(
        r"(?i)(\b(?:địa\s+chỉ(?:\s+thường\s+trú|\s+cư\s+trú|\s+hiện\s+tại|\s+liên\s+lạc)?|nơi\s+(?:thường\s+trú|cư\s+trú|ở))\s*[:：\s]\s*)([^\r\n]+)"
    ),
}

# 2.2 Nhóm Heuristic Entity (Quét sau - chỉ mask span value, không mask vai trò)
HEURISTIC_ANCHORS: Dict[PiiType, re.Pattern] = {
    # Họ tên cá nhân: Anchor "Họ [và ]tên:", "Ông/Bà", "Người lao động:", "Đại diện:"
    PiiType.PERSON_NAME: re.compile(
        r"(?i)(\b(?:họ\s+(?:và\s+)?tên|ông/bà|ông|bà|người\s+lao\s+động|đại\s+diện)\s*[:：\s]\s*)([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,6})"
    ),

    # Tên pháp nhân: Anchor "Công ty", "Tập đoàn", "MST"
    PiiType.LEGAL_ENTITY: re.compile(
        r"(?i)(\b(?:công\s+ty|tập\s+đoàn|tổng\s+công\s+ty|doanh\s+nghiệp)\s+(?:cổ\s+phần|tnhh|mtv|đầu\s+tư|thương\s+mại)?\s*)([A-Z0-9À-Ỹ][^\r\n,.;:]{2,50})"
    ),
}

# 2.3 Preserve-list theo TDD §10.2: Tuyệt đối không mask nhầm
PRESERVE_LIST: Set[str] = {
    "người lao động", "nld", "nlđ",
    "người sử dụng lao động", "nsdld", "nsdlđ",
    "giám đốc", "tổng giám đốc", "trưởng phòng", "kế toán trưởng", "nhân viên",
    "lương", "phụ cấp", "bảo hiểm", "giờ làm"
}

ADMIN_KEYWORDS_PATTERN = re.compile(
    r"(?i)\b(?:xã|phường|thị\s+trấn|quận|huyện|thị\s+xã|tỉnh|thành\s+phố|tp\.?)\b"
)


# ==============================================================================
# 3. DETECTOR PIPELINE (privacy/detector.py)
# ==============================================================================

def _is_preserved(val: str) -> bool:
    """Kiểm tra giá trị có thuộc preserve-list hay không."""
    return val.strip().lower() in PRESERVE_LIST


def _resolve_overlaps(spans: List[Tuple[PiiSpan, bool]]) -> List[PiiSpan]:
    """
    Resolve overlap theo TDD §10.2:
    - Ưu tiên 1: High-precision regex > Heuristic entity.
    - Ưu tiên 2: Chiều dài span lớn hơn (dài hơn ưu tiên trước).
    - Triệt tiêu hoàn toàn overlap.
    - Trả về list[PiiSpan] được sort theo start tăng dần.
    """
    # Key sắp xếp: (is_high_precision: True trước, length: lớn trước, start: nhỏ trước)
    sorted_candidates = sorted(
        spans,
        key=lambda item: (item[1], item[0].end - item[0].start, -item[0].start),
        reverse=True
    )

    accepted: List[PiiSpan] = []
    for span, _ in sorted_candidates:
        overlap = any(
            max(span.start, a.start) < min(span.end, a.end)
            for a in accepted
        )
        if not overlap:
            accepted.append(span)

    accepted.sort(key=lambda s: s.start)
    return accepted


def detect(canonical_text: str) -> List[PiiSpan]:
    """
    Phát hiện các span PII trên văn bản canonical_text (privacy/detector.py).
    Thực hiện theo thứ tự TDD §10.2:
    1. Regex high-precision
    2. Heuristic entity với anchor (chỉ lấy value)
    3. Kiểm tra preserve-list
    4. Resolve overlap
    """
    norm_text = unicodedata.normalize("NFC", canonical_text)
    raw_spans: List[Tuple[PiiSpan, bool]] = []

    # Bước 1: High-precision regex
    for pii_type, pattern in REGEX_HIGH_PRECISION.items():
        for m in pattern.finditer(norm_text):
            if pii_type in (PiiType.BANK_ACCOUNT, PiiType.DATE_OF_BIRTH, PiiType.RESIDENTIAL_ADDRESS):
                # Anchor ở Group 1, Value ở Group 2 -> chỉ mask Group 2
                val = m.group(2).strip()
                if not val or _is_preserved(val):
                    continue
                if pii_type == PiiType.RESIDENTIAL_ADDRESS and not ADMIN_KEYWORDS_PATTERN.search(val):
                    continue
                start_idx = m.start(2)
                end_idx = start_idx + len(val)
                raw_spans.append((PiiSpan(type=pii_type, start=start_idx, end=end_idx), True))
            else:
                val = m.group(0).strip()
                if not val or _is_preserved(val):
                    continue
                raw_spans.append((PiiSpan(type=pii_type, start=m.start(0), end=m.end(0)), True))

    # Bước 2: Heuristic entity (Anchor ở Group 1, Value ở Group 2)
    for pii_type, pattern in HEURISTIC_ANCHORS.items():
        for m in pattern.finditer(norm_text):
            val = m.group(2).strip()
            if not val or _is_preserved(val):
                continue
            start_idx = m.start(2)
            end_idx = start_idx + len(val)
            raw_spans.append((PiiSpan(type=pii_type, start=start_idx, end=end_idx), False))

    # Bước 3 & 4: Resolve overlaps
    return _resolve_overlaps(raw_spans)


# ==============================================================================
# 4. MASKER & BOUNDARY GUARD (privacy/masker.py & clause/segmenter.py)
# ==============================================================================

def mask_value(text: str, pii_type: PiiType) -> str:
    """
    Tạo placeholder thay thế giá trị PII (TDD §10.1).
    Bảo toàn 100% số lượng Unicode code points sau NFC:
    assert len(mask_value(text, pii_type)) == len(text)
    """
    norm_text = unicodedata.normalize("NFC", text)
    n = len(norm_text)
    tag = TYPE_TAG[pii_type]
    if n >= len(tag):
        return tag + "_" * (n - len(tag))
    return TYPE_SHORT_CODE[pii_type] * n


def mask(canonical_text: str) -> MaskResult:
    """
    Che giấu toàn bộ canonical_text TRƯỚC segmentation (privacy/masker.py).
    Không lưu bảng ánh xạ ngược để đảm bảo an toàn riêng tư.
    """
    norm_text = unicodedata.normalize("NFC", canonical_text)
    spans = detect(norm_text)

    # Thay thế ngược từ cuối về đầu chuỗi để giữ nguyên index start:end
    chars = list(norm_text)
    for span in reversed(spans):
        val = norm_text[span.start:span.end]
        replacement = mask_value(val, span.type)
        assert len(replacement) == (span.end - span.start), (
            f"Lỗi: placeholder '{replacement}' khác độ dài với '{val}'"
        )
        chars[span.start:span.end] = list(replacement)

    masked_text = "".join(chars)
    assert len(masked_text) == len(norm_text), "Bất biến vi phạm: độ dài chuỗi bị thay đổi sau mask!"
    return MaskResult(masked_text=masked_text, pii_spans=spans)


def boundary_guard(pos: int, pii_spans: List[PiiSpan]) -> bool:
    """
    Quy tắc an toàn biên (clause/segmenter.py [TDD §10.3]):
    Trả về False nếu start < pos < end của bất kỳ span nào.
    """
    return not any(span.start < pos < span.end for span in pii_spans)


def adjust_boundary(pos: int, pii_spans: List[PiiSpan]) -> int:
    """Dời biên pos ra đầu/cuối span gần nhất nếu rơi vào bên trong placeholder."""
    for span in pii_spans:
        if span.start < pos < span.end:
            dist_to_start = pos - span.start
            dist_to_end = span.end - pos
            return span.start if dist_to_start <= dist_to_end else span.end
    return pos