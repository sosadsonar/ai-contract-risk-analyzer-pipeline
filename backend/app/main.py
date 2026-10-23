"""Dev sample API; demo/eval cannot serve until the real pipeline is integrated."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.core.config import load_settings, validate_for_env
from app.session.mock import MockStore

settings = load_settings()
validate_for_env(settings)
if settings.APP_ENV != "dev":
    raise RuntimeError("Pipeline C-05/C-06 chưa tích hợp; không thể chạy mock trong demo/eval")

app = FastAPI(title="AI Contract Risk Analyzer API", version="0.1.0")
app.state.mock_store = MockStore(settings)
app.include_router(health_router)
app.include_router(sessions_router)


@app.get("/")
def root():
    return {"message": "AI Contract Risk Analyzer API (dev mock)"}
