"""Session API. Pipeline thật (X-19) khi có provider; dev không có provider thì dùng fixture mẫu.

Chế độ:
  * demo/eval: luôn pipeline thật; `validate_for_env` fail-fast thiếu key/model/quota/reserve/salt; corpus phải
    APPROVED (loader từ chối DRAFT).
  * dev + (`DEV_LLM_PROVIDER=fake|local` hoặc có GEMINI_API_KEY + GEMINI_MODEL_ID): pipeline thật; corpus DRAFT
    được phép (allow_draft); thiếu corpus ⇒ chạy không retrieval (mọi rủi ro INSUFFICIENT_EVIDENCE).
  * dev còn lại: runner mẫu trả fixture `final_result_v1` (không phân tích file upload).
"""
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.ai.dev_fake_client import FAKE_MODEL_ID
from app.ai.factory import make_provider
from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.core.config import Settings, load_settings, validate_for_env
from app.domain.errors import LegalCorpusConflict
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.legal.data_graph import DataGraph
from app.ops.metadata_db import init_db
from app.ops.quota import DailyQuota
from app.ops.rate_limit import SlidingWindowLimiter
from app.ops.runlog import RunLogWriter
from app.ops.session_ledger import SessionLedger
from app.pipeline import PipelineDeps
from app.session.cleanup import CleanupScheduler
from app.session.lock import ProcessingLease
from app.session.orchestrator import Orchestrator, make_pipeline_runner
from app.session.store import InMemorySessionStore

log = logging.getLogger("app")
settings = load_settings()
validate_for_env(settings)

_ROOT = Path(__file__).resolve().parents[2]


def pipeline_enabled(cfg: Settings) -> bool:
    if cfg.APP_ENV != "dev":
        return True
    return cfg.DEV_LLM_PROVIDER in ("fake", "local") or bool(cfg.GEMINI_API_KEY and cfg.GEMINI_MODEL_ID)


def load_legal(cfg: Settings):
    """(corpus, retriever, data_graph). demo/eval: lỗi corpus ⇒ không khởi động (fail-fast)."""
    root = Path(cfg.LEGAL_CORPUS_DIR)
    root = root if root.is_absolute() else _ROOT / root
    allow_draft = cfg.APP_ENV == "dev"
    try:
        corpus = load_corpus(root, allow_draft=allow_draft)
    except LegalCorpusConflict:
        if cfg.APP_ENV != "dev":
            raise
        log.warning("legal corpus unavailable in dev; risks will be INSUFFICIENT_EVIDENCE")
        return None, None, None
    retriever = BaselineRetriever(corpus, final_k=cfg.RETRIEVAL_FINAL_K, seed_k=cfg.RETRIEVAL_SEED_K,
                                  allow_draft=allow_draft)
    graph = DataGraph(corpus, allow_draft=allow_draft) if cfg.DATA_GRAPH_ENABLED else None
    return corpus, retriever, graph


def build_runner(cfg: Settings, quota: DailyQuota, runlog: RunLogWriter):
    if not pipeline_enabled(cfg):
        return None
    provider = make_provider(cfg)
    run_cfg = cfg
    if cfg.APP_ENV == "dev" and cfg.DEV_LLM_PROVIDER == "fake" and not cfg.GEMINI_MODEL_ID:
        run_cfg = cfg.model_copy(update={"GEMINI_MODEL_ID": FAKE_MODEL_ID})
    corpus, retriever, graph = load_legal(cfg)

    def deps_for(session):
        return PipelineDeps(run_cfg, provider, SessionLedger(quota, runlog, session.session_id), corpus,
                            retriever, graph, cfg.APP_COMMIT)

    return make_pipeline_runner(deps_for)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = init_db(settings.OPS_DB_PATH)
    app.state.settings = settings
    app.state.db = db
    app.state.store = InMemorySessionStore(db)
    app.state.lease = ProcessingLease()
    app.state.quota = DailyQuota(db, settings.DAILY_LLM_CALL_QUOTA, settings.SESSION_CALL_RESERVE)
    runner = build_runner(settings, app.state.quota, RunLogWriter(db))
    app.state.pipeline_enabled = runner is not None
    app.state.orchestrator = Orchestrator(app.state.store, app.state.lease, runner)
    app.state.rate = SlidingWindowLimiter(db, settings.RATE_LIMIT_HMAC_SALT or secrets.token_hex(32),
                                         settings.RATE_LIMIT_UPLOADS, settings.RATE_LIMIT_WINDOW_SECONDS)
    app.state.cleanup = CleanupScheduler(app.state.orchestrator, settings.SESSION_TTL_MINUTES,
                                         settings.EXPIRED_TOMBSTONE_HOURS)
    cleanup_task = asyncio.create_task(app.state.cleanup.run())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        for sid in list(app.state.store.sessions):
            app.state.orchestrator.end(sid)
        db.close()


app = FastAPI(title="AI Contract Risk Analyzer API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(sessions_router)


@app.get("/")
def root():
    mode = "pipeline" if getattr(app.state, "pipeline_enabled", False) else "dev sample"
    return {"message": f"AI Contract Risk Analyzer API ({mode})"}
