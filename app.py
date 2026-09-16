import os
import sys

def _log(msg: str) -> None:
    print(f"[boot] {msg}", flush=True)

_log("python starting")
_log(f"port from env: {os.environ.get('PORT', '(unset)')}")

# ---------------------------------------------------------------------------
# Import phase — log each step so a crash here is pinpointable
# ---------------------------------------------------------------------------
try:
    from nicegui import ui, app
    _log("imported nicegui")
except Exception as e:
    _log(f"FATAL: nicegui import failed: {type(e).__name__}: {e}")
    sys.exit(1)

try:
    from fastapi import Response
    from config import settings
    _log(f"config loaded · model={settings.GEMINI_MODEL} · "
         f"turso={settings.TURSO_URL[:40]}…")
except Exception as e:
    _log(f"FATAL: config import failed: {type(e).__name__}: {e}")
    sys.exit(1)

try:
    from utils.logging_config import setup_logging
    from ui.theme import apply_theme
    from ui.pages.home import render as render_home
    from ui.pages.results import render as render_results
    from ui.pages.history import render as render_history
    _log("imported ui + pages")
except Exception as e:
    _log(f"FATAL: ui import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from core.db import init_db
    _log("imported core.db")
except Exception as e:
    _log(f"FATAL: core.db import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


setup_logging(settings.LOG_LEVEL)
app.add_static_files("/assets", "assets")
apply_theme()
_log("theme applied")


@app.get("/test-gemini")
def test_gemini():
    """Diagnostic — calls Gemini REST directly with hard timeout."""
    import httpx, time
    from config import settings

    model = settings.GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": "Reply with the single word: OK"}]}]}
    headers = {"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY}

    t0 = time.time()
    try:
        r = httpx.post(url, json=body, headers=headers, timeout=30.0)
        elapsed = time.time() - t0
        return Response(
            content=(
                f"model: {model}\n"
                f"elapsed: {elapsed:.2f}s\n"
                f"status: {r.status_code}\n\n"
                f"body:\n{r.text[:1500]}"
            ),
            media_type="text/plain",
        )
    except Exception as e:
        return Response(
            content=f"FAILED after {time.time()-t0:.2f}s\n{type(e).__name__}: {e}",
            media_type="text/plain",
        )
@app.get("/test-gemini")
def test_gemini():
    """Bare-metal Gemini test with hard 30s timeout."""
    import concurrent.futures
    from config import settings
    import google.generativeai as genai

    def _run():
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # 1) What models does this key see?
        try:
            available = [
                m.name.replace("models/", "")
                for m in genai.list_models()
                if "generateContent" in getattr(m, "supported_generation_methods", [])
            ]
        except Exception as e:
            return f"LIST_MODELS_FAILED: {type(e).__name__}: {e}"

        # 2) Try each configured model with a hard 30s timeout
        tried = []
        for name in [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]:
            tried.append(name)
            if name not in available:
                tried[-1] += " (NOT AVAILABLE)"
                continue
            try:
                model = genai.GenerativeModel(name)
                resp = model.generate_content(
                    "Reply with exactly: OK",
                    request_options={"timeout": 30},
                )
                return (
                    f"SUCCESS with {name}\n"
                    f"Response: {resp.text!r}\n\n"
                    f"Available models: {available}"
                )
            except Exception as e:
                return (
                    f"MODEL_FAILED: {name}\n"
                    f"{type(e).__name__}: {e}\n\n"
                    f"Available models: {available}\n"
                    f"Tried: {tried}"
                )
        return f"NO USABLE MODEL\nAvailable: {available}\nTried: {tried}"

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run)
            return Response(content=future.result(timeout=40), media_type="text/plain")
    except concurrent.futures.TimeoutError:
        return Response(content="HARD TIMEOUT after 40s — Gemini is unreachable or SDK is stuck", media_type="text/plain")
    except Exception as e:
        return Response(content=f"UNEXPECTED: {type(e).__name__}: {e}", media_type="text/plain")


@ui.page("/")
def index():
    render_home()


@ui.page("/results")
def results_page():
    render_results()


@ui.page("/history")
def history_page():
    render_history()


_log("routes registered")


# ---------------------------------------------------------------------------
# Boot sequence
# ---------------------------------------------------------------------------
def _safe_init_db() -> None:
    """Try to init the DB. Never raises — Turso being down must not kill boot."""
    try:
        _log("calling init_db() …")
        init_db()
        _log("init_db() done")
    except Exception as e:
        _log(f"WARN: init_db failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ in {"__main__", "__mp_main__"}:
    _safe_init_db()

    _log("about to call ui.run()")
    try:
        ui.run(
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            title="DPR-Matrix",
            favicon="📋",
            reload=False,
            show=False,
            storage_secret=settings.STORAGE_SECRET,
        )
        _log("ui.run() returned cleanly")
    except Exception as e:
        _log(f"FATAL: ui.run() crashed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
