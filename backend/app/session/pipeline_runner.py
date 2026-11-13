"""Explicit dev/eval runner for local preprocessing and injected LLM providers.

The caller owns the canonical source and provider/ledger lifecycle. This runner
is opt-in; its result enters the in-memory session only after masked provider
calls finish.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import date

from app.ai.clause_adapter import classify_clauses, masked_items_from_segmentation
from app.ai.provider import CallLedger, LLMProvider
from app.ai.risk_adapter import LegalCandidate, RiskItemIn, analyze_risks, attach_graph_context
from app.clause.context_resolver import build_masked_clause_map
from app.clause.graph_builder import build_clause_graph
from app.clause.segmenter import segment
from app.domain.errors import AiOutputInvalid, StageCancelled
from app.integrations.risk_assembler import AssemblerContext, assemble_risk_output
from app.legal.corpus_loader import LegalCorpus
from app.privacy.masker import mask
from app.session.final_result import build_final_result_v1
from app.session.store import Session

_ADVICE = re.compile(
    r"(?:bạn|người\s+lao\s+động|nlđ|người\s+sử\s+dụng\s+lao\s+động|nsdlđ|"
    r"hai\s+bên|công\s+ty)\s+nên\b|"
    r"\bnên\s+(?:sửa|bổ\s+sung|thương\s+lượng|yêu\s+cầu|đàm\s+phán|"
    r"bỏ|xóa|thay\s+đổi|quy\s+định\s+lại)\b|"
    r"\b(?:đề\s+nghị\s+sửa|khuyến\s+nghị)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?]+[.!?]?", re.DOTALL)


def sanitize_advice_sentences(explanation: str) -> tuple[str, bool]:
    """Remove advice sentences, preserving factual rationale or fail closed."""
    kept = []
    removed = False
    for match in _SENTENCE.finditer(explanation):
        sentence = match.group()
        if _ADVICE.search(sentence):
            removed = True
        else:
            kept.append(sentence)
    if not removed:
        return explanation, False
    neutral = "".join(kept).strip()
    if len(neutral) < 10:
        raise AiOutputInvalid("explanation lost its neutral rationale after advice removal")
    return neutral, True


def make_pipeline_runner(
    canonical_text: str,
    clause_provider: LLMProvider,
    risk_provider: LLMProvider,
    candidates: Mapping[str, LegalCandidate],
    ledger: CallLedger,
    cfg,
    *,
    corpus: LegalCorpus | None = None,
    retriever=None,
    candidate_ids_by_clause: Mapping[str, list[str]] | None = None,
    enable_plus_lists: bool = True,
    enable_blank_line_paragraphs: bool = True,
):
    """Bind a canonical source to an async runner without persisting it in Session."""
    if retriever is not None and corpus is None:
        raise ValueError("retrieval requires a validated legal corpus")

    async def run(session: Session, *, cancel: Callable[[], bool]) -> dict:
        if cancel():
            raise StageCancelled()
        masked = mask(canonical_text)
        segmented = segment(canonical_text, masked.masked_text, masked.pii_spans,
                            enable_plus_lists=enable_plus_lists,
                            enable_blank_line_paragraphs=enable_blank_line_paragraphs)
        graph, _ = build_clause_graph(segmented.clauses, masked.masked_text)
        all_masked = build_masked_clause_map(segmented, masked.masked_text)
        eligible = masked_items_from_segmentation(segmented, masked.masked_text)
        classified = await classify_clauses(eligible, clause_provider, ledger, cfg, cancel=cancel)
        ids = dict(candidate_ids_by_clause or {})
        catalog = dict(candidates)
        analysis_date = date.fromisoformat(session.analysis_date)
        if retriever is not None:
            for item in classified.items:
                retrieved = retriever.retrieve(all_masked[item.clause_id], item.clause_labels,
                                               as_of=analysis_date)
                for candidate in retrieved.baseline_pool:
                    catalog[candidate.citation_id] = LegalCandidate(
                        candidate.citation_id, candidate.content,
                        candidate.document_name, candidate.article)
                ids[item.clause_id] = [c.citation_id for c in retrieved.baseline_pool]
        risk_items = [RiskItemIn(item.clause_id, all_masked[item.clause_id], item.clause_labels,
                                 list(ids.get(item.clause_id, ())))
                      for item in classified.items]
        related = attach_graph_context(
            risk_items, graph, all_masked,
            max_related=cfg.CLAUSE_GRAPH_MAX_RELATED,
            max_context_chars=cfg.CLAUSE_GRAPH_MAX_CONTEXT_CHARS,
        )
        output = await analyze_risks(session.role.value, related, catalog,
                                     risk_provider, ledger, cfg, cancel=cancel)
        selected = {item.clause_id: set(item.candidate_ids) for item in related}
        provisions = {p.citation_id: p for p in corpus.provisions} if corpus else {}
        validated = output.to_dict()
        used: set[str] = set()
        for item in validated["items"]:
            selected_before_filter = list(item["citation_ids"])
            valid = []
            for cid in item["citation_ids"]:
                provision = provisions.get(cid)
                if (cid in selected[item["clause_id"]] and provision is not None
                        and provision.effective_from <= analysis_date
                        and (provision.effective_to is None
                             or analysis_date <= provision.effective_to)
                        and cid not in valid):
                    valid.append(cid)
            item["citation_ids"] = valid
            if not valid:
                item["evidence_status"] = "INSUFFICIENT_EVIDENCE"
                if selected_before_filter:
                    item["explanation"] = (
                        "Chưa đủ căn cứ pháp lý đã xác thực để kết luận về điều khoản này.")
            item["explanation"], _ = sanitize_advice_sentences(item["explanation"])
            used.update(valid)
        citation_objects = [
            {"citation_id": cid, "document_name": p.document_name,
             "article": p.article, "content": p.content}
            for cid, p in provisions.items() if cid in used
        ]
        upstream = [
            {"clause_id": c.clause_id, "clause_number": c.structure.number,
             "start_char": c.start_char, "end_char": c.end_char,
             "original_text": c.original_text,
             "clause_labels": next((x.clause_labels for x in classified.items
                                    if x.clause_id == c.clause_id), [])}
            for c in segmented.clauses
        ]
        ctx = AssemblerContext(
            session_id=str(session.session_id), role=session.role.value,
            clause_stage={"model_id": classified.model_id,
                          "prompt_version": classified.prompt_version,
                          "taxonomy_version": classified.taxonomy_version},
            citations=citation_objects, model_id=output.model_id,
            prompt_version=output.prompt_version,
        )
        assembled = assemble_risk_output(upstream, validated, ctx, canonical_text=canonical_text)
        related_ids = {item.clause_id: [c.clause_id for c in item.related_clauses]
                       for item in related}
        pins = {
            "extraction_version": getattr(cfg, "EXTRACTION_VERSION", "caller_canonical_v1"),
            "clause_taxonomy_version": classified.taxonomy_version,
            "risk_taxonomy_version": output.risk_taxonomy_version,
            "severity_rubric_version": output.severity_rubric_version,
            "corpus_version": corpus.corpus_version if corpus else "not_loaded",
            "data_graph_version": corpus.graph_version if corpus else "not_loaded",
            "clause_prompt_version": classified.prompt_version,
            "risk_prompt_version": output.prompt_version,
            "model_id": output.model_id,
            "temperature": getattr(cfg, "GEMINI_TEMPERATURE", 0.0),
            "app_commit": getattr(cfg, "APP_COMMIT", "dev-unpinned"),
        }
        return build_final_result_v1(
            session_id=str(session.session_id), role=session.role.value,
            analysis_date=session.analysis_date, canonical_text=canonical_text,
            clauses=upstream, merged=assembled.merged,
            related_clause_ids=related_ids, version_pins=pins,
        )

    return run
