"""Deterministic, format-independent canonical text (TDD §8.4)."""

import re
import unicodedata


def canonicalize(chunks: list[str]) -> str:
    """Keep structural newlines; normalize before downstream code-point offsets exist."""
    normalized = []
    for chunk in chunks:
        text = unicodedata.normalize("NFC", chunk)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\N{NO-BREAK SPACE}", " ").replace("\t", " ")
        normalized.append("\n".join(line.rstrip(" ") for line in text.split("\n")).strip("\n"))
    joined = "\n".join(normalized)
    joined = re.sub(r"\n{4,}", "\n\n\n", joined).strip("\n")
    return unicodedata.normalize("NFC", joined)
