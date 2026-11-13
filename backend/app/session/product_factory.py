"""Opt-in product runner construction from a bounded, in-memory PDF upload."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.ai.factory import make_provider
from app.ai.provider import InMemoryLedger
from app.document.canonicalizer import canonicalize
from app.document.pdf_extractor import extract_pdf
from app.document.quality import run_quality_gates
from app.document.scope_precheck import precheck
from app.domain.errors import ValidationReject
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.session.pipeline_runner import make_pipeline_runner


def make_product_runner_factory(
    cfg, corpus_path: Path, *, provider_factory=make_provider,
    ledger_factory=InMemoryLedger,
):
    """Load approved law once; bind each validated source to an ephemeral runner."""
    corpus = load_corpus(corpus_path)
    retriever = BaselineRetriever(
        corpus, final_k=cfg.RETRIEVAL_FINAL_K, seed_k=cfg.RETRIEVAL_SEED_K)
    provider = provider_factory(cfg)

    async def from_upload(upload, session):
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            raise ValidationReject("UNSUPPORTED_FILE_TYPE")
        source = upload.file_content
        if source is None or not source.startswith(b"%PDF-"):
            raise ValidationReject("UNSUPPORTED_FILE_TYPE")
        pages = await asyncio.to_thread(extract_pdf, source, max_pages=cfg.MAX_PDF_PAGES)
        canonical = canonicalize(pages)
        run_quality_gates(canonical)
        if not precheck(canonical, cfg).accept:
            raise ValidationReject("NOT_LABOR_CONTRACT")
        del source, pages
        return make_pipeline_runner(
            canonical, provider, provider, {}, ledger_factory(), cfg,
            corpus=corpus, retriever=retriever,
        )

    return from_upload
