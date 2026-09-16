"""Gemini client — hard timeouts, fast fallback, visible model attempts."""
from __future__ import annotations
import logging
import time

import google.generativeai as genai

from config import settings
from core.errors import GeminiError

log = logging.getLogger("dpr.gemini")

genai.configure(api_key=settings.GEMINI_API_KEY)

# Try the configured model first, then the fallbacks.
_MODELS = [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]

# Hard cap per request — no more 1-hour hangs.
_TIMEOUT_SECONDS = 60
_MAX_ATTEMPTS_PER_MODEL = 1


def _list_available_models() -> list[str]:
    """Ask Google which models this API key can actually use. Never raises."""
    try:
        names = []
        for m in genai.list_models():
            if "generateContent" in getattr(m, "supported_generation_methods", []):
                names.append(m.name.replace("models/", ""))
        return names
    except Exception as e:
        log.warning("Could not list models: %s", e)
        return []


def _candidate_models() -> list[str]:
    """Return models to try in order — validated against the live list if possible."""
    available = _list_available_models()

    # If we can't list models (offline, network issue), just use the chain as-is.
    if not available:
        log.info("Model list unavailable; using configured chain: %s", _MODELS)
        return _MODELS

    log.info("Models available to this key: %s", available)

    chain = []
    for wanted in _MODELS:
        if wanted in available:
            chain.append(wanted)
            log.info("Using configured model: %s", wanted)
        else:
            log.warning("Configured model '%s' not available to this key", wanted)

    # If none of the configured models work, pick the best available fallback.
    if not chain:
        for preferred in (
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro",
        ):
            if preferred in available:
                chain.append(preferred)
                log.warning("Falling back to available model: %s", preferred)
                break

    if not chain:
        raise GeminiError(
            f"No usable Gemini model. Available: {available[:10]}. "
            f"Configured: {_MODELS}"
        )
    return chain


def _call_with_timeout(model_name: str, build_request):
    """Invoke generate_content with a hard timeout via request_options."""
    model = genai.GenerativeModel(model_name)
    for attempt in range(1, _MAX_ATTEMPTS_PER_MODEL + 1):
        try:
            log.info("→ %s (attempt %d)", model_name, attempt)
            t0 = time.time()
            resp = build_request(model)
            log.info("← %s returned in %.1fs", model_name, time.time() - t0)
            return resp.text
        except Exception as e:
            msg = str(e)
            # 404/400 on model ID → don't retry this model.
            if "404" in msg or "not found" in msg.lower() or "not supported" in msg.lower():
                log.warning("Model %s rejected: %s", model_name, msg[:200])
                raise
            if attempt >= _MAX_ATTEMPTS_PER_MODEL:
                log.warning("Model %s failed: %s", model_name, msg[:200])
                raise
            log.warning("Retrying %s after error: %s", model_name, msg[:200])
            time.sleep(2)
    raise GeminiError(f"Model {model_name} exhausted attempts")


def generate_text(prompt: str, json_mode: bool = False) -> str:
    last_err: Exception | None = None
    for name in _candidate_models():
        try:
            def _build(model):
                cfg = {"response_mime_type": "application/json"} if json_mode else {}
                return model.generate_content(
                    prompt,
                    generation_config=cfg,
                    request_options={"timeout": _TIMEOUT_SECONDS},
                )
            return _call_with_timeout(name, _build)
        except Exception as e:
            last_err = e
            continue
    raise GeminiError(f"All Gemini models failed. Last error: {last_err}")


def describe_image(image_bytes: bytes, mime: str, prompt: str) -> str:
    last_err: Exception | None = None
    for name in _candidate_models():
        try:
            def _build(model):
                return model.generate_content(
                    [prompt, {"mime_type": mime, "data": image_bytes}],
                    request_options={"timeout": _TIMEOUT_SECONDS},
                )
            return _call_with_timeout(name, _build)
        except Exception as e:
            last_err = e
            continue
    raise GeminiError(f"All Gemini models failed for image. Last: {last_err}")
