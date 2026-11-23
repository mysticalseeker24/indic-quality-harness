# Handoff — current state

Every Claude Code session reads this first and rewrites "Current state" at each checkpoint (see CLAUDE.md §1). Keep it under ~120 lines; history goes in the Session log (one line per session).

## Current state

- **SUBMITTED (23 Nov):** PR https://github.com/Bodhan-AI/Bodhan-AI-Cookbook/pull/113, branch `assignment/quality-harness-mysticalseeker24` on the fork, graded commit `46ac5a5f21b77ee7f9ff823b3d7e20c56ca1b194` (snapshot of this repo at `a32e275`). Do not push to that branch again. Exam done once (docs/EXAM.md): recall 91.6 %, false alarms 4.2 %, gu 93 % / 0 %. Still open: the demo video goes to release `demo-video` (already linked).
- **Phase:** P5 gate passed and P6 built (23 Nov, Saksham asked to move fast to a same-day submission). Now: the one-time exam run, then sample_report, README numbers, Cookbook export and PR.
- **P5 done:** injector output `data/demo_gold.jsonl` (180 items, 75 planted errors, 30 left for a review Saksham did not do); `splits.py` (+ `--known-errors`, D45) writes `demo.jsonl`, `demo_labels.jsonl` (40), `bakeoff.jsonl` (50 incl. 10 te), `demo_gold_reviewed.jsonl`, `splits.json`; `score.py --labels`. Every flag on the 180 real outputs was reviewed (`data/clean_run_review.jsonl`, reviewer `ai-review`): 111 real (36 = Indic-Speak skips bracketed text, confirmed by a controlled test in `outputs/paren_test`), 10 debatable, 13 false alarms.
- **Fixes:** D46 a missing name alone is a hint (all 7 lone entity flags were false); English gloss in brackets is not wrong language; table divider rows are not spoken; D47 omissions/loops next to or inside numbers read out as words; D48 `asr_min_deleted_words` 3 -> 2.
- **Demo (out of sample, 125 items, judge Luna; Kimi rerun in progress -> outputs/demo_kimi):** planted errors 60/61, all labels 92 %, precision 88 %, 0/24 clean flagged, localisation 92 %, category 98 %; CV item recall 90 %, FA 0 %.
- **Bake-off** (8 judges, $5.76): default judge **moonshotai/kimi-k3.1-pro** (Saksham), reasoning effort low; table in README and LLM_BAKEOFF.md.
- **P6 done:** MQM per language, checks-that-could-not-run table, `--fail-on-regression` (exit 3), `dashboard.html`, `api.py`, `voices.py` (run 15/lang in progress -> outputs/voices).
- **Docker:** local `make docker` passes (Docker 29.2.1, image 1.07 GB, ffmpeg 7.1.5; a no-key run in the container is byte-identical to the host).
- **Audio:** release `demo-audio-v1` (234 MB zip of the 180 WAVs data/demo.jsonl points to).
- **History scan (F2):** clean (no key-like strings; only `.env.example` and `outputs/.gitkeep` ever committed).
- **Paid usage:** Bodhan ≈ ₹64 (clean generate run ₹52.39 in 2 h 55 min; re-checks ₹1.63; inject ₹4.83; demo ₹4.82 + ₹0.97 re-checks; bracket test ₹0.30; voices and exam pending). OpenRouter ≈ $6.2 (clean $0.16, held-out $0.02, demo $0.04, bake-off $5.76; Kimi demo ≈ $0.6 pending).

## Open problems

- Exam (`E:\Code and Shit\Work\Bodhan AI\iph-exam data`, only `exam.jsonl`, `calibration.jsonl`, `labels.jsonl`, `run_b\exam.jsonl` and their audio may be opened, by the CLI only): approved once, cap ₹20, judge Kimi.
- Demo video: Saksham records (≤5 min).

## Known issues still open

- K13 format localisation (divider row not located; unmatched `**` at the last marker). K15(b) units/symbols read out in English in tables look garbled. Spoken numbers are not verified.

## Next 3 tasks

1. Exam run A + B (`--baseline`) + scorecard; put numbers in README/PR as they are.
2. `sample_report/` from the Kimi demo run; fill README placeholders (EXAM_RESULTS, VOICE_RESULTS, DEMO_VIDEO, RUNTIME_LINE).
3. Saksham makes the repo public; export to the Cookbook fork (SUBMISSION.md), PR body from `docs/dev/PR_BODY.md`, his approval, push, PR.

## Read next

- README.md, docs/dev/SUBMISSION.md, docs/dev/PR_BODY.md, docs/dev/DECISIONS.md (D43-D48).

## Next session prompt

```
Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
Next up: finish the submission (exam numbers into README/PR, sample_report, Cookbook export and PR).
```

## Session log

| # | Date | Tool | Summary |
|---|---|---|---|
| 0 | 23 Nov 2026 | claude.ai | Design, research, drafts, starter pack, prompt playbook |
| 1 | 23 Nov 2026 | coding session | Phase 1: K12/K4/K10, core unit tests, stub server, pipeline/CLI/report/diff, offline e2e + determinism; repo connected; commit history rewritten without trailers |
| 1b | 23 Nov 2026 | coding session | Phase 2: K3/K6/K8, check tables, 4 table-driven fixes, clean false-alarm suite (0/20); .env + hygiene test; live probe found 404 text routes → chat-transport fallback; D29 transliterate key (live-verified); D26 acked; D30 export hygiene; D31 README AI note |
| 2 | 23 Nov 2026 | coding session | Phase 3: D32 setuptools; K11 AIMD + one retry policy; K1 format chain; K2 judge (tie-break, jury, repeat, windows; replica-blindness fix); bakeoff.py; live smoke on gpt-6-luna (json_schema, error flagged, $0.0014); mini bake-off; panel and P5 bake-off decided (D33); key-exposure scan; docker build blocked |
| 2b | 23 Nov 2026 | same session | Phase 4: K5 time map with ASR chunk anchors, ~10 s chunking (29 s where needed, D37); stub tone-words; speech check tables + second-opinion tests; live speech smoke ₹0.26 (429 Retry-After 58 s handled); D38 numbers read out as words (false garbled found live); exam set sealed until P7 |
- 23 Nov (late): P5 gate + P6: splits, flag review (D45), D46-D48 fixes, bake-off (Kimi default), report extras, api, voices, audio release, history scan clean.
