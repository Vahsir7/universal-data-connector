from fastapi import FastAPI
from app.routers import health, data
from app.utils.logging import configure_logging
import logging
import time
from contextlib import contextmanager

configure_logging()
logger = logging.getLogger(__name__)


app = FastAPI(title="Universal Data Connector")

app.include_router(health.router)
app.include_router(data.router)
