from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.identity import router as identity_router
from app.api.opportunities import router as opportunities_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.scheduler.jobs import create_scheduler


settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    scheduler = create_scheduler(settings) if settings.scheduler_enabled else None
    if scheduler is not None:
        scheduler.start()
    logger.info(
        "application_started",
        app_name=settings.app_name,
        environment=settings.environment,
        crawler_interval=settings.crawler_interval,
        scheduler_keywords=settings.scheduler_keywords,
        scheduler_enabled=settings.scheduler_enabled,
    )
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        logger.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration = perf_counter() - started
        logger.exception(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            duration_seconds=round(duration, 4),
        )
        raise

    duration = perf_counter() - started
    logger.info(
        "http_request_finished",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=round(duration, 4),
    )
    return response


app.include_router(health_router)
app.include_router(identity_router)
app.include_router(opportunities_router)
