"""Extract DOCX body in document order, using the accepted state of OOXML revisions.

SRS OI-11 (decision_SRS_OI-11_v3, phương án A — visual text fidelity): automatic numbering
in the supported formats (decimal, decimalZero, lower/upper letter, lower/upper Roman, bullet)
is materialized as a leading marker; typed markers stay as ordinary text and are never removed
or duplicated. Formats outside that list are left unmaterialized (known limitation) — the
extractor never guesses a marker. It does not export level/parent/numbering kind.
"""

import io
import re
from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn

from app.domain.errors import ValidationReject

_P = qn("w:p")
_TBL = qn("w:tbl")
_TXBX = qn("w:txbxContent")
_OMIT = {qn(tag) for tag in ("w:del", "w:moveFrom", "w:delText", "w:instrText")}
_TEXT = qn("w:t")
_TAB = qn("w:tab")
_BREAKS = {qn("w:br"), qn("w:cr")}
_BLOCK_WRAPPERS = {qn(tag) for tag in ("w:sdt", "w:sdtContent", "w:ins", "w:moveTo")}


def _child(element, tag):
    return element.find(qn(tag)) if element is not None else None


def _value(element, tag, default=None):
    found = _child(element, tag)
    return found.get(qn("w:val"), default) if found is not None else default


def _roman(number):
    parts = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
             (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    output = []
    for value, symbol in parts:
        count, number = divmod(number, value)
        output.append(symbol * count)
    return "".join(output)


def _format(number, fmt):
    if fmt == "decimal":
        return str(number)
    if fmt == "decimalZero":
        return f"{number:02d}"
    if fmt in ("lowerLetter", "upperLetter"):
        value = ""
        while number > 0:
            number, remainder = divmod(number - 1, 26)
            value = chr(65 + remainder) + value
        return value.lower() if fmt == "lowerLetter" else value
    if fmt in ("lowerRoman", "upperRoman") and 0 < number <= 3999:
        value = _roman(number)
        return value.lower() if fmt == "lowerRoman" else value
    return None


class _Numbering:
    def __init__(self, document):
        self.document = document
        try:
            root = document.part.numbering_part.element
        except KeyError:
            self.abstract = {}
            self.nums = {}
        else:
            self.abstract = {item.get(qn("w:abstractNumId")): item for item in root.findall(qn("w:abstractNum"))}
            self.nums = {item.get(qn("w:numId")): item for item in root.findall(qn("w:num"))}
        self.counts = {}

    def prefix(self, paragraph):
        direct = _child(_child(paragraph._p, "w:pPr"), "w:numPr")
        num_id = _value(direct, "w:numId")
        level_text = _value(direct, "w:ilvl")
        style = paragraph.style
        while (num_id is None or level_text is None) and style is not None:
            style_num = _child(_child(style._element, "w:pPr"), "w:numPr")
            if num_id is None:
                num_id = _value(style_num, "w:numId")
            if level_text is None:
                level_text = _value(style_num, "w:ilvl")
            style = style.base_style
        if not num_id or num_id == "0" or num_id not in self.nums:
            return ""
        num = self.nums[num_id]
        abstract = self.abstract.get(_value(num, "w:abstractNumId"))
        if abstract is None:
            return ""
        level_index = int(level_text or "0")
        if not 0 <= level_index <= 8:
            return ""
        levels = {int(level.get(qn("w:ilvl"))): level for level in abstract.findall(qn("w:lvl"))}
        overrides = {int(override.get(qn("w:ilvl"))): override
                     for override in num.findall(qn("w:lvlOverride"))}

        def effective(index):
            """Level definition after w:lvlOverride/w:lvl (OI-11 regression a)."""
            found = _child(overrides.get(index), "w:lvl")
            return found if found is not None else levels.get(index)

        def start_of(index):
            ref = effective(index)
            return int(_value(overrides.get(index), "w:startOverride",
                              _value(ref, "w:start", "1")))

        level = effective(level_index)
        if level is None:
            return ""
        template = _value(level, "w:lvlText", "")
        fmt = _value(level, "w:numFmt")
        if fmt == "bullet":
            return ("•" if template == "\uf0b7" else template) + " " if template else ""
        if _format(1, fmt) is None:
            return ""  # OI-11: leave unsupported numbering unmaterialized.
        counts = self.counts.setdefault(num_id, [None] * 9)
        counts[level_index] = start_of(level_index) if counts[level_index] is None else counts[level_index] + 1
        for lower in range(level_index + 1, 9):
            # w:lvlRestart: 0 = never restart; n = restart only after level n (1-based) or higher
            # is used; absent = restart after any higher level (OI-11 regression b).
            restart = _value(effective(lower), "w:lvlRestart")
            if restart is not None and (int(restart) == 0 or level_index + 1 > int(restart)):
                continue
            counts[lower] = None

        def substitute(match):
            index = int(match.group(1)) - 1
            ref = effective(index)
            if ref is None:
                return match.group(0)
            value = counts[index]
            if value is None:
                value = start_of(index)
            return _format(value, _value(ref, "w:numFmt")) or match.group(0)

        return re.sub(r"%([1-9])", substitute, template) + " "


def _paragraph_text(element, numbering):
    content = []
    anchored_boxes = []

    def visit(node):
        if node.tag in _OMIT:
            return
        if node.tag == _TXBX:
            anchored_boxes.extend(_blocks(node, numbering))
            return
        if node.tag == _TEXT:
            content.append(node.text or "")
        elif node.tag == _TAB:
            content.append("\t")
        elif node.tag in _BREAKS:
            content.append("\n")
        else:
            for child in node:
                visit(child)

    visit(element)
    text = "".join(content).strip()
    if text:
        from docx.text.paragraph import Paragraph
        prefix = numbering.prefix(Paragraph(element, numbering.document))
        marker = prefix.strip()
        # OI-11: an automatic marker already typed at the start of the text is not added twice.
        if marker and not (text.startswith(marker) and text[len(marker):][:1] in ("", " ", "\t")):
            text = prefix + text
    return text, anchored_boxes


def _blocks(container, numbering):
    chunks = []
    for child in container:
        if child.tag in _OMIT:
            continue
        if child.tag == _P:
            text, boxes = _paragraph_text(child, numbering)
            if text:
                chunks.append(text)
            chunks.extend(boxes)
        elif child.tag == _TBL:
            for row in child.findall(qn("w:tr")):
                cells = []
                for cell in row.findall(qn("w:tc")):
                    text = "\n".join(_blocks(cell, numbering))
                    cells.append(text)
                if any(cells):
                    chunks.append(" | ".join(cells))
        elif child.tag in _BLOCK_WRAPPERS:
            chunks.extend(_blocks(child, numbering))
    return chunks


def extract_docx(path: Path | bytes) -> list[str]:
    """Return canonicalizer-ready chunks; exclude header/footer, comments and footnotes."""
    try:
        document = Document(io.BytesIO(bytes(path)) if isinstance(path, (bytes, bytearray)) else path)
    except (PackageNotFoundError, BadZipFile, KeyError, ValueError) as exc:
        raise ValidationReject("UNSUPPORTED_FILE_TYPE") from exc
    numbering = _Numbering(document)
    return _blocks(document.element.body, numbering)
