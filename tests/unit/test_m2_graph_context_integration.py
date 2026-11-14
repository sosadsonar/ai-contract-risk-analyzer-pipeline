"""Việc 4 — M2 mock-provider integration: ClauseGraph → masked context → RiskItemIn → analyze_risks.

Fixture hoàn toàn de-identified: không text hợp đồng thật, không PII, không T2.
Mục tiêu: xác minh đường dữ liệu end-to-end (schema, context attachment, INV-04/05 bất biến)
bằng FakeProvider (không gọi Gemini thật).

Giới hạn rõ ràng (ghi trong bàn giao cho Codex):
- Orchestrator vẫn dùng sample_result (mock) — chưa nối Risk Adapter vào run().
- REFERS_TO chưa được build_clause_graph() tạo ra (W5 — tuần 5).
- Fixture dùng context đã che PII (placeholder <NAME>, <ORG>, v.v.) — không canonical text.
"""

import asyncio
import json
from types import SimpleNamespace

from app.ai.provider import InMemoryLedger, LLMResponse
from app.ai.risk_adapter import (
    LegalCandidate,
    RiskItemIn,
    RiskOutput,
    analyze_risks,
    attach_graph_context,
    build_context_traces,
)
from app.clause.context_resolver import build_masked_clause_map, resolve_context
from app.clause.graph_builder import ClauseEdge, ClauseGraph, build_clause_graph
from app.clause.segmenter import ClauseStructure, SegmentedClause
from app.core.enums import ClauseEdgeType
from app.privacy.masker import mask_value
from app.privacy.pii_types import PiiType

# ---------------------------------------------------------------------------
# Fixture helpers — de-identified, không text hợp đồng thật
# ---------------------------------------------------------------------------

CFG = SimpleNamespace(
    GEMINI_MODEL_ID="mock-model",
    RISK_BATCH_SIZE=5,
    LLM_PARALLELISM=1,
    LLM_TIMEOUT_SECONDS=5,
    LLM_AUTO_RETRY=1,
)

CANDS = {
    "BLLD2019:art25": LegalCandidate(
        "BLLD2019:art25",
        "Thời gian thử việc không quá 60 ngày với công việc có chức danh nghề...",
        "Bộ luật Lao động 2019",
        "Điều 25",
    ),
    "BLLD2019:art90": LegalCandidate(
        "BLLD2019:art90",
        "Tiền lương là số tiền mà người sử dụng lao động trả cho người lao động...",
        "Bộ luật Lao động 2019",
        "Điều 90",
    ),
}

# Graph: cl_0001 -NEXT-> cl_0002 -NEXT-> cl_0003; cl_0001 PARENT_OF cl_0002
_NODES = ("cl_0001", "cl_0002", "cl_0003")
_EDGES = (
    ClauseEdge("cl_0001", "cl_0002", ClauseEdgeType.NEXT),
    ClauseEdge("cl_0002", "cl_0003", ClauseEdgeType.NEXT),
    ClauseEdge("cl_0001", "cl_0002", ClauseEdgeType.PARENT_OF),
)
GRAPH = ClauseGraph(node_ids=_NODES, edges=_EDGES)

# Masked clauses (placeholder, không PII)
MASKED = {
    "cl_0001": "Điều 1. Thời gian thử việc: <ORG> sẽ áp dụng thời gian thử việc <DURATION>.",
    "cl_0002": "Điều 1.1. Lương thử việc: không ít hơn <PERCENT>% mức lương chính thức.",
    "cl_0003": "Điều 2. Hình thức trả lương: <ORG> trả lương theo kỳ hạn <DURATION>.",
}

ITEMS_BASE = [
    RiskItemIn("cl_0001", MASKED["cl_0001"], ["PROBATION_CLAUSE"], ["BLLD2019:art25"]),
    RiskItemIn("cl_0002", MASKED["cl_0002"], ["COMPENSATION_BENEFITS"], ["BLLD2019:art90"]),
    RiskItemIn("cl_0003", MASKED["cl_0003"], ["COMPENSATION_BENEFITS"], ["BLLD2019:art90"]),
]


class FakeProvider:
    """Mock LLM — trả kết quả hợp lệ theo schema risk_output_v2 mà không gọi Gemini."""

    def __init__(self, response_fn=None):
        self.calls: list[dict] = []
        self._fn = response_fn or self._default_fn

    @staticmethod
    def _default_fn(messages: list[dict]) -> dict:
        req = json.loads(messages[1]["content"])
        items = []
        for it in req["items"]:
            cid = it["clause_id"]
            cand_ids = it.get("candidate_ids", [])
            items.append({
                "clause_id": cid,
                "basis_type": "UNFAVORABLE",
                "risk_labels": ["PROBATION" if cid == "cl_0001" else "WAGE_AMOUNT_COMPONENTS"],
                "citation_ids": cand_ids[:1] if cand_ids else [],
                "evidence_status": "SUPPORTED" if cand_ids else "INSUFFICIENT_EVIDENCE",
                "explanation": f"Điều khoản {cid} có dấu hiệu bất lợi cho người lao động theo pháp luật.",
            })
        return {"schema_version": "risk_output_v2", "items": items}

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        self.calls.append({"model_id": model_id, "messages": messages})
        return LLMResponse(
            data=self._fn(messages),
            model_id=model_id,
            in_tokens=50,
            out_tokens=20,
        )


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Việc 4 — Tests
# ---------------------------------------------------------------------------


class TestAttachGraphContext:
    """Xác minh attach_graph_context() đúng schema và bất biến INV-04."""

    def test_attach_graph_context_adds_related_clauses(self):
        items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        # cl_0001: có NEXT→cl_0002 (NEXT), PARENT_OF→cl_0002 (CHILD_OF from target's view)
        item_0001 = next(i for i in items if i.clause_id == "cl_0001")
        related_ids = [r.clause_id for r in item_0001.related_clauses]
        # cl_0002 là con trực tiếp của cl_0001 (CHILD_OF) và là NEXT
        assert "cl_0002" in related_ids

    def test_attach_graph_context_respects_max_related(self):
        items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED, max_related=1)
        for item in items:
            assert len(item.related_clauses) <= 1

    def test_attach_graph_context_respects_budget(self):
        # Budget rất nhỏ → không thêm context nào
        items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED, max_context_chars=5)
        for item in items:
            assert item.related_clauses == []

    def test_attach_graph_context_no_canonical_text_in_related(self):
        items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        for item in items:
            for rc in item.related_clauses:
                # masked_text phải khớp MASKED dict (không phải canonical)
                assert rc.masked_text == MASKED[rc.clause_id]

    def test_attach_graph_context_no_self_loop(self):
        """Target clause không xuất hiện trong related_clauses của chính nó."""
        items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        for item in items:
            related_ids = [r.clause_id for r in item.related_clauses]
            assert item.clause_id not in related_ids

    def test_attach_graph_context_does_not_mutate_inputs(self):
        original_related = [list(i.related_clauses) for i in ITEMS_BASE]
        attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        for i, item in enumerate(ITEMS_BASE):
            assert list(item.related_clauses) == original_related[i]


class TestRiskItemInPayload:
    """Xác minh to_payload() không rò canonical/offset (INV-04)."""

    def test_payload_no_canonical_no_offset(self):
        items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        for item in items:
            payload = item.to_payload()
            payload_str = json.dumps(payload)
            assert "canonical" not in payload_str
            assert "offset" not in payload_str
            assert "original_text" not in payload_str

    def test_payload_related_clauses_schema(self):
        items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        for item in items:
            payload = item.to_payload()
            for rc in payload.get("related_clauses", []):
                assert set(rc.keys()) == {"clause_id", "relation", "masked_text"}


class TestEndToEndMockProvider:
    """Đường dữ liệu đầy đủ: attach_graph_context → analyze_risks (mock provider)."""

    def test_end_to_end_happy_path(self):
        provider = FakeProvider()
        ledger = InMemoryLedger()
        items_with_context = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        output: RiskOutput = run(
            analyze_risks("EMPLOYEE", items_with_context, CANDS, provider, ledger, CFG)
        )
        assert isinstance(output, RiskOutput)
        assert len(output.items) == 3
        clause_ids = {r.clause_id for r in output.items}
        assert clause_ids == {"cl_0001", "cl_0002", "cl_0003"}

    def test_end_to_end_no_contract_text_in_provider_call(self):
        """Payload gửi đi chỉ có masked_text, không canonical/original."""
        provider = FakeProvider()
        items_with_context = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        run(analyze_risks("EMPLOYEE", items_with_context, CANDS, provider, InMemoryLedger(), CFG))
        for call in provider.calls:
            payload_str = json.dumps(call["messages"])
            assert "canonical" not in payload_str
            assert "original_text" not in payload_str

    def test_synthetic_canonical_sentinel_is_absent_from_provider_request(self):
        """Transport uses the supplied masked value; Masker-to-adapter wiring remains separate."""
        canonical_secret = "NguyenVanAnSyntheticSecret"
        masked_secret = mask_value(canonical_secret, PiiType.PERSON_NAME)
        assert canonical_secret != masked_secret
        canonical = f"Người lao động {canonical_secret} có thỏa thuận thử việc."
        masked = canonical.replace(canonical_secret, masked_secret)
        assert len(masked) == len(canonical)
        graph = ClauseGraph(("cl_0001", "cl_0002"),
                            (ClauseEdge("cl_0001", "cl_0002", ClauseEdgeType.NEXT),))
        masked_map = {"cl_0001": masked, "cl_0002": "Thời gian thử việc áp dụng theo thỏa thuận."}
        item = RiskItemIn("cl_0002", masked_map["cl_0002"], ["PROBATION"], ["BLLD2019:art25"])
        provider = FakeProvider()
        run(analyze_risks("EMPLOYEE", attach_graph_context([item], graph, masked_map),
                          CANDS, provider, InMemoryLedger(), CFG))
        request = json.dumps(provider.calls[0]["messages"], ensure_ascii=False)
        assert canonical_secret not in request
        assert masked_secret in request

    def test_end_to_end_model_id_pinned(self):
        provider = FakeProvider()
        items_with_context = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        output = run(analyze_risks("EMPLOYEE", items_with_context, CANDS, provider, InMemoryLedger(), CFG))
        assert output.model_id == "mock-model"
        assert output.prompt_version.startswith("risk_prompt_v2+")  # X-22

    def test_end_to_end_output_schema_valid(self):
        provider = FakeProvider()
        items_with_context = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
        output = run(analyze_risks("EMPLOYEE", items_with_context, CANDS, provider, InMemoryLedger(), CFG))
        d = output.to_dict()
        assert d["schema_version"] == "risk_output_v2"
        assert isinstance(d["items"], list)
        for item in d["items"]:
            assert "clause_id" in item
            assert "risk_labels" in item
            assert "basis_type" in item
            assert "evidence_status" in item
            assert "explanation" in item


class TestGapDocumentation:
    """Kiểm tra rằng các giới hạn hiện tại được ghi nhận đúng."""

    def test_refers_to_builder_and_context_priority(self):
        """Internal contract reference takes priority over hierarchy and adjacency."""
        parent = "Điều 1. Nội dung"
        child = "Theo Điều 1 của hợp đồng"
        source = parent + "\n" + child
        clauses = [
            SegmentedClause("cl_0001", parent, 0, len(parent), ClauseStructure(1, "1", None)),
            SegmentedClause("cl_0002", child, len(parent) + 1, len(source),
                            ClauseStructure(2, "1.1", "cl_0001")),
        ]
        built, _ = build_clause_graph(clauses, source)
        assert [(e.src, e.dst) for e in built.edges_of(ClauseEdgeType.REFERS_TO)] == [
            ("cl_0002", "cl_0001")]
        assert built.edges_of(ClauseEdgeType.NEXT)
        assert built.edges_of(ClauseEdgeType.PARENT_OF)
        masked_map = {"cl_0001": parent, "cl_0002": child}
        selected = resolve_context(built, "cl_0002", masked_map)
        assert [(r.clause_id, r.relation) for r in selected] == [("cl_0001", "REFERS_TO")]
        item = RiskItemIn("cl_0002", child, ["COMPENSATION_BENEFITS"])
        attached = attach_graph_context([item], built, masked_map)
        assert attached[0].related_clauses[0].relation == "REFERS_TO"

    def test_context_resolver_handles_no_refers_to(self):
        """A graph without internal references still supplies hierarchy context."""
        ctx = resolve_context(GRAPH, "cl_0002", MASKED)
        # cl_0002: PARENT_OF (cl_0001 là cha), NEXT (cl_0003 kế tiếp)
        relation_types = {c.relation for c in ctx}
        assert "REFERS_TO" not in relation_types  # chưa có REFERS_TO edge
        assert relation_types  # nhưng vẫn có context từ PARENT_OF / NEXT


def test_context_trace_contains_only_ids_and_counts():
    items = attach_graph_context(ITEMS_BASE, GRAPH, MASKED)
    traces = build_context_traces(items)
    assert traces[0]["target_clause_id"] == "cl_0001"
    assert traces[0]["context_chars"] == sum(len(r.masked_text) for r in items[0].related_clauses)
    assert traces[0]["included_in_risk_request"] is True
    assert all("masked_text" not in str(trace) for trace in traces)
    assert all(not trace["included_in_risk_request"]
               for trace in build_context_traces(items, included_in_risk_request=False))


def test_masked_map_keeps_ineligible_parent_without_original_text():
    from app.ai.clause_adapter import masked_items_from_segmentation
    from app.clause.segmenter import segment
    source = "Điều 1. Quy định chung:\n1.1 Người lao động thực hiện công việc theo Điều 1 của Hợp đồng này."
    masked = source.replace("Quy định", "XXXXXXXX")
    result = segment(source, masked, [])
    all_masked = build_masked_clause_map(result, masked)
    eligible = masked_items_from_segmentation(result, masked)
    assert len(all_masked) == len(result.clauses)
    assert len(eligible) < len(all_masked)
    assert "XXXXXXXX" in all_masked[result.clauses[0].clause_id]
    graph, _ = build_clause_graph(result.clauses, masked)
    child = next(c for c in result.clauses if c.structure.parent_clause_id)
    ctx = resolve_context(graph, child.clause_id, all_masked)
    assert any(c.clause_id == child.structure.parent_clause_id for c in ctx)
