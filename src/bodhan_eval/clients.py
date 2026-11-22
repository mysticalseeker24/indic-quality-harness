"""Clients for Bodhan models and the judge LLM.

Every call goes through the same path:

    cache lookup -> budget reservation -> concurrency slot -> HTTP with retries -> cache write

Bodhan endpoints (https://console.bodhan.ai/api-docs/):
  POST /translate                 indic-translate      (no model field; target_language only)
  POST /transliterate             indic-transliterate
  POST /v1/audio/speech           indic-speak          (WAV PCM16 24 kHz mono)
  POST /v1/audio/transcriptions   indic-transcribe     (<= 30 s of audio per request)

The LLM is any OpenAI-compatible chat endpoint (LLM_BASE_URL / LLM_MODEL / LLM_API_KEY).
It is only ever asked to *read* and *classify*; it never produces Indian-language text.
"""

from __future__ import annotations

import io
import json
import logging
import random
import re
import threading
import time
import wave
from typing import Any

import requests

from .budget import Budget, BudgetExceeded
from .cache import Cache, bytes_hash
from .config import Settings, defaults

log = logging.getLogger("bodhan_eval.clients")

TRANSLATE_MODEL = "indic-translate"
TRANSLITERATE_MODEL = "indic-transliterate"
SPEAK_MODEL = "indic-speak"
TRANSCRIBE_MODEL = "indic-transcribe"


class ServiceUnavailable(RuntimeError):
    """A model cannot be called (no key configured). Checks that need it skip themselves."""


class BodhanError(RuntimeError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"HTTP {status} {code}: {message}")
        self.status = status
        self.code = code


class _Retryable(Exception):
    def __init__(self, msg: str, retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


def _retry(fn, attempts: int, what: str):
    for i in range(attempts):
        try:
            return fn()
        except _Retryable as e:
            if i == attempts - 1:
                raise BodhanError(0, "retries_exhausted", f"{what}: {e}") from e
            wait = e.retry_after if e.retry_after else min(30.0, 1.5 * 2**i) * (0.5 + random.random() / 2)
            log.warning("%s failed (%s); retry %d/%d in %.1fs", what, e, i + 1, attempts - 1, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")


def wav_duration_s(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data)) as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError):
        return 30.0  # unknown container: assume the per-request maximum for budgeting


class BodhanClient:
    def __init__(self, settings: Settings, cache: Cache, budget: Budget):
        self.s = settings
        self.cache = cache
        self.budget = budget
        self.costs = defaults()["costs_inr"]
        n = max(1, settings.concurrency)
        self._slots = {svc: threading.BoundedSemaphore(n) for svc in ("translate", "speak", "transcribe")}

    # ---- plumbing -------------------------------------------------------
    def _key_for(self, service: str) -> str:
        key = {"translate": self.s.translate_key, "speak": self.s.speak_key, "transcribe": self.s.transcribe_key}[
            service
        ]
        if not key:
            env = {
                "translate": "BODHAN_TRANSLATE_KEY",
                "speak": "BODHAN_SPEAK_KEY",
                "transcribe": "BODHAN_TRANSCRIBE_KEY",
            }[service]
            raise ServiceUnavailable(f"{env} is not set")
        return key

    def available(self, service: str) -> bool:
        try:
            self._key_for(service)
            return True
        except ServiceUnavailable:
            return False

    def _post(
        self, service: str, path: str, *, json_body: dict | None = None, files=None, data=None
    ) -> requests.Response:
        url = f"{self.s.bodhan_base_url}{path}"
        headers = {"Authorization": f"Bearer {self._key_for(service)}"}

        def once() -> requests.Response:
            try:
                r = requests.post(
                    url, headers=headers, json=json_body, files=files, data=data, timeout=self.s.request_timeout_s
                )
            except (requests.ConnectionError, requests.Timeout) as e:
                raise _Retryable(str(e)) from e
            if r.status_code == 429 or r.status_code >= 500:
                ra = r.headers.get("retry-after")
                raise _Retryable(
                    f"HTTP {r.status_code}", float(ra) if ra and ra.replace(".", "", 1).isdigit() else None
                )
            if r.status_code >= 400:
                try:
                    err = r.json().get("error", {})
                except ValueError:
                    err = {}
                raise BodhanError(
                    r.status_code, str(err.get("code", r.status_code)), str(err.get("message", r.text[:300]))
                )
            return r

        with self._slots[service]:
            return _retry(once, self.s.max_retries, f"{service} {path}")

    def _cached(self, service: str, kind: str, model: str, params: dict, payload: Any, estimate: float, call):
        key = self.cache.key(kind, model, params, payload)
        hit = self.cache.get(key)
        if hit is not None:
            value, cost = hit
            self.budget.record_cache_hit(service, cost)
            return value, True
        self._key_for(service)  # fail fast without reserving budget
        self.budget.reserve(service, estimate)
        try:
            value, cost = call()
        except BaseException:
            self.budget.release(estimate)
            raise
        self.budget.settle(service, estimate, cost)
        self.cache.put(key, kind, value, cost)
        return value, False

    # ---- translation ------------------------------------------------------
    def translate(self, text: str, target_language: str) -> dict:
        """Returns {"translation", "truncated", "cached"}. Splits and retries on 413."""
        estimate = max(32, len(text)) * 1.5 * self.costs["translate_per_output_token"]

        def call():
            r = self._post("translate", "/translate", json_body={"text": text, "target_language": target_language})
            body = r.json()
            tokens = int((body.get("usage") or {}).get("completion_tokens", 0))
            value = {"translation": body.get("translation", ""), "truncated": bool(body.get("truncated", False))}
            return value, tokens * self.costs["translate_per_output_token"]

        try:
            value, cached = self._cached(
                "translate", "translate", TRANSLATE_MODEL, {"target_language": target_language}, text, estimate, call
            )
        except BodhanError as e:
            if e.status == 413 and len(text) > 200:
                return self._translate_in_parts(text, target_language)
            raise
        return {**value, "cached": cached}

    def _translate_in_parts(self, text: str, target_language: str) -> dict:
        parts = re.split(r"(\n\s*\n)", text)  # keep blank-line separators
        if len(parts) == 1:
            mid = len(text) // 2
            cut = text.rfind(". ", 0, mid)
            cut = cut + 2 if cut > 0 else mid
            parts = [text[:cut], text[cut:]]
        out, truncated, cached = [], False, True
        for p in parts:
            if not p.strip():
                out.append(p)
                continue
            r = self.translate(p, target_language)
            out.append(r["translation"])
            truncated |= r["truncated"]
            cached &= r["cached"]
        return {"translation": "".join(out), "truncated": truncated, "cached": cached}

    def transliterate(self, text: str, language: str) -> str:
        estimate = max(16, len(text)) * 2 * self.costs["translate_per_output_token"]

        def call():
            r = self._post(
                "translate", "/transliterate", json_body={"text": text, "language": language, "script": "native"}
            )
            body = r.json()
            tokens = int((body.get("usage") or {}).get("completion_tokens", 0))
            return body.get("transliteration", ""), tokens * self.costs["translate_per_output_token"]

        value, _ = self._cached(
            "translate", "transliterate", TRANSLITERATE_MODEL, {"language": language}, text, estimate, call
        )
        return value

    # ---- speech -----------------------------------------------------------
    def speak(self, text: str, lang: str, voice: str, style: str | None = None) -> bytes:
        instructions = {"lang": lang}
        if style:
            instructions["style"] = style
        cost = len(text) * self.costs["speak_per_char"]

        def call():
            body = {
                "model": SPEAK_MODEL,
                "input": text,
                "voice": voice,
                "instructions": json.dumps(instructions, ensure_ascii=False),
            }
            r = self._post("speak", "/v1/audio/speech", json_body=body)
            digest = self.cache.put_blob(r.content, ".wav")
            return {"blob": digest}, cost

        value, _ = self._cached(
            "speak", "speak", SPEAK_MODEL, {"voice": voice, "instructions": instructions}, text, cost, call
        )
        return self.cache.blob_path(value["blob"]).read_bytes()

    def transcribe(self, wav_bytes: bytes, language: str) -> str:
        seconds = wav_duration_s(wav_bytes)
        cost = seconds * self.costs["transcribe_per_second"]

        def call():
            files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
            r = self._post(
                "transcribe",
                "/v1/audio/transcriptions",
                files=files,
                data={"model": TRANSCRIBE_MODEL, "language": language},
            )
            return r.json().get("text", ""), cost

        value, _ = self._cached(
            "transcribe", "transcribe", TRANSCRIBE_MODEL, {"language": language}, bytes_hash(wav_bytes), cost, call
        )
        return value


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

_INDIC_RANGE = re.compile(r"[ऀ-෿؀-ۿꯀ-꯿᱐-᱿]+")


def strip_indic(text: str) -> str:
    """Remove any Indian-script characters from LLM-written prose (belt and braces for the 'LLM never writes Indic' rule)."""
    return _INDIC_RANGE.sub("[…]", text)


def parse_json_object(text: str) -> dict | None:
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(t[start : end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


class LLMClient:
    def __init__(self, settings: Settings, cache: Cache, budget: Budget, inr_per_1k_tokens: float = 0.0):
        self.s = settings
        self.cache = cache
        self.budget = budget
        self.price = inr_per_1k_tokens
        self._json_mode = True
        self._client = None
        self._slot = threading.BoundedSemaphore(max(1, settings.concurrency))
        if self.available():
            from openai import OpenAI

            self._client = OpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                max_retries=settings.max_retries,
                timeout=settings.request_timeout_s,
            )

    def available(self) -> bool:
        return bool(self.s.llm_model and self.s.llm_api_key)

    @property
    def model(self) -> str:
        return self.s.llm_model or "none"

    def chat_json(self, messages: list[dict], *, max_tokens: int = 1500) -> dict | None:
        """Temperature-0 chat call returning a parsed JSON object (or None if unparseable). Cached by exact input."""
        if not self.available():
            raise ServiceUnavailable("LLM_MODEL / LLM_API_KEY are not set")
        params = {"temperature": 0, "max_tokens": max_tokens}
        key = self.cache.key("llm", self.model, params, messages)
        hit = self.cache.get(key)
        if hit is not None:
            value, cost = hit
            self.budget.record_cache_hit("llm", cost)
            self.budget.add_llm_tokens(value.get("prompt_tokens", 0), value.get("completion_tokens", 0))
            return parse_json_object(value["text"])
        estimate = self.price * (sum(len(m["content"]) for m in messages) / 3 + max_tokens) / 1000
        self.budget.reserve("llm", estimate)
        try:
            with self._slot:
                text, usage = self._call(messages, params)
        except BaseException:
            self.budget.release(estimate)
            raise
        cost = self.price * (usage[0] + usage[1]) / 1000
        self.budget.settle("llm", estimate, cost)
        self.budget.add_llm_tokens(*usage)
        self.cache.put(key, "llm", {"text": text, "prompt_tokens": usage[0], "completion_tokens": usage[1]}, cost)
        return parse_json_object(text)

    def _call(self, messages: list[dict], params: dict) -> tuple[str, tuple[int, int]]:
        if self._client is None:
            raise ServiceUnavailable("LLM not configured (LLM_MODEL / LLM_API_KEY)")
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": params["temperature"],
            "max_tokens": params["max_tokens"],
        }
        if self._json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as e:  # some providers reject response_format: fall back to plain text + JSON parsing
            msg = str(e).lower()
            if self._json_mode and ("response_format" in msg or "json" in msg):
                log.info("LLM provider rejected response_format; falling back to plain JSON prompting")
                self._json_mode = False
                kwargs.pop("response_format", None)
                resp = self._client.chat.completions.create(**kwargs)
            else:
                raise
        text = resp.choices[0].message.content or ""
        u = getattr(resp, "usage", None)
        usage = (int(getattr(u, "prompt_tokens", 0) or 0), int(getattr(u, "completion_tokens", 0) or 0))
        return text, usage


__all__ = [
    "BodhanClient",
    "LLMClient",
    "ServiceUnavailable",
    "BodhanError",
    "BudgetExceeded",
    "strip_indic",
    "parse_json_object",
    "wav_duration_s",
]
