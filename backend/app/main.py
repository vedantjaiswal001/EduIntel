"""FastAPI application factory for EduIntel."""
from __future__ import annotations

import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging("DEBUG" if settings.DEBUG else "INFO")
logger = get_logger("eduintel")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} API",
        version=__version__,
        description=(
            "AI-powered education intelligence & intervention platform. "
            "Combines ML risk prediction, explainability, NLP, RAG and analytics."
        ),
        docs_url="/docs",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info("request", extra={
            "method": request.method, "path": request.url.path,
            "status": response.status_code, "elapsed_ms": elapsed_ms})
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.on_event("startup")
    def on_startup() -> None:
        # Never log secrets; only non-sensitive configuration.
        logger.info("startup", extra={
            "environment": settings.ENVIRONMENT, "llm_provider": settings.LLM_PROVIDER,
            "embedding_model": settings.EMBEDDING_MODEL_NAME})

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built React SPA in production (single-service deploy).

    When FRONTEND_DIST is empty or missing (local dev), only a JSON root is
    served and the Vite dev server handles the SPA.
    """
    dist = settings.FRONTEND_DIST
    if not dist or not os.path.isdir(dist):
        @app.get("/", tags=["system"])
        def root():
            return {"service": settings.PROJECT_NAME, "version": __version__,
                    "docs": "/docs", "api": settings.API_PREFIX}
        return

    assets = os.path.join(dist, "assets")
    if os.path.isdir(assets):
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    index_file = os.path.join(dist, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api") or full_path in ("docs", "redoc"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = os.path.join(dist, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(index_file)  # SPA client-side routing


app = create_app()
