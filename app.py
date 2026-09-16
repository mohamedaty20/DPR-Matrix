import os
from nicegui import ui, app
from fastapi import Response

from config import settings
from utils.logging_config import setup_logging
from ui.theme import apply_theme
# ...

apply_theme()   # <-- MUST be before page decorators

@ui.page("/")
def index():
    home.render()

@ui.page("/results")
def results_page():
    results.render()

apply_theme()

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
