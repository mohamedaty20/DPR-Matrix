"""Gemini client — direct REST via httpx. No SDK, no gRPC, hard timeouts.

Deterministic: temperature=0, topP=1, topK=1, seed=42 on every call.
"""
from __future__ import annotations

import base64
import json
import logging
import time

import httpx

from config import settings
from core.errors import GeminiError

log = logging.getLogger("dpr.gemini")

_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)


class _ModelNotFound(Exception):
    """Raised when a specific model ID returns 404 — try next, don't retry."""


def _models_chain() -> list[str]:
    return [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]


def _gen_config(json_mode: bool) -> dict:
    """Deterministic generation config. Do NOT increase temperature."""
    cfg: dict = {
        "temperature": 0.0,   # no creativity — extraction only
        "topP": 1.0,
        "topK": 1,
        "seed": 42,           # reproducible sampling
    }
    if json_mode:
        cfg["response_mime_type"] = "application/json"
    return cfg


def _call(model: str, parts: list[dict], json_mode: bool) -> str:
    url = f"{_API_BASE}/models/{model}:generateContent"
    body: dict = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": _gen_config(json_mode),
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.GEMINI_API_KEY,
    }

    print(f"[gemini] POST {model} (json={json_mode}, temp=0, seed=42) …",
          flush=True)
    t0 = time.time()
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(url, json=body, headers=headers)
    except httpx.TimeoutException as e:
        print(f"[gemini] TIMEOUT on {model}: {e}", flush=True)
        raise GeminiError(f"Timeout calling {model}: {e}") from e
    except httpx.RequestError as e:
        print(f"[gemini] NETWORK ERROR on {model}: {e}", flush=True)
        raise GeminiError(f"Network error calling {model}: {e}") from e

    print(f"[gemini] ← {model} status={r.status_code} in {time.time()-t0:.1f}s",
          flush=True)

    if r.status_code == 404:
        raise _ModelNotFound(f"Model '{model}' returned 404")

    if r.status_code >= 400:
        try:
            err = r.json().get("error", {})
            msg = err.get("message", r.text[:300])
        except Exception:
            msg = r.text[:300]
        print(f"[gemini] ERROR {r.status_code} on {model}: {msg[:200]}",
              flush=True)
        raise GeminiError(f"HTTP {r.status_code} on {model}: {msg}")

    try:
        data = r.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise GeminiError(f"No candidates: {json.dumps(data)[:300]}")
        out_parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in out_parts)
        if not text:
            raise GeminiError(f"Empty text: {json.dumps(data)[:300]}")
        return text
    except (KeyError, IndexError) as e:
        raise GeminiError(f"Malformed response: {json.dumps(data)[:300]}") from e


def generate_text(prompt: str, json_mode: bool = False) -> str:
    parts = [{"text": prompt}]
    last_err: Exception | None = None
    for m in _models_chain():
        try:
            return _call(m, parts, json_mode)
        except _ModelNotFound as e:
            print(f"[gemini] skip {m}: {e}", flush=True)
            last_err = e
            continue
        except Exception as e:
            print(f"[gemini] fail {m}: {type(e).__name__}: {e}", flush=True)
            last_err = e
            continue
    raise GeminiError(f"All models failed. Last: {last_err}")


def describe_image(image_bytes: bytes, mime: str, prompt: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": mime, "data": b64}},
    ]
    last_err: Exception | None = None
    for m in _models_chain():
        try:
            return _call(m, parts, json_mode=False)
        except _ModelNotFound as e:
            print(f"[gemini] skip {m}: {e}", flush=True)
            last_err = e
            continue
        except Exception as e:
            print(f"[gemini] fail {m}: {type(e).__name__}: {e}", flush=True)
            last_err = e
            continue
    raise GeminiError(f"All models failed for image. Last: {last_err}")
