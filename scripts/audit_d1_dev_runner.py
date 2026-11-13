"""Exercise the injected Dev runner on four D1 sources with fake providers.

This tests the assembly path and privacy/offset invariants. Fake risk outputs
are structural fixtures and must not be interpreted as M2 performance.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from app.ai.provider import InMemoryLedger, LLMResponse
from app.core.enums import Role, SessionStatus
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.privacy.masker import mask
from app.risk.taxonomy import severity_for_labels
from app.session.lock import ProcessingLease
from app.session.orchestrator import Orchestrator
from app.session.pipeline_runner import make_pipeline_runner
from app.session.store import InMemorySessionStore


class LocalProvider:
    def __init__(self, kind: str):
        self.kind = kind
        self.requests = []

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        request = json.loads(messages[1]["content"])
        self.requests.append(request)
        if self.kind == "clause":
            items = [{"clause_id": row["clause_id"],
                      "clause_labels": ["COMPENSATION_BENEFITS"]}
                     for row in request["items"]]
            result = {"items": items}
        else:
            items = []
            for row in request["items"]:
                ids = row["candidate_ids"]
                if ids:
                    items.append({
                        "clause_id": row["clause_id"],
                        "basis_type": "AMBIGUOUS",
                        "risk_labels": ["UNILATERAL_CHANGE"],
                        "citation_ids": [ids[0]],
                        "evidence_status": "SUPPORTED",
                        "explanation": "Điều khoản cần làm rõ cách áp dụng giữa hai bên.",
                    })
            result = {"schema_version": "risk_output_v2", "items": items}
        return LLMResponse(result, model_id)


def audit(data_root: Path, corpus_root: Path) -> dict:
    corpus = load_corpus(corpus_root)
    retriever = BaselineRetriever(corpus, final_k=8, seed_k=3)
    restricted = data_root / "data/intake/restricted"
    total_citations = valid_citations = total_quotes = valid_quotes = 0
    total_risk_basis = valid_severity = total_severity = 0
    request_count = 0
    result_versions = {}
    for i in range(1, 5):
        doc = f"HDLD{i:03}"
        source_path = restricted / "D1_m1_runtime_predictions_v01" / f"{doc}.canonical_nfc.txt"
        geometry_path = restricted / "D1_m1_gold_v01" / f"{doc}.gold_segmentation.json"
        raw = source_path.read_bytes()
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
        if hashlib.sha256(raw).hexdigest() != geometry["source_sha256"]:
            raise ValueError("D1 source hash mismatch")
        source = raw.decode("utf-8")
        masked = mask(source)
        store, lease = InMemorySessionStore(), ProcessingLease()
        session = store.create(Role.EMPLOYEE)
        if lease.try_acquire(session.session_id) != session.session_id:
            raise ValueError("Dev session lease unavailable")
        clause, risk = LocalProvider("clause"), LocalProvider("risk")
        cfg = SimpleNamespace(GEMINI_MODEL_ID="local-structural-fixture",
                              CLAUSE_BATCH_SIZE=20, RISK_BATCH_SIZE=6,
                              LLM_PARALLELISM=1, LLM_TIMEOUT_SECONDS=5,
                              LLM_AUTO_RETRY=0, CLAUSE_GRAPH_MAX_RELATED=3,
                              CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000)
        runner = make_pipeline_runner(source, clause, risk, {}, InMemoryLedger(),
                                      cfg, corpus=corpus, retriever=retriever)
        asyncio.run(Orchestrator(store, lease, pipeline_runner=runner).run(session))
        if session.status != SessionStatus.COMPLETED:
            raise ValueError("D1 Dev runner did not complete")
        result = session.result
        result_versions[doc] = result["schema_version"]
        request_count += len(clause.requests) + len(risk.requests)
        for request in clause.requests + risk.requests:
            payload = json.dumps(request, ensure_ascii=False)
            for pii in masked.pii_spans:
                token = source[pii.start:pii.end]
                if len(token) >= 8 and token in payload:
                    raise ValueError("canonical PII reached a provider request")
        for row in result["risk_records"]:
            total_quotes += 1
            valid_quotes += source[row["start_char"]:row["end_char"]] == row["quote"]
            total_risk_basis += 1
            if not row["risk_basis"] or len(row["risk_basis"]) != len(row["risk_labels"]):
                raise ValueError("risk_basis missing or mismatched")
            expected = severity_for_labels(row["risk_labels"],
                                           row["risk_basis"][0]["basis_type"],
                                           "EMPLOYEE")
            total_severity += expected is not None
            valid_severity += row["severity"] == (expected.value if expected else None)
            for cid in row["citation_ids"]:
                total_citations += 1
                valid_citations += cid in {p.citation_id for p in corpus.provisions}
    return {
        "status": "DEV_STRUCTURAL_FAKE_PROVIDER_NOT_PRODUCT_M2",
        "documents": 4,
        "result_versions": result_versions,
        "provider_request_batches": request_count,
        "risk_basis_records": total_risk_basis,
        "m3a_technical_citation_validity": {
            "valid": valid_citations, "total": total_citations,
            "rate": valid_citations / total_citations if total_citations else None,
        },
        "m4_technical_exact_quote": {
            "valid": valid_quotes, "total": total_quotes,
            "rate": valid_quotes / total_quotes if total_quotes else None,
        },
        "severity_from_taxonomy": {
            "valid": valid_severity, "total": total_severity,
        },
        "limitations": [
            "make_pipeline_runner returns dev_pipeline_result_v1, not product final_result_v1.",
            "The providers emit synthetic labels and citations; no semantic M2/M3a accuracy is measured.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.data_root, args.corpus_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"documents": result["documents"],
                      "result_versions": sorted(set(result["result_versions"].values())),
                      "m3a_valid": result["m3a_technical_citation_validity"]["valid"],
                      "m4_valid": result["m4_technical_exact_quote"]["valid"]}))


if __name__ == "__main__":
    main()
