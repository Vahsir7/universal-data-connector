import logging
import time
from contextlib import asynccontextmanager

from app.routers import assistant, data, health
from app.utils.logging import configure_logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


configure_logging()
logger = logging.getLogger(__name__)


#lifespan of the application
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
    ],
)

#requesting logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info("%s %s -> %s (%.2fms)", request.method, request.url.path, response.status_code, duration)
    return response

# 3. Validation error handler (422)
@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid request parameters",
            "details": exc.errors()
        }
    })

# 4. HTTP exception handler (404, 503, etc.)
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

# 5. Catch-all unhandled exception handler (500)
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred"
        }
    })



app.include_router(health.router)
app.include_router(data.router)
app.include_router(assistant.router)
