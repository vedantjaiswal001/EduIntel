"""Provider-agnostic LLM abstraction.

The rest of the application depends only on the `LLMProvider` interface, never
on a specific vendor SDK. Supported providers:
  * Gemini (google-generativeai)
  * OpenAI-compatible (any endpoint implementing /chat/completions)
  * Local fallback — no external call; used when no key/provider is available,
    so RAG and the analyst degrade gracefully to grounded, extractive output
    instead of failing.

`get_llm()` selects the provider from settings and reports `.available` so
callers can choose an offline path (e.g. rule-based feedback classification or
extractive summarisation) when generation is not available.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    pass


class LLMProvider(ABC):
    name: str = "base"
    available: bool = False

    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None) -> str:
        ...

    def generate_json(self, prompt: str, system: Optional[str] = None) -> dict:
        """Generate and parse a JSON object (tolerant of code fences/prose)."""
        raw = self.generate(prompt, system=system, temperature=0.0)
        return _extract_json(raw)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        self.available = False
        self._model = None
        if not settings.GEMINI_API_KEY:
            return
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._genai = genai
            self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.available = True
        except Exception as exc:  # pragma: no cover
            logger.warning("Gemini unavailable: %s", exc)

    def generate(self, prompt, system=None, temperature=None, max_tokens=None) -> str:
        if not self.available:
            raise LLMError("Gemini provider not available")
        full = f"{system}\n\n{prompt}" if system else prompt
        cfg = {
            "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
            "max_output_tokens": settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens,
        }
        # Hard wall-clock timeout on a DAEMON thread: the vendor SDK retries
        # internally, so we cap the whole call and never block process exit on a
        # runaway thread. On failure/timeout we mark the provider unavailable so
        # callers degrade to the offline path instantly.
        import threading

        box: dict = {}

        def _call() -> None:
            try:
                resp = self._model.generate_content(
                    full, generation_config=cfg, request_options={"timeout": 12}
                )
                box["text"] = (resp.text or "").strip()
            except Exception as exc:  # noqa: BLE001
                box["error"] = exc

        th = threading.Thread(target=_call, daemon=True)
        th.start()
        th.join(15)
        if "text" in box:
            return box["text"]
        self.available = False
        err = box.get("error", "timeout")
        logger.warning("Gemini call failed (%s); marking provider unavailable.", err)
        raise LLMError(str(err))


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        self.available = bool(settings.OPENAI_API_KEY)

    def generate(self, prompt, system=None, temperature=None, max_tokens=None) -> str:
        if not self.available:
            raise LLMError("OpenAI provider not available")
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
            "max_tokens": settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens,
        }
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{settings.OPENAI_BASE_URL}/chat/completions",
                            json=payload, headers=headers)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()


class LocalFallbackProvider(LLMProvider):
    """No external LLM. `available` is False so callers use offline paths."""

    name = "local"
    available = False

    def generate(self, prompt, system=None, temperature=None, max_tokens=None) -> str:
        raise LLMError("No LLM provider configured; use the offline path.")


@lru_cache
def get_llm() -> LLMProvider:
    provider = settings.LLM_PROVIDER
    if provider == "gemini":
        g = GeminiProvider()
        if g.available:
            return g
    elif provider == "openai":
        o = OpenAIProvider()
        if o.available:
            return o
    logger.info("LLM provider '%s' not available; using local fallback.", provider)
    return LocalFallbackProvider()


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    # strip ```json ... ``` fences
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = m.group(1) if m else text
    # else grab the first {...} block
    if not m:
        b = re.search(r"\{.*\}", candidate, re.DOTALL)
        candidate = b.group(0) if b else candidate
    try:
        return json.loads(candidate)
    except Exception:
        return {}
