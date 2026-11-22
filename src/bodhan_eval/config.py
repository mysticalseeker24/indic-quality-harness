"""Settings, language registry and taxonomy.

Everything language- or category-specific lives in the JSON files under
``bodhan_eval/data`` so a new language or a new label vocabulary needs no code
change. Secrets come only from environment variables (or a local ``.env``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path


def _load_json(name: str) -> dict:
    return json.loads(resources.files("bodhan_eval.data").joinpath(name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def langs() -> dict:
    return _load_json("langs.json")


@lru_cache(maxsize=1)
def taxonomy() -> dict:
    return _load_json("taxonomy.json")


@lru_cache(maxsize=1)
def defaults() -> dict:
    return _load_json("defaults.json")


CATEGORIES: tuple[str, ...] = tuple(_load_json("taxonomy.json")["categories"])
TRANSLATION_CATEGORIES = tuple(
    c for c, v in _load_json("taxonomy.json")["categories"].items() if v["area"] == "translation"
)
SPEECH_CATEGORIES = tuple(c for c, v in _load_json("taxonomy.json")["categories"].items() if v["area"] == "speech")


def canonical_category(label_type: str | None) -> str | None:
    """Map a label's free-form ``type`` to a canonical category, or None if unknown."""
    if not label_type:
        return None
    key = label_type.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_or_")
    return taxonomy()["aliases"].get(key)


def canonical_severity(sev: str | None) -> str:
    if not sev:
        return "major"
    return taxonomy()["severity_aliases"].get(str(sev).strip().lower(), "major")


def category_group(cat: str) -> str:
    return taxonomy()["categories"].get(cat, {}).get("group", cat)


def category_area(cat: str) -> str:
    return taxonomy()["categories"].get(cat, {}).get("area", "translation")


@dataclass(frozen=True)
class LangInfo:
    code: str
    name: str
    script: str | None
    voices: tuple[str, ...]
    tts_lang: str
    asr_lang: str
    function_words: tuple[str, ...] = ()
    marker_chars: tuple[str, ...] = ()
    known: bool = True


def lang_info(code: str) -> LangInfo:
    """Look up a language. Unknown codes still work: checks that need script data skip themselves."""
    entry = langs()["languages"].get(code)
    if entry is None:
        return LangInfo(code=code, name=code, script=None, voices=(), tts_lang=code, asr_lang=code, known=False)
    return LangInfo(
        code=code,
        name=entry["name"],
        script=entry.get("script"),
        voices=tuple(entry.get("voices", [])),
        tts_lang=entry.get("tts_lang", code),
        asr_lang=entry.get("asr_lang", code),
        function_words=tuple(entry.get("function_words", [])),
        marker_chars=tuple(entry.get("marker_chars", [])),
    )


def same_script_languages(code: str) -> list[str]:
    info = lang_info(code)
    if not info.script:
        return []
    return sorted(c for c, v in langs()["languages"].items() if v.get("script") == info.script and c != code)


def load_dotenv_if_present() -> None:
    """Load ``.env`` from the working directory if python-dotenv is installed. Never overrides real env vars."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    load_dotenv(Path.cwd() / ".env", override=False)


@dataclass
class Settings:
    """Runtime settings. Keys are read from the environment only."""

    bodhan_base_url: str = "https://api.bodhan.ai"
    translate_key: str | None = None
    speak_key: str | None = None
    transcribe_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    concurrency: int = 6
    request_timeout_s: float = 90.0
    max_retries: int = 5
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv_if_present()
        fallback = os.environ.get("BODHAN_API_KEY") or None  # Cookbook convention: one key for all models
        return cls(
            bodhan_base_url=os.environ.get("BODHAN_BASE_URL", "https://api.bodhan.ai").rstrip("/"),
            translate_key=os.environ.get("BODHAN_TRANSLATE_KEY") or fallback,
            speak_key=os.environ.get("BODHAN_SPEAK_KEY") or fallback,
            transcribe_key=os.environ.get("BODHAN_TRANSCRIBE_KEY") or fallback,
            llm_base_url=os.environ.get("LLM_BASE_URL") or None,
            llm_model=os.environ.get("LLM_MODEL") or None,
            llm_api_key=os.environ.get("LLM_API_KEY") or None,
        )
