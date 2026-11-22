# Handoff — current state

Every Claude Code session reads this first and rewrites "Current state" at each checkpoint (see CLAUDE.md §1). Keep it under ~120 lines; history goes in the Session log (one line per session).

## Current state

- **Phase:** 0 → starting **Phase 1** (foundation and the runnable command).
- **Done before Claude Code:** design and analysis in claude.ai; draft modules written and smoke-tested (see BUILD_PLAN status table); three draft bugs fixed (untranslated text not flagged; broken LaTeX reported twice; truncation also reported as garbled); Cookbook validator passes on this folder; package installs from a clean venv; `ruff` clean.
- **Known open issues:** K1–K12 in `docs/dev/BUILD_PLAN.md` (K12: 41 `mypy` annotation errors in drafts — fix first in Phase 1).
- **Paid usage so far:** Bodhan ₹0 of ₹200 credit · OpenRouter $0 of $10.
- **Environment:** Python 3.10+ venv; `ffmpeg` installed; `.env` filled by Saksham (never printed).
- **Exam project:** not started (prompt Saksham at the Phase 1 gate).
- **Repo visibility:** private (must be made public before export — CLAUDE.md §3).

## Next 3 tasks

1. Phase 1: fix K12 (mypy), K4, K10; write unit tests for normalize, spans, markup, cache, budget, dataset.
2. Phase 1: `testing/stub_server.py`, `pipeline.py`, `cli.py`, minimal `report.py`.
3. Phase 1 gate: offline 10-item e2e via the exact command; rerun gives identical bytes and ₹0 spent.

## Read next

- `docs/dev/BUILD_PLAN.md` (Phase 1 section and known issues)
- `docs/dev/TESTING.md` §1, §4, §5
- `docs/dev/CONVENTIONS.md`
- `src/bodhan_eval/checks/base.py`, `models.py`, `config.py`

## Next session prompt

```
Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
Next up: Phase 1 — fix K12, K4, K10 with unit tests, then build the stub server, pipeline.py, cli.py and minimal report.py.
```

## Session log

| # | Date | Tool | Summary |
|---|---|---|---|
| 0 | 23 Nov 2026 | claude.ai | Design, research, drafts, starter pack, prompt playbook |
