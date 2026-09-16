import time
import google.generativeai as genai
from config import settings
from core.errors import GeminiError

genai.configure(api_key=settings.GEMINI_API_KEY)

_MODELS = [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]
_model_cache = {}

def _model(name: str):
    if name not in _model_cache:
        _model_cache[name] = genai.GenerativeModel(name)
    return _model_cache[name]

def _with_fallback(fn):
    last_err = None
    for name in _MODELS:
        try:
            return fn(_model(name))
        except Exception as e:
            last_err = e
            if "404" in str(e) or "not found" in str(e).lower():
                continue
            time.sleep(1)
    raise GeminiError(f"All Gemini models failed. Last: {last_err}")

def generate_text(prompt: str, json_mode: bool = False) -> str:
    def call(model):
        cfg = {"response_mime_type": "application/json"} if json_mode else {}
        return model.generate_content(prompt, generation_config=cfg).text
    return _with_fallback(call)

def describe_image(image_bytes: bytes, mime: str, prompt: str) -> str:
    def call(model):
        return model.generate_content([
            prompt,
            {"mime_type": mime, "data": image_bytes},
        ]).text
    return _with_fallback(call)
