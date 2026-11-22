from __future__ import annotations

import pytest

from bodhan_eval.config import canonical_category, canonical_severity, lang_info, normalize_lang_code


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("hi", "hi", id="already-canonical"),
        pytest.param("HI", "hi", id="upper-case"),
        pytest.param(" ta ", "ta", id="whitespace"),
        pytest.param("hi-IN", "hi", id="region-subtag"),
        pytest.param("bn_in", "bn", id="underscore-region"),
        pytest.param("ks-Deva", "ks-Deva", id="script-variant-kept"),
        pytest.param("KS-DEVA", "ks-Deva", id="script-variant-case"),
        pytest.param("mni-beng", "mni-Beng", id="script-variant-lower"),
        pytest.param("sd-Arab-PK", "sd-Arab", id="script-variant-with-region"),
        pytest.param("sd-Deva", "sd", id="unknown-script-falls-back-to-base"),
        pytest.param("xx", "xx", id="unknown-code-unchanged"),
        pytest.param("xx-YY", "xx-YY", id="unknown-code-with-region-unchanged"),
    ],
)
def test_normalize_lang_code(raw: str, expected: str) -> None:
    assert normalize_lang_code(raw) == expected


def test_unknown_language_still_has_info() -> None:
    info = lang_info("xx")
    assert info.known is False
    assert info.script is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Omission", "omission"), ("number or unit", "number"), ("no-such-type", None), (None, None)],
)
def test_canonical_category(raw: str | None, expected: str | None) -> None:
    assert canonical_category(raw) == expected


def test_canonical_severity_defaults_to_major() -> None:
    assert canonical_severity(None) == "major"
    assert canonical_severity("weird") == "major"
