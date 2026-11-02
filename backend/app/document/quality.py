"""Typed extraction-quality rejection; thresholds frozen for extract_pdf_v1."""

import re
import unicodedata

from app.domain.errors import ValidationReject

LEGACY_GLYPHS = frozenset("®¸µ¶¬¨©ª«­®¯°±²³´µ¶·¸¹º»¼½¾¿")
_VIETNAMESE_WORDS = frozenset({
    "hợp", "đồng", "lao", "động", "người", "điều", "bên", "thời",
    "lương", "công", "việc", "theo", "và", "của", "được", "trách", "nhiệm",
})
_MOJIBAKE = re.compile(r"(?:Ã[\x80-\xff]|Â[\x80-\xff]|Æ[\x80-\xff]|Ð[\x80-\xff])")


def run_quality_gates(text: str, *, min_useful_chars: int = 100) -> None:
    """Reject unusable content; legacy patterns require a second plausibility check."""
    useful = sum(not char.isspace() for char in text)
    if useful < min_useful_chars:
        raise ValidationReject("NO_EXTRACTABLE_TEXT")

    n = len(text)
    replacements = text.count("\ufffd")
    controls = sum(unicodedata.category(char) == "Cc" and char not in "\n\t" for char in text)
    printable = sum(char.isprintable() or char in "\n\t" for char in text)
    if (replacements > max(5, 0.002 * n)
            or controls > 0.001 * n
            or printable < 0.95 * n):
        raise ValidationReject("UNSUPPORTED_TEXT_ENCODING")

    suspicious = sum(char in LEGACY_GLYPHS for char in text)
    mojibake = len(_MOJIBAKE.findall(text))
    if n >= 200 and (suspicious > 0.01 * n or mojibake >= 3):
        words = re.findall(r"[^\W\d_]+", text.casefold(), re.UNICODE)
        common = sum(word in _VIETNAMESE_WORDS for word in words)
        if common < max(3, len(words) // 8):
            raise ValidationReject("UNSUPPORTED_TEXT_ENCODING")
