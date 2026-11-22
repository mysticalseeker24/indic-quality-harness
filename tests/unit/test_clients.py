"""Bodhan and LLM clients against the local stub: retries, splitting, caching, fallbacks (TESTING.md §4)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from bodhan_eval.budget import Budget
from bodhan_eval.cache import Cache
from bodhan_eval.clients import BodhanClient, BodhanError, LLMClient, ServiceUnavailable, strip_indic
from bodhan_eval.config import Settings
from bodhan_eval.testing.stub_server import StubServer

PARA_1 = "The first paragraph is long enough to matter. " * 3
PARA_2 = "The second paragraph follows after a blank line. " * 3
FIXTURE = {
    "translate": {
        "hi": {"Water boils.": "पानी उबलता है।", "Cut short.": {"text": "छोटा", "truncated": True}},
        "en": {"पानी उबलता है।": "Water boils."},
    },
    "transliterate": {"hi": {"Newton": "न्यूटन"}},
    "chat": [
        {"contains": "verdict please", "content": '{"errors": [], "note": "fine"}'},
        {"contains": "prose please", "content": "I think it is fine."},
    ],
}


@pytest.fixture
def stub() -> Iterator[StubServer]:
    with StubServer(FIXTURE) as s:
        yield s


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[Cache]:
    c = Cache(tmp_path / "cache")
    yield c
    c.close()


def settings_for(stub: StubServer, **kw) -> Settings:
    base = {
        "bodhan_base_url": stub.url,
        "translate_key": "stub-key",
        "speak_key": "stub-key",
        "transcribe_key": "stub-key",
        "llm_base_url": f"{stub.url}/v1",
        "llm_model": "stub-judge",
        "llm_api_key": "stub-key",
        "max_retries": 3,
        "request_timeout_s": 10.0,
    }
    return Settings(**{**base, **kw})


def bodhan(stub: StubServer, cache: Cache, budget: Budget | None = None, **kw) -> BodhanClient:
    return BodhanClient(settings_for(stub, **kw), cache, budget or Budget(None))


# ---- translation -------------------------------------------------------------


def test_translate_200_then_cache_hit(stub: StubServer, cache: Cache) -> None:
    budget = Budget(None)
    c = bodhan(stub, cache, budget)
    first = c.translate("Water boils.", "hi")
    second = c.translate("Water boils.", "hi")
    assert first == {"translation": "पानी उबलता है।", "truncated": False, "cached": False}
    assert second["cached"] is True
    assert len(stub.requests) == 1
    assert budget.total_spent > 0 and budget.used["translate"] == pytest.approx(2 * budget.spent["translate"])


def test_translate_records_truncated(stub: StubServer, cache: Cache) -> None:
    assert bodhan(stub, cache).translate("Cut short.", "hi")["truncated"] is True


def test_translate_413_splits_on_blank_lines_and_rejoins(stub: StubServer, cache: Cache) -> None:
    text = PARA_1 + "\n\n" + PARA_2
    stub.add_fault("/translate", 413, times=1, code="payload_too_large")
    out = bodhan(stub, cache).translate(text, "en")
    assert out["translation"] == text  # the stub echoes unknown text; the separator survives the rejoin
    assert [r["status"] for r in stub.requests] == [413, 200, 200]


def test_translate_429_retries_after_header(stub: StubServer, cache: Cache) -> None:
    stub.add_fault("/translate", 429, times=2, retry_after="0.01")
    assert bodhan(stub, cache).translate("Water boils.", "hi")["translation"] == "पानी उबलता है।"
    assert [r["status"] for r in stub.requests] == [429, 429, 200]


def test_translate_500_then_success(stub: StubServer, cache: Cache) -> None:
    stub.add_fault("/translate", 500, times=1, retry_after="0.01")
    assert bodhan(stub, cache).translate("Water boils.", "hi")["cached"] is False
    assert [r["status"] for r in stub.requests] == [500, 200]


def test_retries_exhausted_raises_and_releases_reservation(stub: StubServer, cache: Cache) -> None:
    stub.add_fault("/translate", 503, times=-1, retry_after="0.01")
    budget = Budget(1.0)
    with pytest.raises(BodhanError) as err:
        bodhan(stub, cache, budget, max_retries=2).translate("Water boils.", "hi")
    assert err.value.code == "retries_exhausted"
    assert budget.reserved == 0.0 and budget.total_spent == 0.0
    assert cache.get(Cache.key("translate", "indic-translate", {"target_language": "hi"}, "Water boils.")) is None


def test_transliterate(stub: StubServer, cache: Cache) -> None:
    assert bodhan(stub, cache).transliterate("Newton", "hi") == "न्यूटन"


def test_translate_uses_chat_transport_when_route_is_missing(stub: StubServer, cache: Cache) -> None:
    """The hosted gateway answered 404 on /translate (API_NOTES, 23 Nov); the chat transport serves the same model."""
    stub.add_fault("/translate", 404, times=-1, code="404", message="Not Found")
    c = bodhan(stub, cache)
    assert c.translate("Water boils.", "hi") == {"translation": "पानी उबलता है।", "truncated": False, "cached": False}
    assert c.translate("Cut short.", "hi")["truncated"] is True  # finish_reason "length"
    assert [r["path"] for r in stub.requests] == ["/translate", "/v1/chat/completions", "/v1/chat/completions"]
    assert stub.requests[1]["model"] == "indic-translate"


def test_transliterate_uses_chat_transport_when_route_is_missing(stub: StubServer, cache: Cache) -> None:
    stub.add_fault("/transliterate", 404, times=-1)
    assert bodhan(stub, cache).transliterate("Newton", "hi") == "न्यूटन"
    assert stub.requests[-1]["model"] == "indic-transliterate"


def test_other_client_errors_do_not_switch_transport(stub: StubServer, cache: Cache) -> None:
    stub.add_fault("/translate", 400, times=1, code="unsupported_language")
    with pytest.raises(BodhanError) as err:
        bodhan(stub, cache).translate("Water boils.", "xx")
    assert err.value.status == 400
    assert [r["path"] for r in stub.requests] == ["/translate"]


def test_missing_key_is_service_unavailable_before_any_request(stub: StubServer, cache: Cache) -> None:
    budget = Budget(1.0)
    c = bodhan(stub, cache, budget, translate_key=None)
    assert c.available("translate") is False
    with pytest.raises(ServiceUnavailable, match="BODHAN_TRANSLATE_KEY"):
        c.translate("Water boils.", "hi")
    assert stub.requests == [] and budget.reserved == 0.0


# ---- speech ------------------------------------------------------------------


def test_tts_wav_returned_and_cached_as_blob(stub: StubServer, cache: Cache) -> None:
    c = bodhan(stub, cache)
    wav = c.speak("पानी उबलता है।", "hi", "Kavya")
    assert wav[:4] == b"RIFF"
    assert c.speak("पानी उबलता है।", "hi", "Kavya") == wav
    assert len(stub.requests) == 1
    assert len(list((cache.root / "blobs").glob("*.wav"))) == 1


def test_tts_422_is_not_retried(stub: StubServer, cache: Cache) -> None:
    with pytest.raises(BodhanError) as err:
        bodhan(stub, cache).speak("   ", "hi", "Kavya")
    assert err.value.status == 422
    assert len(stub.requests) == 1


# ---- LLM ---------------------------------------------------------------------


def llm(stub: StubServer, cache: Cache, **kw) -> LLMClient:
    return LLMClient(settings_for(stub, max_retries=0, **kw), cache, Budget(None))


def test_llm_json_object_answer_parsed_and_cached(stub: StubServer, cache: Cache) -> None:
    client = llm(stub, cache)
    msgs = [{"role": "user", "content": "verdict please"}]
    assert client.chat_json(msgs) == {"errors": [], "note": "fine"}
    assert client.chat_json(msgs) == {"errors": [], "note": "fine"}
    assert len(stub.requests) == 1 and stub.requests[0]["response_format"] is True


def test_llm_falls_back_when_response_format_is_rejected(stub: StubServer, cache: Cache) -> None:
    stub.add_fault("/chat/completions", 400, times=1, message="response_format is not supported by this model")
    client = llm(stub, cache)
    assert client.chat_json([{"role": "user", "content": "verdict please"}]) == {"errors": [], "note": "fine"}
    assert stub.requests[0]["status"] == 400
    assert stub.requests[1]["response_format"] is False


def test_llm_non_json_answer_is_none(stub: StubServer, cache: Cache) -> None:
    assert llm(stub, cache).chat_json([{"role": "user", "content": "prose please"}]) is None


def test_llm_unconfigured_is_service_unavailable(stub: StubServer, cache: Cache) -> None:
    client = llm(stub, cache, llm_model=None)
    assert client.available() is False
    with pytest.raises(ServiceUnavailable):
        client.chat_json([{"role": "user", "content": "x"}])


def test_strip_indic_masks_indian_scripts_in_llm_prose() -> None:
    assert strip_indic("The word पानी is fine, as is தண்ணீர்.") == "The word […] is fine, as is […]."
