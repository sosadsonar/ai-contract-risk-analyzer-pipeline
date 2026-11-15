"""`analyze()` — chuỗi stage end-to-end dùng chung cho orchestrator (HTTP) và harness đánh giá (X-19).

Thứ tự (SRS 2.2 / TDD §7):
  VALIDATING : EXTRACTION → SCOPE_PRECHECK → PII_MASKING → SEGMENTATION → CLAUSE_GRAPH   (cục bộ)
  PROCESSING : CLAUSE_CLASSIFICATION (LLM #1) → LEGAL_RETRIEVAL → RISK_ANALYSIS (LLM #2)
               → CITATION_VALIDATION → ASSEMBLY  →  `final_result_v1`

Móc:
  * `on_stage(stage)` gọi TRƯỚC khi chạy mỗi stage (orchestrator dùng để đổi status/stage; harness đo thời gian).
  * `check_cancel()` trả True ⇒ `StageCancelled` giữa các stage và giữa các lô LLM (End/cleanup).
  * `stop_after=Stage.X` ⇒ dừng sau stage X, trả artifact tới đó (harness đo M1/M7 không cần LLM #2).
  * `resume=ResumeState` ⇒ chạy lại từ CLAUSE_CLASSIFICATION với artifact cục bộ đã có (retry giai đoạn AI,
    chỉ khi version pin trùng; khác ⇒ chạy lại từ đầu — xem `ResumeState.matches`).

Bất biến giữ ở đây: chỉ masked text ra provider (INV-04); offset/quote chỉ từ canonical clause (INV-02/03);
severity do bảng taxonomy (INV-06); artifact chỉ nằm trong RAM của lời gọi, không ghi đĩa, không log nội dung.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Callable, Optional

from app.ai.clause_adapter import ClauseOutput, classify_clauses, masked_items_from_segmentation
from app.ai.provider import CallLedger, LLMProvider
from app.ai.risk_adapter import LegalCandidate, RelatedClause, RiskItemIn, RiskOutput, analyze_risks
from app.clause.context_resolver import build_masked_clause_map, resolve_risk_context
from app.clause.graph_builder import ClauseGraph, build_clause_graph
from app.clause.segmenter import SegmentationResult, segment
from app.clause.taxonomy import DATA_TAXONOMY_VERSION
from app.core.enums import Role, Stage
from app.document.extractor import ExtractionResult, detect_kind_bytes, extract_bytes
from app.document.scope_precheck import precheck
from app.domain.errors import StageCancelled, ValidationReject
from app.integrations.risk_assembler import AssemblerContext, assemble_risk_output
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import LegalCorpus
from app.legal.data_graph import DataGraph, get_candidates
from app.privacy.masker import mask
from app.privacy.pii_types import MaskResult
from app.result.notices import DATA_NOTICE, DISCLAIMER
from app.risk.citation_validator import CitationStats, effective_provisions, validate_citations
from app.risk.lint import lint_explanation, sanitize_explanation
from app.risk.taxonomy import RISK_TAXONOMY_VERSION, SEVERITY_RUBRIC_VERSION

PIPELINE_VERSION = "pipeline_v1"
INELIGIBLE_LABEL = "OTHER"
INSUFFICIENT_FALLBACK = "Chưa đủ căn cứ pháp lý trong kho luật đóng để kết luận chắc chắn về điều khoản này."
LOCAL_STAGES = (Stage.EXTRACTION, Stage.SCOPE_PRECHECK, Stage.PII_MASKING, Stage.SEGMENTATION, Stage.CLAUSE_GRAPH)
AI_STAGES = (Stage.CLAUSE_CLASSIFICATION, Stage.LEGAL_RETRIEVAL, Stage.RISK_ANALYSIS,
             Stage.CITATION_VALIDATION, Stage.ASSEMBLY)


@dataclass
class PipelineDeps:
    cfg: Any
    provider: LLMProvider
    ledger: CallLedger
    corpus: Optional[LegalCorpus] = None
    retriever: Optional[BaselineRetriever] = None
    data_graph: Optional[DataGraph] = None
    app_commit: str = "unknown"


@dataclass
class PipelineArtifacts:
    """Artifact từng stage (RAM). `traces`/`diagnostics` chỉ dev/eval, không vào kết quả sản phẩm."""

    extraction: Optional[ExtractionResult] = None
    masking: Optional[MaskResult] = None
    segmentation: Optional[SegmentationResult] = None
    clause_graph: Optional[ClauseGraph] = None
    graph_diagnostics: list = field(default_factory=list)
    clause_output: Optional[ClauseOutput] = None
    candidates: dict[str, list[str]] = field(default_factory=dict)
    graph_fallbacks: int = 0
    risk_output: Optional[RiskOutput] = None
    citation_stats: Optional[CitationStats] = None
    traces: list[dict] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)
    final_result: Optional[dict] = None
    completed: list[Stage] = field(default_factory=list)


@dataclass(frozen=True)
class ResumeState:
    """Artifact cục bộ giữ lại cho retry giai đoạn AI (TDD §5.5; cut item 2 nếu trễ)."""

    artifacts: PipelineArtifacts
    pins: tuple

    def matches(self, deps: PipelineDeps) -> bool:
        return self.pins == _resume_pins(deps)


def _resume_pins(deps: PipelineDeps) -> tuple:
    cfg = deps.cfg
    return (getattr(cfg, "GEMINI_MODEL_ID", None), getattr(cfg, "CLAUSE_GRAPH_ENABLED", True),
            deps.corpus.corpus_version if deps.corpus else None, DATA_TAXONOMY_VERSION, RISK_TAXONOMY_VERSION)


def _cancel_point(check_cancel: Optional[Callable[[], bool]]) -> None:
    if check_cancel is not None and check_cancel():
        raise StageCancelled()


async def analyze(
    data: bytes,
    display_name: str,
    role: Role | str,
    *,
    session_id: str,
    analysis_date: date,
    deps: PipelineDeps,
    on_stage: Optional[Callable[[Stage], None]] = None,
    check_cancel: Optional[Callable[[], bool]] = None,
    stop_after: Optional[Stage] = None,
    resume: Optional[ResumeState] = None,
    into: Optional[PipelineArtifacts] = None,
) -> PipelineArtifacts:
    """`into`: đối tượng artifact do caller giữ, để khi stage AI lỗi vẫn lấy được artifact cục bộ (resume)."""
    role = Role(role)
    cfg = deps.cfg

    def enter(stage: Stage) -> None:
        _cancel_point(check_cancel)
        if on_stage is not None:
            on_stage(stage)

    def done(stage: Stage, art: PipelineArtifacts) -> bool:
        art.completed.append(stage)
        return stop_after == stage

    if resume is not None and resume.matches(deps):
        art = resume.artifacts
        art.completed = [s for s in art.completed if s in LOCAL_STAGES]
    else:
        art = into if into is not None else PipelineArtifacts()
        # ---------------- VALIDATING (cục bộ, chạy trong worker thread để không chặn event loop)
        enter(Stage.EXTRACTION)
        kind = detect_kind_bytes(data, display_name)
        art.extraction = await asyncio.to_thread(
            extract_bytes, data, kind, max_pdf_pages=cfg.MAX_PDF_PAGES, max_docx_chars=cfg.MAX_DOCX_CHARS,
            max_upload_bytes=cfg.MAX_UPLOAD_MB * 1024 * 1024)
        if done(Stage.EXTRACTION, art):
            return art
        canonical = art.extraction.canonical_text

        enter(Stage.SCOPE_PRECHECK)
        if not precheck(canonical, cfg).accept:
            raise ValidationReject("NOT_LABOR_CONTRACT")
        if done(Stage.SCOPE_PRECHECK, art):
            return art

        enter(Stage.PII_MASKING)
        art.masking = await asyncio.to_thread(mask, canonical)
        if done(Stage.PII_MASKING, art):
            return art

        enter(Stage.SEGMENTATION)
        # rules_v1.3 (Data Lead, D1/D2 Dev): `+` là cấp con có cổng khối cha ≥ 160 ký tự + tách đoạn sau
        # dòng trống. Cấu hình này là cấu hình đã đo M1/M2 Dev (merge 14/11, sửa OI-11 §2).
        art.segmentation = await asyncio.to_thread(
            segment, canonical, art.masking.masked_text, art.masking.pii_spans, max_clauses=cfg.MAX_CLAUSES,
            enable_plus_lists=True, enable_blank_line_paragraphs=True)
        if done(Stage.SEGMENTATION, art):
            return art

        enter(Stage.CLAUSE_GRAPH)
        if getattr(cfg, "CLAUSE_GRAPH_ENABLED", True):
            art.clause_graph, art.graph_diagnostics = build_clause_graph(
                art.segmentation.clauses, art.masking.masked_text)
        if done(Stage.CLAUSE_GRAPH, art):
            return art

    masked_text = art.masking.masked_text
    clauses = art.segmentation.clauses
    masked_by_id = build_masked_clause_map(art.segmentation, masked_text)

    # ---------------- PROCESSING
    enter(Stage.CLAUSE_CLASSIFICATION)
    art.clause_output = await classify_clauses(
        masked_items_from_segmentation(art.segmentation, masked_text), deps.provider, deps.ledger, cfg,
        cancel=check_cancel)
    labels_by_id = {i.clause_id: list(i.clause_labels) for i in art.clause_output.items}
    # Clause không đủ điều kiện phân loại (phần mở đầu trước Điều 1, khối chữ ký, dòng chỉ có tiêu đề —
    # `app.clause.eligibility`) không gửi LLM #1/#2; trong kết quả mang nhãn OTHER (schema cần ≥ 1 nhãn).
    analyzed = [c for c in clauses if c.clause_id in labels_by_id]
    if done(Stage.CLAUSE_CLASSIFICATION, art):
        return art

    enter(Stage.LEGAL_RETRIEVAL)
    catalog: dict[str, LegalCandidate] = {}
    provision_clause: dict[str, Optional[str]] = {}
    for c in analyzed:
        ids: list[str] = []
        if deps.retriever is not None:
            pool, fallback = get_candidates(deps.retriever, deps.data_graph, masked_by_id[c.clause_id],
                                            labels_by_id[c.clause_id], analysis_date, cfg)
            art.graph_fallbacks += int(fallback)
            for cand in pool:
                ids.append(cand.citation_id)
                catalog.setdefault(cand.citation_id, LegalCandidate(
                    cand.citation_id, cand.content, cand.document_name, cand.article))
        art.candidates[c.clause_id] = ids
    if deps.corpus is not None:
        provision_clause = {p.citation_id: p.clause for p in deps.corpus.provisions}
    if done(Stage.LEGAL_RETRIEVAL, art):
        return art

    enter(Stage.RISK_ANALYSIS)
    items: list[RiskItemIn] = []
    for c in analyzed:
        context, trace = resolve_risk_context(
            c.clause_id, art.clause_graph, masked_by_id, labels_by_id,
            max_related=cfg.CLAUSE_GRAPH_MAX_RELATED, max_context_chars=cfg.CLAUSE_GRAPH_MAX_CONTEXT_CHARS)
        art.traces.append(trace.to_dict())
        items.append(RiskItemIn(
            c.clause_id, masked_by_id[c.clause_id], labels_by_id[c.clause_id], art.candidates[c.clause_id],
            [RelatedClause(x.clause_id, x.relation, x.masked_text) for x in context]))
    art.risk_output = await analyze_risks(role.value, items, catalog, deps.provider, deps.ledger, cfg,
                                          cancel=check_cancel)
    if done(Stage.RISK_ANALYSIS, art):
        return art

    enter(Stage.CITATION_VALIDATION)
    effective = effective_provisions(deps.corpus, analysis_date) if deps.corpus is not None else {}
    validated, art.citation_stats = validate_citations(art.risk_output.items, art.candidates, effective)
    cleaned = []
    for it in validated:
        if not it.need_review and lint_explanation(it.explanation, it.citation_ids):
            # Citation vừa bị lọc ⇒ explanation có thể nhắc điều luật không còn hợp lệ: xóa câu đó.
            text = sanitize_explanation(it.explanation, it.citation_ids) or INSUFFICIENT_FALLBACK
            it = replace(it, explanation=text, sanitized=True)
        cleaned.append(it)
    if done(Stage.CITATION_VALIDATION, art):
        return art

    enter(Stage.ASSEMBLY)
    used = {cid for it in cleaned for cid in it.citation_ids}
    citations = []
    for cid in sorted(used):
        cand = catalog[cid]
        entry = {"citation_id": cid, "document_name": cand.document_name, "article": cand.article,
                 "content": cand.content}
        if provision_clause.get(cid):
            entry["clause"] = str(provision_clause[cid])
        citations.append(entry)
    result_labels = {c.clause_id: labels_by_id.get(c.clause_id, [INELIGIBLE_LABEL]) for c in clauses}
    upstream = [{"clause_id": c.clause_id, "clause_number": c.structure.number, "start_char": c.start_char,
                 "end_char": c.end_char, "original_text": c.original_text,
                 "clause_labels": result_labels[c.clause_id]} for c in clauses]
    ai_items = []
    for it in cleaned:
        d = it.to_dict()
        if it.need_review:
            d["need_review"] = True
        ai_items.append(d)
    assembled = assemble_risk_output(
        upstream, {"schema_version": "risk_output_v2", "items": ai_items},
        AssemblerContext(session_id=session_id, role=role.value, clause_stage={}, citations=citations,
                         model_id=art.risk_output.model_id, prompt_version=art.risk_output.prompt_version),
        canonical_text=art.extraction.canonical_text)
    art.diagnostics = {**assembled.diagnostics,
                       "graph": [{"code": d.code, "clause_id": d.clause_id} for d in art.graph_diagnostics],
                       "citations_outside_candidate": art.risk_output.citations_outside_candidate,
                       "citation_stats": art.citation_stats.__dict__,
                       "graph_fallbacks": art.graph_fallbacks,
                       "sanitized": sum(i.sanitized for i in cleaned)}
    art.diagnostics["ineligible_clauses"] = len(clauses) - len(analyzed)
    art.final_result = _final_result(art, assembled.merged, role, session_id, analysis_date, deps, result_labels)
    done(Stage.ASSEMBLY, art)
    return art


def _final_result(art: PipelineArtifacts, merged: dict, role: Role, session_id: str, analysis_date: date,
                  deps: PipelineDeps, labels_by_id: dict[str, list[str]]) -> dict:
    risk_keys = ("clause_id", "risk_labels", "risk_basis", "severity", "explanation", "evidence_status",
                 "citation_ids", "related_clause_ids", "needs_review")
    risks = [{k: c[k] for k in risk_keys if k in c} for c in merged["clauses"]]
    corpus = deps.corpus
    return {
        "schema_version": "final_result_v1",
        "offset_unit": "unicode_code_point",
        "session_id": session_id,
        "role": role.value,
        "status": "COMPLETED",
        "analysis_date": analysis_date.isoformat(),
        "canonical_text": art.extraction.canonical_text,
        "clauses": [{"clause_id": c.clause_id, "original_text": c.original_text, "start_char": c.start_char,
                     "end_char": c.end_char, "clause_labels": labels_by_id[c.clause_id]}
                    for c in art.segmentation.clauses],
        "risks": risks,
        "citations": merged["citations"],
        "disclaimer": DISCLAIMER,
        "data_notice": DATA_NOTICE,
        "version_pins": {
            "extraction_version": art.extraction.extraction_version,
            "clause_taxonomy_version": art.clause_output.taxonomy_version,
            "risk_taxonomy_version": merged["risk_taxonomy_version"],
            "severity_rubric_version": SEVERITY_RUBRIC_VERSION,
            "corpus_version": corpus.corpus_version if corpus else "none",
            "data_graph_version": corpus.graph_version if corpus and deps.data_graph else "disabled",
            "clause_prompt_version": art.clause_output.prompt_version,
            "risk_prompt_version": merged["prompt_version"],
            "model_id": merged["model_id"],
            "temperature": float(getattr(deps.cfg, "TEMPERATURE", 0.0)),
            "app_commit": deps.app_commit,
        },
    }


def resume_state(art: PipelineArtifacts, deps: PipelineDeps) -> Optional[ResumeState]:
    """Giữ artifact cục bộ khi lỗi ở giai đoạn AI để Retry chạy lại từ CLAUSE_CLASSIFICATION."""
    if all(s in art.completed for s in LOCAL_STAGES):
        return ResumeState(art, _resume_pins(deps))
    return None
