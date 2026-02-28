from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.database import init_db
from app.core.logging import log_event, setup_logging
from app.core.request_context import set_request_id

app = FastAPI(title="InterviewSim Python Brain", version="0.1.0")
setup_logging()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    set_request_id(request_id)
    started = perf_counter()
    log_event(
        "http.request.start",
        method=request.method,
        path=request.url.path,
        query=str(request.url.query),
    )
    try:
        response = await call_next(request)
        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        log_event(
            "http.request.end",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
    except Exception as exc:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        log_event(
            "http.request.error",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            error=str(exc),
        )
        raise

@app.on_event("startup")
def on_startup() -> None:
    init_db()
    log_event("app.startup.ready")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


project_root = Path(__file__).resolve().parents[3]
frontend_dir = project_root / "frontend" / "web-chat"
if frontend_dir.exists():
    app.mount("/web", StaticFiles(directory=str(frontend_dir), html=True), name="web")


@app.get("/")
def root():
    if frontend_dir.exists():
        return RedirectResponse(url="/web/", status_code=307)
    return {"message": "InterviewSim backend is running"}
