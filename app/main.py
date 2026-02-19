"""Application entry point, creates the FastAPI app, registers middleware, exception handlers, and all sub-routers."""

import logging
import time
from contextlib import asynccontextmanager

from app.routers import assistant, auth, data, export, health, ui, webhooks
from app.utils.logging import configure_logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


configure_logging()
logger = logging.getLogger(__name__)


# Lifespan context manager – runs startup/shutdown logic
@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting Universal Data Connector...")
    start_time = time.time()
    yield
    elapsed_time = time.time() - start_time
    logger.info("Universal Data Connector stopped. Total uptime: %.2f seconds.", elapsed_time)

app = FastAPI(
    title="Universal Data Connector",
    version="1.0.0",
    description="Unified connector API for LLM function/tool calling",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Data", "description": "LLM-callable data access endpoints"},
        {"name": "Health", "description": "Service liveness and readiness checks"},
        {"name": "Assistant", "description": "Direct GPT/Claude function-calling endpoint"},
        {"name": "Auth", "description": "API key lifecycle and admin operations"},
        {"name": "Webhooks", "description": "Inbound real-time update notifications"},
        {"name": "Export", "description": "Download filtered data as CSV or Excel"},
        {"name": "UI", "description": "Browser-based API test interface"},
    ],
)

# Request-logging middleware – logs method, path, status and duration
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info("%s %s -> %s (%.2fms)", request.method, request.url.path, response.status_code, duration)
    return response

# Validation error handler – returns structured 422 JSON
@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid request parameters",
            "details": exc.errors()
        }
    })

# HTTP exception handler – normalises detail into error envelope
@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        message = detail.get("message", "Request failed")
        details = detail.get("details")
    else:
        code = "HTTP_ERROR"
        message = str(detail)
        details = None

    return JSONResponse(status_code=exc.status_code, content={
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    })

# Catch-all handler – prevents raw 500 tracebacks leaking to clients
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred"
        }
    })

# Register all sub-routers
app.include_router(health.router)
app.include_router(data.router)
app.include_router(assistant.router)
app.include_router(auth.router)
app.include_router(export.router)
app.include_router(webhooks.router)
app.include_router(ui.router)
