# Handoff — current state

Every Claude Code session reads this first and rewrites "Current state" at each checkpoint (see CLAUDE.md §1). Keep it under ~120 lines; history goes in the Session log (one line per session).

## Current state

- **Phase:** **Phase 2 gate passed** (23 Nov). Next: **Phase 3** (judge and LLM layer), after Saksham's go.
- **Done in Phase 2:**
  - K3 (`BtLimits` passed as a value; check instances hold no state), K6 (`pipeline.prefetch_transliterations` dedupes per (lang, term); `entity_max_transliterations` caps direct calls; no transliteration for languages without Indic script data), K8 (two-pass clustering; unlocated signals join the strongest cluster of their category).
  - TESTING.md §2 tables for script, format, numbers (incl. every digit system, Indian grouping, unit/month via back-translation), length, back-translation and entities: `tests/unit/test_check_tables_*.py`. Shared fixtures in `tests/conftest.py` (real `RunContext`, `run_one`, `run_chain`, `fuse_item`).
  - Fixes found by the tables: `has_markup` ignored Markdown links; units compared by spelling (km vs kilometres false alarm) and only within one family (litres -> kg missed); `entity_match_similarity` 72 -> 85 (D26, see open question 2).
  - Clean-item false-alarm suite (`tests/e2e/test_false_alarms.py`, 20 items hi/bn/ta): **0 flagged, 0 in review**. A guard rejects control characters in fixtures. Shell heredocs collapse `\\`, so generate fixtures from files and use `chr(92)`.
  - **Live API finding (D24):** hosted `/translate` and `/transliterate` answer 404; the documented chat transport works. Clients fall back automatically (verified live). Keys are scoped per model (API_NOTES).
  - Secrets: `.env` filled by Saksham (Bodhan translate/speak/transcribe/transliterate keys, OpenRouter key; `LLM_MODEL` empty until the P3 bake-off). `tests/unit/test_repo_hygiene.py` fails `make check` if `.env` is tracked or any repo file holds a value from it or a key-shaped string.
  - `make check`: ruff and mypy clean, **313 tests pass** (~20 s).
- **Paid usage so far:** Bodhan ≈ ₹0.01 of ₹200 (key probe + one live fallback check) · OpenRouter $0 (key limit shows 50).
- **Environment (Windows 11):** `.venv` on Python 3.13.9 (CI runs 3.10 and 3.12); GNU make from winget. In PowerShell put `.venv\Scripts` and `%LOCALAPPDATA%\Microsoft\WinGet\Links` on PATH before `make`. PowerShell 5.1 drops empty-string arguments to native commands: use bash for those. Repo git config: `core.autocrlf=false`, GitHub credentials via `gh auth git-credential` (repo-local). `.claude/` is ignored via `.git/info/exclude`.
- **Git:** `main`. Commit messages are plain conventional commits, no attribution trailers (D23). Push in batches of ≥5 commits. **4 commits are not pushed yet** (go out with the next batch).
- **Exam project:** reminded at the Phase 1 gate; status unknown here.
- **Repo visibility:** private (make public before export — CLAUDE.md §3).

## Open questions for Saksham

1. **Read `BODHAN_TRANSLITERATE_KEY`?** Live probe: keys are scoped per model, so the translate key cannot transliterate. Proposal: clients use `BODHAN_TRANSLITERATE_KEY`, falling back to `BODHAN_API_KEY`, then the translate key. The graders set only the three documented keys, so without it entity checks fall back to Latin and back-translation matching. Env contract change → needs a yes.
2. **Ack D26:** `entity_match_similarity` raised 72 -> 85 (a default in `defaults.json`, changed as a Phase 2 table fix).
3. **Before the repo goes public:** `.gitattributes` exports itself and names `CLAUDE.md`; README "AI assistance" wording (the spec asks for a brief note); keep `CLAUDE.md` and `docs/dev/` tracked or not.
4. setuptools warns that the `project.license` TOML table is deprecated (removal 2027-02-18). `license = "Apache-2.0"` needs `setuptools>=77`.
5. Security: the keys were pasted into a chat transcript; consider rotating them after the submission.

## Known issues still open

K1, K2, K11 (P3) · K5 (P4) — details in BUILD_PLAN.md. `summary.md` is plain (P6).

## Next 3 tasks

1. Phase 3: K1 (LLM response-format fallback chain, empty-content retry, `--llm-extra-body`) and K11 (AIMD concurrency), test-first against the stub.
2. Phase 3: K2 (adaptive replicas, jury, repeat-consistency sample, long-text windows) + the four judge CLI flags (D17); judge parsing tests (TESTING.md §2 judge row, §4 LLM rows).
3. Phase 3: `bakeoff.py` + live smoke (5 items, 1 cheap model, `--max-cost-inr 2`). Show the model list and cost estimate first (CLAUDE.md §3).

## Read next

- `docs/dev/BUILD_PLAN.md` (P3; K1, K2, K11)
- `docs/dev/LLM_BAKEOFF.md`, `docs/dev/TESTING.md` §2 (judge row) and §4
- `src/bodhan_eval/checks/judge.py`, `clients.py` (LLMClient), `data/judge_rubric.md`

## Next session prompt

```
Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
Next up: Phase 3 — K1 and K11 test-first against the stub, then K2 and the judge flags, then bakeoff.py and the live smoke (show the model list and cost estimate first).
```

## Session log

| # | Date | Tool | Summary |
|---|---|---|---|
| 0 | 23 Nov 2026 | claude.ai | Design, research, drafts, starter pack, prompt playbook |
| 1 | 23 Nov 2026 | coding session | Phase 1: K12/K4/K10, core unit tests, stub server, pipeline/CLI/report/diff, offline e2e + determinism; repo connected; commit history rewritten without trailers |
| 1b | 23 Nov 2026 | coding session | Phase 2: K3/K6/K8, check tables, 4 table-driven fixes, clean false-alarm suite (0/20); .env + hygiene test; live probe found 404 text routes → chat-transport fallback |
