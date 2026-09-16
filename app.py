import os
from nicegui import ui, app
from fastapi import Response

from config import settings
from utils.logging_config import setup_logging
from ui.theme import apply_theme
from core.db import init_db

# Direct imports of the render functions — no package-level indirection
from ui.pages.home import render as render_home
from ui.pages.results import render as render_results


setup_logging(settings.LOG_LEVEL)
app.add_static_files("/assets", "assets")

apply_theme()  # register shared CSS before any page is created


@app.get("/healthz")
def healthz():
    return Response(content="ok", media_type="text/plain")


@ui.page("/")
def index():
    render_home()


@ui.page("/results")
def results_page():
    render_results()


if __name__ in {"__main__", "__mp_main__"}:
    try:
        init_db()
    except Exception as e:
        print(f"[warn] DB init failed: {e}")

    ui.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        title="DPR-Matrix",
        favicon="📋",
        reload=False,
        show=False,
        storage_secret=settings.STORAGE_SECRET,
    )
