"""Opt-in factory rejects unsupported uploads and binds approved local law."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.core.config import Settings
from app.core.enums import Role
from app.domain.errors import ValidationReject
from app.session.product_factory import make_product_runner_factory
from app.session.store import InMemorySessionStore

SOURCE = (
    "HỢP ĐỒNG LAO ĐỘNG\nĐiều 1. Công việc và tiền lương:\n"
    "Người lao động thực hiện công việc theo hợp đồng; "
    "công ty trả tiền lương và phụ cấp theo thỏa thuận của hai bên."
)
CORPUS = Path(__file__).resolve().parents[2] / "data/legal_corpus"


def test_factory_uses_bounded_pdf_source_and_approved_corpus(monkeypatch):
    import app.session.product_factory as module

    assert CORPUS.exists()
    monkeypatch.setattr(module, "extract_pdf", lambda source, *, max_pages: [SOURCE])
    cfg = Settings(GEMINI_MODEL_ID="fake-model", DEV_LLM_PROVIDER="local")
    factory = make_product_runner_factory(cfg, CORPUS,
                                          provider_factory=lambda _cfg: object())
    session = InMemorySessionStore().create(Role.EMPLOYEE)
    upload = SimpleNamespace(filename="synthetic.pdf", file_content=b"%PDF-test")
    runner = asyncio.run(factory(upload, session))
    assert callable(runner)
    upload.filename = "synthetic.docx"
    with pytest.raises(ValidationReject):
        asyncio.run(factory(upload, session))
