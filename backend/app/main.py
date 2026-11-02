"""Development sample API; demo/eval fail closed until real stages are integrated."""
import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.core.config import load_settings, validate_for_env
from app.ops.metadata_db import init_db
from app.ops.quota import DailyQuota
from app.ops.rate_limit import SlidingWindowLimiter
from app.session.cleanup import CleanupScheduler
from app.session.lock import ProcessingLease
from app.session.orchestrator import Orchestrator
from app.session.store import InMemorySessionStore

settings = load_settings()
validate_for_env(settings)
if settings.APP_ENV != "dev":
    raise RuntimeError("Pipeline chưa tích hợp; không thể chạy sample trong demo/eval")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = init_db(settings.OPS_DB_PATH)
    app.state.settings = settings
    app.state.db = db
    app.state.store = InMemorySessionStore(db)
    app.state.lease = ProcessingLease()
    app.state.orchestrator = Orchestrator(app.state.store, app.state.lease)
    app.state.quota = DailyQuota(db, settings.DAILY_LLM_CALL_QUOTA, settings.SESSION_CALL_RESERVE)
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
    return {"message": "AI Contract Risk Analyzer API (dev sample only)"}
