from fastapi import FastAPI
from app.api.routes.contracts import router as contract_router

from app.api.routes.health import router as health_router
from app.core.upload_limits import UploadLimitsMiddleware

app = FastAPI(
    title="AI Contract Risk Analyzer API",
    version="0.1.0"
)

app.include_router(health_router)
app.add_middleware(UploadLimitsMiddleware)
app.include_router(contract_router)


@app.get("/")
def root():
    return {
        "message": "AI Contract Risk Analyzer API"
    }
