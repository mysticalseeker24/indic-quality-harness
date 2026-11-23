# Handoff — current state

Every Claude Code session reads this first and rewrites "Current state" at each checkpoint (see CLAUDE.md §1). Keep it under ~120 lines; history goes in the Session log (one line per session).

## Current state

- **Phase:** **Phase 4 gate passed** (23 Nov). Next: **Phase 5** (injector, scorer, demo data, calibration loop, full judge bake-off), after Saksham's go.
- **Done in Phase 4** (details in DECISIONS D37–D38, ARCHITECTURE §3 "Where in the text a speech finding is", TESTING §2):
  - **K5 / D37** ASR chunking at a sentence pause near every 10 s (6-14 s), else the nearest sentence pause up to 29 s, else a word gap, else the quietest point at 18-29 s (`audio.chunk_plan`). Second opinion on long chunks 18-29 s at least 1.5 s from every primary cut, one chunk for 14-29 s audio, middle split for short audio (`audio.alt_chunk_plan`). New `check_params`: `asr_chunk_target_s` 10, `asr_chunk_max_s` 29.
  - **Time map** (`checks/speech.py`: `TimeMap`, `proportional_map`, `anchored_map`, `relocate`): positions follow speaking time (pauses excluded); each ASR chunk is an anchor (its aligned words). `audio_stats` places silences/noise/clipping proportionally with `details.time_s`; `asr` re-places them with anchors (`details.located_by`). `_time_to_char` is gone. `asr` transcribes per chunk and keeps each word's chunk.
  - **Stub tone-words** (`testing/stub_server.py`: `tone_word`, `tone_speech`, `decode_tone_words`; fixture `transcribe: {lang: {tone_words, errors: [{min_s, max_s, drop_last_words | repeat_last_words}]}}`): tests choose exactly what is spoken; chunking, alignment and second opinion run for real. Use it for the P5 speech injector tests.
  - **Tests:** `tests/unit/test_speech_time.py` (chunk plans, time map, end-to-end relocation), `tests/unit/test_check_tables_speech.py` (audio_stats and asr must-catch / must-not-flag, >30 s chunking, MP3 via ffmpeg — skipped locally, CI installs ffmpeg — second-opinion dismissals for words lost or repeated at chunk ends).
  - **Live speech smoke** (Saksham's yes): 9 fixture sources hi/bn/ta, translations removed, `--generate --speech-sample 1 --no-judge --max-cost-inr 3` -> ₹0.26. Valid mono 16-bit 24 kHz WAVs (two sent to Saksham to listen), ASR CER 0 (hi, bn) and ≤ 2 % (ta), duration ratios 0.75-1.41. Indic-Speak gave **429 with Retry-After 58 s**; AIMD halved speak to 3 and the retry worked.
  - **D38 fix found live:** Tamil TTS read "365" in English; in a 5-word item that made CER 106 % and a false `speech_garbled`. Numerals read out as words are now excluded from garbled/omission/repetition (`numbers_read_out`, `NUMERAL_RE`), and `spoken_chars` counts a numeral's digits as 5 characters (`speech_chars_per_digit`, new default). Rerun from cache: 0 flags, ₹0.
  - `make check`: ruff and mypy clean, **459 tests pass, 1 skipped** (MP3 needs ffmpeg) (~34 s).
- **Paid usage so far:** Bodhan ≈ ₹0.27 of ₹200 · OpenRouter ≈ $0.0039 reported.
- **Environment (Windows 11):** `.venv` on Python 3.13.9 (CI runs 3.10 and 3.12); GNU make from winget; **no ffmpeg locally** (CI has it). In PowerShell put `.venv\Scripts` and `%LOCALAPPDATA%\Microsoft\WinGet\Links` on PATH before `make`. PowerShell 5.1 drops empty-string arguments: use bash. In this Bash tool, heredocs with nested quotes break: write scripts to the scratchpad. `python -I` ignores `PYTHONIOENCODING`, and the console is cp1252: write Indic text to a UTF-8 file and Read it. Never read `.env` into the chat; edit it with `dotenv.set_key` and print names only. The auto-mode classifier may block paid runs: ask Saksham for an explicit yes first.
- **Git:** `main`, plain conventional commits (D23), pushed at every checkpoint and at >= 5 unpushed commits (standing yes for normal pushes).
- **Exam project:** **done and sealed** (Saksham, 23 Nov: it offers to send files and a handover). Nothing from it comes into this repo or chat before Phase 7 — no files, no handover notes, no counts or error mix. At Phase 7 Saksham gives the exact file paths; run once, report as is (CLAUDE.md §3, §4.8).
- **Repo visibility:** private (make public before export — CLAUDE.md §3).

## Open problems

1. **CI has been red since Phase 1** (found 23 Nov, after the P4 push): `rapidfuzz==3.14.6` (pinned in the draft import) needs Python >= 3.11 and 3.14.x has no 3.10 wheels, so the 3.10 job fails at `pip install` and fail-fast cancels 3.12 — the tests never ran in CI. Fix waiting for Saksham's yes (dependency change): pin `rapidfuzz==3.13.0`, the last release with 3.10 wheels (dry-resolved for py3.10 and py3.12 Linux and py3.13 Windows), or drop Python 3.10. The CI `docker` job (build + `--help`) and `cookbook-validator` pass, which verifies the D32 Docker build; local `make docker` still waits for Docker on Saksham's laptop.
2. **Keys:** all five key values appear in three earlier Claude Code transcripts of this project (23 Nov); none in git or repo files. Rotation recommended (Saksham plans it after submission).

## Known issues still open

None from K1–K12. `summary.md` is plain (P6).

## Next 3 tasks

1. Phase 5: `inject.py` (BUILD_PLAN P5: methods per category, three severities, seeded per item, speech edits labelled through the same time map; never calls the LLM — tested) and `score.py`.
2. Phase 5: demo dataset per DATASET_PLAN.md, the clean `--generate` run, then the human milestone (CLAUDE.md §3): export a review CSV for Saksham's labels and confirm dataset sources/licences.
3. Phase 5: the bake-off set and the full 8-model judge bake-off (LLM_BAKEOFF.md; `--dry-run` estimate on the real set first, Saksham's approval, then run and recommend a default).

## Read next

- `docs/dev/BUILD_PLAN.md` (P5), `docs/dev/DATASET_PLAN.md`, `docs/dev/LLM_BAKEOFF.md` (Status, Procedure)
- `docs/dev/TESTING.md` §3 and §6
- `src/bodhan_eval/generate.py`, `src/bodhan_eval/calibrate.py`, `src/bodhan_eval/checks/speech.py` (time map)

## Next session prompt

```
Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
Next up: Phase 5 — inject.py and score.py test-first (injector never calls the LLM), then the demo dataset and the clean --generate run (estimate first), the review CSV for my labels, and the full judge bake-off after my approval; stop at the P5 gate.
```

## Session log

| # | Date | Tool | Summary |
|---|---|---|---|
| 0 | 23 Nov 2026 | claude.ai | Design, research, drafts, starter pack, prompt playbook |
| 1 | 23 Nov 2026 | coding session | Phase 1: K12/K4/K10, core unit tests, stub server, pipeline/CLI/report/diff, offline e2e + determinism; repo connected; commit history rewritten without trailers |
| 1b | 23 Nov 2026 | coding session | Phase 2: K3/K6/K8, check tables, 4 table-driven fixes, clean false-alarm suite (0/20); .env + hygiene test; live probe found 404 text routes → chat-transport fallback; D29 transliterate key (live-verified); D26 acked; D30 export hygiene; D31 README AI note |
| 2 | 23 Nov 2026 | coding session | Phase 3: D32 setuptools; K11 AIMD + one retry policy; K1 format chain; K2 judge (tie-break, jury, repeat, windows; replica-blindness fix); bakeoff.py; live smoke on gpt-6-luna (json_schema, error flagged, $0.0014); mini bake-off; panel and P5 bake-off decided (D33); key-exposure scan; docker build blocked |
| 2b | 23 Nov 2026 | same session | Phase 4: K5 time map with ASR chunk anchors, ~10 s chunking (29 s where needed, D37); stub tone-words; speech check tables + second-opinion tests; live speech smoke ₹0.26 (429 Retry-After 58 s handled); D38 numbers read out as words (false garbled found live); exam set sealed until P7 |
