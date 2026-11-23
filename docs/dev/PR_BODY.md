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

RESULTS_BLOCK

## Demo video

DEMO_VIDEO

## Trade-offs and known limitations

LIMITATIONS_BLOCK

## Cost and runtime

COST_BLOCK

## AI assistance

AI_BLOCK
