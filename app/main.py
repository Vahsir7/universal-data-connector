import logging
import time
from contextlib import asynccontextmanager

from app.routers import health, data
from app.utils.logging import configure_logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


configure_logging()
logger = logging.getLogger(__name__)


#lifespan of the application
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Universal Data Connector...")
    start_time = time.time()
    yield
    elapsed_time = time.time() - start_time
    logger.info(f"Universal Data Connector stopped. Total uptime: {elapsed_time:.2f} seconds.")

app = FastAPI(title="Universal Data Connector", lifespan=lifespan)

#requesting logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    return response

# 3. Validation error handler (422)
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid request parameters",
            "details": exc.errors()
        }
    })

# 4. HTTP exception handler (404, 503, etc.)
@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={
        "error": {
            "code": exc.detail.get("code", "HTTP_ERROR"),
            "message": exc.detail.get("message", str(exc.detail))
        }
    })

# 5. Catch-all unhandled exception handler (500)
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred"
        }
    })



app.include_router(health.router)
app.include_router(data.router)
