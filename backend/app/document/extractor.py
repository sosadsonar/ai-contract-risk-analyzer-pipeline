"""PDF-only Week 3 extraction; DOCX is scheduled for C-08(b)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.enums import Role
from app.document.canonicalizer import canonicalize
from app.document.pdf_extractor import extract_pdf
from app.document.quality import run_quality_gates
from app.domain.errors import ValidationReject

EXTRACTION_VERSION = "extract_pdf_v1"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class ExtractionResult:
    canonical_text: str
    extraction_version: str
    page_count: int
    char_count: int

    def to_artifact(self, filename: str, role: Role) -> dict:
        """Assemble the RAM-only extraction_v1 artifact when the orchestrator needs it."""
        return {"schema_version": "extraction_v1", "filename": filename,
                "role": role.value, "extraction_version": self.extraction_version,
                "canonical_text": self.canonical_text, "page_count": self.page_count,
                "char_count": self.char_count}


def detect_kind(path: Path, display_name: str) -> Literal["pdf"]:
    """Never infer PDF format from extension alone."""
    if not display_name.lower().endswith(".pdf") or not path.is_file():
        raise ValidationReject("UNSUPPORTED_FILE_TYPE")
    with path.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise ValidationReject("UNSUPPORTED_FILE_TYPE")
    return "pdf"


def extract(path: Path, kind: Literal["pdf"], *, max_pdf_pages: int = 30,
            max_upload_bytes: int = MAX_UPLOAD_BYTES) -> ExtractionResult:
    """Extract a checked PDF synchronously; caller runs this in a threadpool."""
    if kind != "pdf":
        raise ValidationReject("UNSUPPORTED_FILE_TYPE")
    if path.stat().st_size > max_upload_bytes:
        raise ValidationReject("FILE_TOO_LARGE")
    pages = extract_pdf(path, max_pages=max_pdf_pages)
    text = canonicalize(pages)
    run_quality_gates(text)
    return ExtractionResult(text, EXTRACTION_VERSION, len(pages), len(text))
