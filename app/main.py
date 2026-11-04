import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.config import settings
from app.routers import applications, drafts, health, jobs, matches, resume, search


logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI Job Search Agent",
    version="0.1.0",
)
logger = logging.getLogger("app.requests")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(search.router)
app.include_router(jobs.router)
app.include_router(resume.router)
app.include_router(matches.router)
app.include_router(applications.router)
app.include_router(drafts.router)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            "http_request method=%s path=%s status_code=%s duration_ms=%s",
            request.method,
            request.url.path,
            status_code,
            elapsed_ms,
        )
