# Handoff — current state

Every Claude Code session reads this first and rewrites "Current state" at each checkpoint (see CLAUDE.md §1). Keep it under ~120 lines; history goes in the Session log (one line per session).

## Current state

- **Phase:** **Phase 1 gate passed** (23 Nov). Next: **Phase 2** (translation checks hardened), after Saksham's go.
- **Done in Phase 1:**
  - K12 (mypy clean: `Check.translation(r)` helper, typed containers), K4 (one-pass calibration loader with the three line shapes; `id`+`lang` lines no longer fall back to id-only), K10 (`config.normalize_lang_code`: `hi-IN`/`HI` → `hi`, script variants kept, warn once).
  - Unit tests: normalize, spans, markup, cache, budget, config, dataset, clients (via stub), stub server.
  - `bodhan_eval/testing/stub_server.py` (real HTTP, API request rules enforced, fixtures + fault injection, speech-like TTS audio).
  - `pipeline.py`, `cli.py`, minimal `report.py`, minimal `diff.py` (D17–D22 in DECISIONS.md).
  - e2e (`tests/e2e/test_cli_e2e.py`, fixtures in `tests/fixtures/e2e/`): exact command as a subprocess, rerun byte-identical at ₹0, empty diff, `--generate`.
  - `make check`: ruff clean, mypy clean, **221 tests pass** (~15 s).
- **Paid usage so far:** Bodhan ₹0 of ₹200 · OpenRouter $0 of $10.
- **Environment (Windows 11):** `.venv` on Python 3.13.9 (CI runs 3.10 and 3.12); GNU make from winget (`ezwinports.make`). In PowerShell put `.venv\Scripts` and `%LOCALAPPDATA%\Microsoft\WinGet\Links` on PATH before `make`. PowerShell 5.1 drops empty-string arguments to native commands: use bash for those. Repo git config: `core.autocrlf=false` (files are LF), GitHub credentials via `gh auth git-credential` (repo-local, account mysticalseeker24). `.claude/` is ignored via `.git/info/exclude`.
- **Git:** `main` tracks `origin/main` (private). Commit messages are plain conventional commits with **no attribution trailers** (D23). Push in batches of ≥5 commits.
- **Exam project:** not started — Saksham was reminded at the Phase 1 gate (CLAUDE.md §3).
- **Repo visibility:** private (must be made public before export — CLAUDE.md §3).

## Open questions for Saksham

1. **Transliteration key.** The Bodhan console issues one key per model, but `clients.transliterate` sends `/transliterate` with the *translate* key, likely a 401 on the hosted API. Proposal: optional `BODHAN_TRANSLITERATE_KEY`, falling back to the translate key (env contract change → needs a yes). Verify in the first live smoke.
2. **Before the repo goes public:** `.gitattributes` exports itself and names `CLAUDE.md` (add `.gitattributes export-ignore`?); README "AI assistance" wording (the spec asks for a brief note); keep `CLAUDE.md` and `docs/dev/` tracked in the public personal repo or not.
3. **`.env`** is not in the project folder yet (needed before the first paid run; Phase 1 is offline).
4. setuptools warns that the `project.license` TOML table is deprecated (removal 2027-02-18). Switching to `license = "Apache-2.0"` needs `setuptools>=77` in `[build-system]`. Small, but it is a packaging change.

## Known issues still open

K1, K2, K11 (P3) · K3, K6, K8 (P2) · K5 (P4) — details in BUILD_PLAN.md. Also: `summary.md` is plain (P6 polishes wording such as "1 bad lines").

## Next 3 tasks

1. Phase 2: fix K3, K6, K8, each starting with a failing test.
2. Phase 2: table-driven must-catch / must-not-flag tests for script, format, numbers, length, back-translation, entities (TESTING.md §2), incl. every Indic digit system, Indian grouping, `H2O`/`CO2`, translated `\text{}`, table headers, kept English names, legitimate reordering.
3. Phase 2 gate: false-alarm suite on clean fixtures → zero tier-0 flags.

## Read next

- `docs/dev/BUILD_PLAN.md` (P2 section; K3, K6, K8)
- `docs/dev/TESTING.md` §2
- `src/bodhan_eval/checks/deterministic.py`, `checks/roundtrip.py`, `fusion.py`
- `src/bodhan_eval/testing/stub_server.py` (docstring: how fixtures map back-translations)

## Next session prompt

```
Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
Next up: Phase 2 — fix K3, K6 and K8 test-first, then the must-catch / must-not-flag tables for every translation check (TESTING.md §2) and the clean-fixture false-alarm suite.
```

## Session log

| # | Date | Tool | Summary |
|---|---|---|---|
| 0 | 23 Nov 2026 | claude.ai | Design, research, drafts, starter pack, prompt playbook |
| 1 | 23 Nov 2026 | coding session | Phase 1: K12/K4/K10, core unit tests, stub server, pipeline/CLI/report/diff, offline e2e + determinism; repo connected; commit history rewritten without trailers |
