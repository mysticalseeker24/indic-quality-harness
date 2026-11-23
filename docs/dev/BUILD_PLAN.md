# Build plan

Phases are ordered; each ends with a **gate** that must pass before moving on. Update the status table as you go.
Priority if time gets short (the spec says: stop and write what you would do next): P1–P5 are the graded core;
P6 extras are bonus; never cut tests, determinism, calibration or the deterministic checks.

## Status of modules

Legend: ✅ draft written and smoke-tested · 🟡 draft with known issues (see below) · ⬜ to build

| Module | Status | Notes |
|---|---|---|
| `data/langs.json`, `taxonomy.json`, `defaults.json`, `judge_rubric.md` | ✅ | Language registry, label aliases, generic thresholds, judge rubric |
| `config.py`, `models.py` | ✅ | Settings from env; `Item`, `Signal`, `Flag`, `ItemResult` |
| `cache.py`, `budget.py` | ✅ | SQLite content-addressed cache; reserve-before-spend budget |
| `clients.py` | ✅ | Bodhan + LLM clients; chat-transport fallback (D24); response-format chain, extra body, empty-answer retry, provider cost (K1, D35); AIMD limits and one retry policy (K11, D34); 429 pauses the service and is waited out (D43) |
| `normalize.py`, `spans.py`, `markup.py` | ✅ | Offset-preserving normalisation, span maths, Markdown/LaTeX parsing |
| `checks/deterministic.py` | ✅ | script/language, format, length, reference; tables pass (P2) |
| `checks/roundtrip.py` | ✅ | back-translation + DP alignment, numbers, entities, term consistency; K3, K6 fixed and tables pass (P2) |
| `checks/judge.py` | ✅ | token-index judge, strict schema; adaptive replicas, jury, repeat-consistency, long-text windows (K2, D36) |
| `checks/speech.py`, `audio.py` | ✅ | waveform stats, ASR in ~10 s chunks at pauses (29 s where needed), alignment, second opinion on long chunks; time map with ASR anchors (K5, D37); check tables pass (P4) |
| `fusion.py` | ✅ | clustering + noisy-OR + thresholds; K8 fixed (P2) |
| `calibrate.py` | ✅ | matching, metrics, per-category tuning, 2-fold CV |
| `dataset.py` | ✅ | loader + one-pass calibration file; K4, K10 fixed in P1 |
| `generate.py` | ✅ | translation fill-in, budgeted speech planner, TTS chunking |
| `cli.py`, `pipeline.py` | ✅ | P1: the runnable command; judge flags added in P3 (D17) |
| `testing/stub_server.py` (+ fakes) | ✅ | P1 — local HTTP stub for Bodhan + OpenAI-compatible endpoints, fault injection |
| `report.py` | 🟡 | P1 minimal done (deterministic files, plain summary.md); P6 polished |
| `diff.py` | 🟡 | P1 minimal (D18); P6 full |
| `inject/` (package) | ✅ | P5 — 33 methods (20 text, 7 `--with-models`, 6 speech), seeded per item and method, labels with severity; never holds an LLM client (D41); tests incl. tier-0 round trips |
| `score.py` | ✅ | P5 — hidden-test-style scorecard (`--exclude` for out-of-sample); offline inject → run → calibrate → score loop test |
| `splits.py` | ✅ | P5 — unlabelled demo set, calibration subset (40, half clean, every category) and bake-off set (50 incl. 10 te, text only) from the labelled gold (DATASET_PLAN step 5) |
| `review.py` | ✅ | P5 (pulled forward from P6) — review sheet export (flagged, review queue, seeded sample of the rest; back-translation from cache) and import of the answers as `annotator: saksham` labels for `--calibration`; P6 adds the review-queue view |
| `bakeoff.py` | ✅ | P3 — judge model comparison; estimate + `--max-usd` refusal and stop; mini run done, full run after P5 (D33) |
| `api.py` | ✅ | P6 — `Harness.check_translation / check_speech / evaluate`, no CLI imports |
| extras: `mqm.py`, `dashboard.py`, `voices.py`, CI mode, `api.py` | ✅ | P6 — MQM per language, checks-that-could-not-run table, `--fail-on-regression` (exit 3), static dashboard, voice comparison, library API |

## Known issues in the drafts (fix in the phase noted)

- ✅ fixed in P3 — **K1 (P3) `clients.LLMClient`**: implement the response-format fallback chain `json_schema (strict)` → `json_object` → plain prompt, remembering per model what worked. Add `--llm-extra-body '<json>'` merged into requests via `extra_body` (e.g. OpenRouter `{"reasoning": {"effort": "low"}}` to cap reasoning tokens) — optional, off by default, so the harness stays provider-neutral. If `message.content` is empty (reasoning models that used all `max_tokens`), retry once with double `max_tokens`. Record provider-reported cost when the response includes it.
- ✅ fixed in P3 — **K2 (P3) `checks/judge.py`**: (a) adaptive replicas — run 2; if their category sets disagree, run a 3rd and take the majority (`--judge-max-replicas`, default 3); (b) `--judge-models a,b,c` jury using the same base URL/key, falling back to `LLM_MODEL`; (c) repeat-consistency: on a deterministic sample (`--judge-repeat-sample 0.1`), re-send the *identical* prompt with a cache-bypass marker in the cache key only (not in the prompt) and report agreement separately from order-consistency; (d) translations over ~1,200 tokens: judge in overlapping windows of segments and offset token indices back.
- ✅ fixed in P2 — **K3 (P2) `BackTranslationCheck`** stores `extra_min/extra_share` on the shared check instance; pass them as locals to `_partial`.
- ✅ fixed in P1 — **K4 (P1) `dataset.apply_calibration_file`** reads the file twice; restructure into one pass and unit-test the three line shapes (full item, id+lang+labels, id+labels).
- ✅ fixed in P4 — **K5 (P4) speech localisation**: time→char mapping is proportional. Improve with chunk anchors: each ASR chunk has a known time range; align chunk transcripts separately so word positions inherit chunk times.
- ✅ fixed in P2 — **K6 (P2) entities**: cap transliteration calls per item; batch unique entities across the dataset first (dedupe) to save calls.
- ✅ fixed in P2 — **K8 (P2) fusion**: an unlocated signal (no span, no source span) of category C should join the strongest existing cluster of C instead of producing a separate flag.
- ✅ fixed in P1 — **K10 (P1) language codes**: normalise `hi-IN`/`HI` → `hi` (warn once); keep script variants (`ks-Deva`, `mni-Beng`, `sd-Arab`).
- ✅ fixed in P1 — **K12 (P1) type checking**: `mypy` currently reports 41 annotation-level errors in the drafts (mostly `arg-type`/`index` on `Optional` spans and untyped empty lists in calibrate.py, roundtrip.py, deterministic.py, speech.py, judge.py, clients.py). Fix them so `make check` is green; no behaviour changes.
- ⬜ open — **K15 (P5/P6) false alarms left after the clean-run review (D45)**: (a) ✅ fixed by D46: `entities` alone flagged 6 names that were translated or written as exonyms (BCE -> கி.மு, Part IX -> নবম ভাগ, Satluj -> শতদ্রু) or transliterated differently (Satluj -> சட்லஜ், Buisson -> பியூசன்); a missing name alone now stays below the flag threshold; (b) `asr` `speech_garbled` on a table whose units and '=' Indic-Speak read out in English (CER 88 %); (c) judge nitpicks (3). Fixed in P5: an English gloss in brackets after its translation is not wrong language; table divider rows are no longer sent to Indic-Speak.
- ⬜ open — **K13 (P6/P7) format localisation**: a deleted table separator row is detected (line counts change) but not located (signal has no span); with several bold pairs, an unmatched `**` is reported at the last marker, not the broken pair. Both found by the injector (P5).
- ✅ fixed in P5 — **K14 (P5) false alarms in the clean run** (180 real Bodhan outputs, 23 Nov), all generic: (a) `entities` took position capitals for names: sentence-initial function words ("Near Earth", "The Green Revolution"), table header cells mid-line, bold list items, and words capitalised only at line starts ("- Be protected"); (b) `format` counted `b^{2}` vs `b^2` as a LaTeX change; (c) `numbers` treated a number written as part of a token on one side and standalone on the other as missing/extra ("B12" vs "बी 12", "m/s²" vs "মি/সেকেন্ড২"; D44). Also found in that run: ASR chunk plan crash on 14-18 s of unbroken sound, and 429 retries running out (D43).
- ✅ fixed in P3 — **K11 (P3) adaptive concurrency**: on 429, halve the service's concurrency (min 1); after 20 consecutive successes, +1 up to the configured max (AIMD, like TCP congestion control).

## P1 — Foundation and the runnable command

Build:
- `testing/stub_server.py`: a tiny `http.server` that serves `/translate`, `/transliterate`, `/v1/audio/speech`, `/v1/audio/transcriptions` and `/chat/completions` with scripted, deterministic responses (lookup tables loaded from a fixture JSON). Tests point `BODHAN_BASE_URL` and `LLM_BASE_URL` at it, so the **exact CLI and real HTTP clients** are exercised with no special test code paths in the harness. It can also inject 429/5xx/413 for retry tests.
- `pipeline.py`:
  1. `Settings.from_env()`, `Cache(--cache-dir, default .cache/bodhan_eval)`, `Budget(--max-cost-inr)`, clients, JSONL event log at `<out>/logs/events.jsonl`.
  2. Load dataset (+ calibration file). Count bad lines, filtered items, notes.
  3. If `--generate`: fill translations (thread pool), plan speech (`generate.plan_speech`), synthesise to `<out>/audio/`, write `<out>/generated.jsonl` (paths relative to `<out>`).
  4. Pre-pass stats per language: length log-ratio median and MAD×1.4826 (n ≥ `length_min_items_per_lang`), speaking rate chars/active-second (n ≥ `rate_min_items_per_lang`). Store in `DatasetStats`.
  5. Per item in a `ThreadPoolExecutor` (`--concurrency`, default 6 per service): run `TRANSLATION_CHECKS` then `SPEECH_CHECKS` in order; wrap each call: `SkipCheck`→skipped(reason), `ServiceUnavailable`→skipped(no key), `BudgetExceeded`→skipped(budget), `BodhanError`/other→error(msg). Record per check `{status, reason, ms, signals, cache_hits}` and log an event.
  6. Dataset-level checks (`DATASET_CHECKS`).
  7. Thresholds: defaults → `--thresholds file.json` → `calibrate.tune` when labelled items exist; also `cross_validated`.
  8. `fusion.fuse` every item; compute `evaluate`, `per_check`, `judge_consistency`.
  9. `report.write_all`, `diff` if `--baseline`, extras.
  10. Exit 0; 1 if the dataset is unreadable or has no valid items; CI mode code in P6.
- `cli.py`: argparse with the required flags plus: `--cache-dir`, `--concurrency`, `--thresholds`, `--no-judge`, `--judge-replicas`, `--judge-max-replicas`, `--judge-models`, `--judge-repeat-sample`, `--no-speech`, `--speech-sample`, `--voice lang=Name`, `--label-span-on {translation,source}`, `--llm-extra-body`, `--llm-inr-per-1k-tokens`, `--log-level`. `--langs` also accepts `all`.
- `report.py` (minimal): `items.jsonl`, `summary.json`, `calibration.json`, a plain `summary.md`; deterministic serialisation helpers.

Gate P1 (**passed 23 Nov**: `make check` green, 221 tests): `make check` green; e2e test runs the exact command against the stub server on a 10-item dataset (hi/ta/bn + one unknown code + one broken line + one missing audio) and asserts the 5 files; rerun → identical bytes and ₹0 spent; unit tests for normalize, spans, markup, cache, budget, dataset.

## P2 — Translation checks hardened

- Fix K3, K6, K8. For each check write a table-driven test file with **must-catch** and **must-not-flag** cases (see TESTING.md §2). Include every Indic digit system, Indian grouping, `H2O`/`CO2`, translated `\text{}`, table header translations, kept English names, legitimate reordering.
- Gate P2 (**passed 23 Nov**: `make check` green, 313 tests; clean suite 0/20 flagged): all deterministic-check tests pass; false-alarm suite (clean fixtures) produces zero flags from tier-0 checks.

## P3 — Judge and LLM layer

- Fix K1, K2, K11. Write `bakeoff.py`: runs tiers 0–1 + judge only on a labelled set for each model in `--models`, prints per-category precision/recall, both consistency rates, invalid-output rate, tokens and cost; refuses to start if the estimated cost exceeds `--max-usd`.
- Live smoke: 5 items, 1 cheap model, `--max-cost-inr 2`.
- Gate P3 (**passed 23 Nov**: `make check` green, 416 tests; live smoke 5 items on `openai/gpt-6-luna`, json_schema, injected error flagged, 0 false alarms, ₹0.62 budgeted / $0.0014 charged; mini bake-off table produced, full panel run moved after P5 by Saksham, D33): judge parsing tests (bad JSON, out-of-range indices, unknown category, Indic text in explanation masked); stub-server tests for each response-format fallback; bake-off table produced (see LLM_BAKEOFF.md).

## P4 — Speech

- Fix K5. Synthetic-audio tests (numpy): inserted silence, clipping, noise burst, truncation, repetition, >30 s chunking, MP3 via ffmpeg. Alignment tests on word lists for omission/tail/repetition/n-gram loop. Second-opinion dismissal test (stub returns the missing words on the alternative chunking).
- Live smoke: `--generate` on 3 items per language with speech, `--max-cost-inr 3`.
- Gate P4 (**passed 23 Nov**: `make check` green, 459 tests + 1 skipped without ffmpeg (runs in CI); live smoke 9 items hi/bn/ta with `--generate`, ₹0.26: valid 24 kHz WAVs, ASR CER 0-2 %, duration ratios 0.75-1.41, 0 flags after the D38 fix; two clips sent to Saksham to listen): tests pass; live audio files play correctly; duration/rate stats sensible.

## P5 — Injector, calibration, scorer, demo data

- `inject.py` — `python -m bodhan_eval.inject --dataset clean.jsonl --out injected.jsonl [--rate 0.5] [--seed 7] [--langs ...] [--categories ...] [--audio-out dir] [--with-models]`. Per item, a seeded RNG (hash of seed+id+lang) chooses clean or one category applicable to the item; several **methods per category** and **three severities**:
  - omission: delete a sentence / a clause / a short phrase (label span on source when sentence-aligned, else zero-width target span);
  - addition: insert a sentence from another same-language item / duplicate-with-variation / (with models) add an English clause and re-translate;
  - mistranslation (with models): antonym/negation/relation swap in English from a fixed list, re-translate, label the diff span;
  - number: change a digit / swap units (via English + re-translate) / change a date or decimal;
  - term: replace an entity with another entity's rendering from the dataset / corrupt a transliteration;
  - format: drop a table pipe, delete a table row separator, remove a closing `$`, unbalance `**`, drop a heading marker, alter a LaTeX command;
  - wrong_language: replace with the source English / one sentence left in English / swap in the same item's other-language output;
  - speech: cut the tail (truncation), remove a middle stretch between pauses (omission), duplicate a stretch (repetition), insert 2–4 s silence, add a noise burst, hard-clip a region (garbled). Label span by proportional time→char.
  Labels carry `"annotator": "injector:<method>"`. The injector must never touch the LLM client (tested).
- `score.py` — hidden-test-style scorecard from a report + gold labels: recall, false-alarm rate, localisation, category accuracy, per error type and per language.
- Demo dataset (see DATASET_PLAN.md): ≥100 items hi/ta/bn (aim 150–180), Markdown + tables + LaTeX share ≥25%; `--generate` run; inject; Saksham labels ~30 items himself (`"annotator": "saksham"`).
- **Full judge bake-off** (moved here from P3, D33): build `data/bakeoff.jsonl` (LLM_BAKEOFF.md step 1), `--dry-run` for the estimate on the real set, show it to Saksham, run the 8-model panel, report the table and a recommended default judge; record the choice in DECISIONS.md after his confirmation.
- Gate P5: injector → harness → `calibration.json` loop works; CV metrics reported; demo report generated; bake-off table produced.

## P6 — Reports and extras (overdelivery)

- `summary.md`: headline table (items, flagged, per-category counts, MQM score per language, cost of outputs used, skipped/bad counts); quality targets table (target vs achieved, with "why" lines for misses, generated from a per-category limitations dictionary); top 10 failures with span text and evidence; per-language and per-category tables; regressions summary when a baseline is given; uncertain-items count with pointer to the review CSV.
- `diff.py` → `diff.md`: match items by `(id, lang)`; flags matched by category group + span overlap; sections: headline deltas per language/category (flag rate, MQM, chrF++, ASR CER), regressions (new flags, severity-sorted, with evidence and span text), improvements, unchanged, items added/removed; warn if thresholds/config hash differ between runs.
- `mqm.py`: penalties minor 1 / major 5 / critical 10; score = max(0, 100 − 100·penalty/source_words) per item and per language.
- `review.py`: `review_queue.csv` of uncertain flags, dismissed candidates and judge-disagreement items (columns: id, lang, category, span, text, evidence, suggested_label, your_label, notes); `--review-answers file.csv` re-ingests answers as labels with `annotator: "saksham"` and re-calibrates.
- `dashboard.py`: one static `dashboard.html` (vanilla JS, data embedded as JSON) with filters by language, category, severity, check; per-item view with highlighted spans.
- `voices.py`: `--compare-voices "hi=Kavya,Amit;ta=Anitha,Arun"` (+ `--compare-sample N`, styles optional) → synthesise the same items per voice, run speech checks, paired comparison table per voice (flag rates, ASR CER, duration ratio) in `voices.md`.
- CI mode: `--fail-on-regression` (+ `--max-new-major N`, `--max-mqm-drop X`) exits 3 when exceeded.
- `api.py`: `Harness(settings=None, cache_dir=...)` with `check_translation(source, translation, lang, reference=None) -> list[Flag]`, `check_speech(text, audio_path_or_bytes, lang) -> list[Flag]`, `evaluate(items) -> RunResult`. Thread-safe, no CLI imports. Used later by the dubbing/narration project as a QA gate.
- Gate P6: report review by Saksham ("can a model team act on this in 10 minutes?"); determinism test still passes with extras on.

## P7 — Exam, robustness, packaging, submission

- Independent exam (EXAM_SEEDER_BRIEF.md) in a separate folder; run once; record results honestly in README/PR.
- Robustness matrix (TESTING.md §6). Clean-clone + Docker test. `make validate` against the Cookbook.
- README (Setup, Run, How it works, Results, Limitations, Cost and runtime, AI assistance), ARCHITECTURE diagrams, design notes, sample report committed under `sample_report/` (text files only), audio hosted externally and linked, ≤5-min demo video.
- **Public-repo gate:** scan full git history for secrets/forbidden files (PROMPTS.md §F2), then ask Saksham to make the repo public and wait for confirmation.
- Export to the Cookbook fork and open the PR (SUBMISSION.md), after Saksham approves the PR text.
