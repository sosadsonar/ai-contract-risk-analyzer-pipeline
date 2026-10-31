"""Local Week 3 PDF validation, without publishing a session result or changing API state.

The caller owns the input file and the returned RAM-only artifacts. Once the
remaining PROCESSING stages exist, the session orchestrator can invoke this
pipeline before advancing a real upload to PROCESSING.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.clause.segmenter import SegmentationResult, segment
from app.core.config import Settings
from app.document.extractor import ExtractionResult, detect_kind, extract
from app.document.scope_precheck import ScopeDecision, precheck
from app.domain.errors import ValidationReject
from app.privacy.masker import mask
from app.privacy.pii_types import MaskResult


@dataclass(frozen=True)
class LocalValidationResult:
    extraction: ExtractionResult
    scope: ScopeDecision
    masking: MaskResult
    segmentation: SegmentationResult


def _validate(path: Path, display_name: str, cfg: Settings) -> LocalValidationResult:
    kind = detect_kind(path, display_name)
    extraction = extract(path, kind, max_pdf_pages=cfg.MAX_PDF_PAGES,
                         max_upload_bytes=cfg.MAX_UPLOAD_MB * 1024 * 1024)
    scope = precheck(extraction.canonical_text, cfg)
    if not scope.accept:
        raise ValidationReject("NOT_LABOR_CONTRACT")
    masking = mask(extraction.canonical_text)
    segmentation = segment(extraction.canonical_text, masking.masked_text,
                           masking.pii_spans, max_clauses=cfg.MAX_CLAUSES)
    return LocalValidationResult(extraction, scope, masking, segmentation)


async def validate_local(path: Path, display_name: str, cfg: Settings) -> LocalValidationResult:
    """Run all implemented VALIDATING stages in a worker, leaving the event loop responsive.

    No artifact is persisted, sent to a provider, or exposed as a final result.
    Input errors propagate as ValidationReject; implementation errors are not
    disguised as contract rejections. This local runner does not own API leases.
    """
    return await asyncio.to_thread(_validate, path, display_name, cfg)
