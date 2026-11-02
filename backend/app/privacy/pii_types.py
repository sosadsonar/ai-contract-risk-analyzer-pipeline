"""Kiểu dữ liệu PII masking (TDD §10.1): loại PII, span, kết quả che, placeholder.

Tách khỏi detector để masker và detector cùng dùng một nguồn kiểu (C-09 a).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PiiType(str, Enum):
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
    """Vị trí PII trên canonical_text (code point, end exclusive)."""

    type: PiiType
    start: int
    end: int


@dataclass(frozen=True)
class MaskResult:
    """Kết quả che PII. Không lưu bảng ánh xạ ngược."""

    masked_text: str
    pii_spans: list[PiiSpan]


TYPE_TAG: dict[PiiType, str] = {
    PiiType.PERSON_NAME: "<NAME>",
    PiiType.DATE_OF_BIRTH: "<DOB>",
    PiiType.NATIONAL_ID_OR_PASSPORT: "<ID>",
    PiiType.RESIDENTIAL_ADDRESS: "<ADDR>",
    PiiType.PHONE: "<PHONE>",
    PiiType.EMAIL: "<EMAIL>",
    PiiType.BANK_ACCOUNT: "<BANK>",
    PiiType.LEGAL_ENTITY: "<ORG>",
}

TYPE_SHORT_CODE: dict[PiiType, str] = {
    PiiType.PERSON_NAME: "N",
    PiiType.DATE_OF_BIRTH: "D",
    PiiType.NATIONAL_ID_OR_PASSPORT: "I",
    PiiType.RESIDENTIAL_ADDRESS: "R",
    PiiType.PHONE: "P",
    PiiType.EMAIL: "E",
    PiiType.BANK_ACCOUNT: "B",
    PiiType.LEGAL_ENTITY: "O",
}
