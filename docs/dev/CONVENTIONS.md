# Coding conventions

The bar: a reviewer at Bodhan reads any file and understands it in one pass; Saksham can explain every line and add a check live in ~10 minutes.

## Layout and boundaries

```
src/bodhan_eval/
  config.py models.py            # settings, data classes (no I/O beyond reading package data)
  normalize.py spans.py markup.py audio.py   # pure helpers (audio.py: only file I/O for wav)
  checks/                        # one class per check; emit Signals only
  fusion.py calibrate.py         # pure: signals -> flags, labels -> metrics/thresholds
  clients.py cache.py budget.py  # all network, all money, all caching
  dataset.py generate.py pipeline.py report.py diff.py inject.py score.py bakeoff.py
  api.py cli.py __main__.py      # entry points; cli depends on api/pipeline, never the reverse
```
- Imports flow downward: entry points → pipeline → checks/fusion → helpers. Checks never import `pipeline`, `cli` or `report`.
- Only `clients.py` talks to the network. Only `budget.py` decides whether money may be spent.
- All tunable numbers live in `data/defaults.json`; all language facts in `data/langs.json`; label vocabularies in `data/taxonomy.json`.

## Python style

- Python ≥ 3.10; `from __future__ import annotations` at the top of every module.
- Type hints on every function signature and on empty collections (`out: list[Signal] = []`). `mypy` must pass with the repo config.
- `ruff format` (line length 120) and `ruff check` clean. No unused imports, no bare `except:`; catch the narrowest exception and record why.
- Naming: modules and functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`, private helpers `_leading_underscore`. Names describe meaning (`deleted_word_run`, not `tmp2`).
- Functions do one thing, ideally ≤ 40 lines (hard ceiling ~60). Prefer early returns over nesting.
- Data: `@dataclass` (frozen where possible) for records; never pass bare dicts between modules except at JSON boundaries.
- No module-level mutable state; config loaders may use `functools.lru_cache`.
- Paths with `pathlib.Path`; text files opened with `encoding="utf-8"`; JSON written with `ensure_ascii=False, sort_keys=True`.
- Concurrency: threads for I/O-bound API calls only; shared objects (cache, budget) are lock-protected; check instances hold no per-item state (pass values as arguments).

## Docstrings and comments

- Module docstring: what the module is for and the key idea, in 3–10 lines.
- Public functions/classes: one-line summary + anything surprising (units, offsets, side effects).
- Comments explain *why* a heuristic or threshold exists, with the alternative you rejected when it matters.
- Evidence strings in signals are written for a model team: what is wrong, where, and the measured value ("Silence of 2.1 s at 3.4–5.5 s").

## Errors, logging, determinism

- A bad item or failing check never aborts the run. Pipeline maps: `SkipCheck` → skipped(reason); `ServiceUnavailable` → skipped(no key); `BudgetExceeded` → skipped(budget); anything else → error(type: message), logged with the item key.
- Structured logs: one JSON line per item × check in `<out>/logs/events.jsonl` (`item`, `check`, `status`, `reason`, `ms`, `signals`, `cache_hits`). Use `logging` for human-readable progress (stderr).
- Determinism: no timestamps, durations, random values, absolute paths or unordered iteration in the five report files. Seeded RNGs derive from stable hashes (`sha256(seed|id|lang)`).
- Never log or print secrets; redact `Authorization` headers in error messages.

## Tests

- `tests/unit/test_<module>.py`, `tests/e2e/`, fixtures in `tests/fixtures/`. Use `pytest.mark.parametrize` with readable ids for must-catch / must-not-flag tables.
- Offline by default (stub server, synthetic audio generated in the test). Paid tests carry `@pytest.mark.live` and a cost estimate in the docstring.
- Every bug fix starts with a failing test.
- No test writes outside `tmp_path`.

## Git

- Branch `main` in the personal repo; feature branches optional (`feat/phase-2-format-check`).
- Conventional commits: `feat|fix|test|docs|refactor|perf|chore(scope): imperative summary` (≤ 72 chars), body explains why when not obvious. Checkpoints: `chore(checkpoint): …`.
- `make check` green before every commit. Never commit `.env`, audio, `outputs/`, caches.
- No history rewrites or force pushes without Saksham's explicit yes.

## Dependencies

- Only what `pyproject.toml` lists, pinned exactly and mirrored in `requirements.txt`. New dependency = ask first, justify in DECISIONS.md.
- Never add MT/ASR/TTS, learned QE or learned language-ID libraries (hard rule).
