import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
REQUIRED_DATA_FILES = [
    BASE_DIR / "data" / "customers.json",
    BASE_DIR / "data" / "support_tickets.json",
    BASE_DIR / "data" / "analytics.json",
]


@router.get("/live", tags=["Health"])
def liveness():
    return {"status": "alive"}


@router.get("/ready", tags=["Health"])
def readiness():
    missing_files = [str(path) for path in REQUIRED_DATA_FILES if not path.exists()]
    if missing_files:
        logger.warning("Readiness check failed. Missing files: %s", missing_files)
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "missing_files": missing_files},
        )
    return {"status": "ready"}


@router.get("", tags=["Health"])
def health_summary():
    return readiness()
