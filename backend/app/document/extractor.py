"""PDF and DOCX extraction into deterministic, RAM-only canonical text."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.enums import Role
from app.document.canonicalizer import canonicalize
from app.document.docx_extractor import extract_docx
from app.document.pdf_extractor import extract_pdf
from app.document.quality import run_quality_gates
from app.domain.errors import ValidationReject

PDF_EXTRACTION_VERSION = "extract_pdf_v1"
DOCX_EXTRACTION_VERSION = "extract_docx_v1"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class ExtractionResult:
    canonical_text: str
    extraction_version: str
    page_count: int | None
    char_count: int

    def to_artifact(self, filename: str, role: Role) -> dict:
        artifact = {"schema_version": "extraction_v1", "filename": filename,
                    "role": role.value, "extraction_version": self.extraction_version,
                    "canonical_text": self.canonical_text, "char_count": self.char_count}
        if self.page_count is not None:
            artifact["page_count"] = self.page_count
        return artifact


def detect_kind(path: Path, display_name: str) -> Literal["pdf", "docx"]:
    """Require a matching extension and signature, never infer type from either alone."""
    if not path.is_file():
        raise ValidationReject("UNSUPPORTED_FILE_TYPE")
    name = display_name.lower()
    with path.open("rb") as source:
        signature = source.read(5)
    if name.endswith(".pdf") and signature == b"%PDF-":
        return "pdf"
    if name.endswith(".docx") and signature[:4] == b"PK\x03\x04":
        return "docx"
    raise ValidationReject("UNSUPPORTED_FILE_TYPE")


def extract(path: Path, kind: Literal["pdf", "docx"], *, max_pdf_pages: int = 30,
            max_docx_chars: int = 100000,
            max_upload_bytes: int = MAX_UPLOAD_BYTES) -> ExtractionResult:
    """Extract a checked file synchronously; caller runs this in a threadpool."""
    if kind not in ("pdf", "docx"):
        raise ValidationReject("UNSUPPORTED_FILE_TYPE")
    if path.stat().st_size > max_upload_bytes:
        raise ValidationReject("FILE_TOO_LARGE")
    if kind == "pdf":
        pages = extract_pdf(path, max_pages=max_pdf_pages)
        text = canonicalize(pages)
        run_quality_gates(text)
        return ExtractionResult(text, PDF_EXTRACTION_VERSION, len(pages), len(text))
    text = canonicalize(extract_docx(path))
    if len(text) > max_docx_chars:
        raise ValidationReject("DOCX_TEXT_LIMIT_EXCEEDED")
    run_quality_gates(text)
    return ExtractionResult(text, DOCX_EXTRACTION_VERSION, None, len(text))
