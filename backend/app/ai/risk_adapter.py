"""Risk Analysis adapter — LLM #2 (TDD §15, C-15 khung, W3).

C-15 (a) (W5): ngoài kiểm cấu trúc, adapter kiểm NGỮ NGHĨA trong cùng cơ chế retry ≤1 có phản hồi
(TDD §15.3, §15.5, X-22):
  * (nhãn, basis_type, vai trò) rơi vào ô '-' của taxonomy;
  * explanation có lời khuyên (`detect_advice`) hoặc dẫn chiếu luật không khớp citation đã chọn
    (`detect_unsupported_reference`, chỉ tính citation thuộc candidate của clause).
Lần đầu vi phạm ⇒ ValueError có phản hồi (chỉ ID/nhãn/mã, không text) ⇒ retry. Lần cuối vẫn vi phạm:
  * gỡ nhãn sai tổ hợp; hết nhãn ⇒ `need_review=True` (bản ghi "nghi ngờ, cần xem xét": INSUFFICIENT,
    severity null, không citation; assembler giữ clause, UI hiện thẻ nét đứt);
  * xóa câu vi phạm bằng `sanitize_explanation`; rỗng ⇒ AiOutputInvalid (FAILED).
Citation validator (lọc theo candidate + hiệu lực, hạ INSUFFICIENT) chạy SAU adapter, ở pipeline.

Bất biến:
  INV-04  ra ngoài chỉ có masked_text, nhãn clause, candidate (nội dung luật công khai), role; không
          canonical/original, offset, structure;
  INV-05  response có field lạ / ID lạ / trùng / nhãn hoặc basis ngoài taxonomy / sai ràng buộc chéo ⇒ từ
          chối; retry ≤1 ⇒ AiOutputInvalid; model KHÔNG khai severity, role, version pin;
  INV-06  severity KHÔNG do adapter quyết (assembler tra bảng).
`related_clause_ids` là trường TÙY CHỌN duy nhất ngoài 6 khóa bắt buộc: mỗi ID phải thuộc
related_clauses của chính clause đó trong batch, không trùng, không tự tham chiếu; khóa lạ vẫn bị từ chối.
`citation_ids` ngoài `candidate_ids` KHÔNG bị từ chối ở đây: validator (TDD §15.4) log rồi lọc; adapter chỉ
đếm vào `citations_outside_candidate` (không chứa text).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field, replace
from typing import Callable, Mapping, Optional

from app.ai.prompts.risk_v1 import (
    BASIS_TYPE_DEFINITIONS,
    OUTPUT_SCHEMA_VERSION,
    RESPONSE_SCHEMA,
    build_messages,
    build_request,
    prompt_pin,
)
from app.ai.provider import CallLedger, LLMProvider, call_with_retry
from app.clause.context_resolver import ContextResolutionTrace, resolve_context
from app.clause.graph_builder import ClauseGraph
from app.core.enums import Role
from app.domain.errors import AiOutputInvalid, StageCancelled
from app.risk.lint import lint_explanation, sanitize_explanation
from app.risk.taxonomy import (
    MAX_RISK_LABELS_PER_CLAUSE,
    RISK_LABEL_SET,
    RISK_TAXONOMY_VERSION,
    SEVERITY_RUBRIC_VERSION,
    invalid_labels_for_role,
    severity_for,
)

_CLAUSE_ID = re.compile(r"^cl_[0-9]{4}$")
_REQUIRED_KEYS = frozenset(
    {"clause_id", "basis_type", "risk_labels", "citation_ids", "evidence_status", "explanation"}
)
_OPTIONAL_KEYS = frozenset({"related_clause_ids"})
_EVIDENCE = {"SUPPORTED", "INSUFFICIENT_EVIDENCE"}
_MIN_EXPLANATION = 10


@dataclass(frozen=True)
class LegalCandidate:
    """Một điều luật trong catalog gửi LLM (nội dung luật công khai, không phải dữ liệu hợp đồng)."""

    candidate_id: str  # ví dụ BLLD2019:art26
    content: str
    document_name: str = ""
    article: str = ""

    def to_payload(self) -> dict:
        return {"content": self.content, "metadata": {"document_name": self.document_name, "article": self.article}}


@dataclass(frozen=True)
class RelatedClause:
    clause_id: str
    relation: str  # REFERS_TO | ... (do Clause Graph quyết)
    masked_text: str


@dataclass(frozen=True)
class RiskItemIn:
    clause_id: str
    masked_text: str
    clause_labels: list[str]
    candidate_ids: list[str] = field(default_factory=list)
    related_clauses: list[RelatedClause] = field(default_factory=list)

    def to_payload(self) -> dict:
        return {
            "clause_id": self.clause_id,
            "masked_text": self.masked_text,
            "clause_labels": list(self.clause_labels),
            "candidate_ids": list(self.candidate_ids),
            "related_clauses": [
                {"clause_id": r.clause_id, "relation": r.relation, "masked_text": r.masked_text}
                for r in self.related_clauses
            ],
        }


def attach_graph_context(
    items: list[RiskItemIn],
    graph: ClauseGraph,
    masked_clauses: Mapping[str, str],
    *,
    max_related: int = 3,
    max_context_chars: int = 6000,
) -> list[RiskItemIn]:
    """Prepare masked related clauses for the M2 request without mutating inputs."""
    return [
        replace(
            item,
            related_clauses=[
                RelatedClause(c.clause_id, c.relation, c.masked_text)
                for c in resolve_context(
                    graph,
                    item.clause_id,
                    masked_clauses,
                    max_related=max_related,
                    max_context_chars=max_context_chars,
                )
            ],
        )
        for item in items
    ]


def build_context_traces(
    items: list[RiskItemIn], *, included_in_risk_request: bool = True,
) -> list[dict]:
    """Ephemeral TDD §12.3 diagnostics: IDs and counts only, never clause text."""
    return [
        ContextResolutionTrace(
            target_clause_id=item.clause_id,
            related=tuple((r.clause_id, r.relation) for r in item.related_clauses),
            included_in_risk_request=included_in_risk_request,
            context_chars=sum(len(r.masked_text) for r in item.related_clauses),
        ).to_dict()
        for item in items
    ]


@dataclass(frozen=True)
class RiskItemOut:
    clause_id: str
    basis_type: str
    risk_labels: list[str]
    citation_ids: list[str]
    evidence_status: str
    explanation: str
    related_clause_ids: list[str] = field(default_factory=list)
    # Không thuộc risk_output_v2 (model không trả): backend đặt khi tổ hợp nhãn/basis/vai trò vẫn sai sau retry.
    need_review: bool = False
    labels_dropped: list[str] = field(default_factory=list)
    sanitized: bool = False

    def to_dict(self) -> dict:
        out = {
            "clause_id": self.clause_id,
            "basis_type": self.basis_type,
            "risk_labels": list(self.risk_labels),
            "citation_ids": list(self.citation_ids),
            "evidence_status": self.evidence_status,
            "explanation": self.explanation,
        }
        if self.related_clause_ids:  # vắng khi rỗng: đầu ra cũ không đổi
            out["related_clause_ids"] = list(self.related_clause_ids)
        return out


INSUFFICIENT_EXPLANATION = "Chưa đủ căn cứ pháp lý đã xác thực để kết luận về điều khoản này."


def allowed_basis(label: str, role: str) -> list[str]:
    return [b for b in BASIS_TYPE_DEFINITIONS if severity_for(label, b, role) is not None]


def semantic_problems(role: str, items: list[RiskItemOut], batch: list[RiskItemIn]) -> list[str]:
    """Phản hồi cho retry (chỉ ID, nhãn, mã — KHÔNG text hợp đồng/explanation)."""
    candidates = {b.clause_id: set(b.candidate_ids) for b in batch}
    problems: list[str] = []
    for it in items:
        for label in invalid_labels_for_role(it.risk_labels, it.basis_type, role):
            allowed = ", ".join(allowed_basis(label, role)) or "không loại nào (không phải rủi ro của vai trò này)"
            problems.append(f"{it.clause_id}: {label} không dùng với {it.basis_type} cho {role}; được phép: {allowed}")
        valid_cites = [c for c in it.citation_ids if c in candidates.get(it.clause_id, set())]
        for code in lint_explanation(it.explanation, valid_cites):
            problems.append(f"{it.clause_id}: explanation vi phạm {code}")
    return problems


def finalize_items(role: str, items: list[RiskItemOut], batch: list[RiskItemIn]) -> list[RiskItemOut]:
    """Lần cuối (không còn retry): gỡ nhãn sai, đánh need_review, sanitize câu vi phạm."""
    candidates = {b.clause_id: set(b.candidate_ids) for b in batch}
    out: list[RiskItemOut] = []
    for it in items:
        bad = invalid_labels_for_role(it.risk_labels, it.basis_type, role)
        if bad and len(bad) == len(it.risk_labels):
            it = replace(it, need_review=True, labels_dropped=list(bad), evidence_status="INSUFFICIENT_EVIDENCE",
                         citation_ids=[])
        elif bad:
            it = replace(it, risk_labels=[x for x in it.risk_labels if x not in bad], labels_dropped=list(bad))
        valid_cites = [c for c in it.citation_ids if c in candidates.get(it.clause_id, set())]
        codes = lint_explanation(it.explanation, valid_cites)
        if codes:
            cleaned = sanitize_explanation(it.explanation, valid_cites)
            if cleaned is None and "advice" in codes:
                raise AiOutputInvalid(f"explanation rỗng sau sanitize ở {it.clause_id}")
            if cleaned is None:
                # Chỉ còn dẫn chiếu luật không có căn cứ hợp lệ (vd. citation ngoài candidate): không FAILED cả
                # phiên mà hạ về INSUFFICIENT_EVIDENCE với câu trung tính (BR-15; hành vi runner Data Lead).
                it = replace(it, explanation=INSUFFICIENT_EXPLANATION, evidence_status="INSUFFICIENT_EVIDENCE",
                             citation_ids=[], sanitized=True)
            else:
                it = replace(it, explanation=cleaned, sanitized=True)
        out.append(it)
    return out


@dataclass(frozen=True)
class RiskOutput:
    """Câu trả lời đã validate của LLM #2 + version pin do backend đóng dấu (không nằm trong response model)."""

    items: list[RiskItemOut]
    model_id: str
    prompt_version: str
    risk_taxonomy_version: str = RISK_TAXONOMY_VERSION
    severity_rubric_version: str = SEVERITY_RUBRIC_VERSION
    citations_outside_candidate: int = 0
    schema_version: str = OUTPUT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        """Đúng `risk_output_v2.json` (additionalProperties=false): chỉ schema_version + items."""
        return {"schema_version": self.schema_version, "items": [i.to_dict() for i in self.items]}

    def pins(self) -> dict:
        return {
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "risk_taxonomy_version": self.risk_taxonomy_version,
            "severity_rubric_version": self.severity_rubric_version,
        }


def make_batches(items: list, size: int) -> list[list]:
    if size <= 0:
        raise ValueError("batch size phải > 0")
    return [items[i : i + size] for i in range(0, len(items), size)]


def _related_ids(it: dict, clause: RiskItemIn) -> list[str]:
    """`related_clause_ids` tùy chọn: thuộc related_clauses của CHÍNH clause, không trùng, không tự tham chiếu."""
    if "related_clause_ids" not in it:
        return []
    rel, cid = it["related_clause_ids"], clause.clause_id
    if not isinstance(rel, list) or any(not isinstance(x, str) or not _CLAUSE_ID.match(x) for x in rel):
        raise ValueError(f"related_clause_ids phải là mảng cl_NNNN ở {cid}")
    if len(set(rel)) != len(rel):
        raise ValueError(f"related_clause_ids bị trùng ở {cid}")
    # FR-32: chỉ cặp có cạnh Clause Graph; context chung (COMMON_*, FR-33) không phải quan hệ mâu thuẫn.
    allowed = {r.clause_id for r in clause.related_clauses if not r.relation.startswith("COMMON_")}
    if any(x == cid or x not in allowed for x in rel):
        raise ValueError(f"related_clause_ids ngoài context hoặc tự tham chiếu ở {cid}")
    return list(rel)


def validate_batch_response(data: dict, batch: list[RiskItemIn]) -> list[RiskItemOut]:
    """Kiểm một response; raise ValueError (message KHÔNG chứa nội dung clause/explanation) nếu sai.

    Clause không có rủi ro được phép vắng mặt (items có thể rỗng); chỉ clause_id thuộc `batch`, mỗi ID tối đa
    một lần. Trả danh sách theo thứ tự clause trong batch.
    """
    if not isinstance(data, dict) or set(data) != {"schema_version", "items"}:
        extra = sorted(set(data) ^ {"schema_version", "items"}) if isinstance(data, dict) else []
        raise ValueError(f"response phải gồm đúng 'schema_version' và 'items' (lệch: {extra})")
    if data["schema_version"] != OUTPUT_SCHEMA_VERSION:
        raise ValueError(f"schema_version phải là {OUTPUT_SCHEMA_VERSION}")
    raw_items = data["items"]
    if not isinstance(raw_items, list):
        raise ValueError("'items' phải là mảng")

    known = {b.clause_id: b for b in batch}
    out: dict[str, RiskItemOut] = {}
    for it in raw_items:
        keys = set(it) if isinstance(it, dict) else set()
        if not isinstance(it, dict) or not _REQUIRED_KEYS <= keys <= _REQUIRED_KEYS | _OPTIONAL_KEYS:
            missing = sorted(_REQUIRED_KEYS - keys)
            extra = sorted(keys - _REQUIRED_KEYS - _OPTIONAL_KEYS)
            raise ValueError(
                f"item phải có đủ {sorted(_REQUIRED_KEYS)}, chỉ thêm tối đa {sorted(_OPTIONAL_KEYS)} "
                f"(thiếu: {missing}, lạ: {extra})"
            )
        cid = it["clause_id"]
        if not isinstance(cid, str) or not _CLAUSE_ID.match(cid):
            raise ValueError("clause_id sai định dạng")
        if cid not in known:
            raise ValueError(f"clause_id không có trong yêu cầu: {cid}")
        if cid in out:
            raise ValueError(f"clause_id trùng: {cid}")
        if it["basis_type"] not in BASIS_TYPE_DEFINITIONS:
            raise ValueError(f"basis_type ngoài enum ở {cid}")
        labels = it["risk_labels"]
        if not isinstance(labels, list) or not 1 <= len(labels) <= MAX_RISK_LABELS_PER_CLAUSE:
            raise ValueError(f"risk_labels phải có 1..{MAX_RISK_LABELS_PER_CLAUSE} nhãn ở {cid}")
        if len(set(labels)) != len(labels) or any(not isinstance(x, str) or x not in RISK_LABEL_SET for x in labels):
            raise ValueError(f"risk_labels trùng hoặc ngoài taxonomy ở {cid}")
        cites = it["citation_ids"]
        if not isinstance(cites, list) or any(not isinstance(c, str) or not c for c in cites) or len(set(cites)) != len(cites):  # noqa: E501
            raise ValueError(f"citation_ids phải là mảng chuỗi không rỗng, không trùng ở {cid}")
        status = it["evidence_status"]
        if status not in _EVIDENCE:
            raise ValueError(f"evidence_status ngoài enum ở {cid}")
        if status == "SUPPORTED" and not cites:
            raise ValueError(f"SUPPORTED cần citation_ids không rỗng ở {cid}")
        if status == "INSUFFICIENT_EVIDENCE" and cites:
            raise ValueError(f"INSUFFICIENT_EVIDENCE phải có citation_ids rỗng ở {cid}")
        expl = it["explanation"]
        if not isinstance(expl, str) or len(expl.strip()) < _MIN_EXPLANATION:
            raise ValueError(f"explanation quá ngắn hoặc không phải chuỗi ở {cid}")
        rel = _related_ids(it, known[cid])
        out[cid] = RiskItemOut(
            cid, it["basis_type"], list(labels), list(cites), status, expl.strip(), related_clause_ids=rel
        )
    return [out[b.clause_id] for b in batch if b.clause_id in out]


def _validate_inputs(role: str, items: list[RiskItemIn], candidates: dict[str, LegalCandidate]) -> None:
    if role not in {r.value for r in Role}:
        raise ValueError(f"role không hợp lệ: {role!r}")
    ids = [i.clause_id for i in items]
    if len(set(ids)) != len(ids):
        raise ValueError("clause_id đầu vào bị trùng")
    for it in items:
        if not _CLAUSE_ID.match(it.clause_id):
            raise ValueError("clause_id đầu vào sai định dạng")
        missing = [c for c in it.candidate_ids if c not in candidates]
        if missing:
            raise ValueError(f"candidate_ids không có trong catalog: {missing[:3]}")


def _batch_request(role: str, batch: list[RiskItemIn], candidates: dict[str, LegalCandidate]) -> dict:
    used: dict[str, dict] = {}
    for it in batch:  # catalog dedupe: mỗi candidate một lần, chỉ gồm ID mà batch tham chiếu
        for cid in it.candidate_ids:
            used.setdefault(cid, candidates[cid].to_payload())
    return build_request(role, [i.to_payload() for i in batch], used)


async def analyze_risks(
    role: str,
    items: list[RiskItemIn],
    candidates: dict[str, LegalCandidate],
    provider: LLMProvider,
    ledger: CallLedger,
    cfg,
    cancel: Optional[Callable[[], bool]] = None,
) -> RiskOutput:
    """Phân tích theo lô (RISK_BATCH_SIZE), song song ≤ LLM_PARALLELISM, kiểm cancel TRƯỚC mỗi lô.

    `cancel()` trả True ⇒ StageCancelled. Lô lỗi ⇒ các lô còn lại bị hủy; lỗi mang mã AI_*.
    """
    if not items:
        raise ValueError("không có clause để phân tích")
    _validate_inputs(role, items, candidates)
    model_id = getattr(cfg, "GEMINI_MODEL_ID", None)
    if not model_id:
        raise ValueError("thiếu model id (GEMINI_MODEL_ID) — không dùng model mặc định ngầm")

    batches = make_batches(items, cfg.RISK_BATCH_SIZE)
    sem = asyncio.Semaphore(max(1, cfg.LLM_PARALLELISM))
    results: dict[int, list[RiskItemOut]] = {}
    resp_model: dict[int, str] = {}
    outside = 0

    retries = min(max(int(cfg.LLM_AUTO_RETRY), 0), 1)

    async def run(idx: int, batch: list[RiskItemIn]) -> None:
        nonlocal outside
        attempts = {"n": 0}

        def validate(data: dict, b: list[RiskItemIn] = batch) -> list[RiskItemOut]:
            strict = attempts["n"] < retries  # còn lượt retry ⇒ vi phạm ngữ nghĩa thì xin model sửa
            attempts["n"] += 1
            parsed_items = validate_batch_response(data, b)
            problems = semantic_problems(role, parsed_items, b)
            if problems and strict:
                raise ValueError("; ".join(problems))
            return finalize_items(role, parsed_items, b)

        async with sem:
            if cancel is not None and cancel():
                raise StageCancelled()
            resp, parsed = await call_with_retry(
                provider,
                ledger,
                model_id=model_id,
                messages=build_messages(_batch_request(role, batch, candidates)),
                response_schema=RESPONSE_SCHEMA,
                timeout_s=cfg.LLM_TIMEOUT_SECONDS,
                validate=validate,
                max_retries=cfg.LLM_AUTO_RETRY,
            )
            if cancel is not None and cancel():  # callback muộn sau End bị bỏ
                raise StageCancelled()
            allowed = {b.clause_id: set(b.candidate_ids) for b in batch}
            outside += sum(1 for r in parsed for c in r.citation_ids if c not in allowed[r.clause_id])
            results[idx] = parsed
            resp_model[idx] = resp.model_id

    tasks = [asyncio.ensure_future(run(i, b)) for i, b in enumerate(batches)]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    merged = [r for i in range(len(batches)) for r in results[i]]
    if len({r.clause_id for r in merged}) != len(merged):  # phòng thủ: không thể xảy ra nếu validate đúng
        raise AiOutputInvalid("hợp nhất các lô bị trùng clause_id")
    models = set(resp_model.values())
    return RiskOutput(
        items=merged,
        model_id=models.pop() if len(models) == 1 else model_id,
        prompt_version=prompt_pin(),
        citations_outside_candidate=outside,
    )
