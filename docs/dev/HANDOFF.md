# Handoff — current state

Every Claude Code session reads this first and rewrites "Current state" at each checkpoint (see CLAUDE.md §1). Keep it under ~120 lines; history goes in the Session log (one line per session).

## Current state

- **Phase:** **Phase 3 gate passed** (23 Nov). Next: **Phase 4** (speech), after Saksham's go.
- **Done in Phase 3** (details in DECISIONS D32–D36, BUILD_PLAN, ARCHITECTURE §4 and §7):
  - **D32** build requirement `setuptools>=77`, SPDX `license = "Apache-2.0"`. Fresh-venv wheel: warning gone, same files, only `License:` -> `License-Expression:`. **`docker build` not verified** (see open problems).
  - **K11 / D34** `clients.AdaptiveLimiter` (one per service incl. `llm`; 429 halves once per window, +1 after 20 successes) and `call_with_retries` shared by Bodhan and the LLM; OpenAI SDK `max_retries=0` (its retries cover 408/409/429/5xx together, checked in the SDK source). New `defaults.json` section `clients` (retry_base_s 1.5, retry_max_wait_s 60, aimd_increase_after 20) and matching `Settings` fields.
  - **K1 / D35** `LLMClient`: `json_schema` -> `json_object` -> plain, per-model memory only after a lower format worked; `--llm-extra-body`; empty answer retried once with 2x `max_tokens`; `usage.cost` recorded (`Budget.llm_cost_usd`, `llm_fresh_tokens`); format cached with the answer; `chat_json(..., schema=, model=, cache_tag=)`. Errors: `ApiError` base, `BodhanError`, `LLMError`.
  - **K2 / D36** `checks/judge.py` rewritten: strict verdict schema; tie-break replica only on category disagreement (`--judge-max-replicas`, default 3); invalid answers replaced; jury `--judge-models`; repeat sample `--judge-repeat-sample` (default 0.1, hash-chosen, no evidence); windows over 1,200 tokens (`max_windows` 8). **Bug fixed on the way:** replicas could see earlier replicas' verdicts as "automatic findings"; findings are now snapshotted before the first replica. `calibrate.judge_consistency` adds `tie_break_rate` and `repeat`.
  - **`bakeoff.py`** (`python -m bodhan_eval.bakeoff`): estimate per model, refusal above `--max-usd`, stop when real spend (max of reported and list price) reaches it, prices from `--price` or OpenRouter `/models`, `bakeoff.json` / `bakeoff.md` / `bakeoff_spend.json`, byte-identical cached reruns. Stub server: chat rules by `starts_with`/`model`/`min_max_tokens`/`times`, `finish_reason`, `cost`, `chat_unsupported_formats`, `GET /models`, logs `user`, `body_hash`, `extra`.
  - Small fixes from the live run: the 404 transport switch is logged once under parallel load; `httpx`/`httpx2`/`openai` INFO lines silenced (`cli.setup_logging`).
  - **Live smoke** (5 items from the clean fixtures + one injected 100 -> 90, `outputs/smoke_input/smoke.jsonl`, git-ignored): `openai/gpt-6-luna`, reasoning effort low: **json_schema** used, the injected error flagged by numbers + both replicas (0.97), 0 false alarms, 12 judge calls, 0 invalid, order and repeat consistency 100 %. OpenRouter charged $0.0014; budget line ₹0.62 (conservative `--llm-inr-per-1k-tokens 0.05`); Bodhan ₹0.0015.
  - **Mini bake-off** (same 5 items, Luna + DeepSeek V4.1 Flash): both json_schema, 0 % invalid, 100 % on the single error (proves the tool, does not rank models). Table in LLM_BAKEOFF.md "Status". DeepSeek was charged 2.8x list price.
  - **Saksham's decisions (23 Nov, D33):** panel `openai/gpt-6.2-sol`, `anthropic/claude-sonnet-5.5`, `google/gemini-4-hydrogen`, `google/gemini-4-neon`, `openai/gpt-6-luna`, `deepseek/deepseek-v4.1-flash`, `moonshotai/kimi-k3.1-pro`, weak `meta-llama/llama-3.1-8b-instruct`; full bake-off **after P5** (moved into the P5 task list and gate); interim judge `LLM_MODEL=openai/gpt-6-luna` (`.env` set, `LLM_BASE_URL=https://openrouter.ai/api/v1`). Estimate for the full run: $4.4–7.5 for 50 items; run with `--max-usd 8`, show the estimate on the real set first.
  - `make check`: ruff and mypy clean, **416 tests pass** (~30 s).
- **Paid usage so far:** Bodhan ≈ ₹0.012 of ₹200 · OpenRouter ≈ $0.0039 reported (smoke $0.0014, mini bake-off $0.0025).
- **Environment (Windows 11):** `.venv` on Python 3.13.9 (CI runs 3.10 and 3.12); GNU make from winget. In PowerShell put `.venv\Scripts` and `%LOCALAPPDATA%\Microsoft\WinGet\Links` on PATH before `make`. PowerShell 5.1 drops empty-string arguments to native commands: use bash for those. In this Bash tool, heredocs with nested quotes break: write scripts to the scratchpad and run them. Never read `.env` into the chat; edit it with `dotenv.set_key` and print names only.
- **Git:** `main`, plain conventional commits (D23), pushed at every checkpoint and at >= 5 unpushed commits (standing yes for normal pushes).
- **Exam project:** in progress in parallel (Saksham, 23 Nov). Never touch it (CLAUDE.md §4.8).
- **Repo visibility:** private (make public before export — CLAUDE.md §3).

## Open problems

1. **Docker:** Docker Desktop is running but its engine never came up (`docker-desktop` WSL distro stopped; `docker info` hangs). D32 still needs `make docker` once Saksham has the engine running.
2. **Keys:** all five key values (four Bodhan keys + OpenRouter) appear in three earlier Claude Code transcripts of this project (sessions `43f0e4e4…`, `933c6234…`, `639b76b1…`, 23 Nov); none in any git object, repo file, `outputs/`, cache or log. Recommended: rotate now (Saksham had planned after submission). The exam project's transcripts were not scanned (rule 8).

## Known issues still open

K5 (P4) — details in BUILD_PLAN.md. `summary.md` is plain (P6).

## Next 3 tasks

1. Phase 4: K5 (speech localisation with chunk anchors) and the synthetic-audio tests (silence, clipping, noise burst, truncation, repetition, >30 s chunking, MP3 via ffmpeg).
2. Phase 4: alignment tests (omission/tail/repetition/n-gram loop) and the second-opinion dismissal test; gate P4.
3. Phase 5: injector, scorer, demo data, Saksham's labels, then the full 8-model bake-off (estimate first).

## Read next

- `docs/dev/BUILD_PLAN.md` (P4; K5)
- `docs/dev/TESTING.md` §2 (audio_stats and asr rows), `docs/dev/API_NOTES.md` (transcribe)
- `src/bodhan_eval/checks/speech.py`, `src/bodhan_eval/audio.py`

## Next session prompt

```
Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
Next up: Phase 4 — K5 speech localisation with chunk anchors and the synthetic-audio test tables, then the alignment and second-opinion tests; stop at the P4 gate. Also run `make docker` if the Docker engine is up.
```

## Session log

| # | Date | Tool | Summary |
|---|---|---|---|
| 0 | 23 Nov 2026 | claude.ai | Design, research, drafts, starter pack, prompt playbook |
| 1 | 23 Nov 2026 | coding session | Phase 1: K12/K4/K10, core unit tests, stub server, pipeline/CLI/report/diff, offline e2e + determinism; repo connected; commit history rewritten without trailers |
| 1b | 23 Nov 2026 | coding session | Phase 2: K3/K6/K8, check tables, 4 table-driven fixes, clean false-alarm suite (0/20); .env + hygiene test; live probe found 404 text routes → chat-transport fallback; D29 transliterate key (live-verified); D26 acked; D30 export hygiene; D31 README AI note |
| 2 | 23 Nov 2026 | coding session | Phase 3: D32 setuptools; K11 AIMD + one retry policy; K1 format chain; K2 judge (tie-break, jury, repeat, windows; replica-blindness fix); bakeoff.py; live smoke on gpt-6-luna (json_schema, error flagged, $0.0014); mini bake-off; panel and P5 bake-off decided (D33); key-exposure scan; docker build blocked |
