from fastapi import FastAPI

from app.config import get_settings
from app.routers import ask

app = FastAPI(title="바다 건너 사장님 API", version="0.1.0")
app.include_router(ask.router)


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "keys": {
            "anthropic": bool(settings.anthropic_api_key),
            "koreaexim": bool(settings.koreaexim_api_key),
            "customs": bool(settings.customs_api_key),
        },
    }
