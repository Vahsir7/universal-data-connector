"""UI router — serves browser-based HTML pages for testing the API.

Provides a simple web interface with three tabs:
  /home/llm  — test the LLM assistant endpoint
  /home/data — explore data source queries
  /home/api  — API key management
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["UI"])

# Static HTML files live alongside the app code in app/ui/
UI_DIR = Path(__file__).resolve().parents[1] / "ui"
UI_LLM_PATH = UI_DIR / "llm.html"
UI_DATA_PATH = UI_DIR / "data.html"
UI_API_PATH = UI_DIR / "api.html"


def _render_file(path: Path) -> HTMLResponse:
    return HTMLResponse(content=path.read_text(encoding="utf-8"))


@router.get("/ui", response_class=HTMLResponse)
@router.get("/home", response_class=HTMLResponse)
def ui_home() -> HTMLResponse:
    return _render_file(UI_LLM_PATH)


@router.get("/home/llm", response_class=HTMLResponse)
def ui_home_llm() -> HTMLResponse:
    return _render_file(UI_LLM_PATH)


@router.get("/home/data", response_class=HTMLResponse)
def ui_home_data() -> HTMLResponse:
    return _render_file(UI_DATA_PATH)


@router.get("/home/api", response_class=HTMLResponse)
def ui_home_api() -> HTMLResponse:
    return _render_file(UI_API_PATH)
