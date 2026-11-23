"""Argument parsing for the optional flags (the required ones are covered by the end-to-end tests)."""

from __future__ import annotations

import pytest

from bodhan_eval.cli import build_parser, options_from_args

REQUIRED = ["--dataset", "d.jsonl", "--langs", "hi", "--out", "out"]


def parse(*extra: str):
    return options_from_args(build_parser().parse_args([*REQUIRED, *extra]))


def test_llm_extra_body_is_off_by_default() -> None:
    assert parse().llm_extra_body is None


def test_llm_extra_body_takes_a_json_object() -> None:
    opts = parse("--llm-extra-body", '{"reasoning": {"effort": "low"}}')
    assert opts.llm_extra_body == {"reasoning": {"effort": "low"}}


@pytest.mark.parametrize("bad", ["not json", "[1, 2]", '"low"'])
def test_llm_extra_body_rejects_anything_but_an_object(bad: str) -> None:
    with pytest.raises(SystemExit):
        parse("--llm-extra-body", bad)
