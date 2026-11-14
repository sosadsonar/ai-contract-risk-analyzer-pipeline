"""Read text PDFs in human order; no PDF coordinates escape this module."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz

from app.domain.errors import ValidationReject


@dataclass(frozen=True)
class _Line:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


def _table_lines(page) -> tuple[list[_Line], list[tuple[float, float, float, float]]]:
    rows: list[_Line] = []
    bounds: list[tuple[float, float, float, float]] = []
    for table in page.find_tables():
        cells = table.extract()
        if len(cells) < 2 or max((len(row) for row in cells), default=0) < 2:
            continue
        x0, y0, x1, y1 = table.bbox
        bounds.append(table.bbox)
        row_height = (y1 - y0) / len(cells)
        for index, cells_in_row in enumerate(cells):
            text = " | ".join(
                value for cell in cells_in_row if cell is not None
                if (value := " ".join(str(cell).split()))
            )
            if text:
                rows.append(_Line(x0, y0 + index * row_height, x1,
                                  y0 + (index + 1) * row_height, text))
    return rows, bounds


def _page_lines(page) -> list[_Line]:
    tables, bounds = _table_lines(page)
    lines = []
    for block in page.get_text("dict", sort=False)["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            if any(x0 >= tx0 - 4 and x1 <= tx1 + 4 and
                   y0 >= ty0 - 4 and y1 <= ty1 + 4 for tx0, ty0, tx1, ty1 in bounds):
                continue  # The flattened table rows replace the original cell text.
            lines.append(_Line(x0, y0, x1, y1, text))
    return lines + tables


def _normalized_line(text: str) -> str:
    return " ".join(text.casefold().split())


def _body_order(lines: list[_Line], width: float) -> list[_Line]:
    midpoint = width / 2
    left = [line for line in lines if line.x1 < midpoint - 8]
    right = [line for line in lines if line.x0 > midpoint + 8]
    if (len(left) < 2 or len(right) < 2 or
            max(line.x1 for line in left) + 16 >= min(line.x0 for line in right)):
        return sorted(lines, key=lambda line: (line.y0, line.x0))
    wide = [line for line in lines if line not in left and line not in right]
    first_y = min(line.y0 for line in left + right)
    last_y = max(line.y1 for line in left + right)
    top = sorted((line for line in wide if line.y0 < first_y), key=lambda line: (line.y0, line.x0))
    bottom = sorted((line for line in wide if line.y0 >= last_y), key=lambda line: (line.y0, line.x0))
    middle = sorted((line for line in wide if first_y <= line.y0 < last_y),
                    key=lambda line: (line.y0, line.x0))
    # Full-width lines in the middle separate sections; do not pull text across them.
    if middle:
        ordered = top[:]
        remaining = left + right
        for separator in middle:
            before = [line for line in remaining if line.y0 < separator.y0]
            ordered.extend(_body_order(before, width) if before else [])
            remaining = [line for line in remaining if line.y0 >= separator.y0]
            ordered.append(separator)
        return ordered + (_body_order(remaining, width) if remaining else []) + bottom
    return top + sorted(left, key=lambda line: (line.y0, line.x0)) + sorted(
        right, key=lambda line: (line.y0, line.x0)
    ) + bottom


def extract_pdf(path: Path | bytes, *, max_pages: int = 30) -> list[str]:
    """Return page texts, including empty pages; enforce page limit before extraction.

    `path` may be the upload bytes held in RAM (X-19: no temp file for session uploads)."""
    try:
        document = (fitz.open(stream=bytes(path), filetype="pdf") if isinstance(path, (bytes, bytearray))
                    else fitz.open(path))
    except (fitz.FileDataError, fitz.EmptyFileError, ValueError, RuntimeError) as exc:
        raise ValidationReject("NO_EXTRACTABLE_TEXT") from exc
    try:
        if document.is_encrypted or document.page_count == 0:
            raise ValidationReject("NO_EXTRACTABLE_TEXT")
        if document.page_count > max_pages:
            raise ValidationReject("PDF_PAGE_LIMIT_EXCEEDED")
        pages = [(page.rect.width, page.rect.height, _page_lines(page)) for page in document]
    finally:
        document.close()

    frequency: Counter[str] = Counter()
    for _, height, lines in pages:
        margin = { _normalized_line(line.text) for line in lines
                  if line.y0 < height * 0.1 or line.y1 > height * 0.9 }
        frequency.update(margin)
    minimum_repeats = math.ceil(len(pages) * 0.6)
    output = []
    for width, height, lines in pages:
        body = []
        for line in lines:
            margin = line.y0 < height * 0.1 or line.y1 > height * 0.9
            key = _normalized_line(line.text)
            if margin and (re.fullmatch(r"(?:trang\s*)?\d+", key) or
                           (len(pages) > 1 and frequency[key] >= minimum_repeats)):
                continue
            body.append(line)
        output.append("\n".join(line.text for line in _body_order(body, width)))
    return output
