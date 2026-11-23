## Summary

A quality harness for Bodhan's **Indic-Translate** and **Indic-Speak** outputs: it finds, localises (character spans in the translation or the source), grades (minor / major / critical) and explains errors in translations and speech, calibrates itself against human labels, compares runs (with a CI gate), and works on languages it has never seen. One command, one report folder; every flag traces back to its evidence. Full source and history: https://github.com/mysticalseeker24/indic-quality-harness (snapshot of commit `SRC_SHA`).

## How to run

```bash
pip install -r requirements.txt && cp .env.example .env   # Bodhan keys + any OpenAI-compatible judge
python -m bodhan_eval --dataset data/demo.jsonl --langs hi,ta,bn --out ./report \
  [--generate] [--baseline ./previous_report] [--calibration labels.jsonl] [--max-cost-inr 50]
```

Or `docker build -t bodhan-eval . && docker run --env-file .env -v "$PWD:/work" bodhan-eval --dataset /work/data/demo.jsonl --langs hi,ta,bn --out /work/report`. `make check` runs lint, types and the test suite with no keys. Demo audio: release `demo-audio-v1` (unzip at the recipe root).

## Architecture

Mermaid architecture diagram and flow chart in `docs/ARCHITECTURE.md`: dataset → (optional `--generate`) → per-language pre-pass → per item, cheap to costly: tier 0 deterministic checks (script/language, Markdown/table/LaTeX format, length, reference chrF++, waveform stats) → tier 1 Bodhan round trips (segment-wise back-translation with DP alignment, numbers, names via Indic-Transliterate, chunked transcription with word alignment and a second opinion) → tier 2 LLM judge (token-index answers, re-ordered replicas) → fusion → calibration → reports. A content-addressed SQLite cache makes reruns free and byte-identical; a reserve-before-spend budget enforces `--max-cost-inr`; adaptive per-service concurrency waits out rate limits instead of dropping checks.

## Harness design

- **Checks emit signals; only fusion makes flags.** Signals pointing at the same place are clustered and combined (noisy-OR) per category; a per-category threshold (calibrated from labels when there are ≥5) decides flag, review queue or nothing. Weak hints (length outliers, a name not found) never flag alone.
- **Judge rubric** (`src/bodhan_eval/data/judge_rubric.md`): the 7 text categories with severity rules; the translation is shown as numbered tokens and the judge answers with token indices, so spans are exact and no Indic text comes from the LLM. Two replicas with re-ordered prompts, a tie-break on disagreement, a repeat sample for consistency, windows for long texts.
- **Calibration** against human labels: matching by category group and span overlap; precision, recall, false alarms, localisation and category accuracy per category and language; thresholds tuned per category with 2-fold cross-validation reported next to in-sample numbers.
- **Measuring itself:** an injector plants 33 kinds of labelled errors across all 10 categories (text edits, re-translated English perturbations, waveform edits; it never calls the LLM), and a scorecard scores a blind run the way a hidden test would.

## Where the LLM is used, and why

Only as the tier-2 judge, for meaning errors that rules and round trips cannot see (mistranslation, omission, addition, terms, register). It reads and classifies; it never writes or corrects Indian-language text (answers are token indices and English explanations; LLM prose passes through an Indic-script filter; tested). Everything else (format, numbers, script, names, speech) is deterministic or uses Bodhan models. The bake-off of 8 judges picked `moonshotai/kimi-k3.1-pro`; any OpenAI-compatible model works, and a weak model degrades gracefully (the harness still runs its other tiers).

## Bodhan models used

`indic-translate` (generation and back-translation), `indic-transliterate` (names), `indic-speak` (generation, voice comparison), `indic-transcribe` (speech checks). No other MT/TTS/ASR, no learned quality-estimation model.

## Results

**Independent blind exam** (built in a separate project with Bodhan models only; never seen by the harness repo; run once; judge Kimi K3.1 Pro): 146 items in hi, ta, bn, te, mr and **gu (never demoed)**, 98 with audio, about half clean.

| Measure | Value |
|---|---|
| Labelled errors caught | **91.6 %** (items with an error: 96 %) |
| False alarms on clean items | **4.2 %** (3 / 71) |
| Precision / localisation / category correct | 81.5 % / 93.4 % / 98.7 % |
| Critical / major / minor errors caught | 10 / 10, 94 %, 82 % |
| Gujarati (never demoed) | 93 % caught, 0 false alarms |
| Weakest | speech repetition 3 / 6, garbled speech 5 / 7, number-flag precision 57 % |

**Demo set** (180 Bodhan outputs hi/ta/bn from NCERT-style Wikipedia passages, 75 planted errors, scored out of sample): planted errors caught 60 / 61, 0 / 24 clean items flagged, precision 88 %, localisation 84 %, category 96 %; 2-fold cross-validated item recall 85 %, false alarms 0 %.

**Bodhan's own errors found:** of 124 flags on the un-injected outputs, 101 were real (reviewed against their evidence, `data/clean_run_review.jsonl`), 10 more after the speech fixes. The biggest: **Indic-Speak silently skips text in parentheses or brackets** (36 cases; confirmed by a controlled test: same sentence 10.67 s with the bracket, 10.41 s without the bracketed words, 12.54 s with commas). Also "achieved in 2025" → "will be achieved" in all three languages, dropped names and qualifiers, wrong technical terms in Tamil, 12.011 → 12.01, flattened Markdown.

**Judge bake-off** (8 models, 50 labelled items incl. Telugu, $5.76): Kimi K3.1 Pro 96 % recall / 4 % false alarms (default), GPT-6 Luna 96 / 8 %, Gemini 4 Hydrogen 93 / 0 %, Gemini 4 Neon 100 / 12 %, DeepSeek V4.1 Flash 96 / 12 %, Claude Sonnet 5.5 93 / 20 %, GPT-6.2 Sol 100 / 28 %, Llama 3.1 8B 85 / 92 %. Full table in the README.

**Voices:** the two voices of each language get flagged on the same items (±1); the speech errors come from the text front end (brackets, numbers), not the voice.


## Demo video

[Demo video (≤ 5 min)](https://github.com/mysticalseeker24/indic-quality-harness/releases/tag/demo-video): a full run on the demo dataset and a walk through the report.

## Trade-offs and known limitations

- Spoken numbers are not verified (a number read out as words is accepted as that number; missing or looping words around it are caught).
- Speech repetition and garbling the transcriber smooths over are missed (exam: repetition 3 / 6, garbled 5 / 7); a single cut word is not reported.
- Number flags are the least precise (57 % on the exam); units read out in English in tables can look garbled.
- Names written as exonyms or translated cannot be matched by transliteration, so a missing name is only a hint and the judge decides.
- Format localisation: a deleted table divider row is detected but not located.
- The demo's real-error labels come from an AI review of the harness's own flags (marked `ai-review`), so recall on real errors is not measured there; planted errors and the independent exam measure it.
- Trade-off: the judge runs on every item with two re-ordered replicas (robust, about $0.75 per 100 items with Kimi, measured on the exam); `--no-judge` or a cheaper model cuts that.

## Cost and runtime

Checking only, per 100 items: about ₹8 with speech checks (transcription dominates) and ₹0.2 without, plus the judge (Kimi K3.1 Pro: about $0.75, measured on the exam; GPT-6 Luna about $0.06). The exam (166 items incl. calibration, 98 with audio) cost ₹3.83 + $1.24 and took 37.6 min, bound by Bodhan's rate limits, which the harness waits out instead of dropping checks; reruns from the cache take minutes and cost nothing.

## AI assistance

- Design and research: Claude (claude.ai) helped read the assignment and the Bodhan docs, compare check designs, and draft the architecture, test plan and build plan.
- Implementation: Claude Code wrote code and tests phase by phase against that plan; each phase ended at a gate (`make check` plus acceptance tests).
- Review and labels: Claude Code reviewed the flags on the real Bodhan outputs against their evidence (marked `ai-review`).
- Decisions: I approved every default, threshold and interface change, chose the judge, set the spending caps, and reviewed every change.
