# Translation and Speech Quality Harness for Bodhan Indic models

An agentic evaluation harness that finds, localises and explains quality problems in **Indic-Translate** translations and **Indic-Speak** audio: every flag says what is wrong, where (character span), how severe, and the evidence behind it. It calibrates itself against human labels, compares runs, and works on languages it has never seen.

**Bodhan models:** indic-translate, indic-transliterate, indic-speak, indic-transcribe
**Languages shown:** Hindi, Tamil, Bengali (any language in `src/bodhan_eval/data/langs.json` works)
**Format:** CLI (`python -m bodhan_eval`) and Python library

> 🚧 Work in progress. Sections marked TODO are filled from real runs.

## What it does

Input: a JSONL file of English sources with optional reference translations, system outputs (text or audio) and human labels. Output: a report folder with per-item flags and evidence, per-language and per-category summaries, calibration against labels, cost, and a diff against a baseline run. Cheap deterministic checks run first, Bodhan round trips next, and the LLM judge and costly speech checks only where they pay off.

## Setup

```bash
git clone https://github.com/mysticalseeker24/indic-quality-harness.git
cd indic-quality-harness
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # or: make setup  (adds test tools)
cp .env.example .env                     # then add your Bodhan keys and judge LLM settings
```
System dependency: `ffmpeg` (only for non-WAV audio). Or use Docker: `docker build -t bodhan-eval .`

## Run

```bash
python -m bodhan_eval \
  --dataset data/demo.jsonl \
  --langs hi,ta,bn \
  --out ./report \
  [--generate] [--baseline ./previous_report] [--calibration labels.jsonl] [--max-cost-inr 50]
```

## How it works

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the architecture diagram, the flow chart, every check, the judge rubric, calibration and how results combine into flags.

## Results

TODO: recall, false alarms, localisation and category accuracy on injected data, per category and language; judge model comparison.

## Sample report

TODO: link `sample_report/summary.md`, the dashboard, and hosted demo audio.

## Demo video

TODO

## Limitations

TODO: error types we miss and why.

## Cost and runtime

TODO: per 100 items, with and without speech checks.

## AI assistance

- **Design and research:** Claude (claude.ai) helped read the assignment and the Bodhan API docs, compare check designs, and draft the architecture, test plan and build plan.
- **Implementation:** Claude Code wrote code and tests phase by phase against that plan. Each phase ended at a gate: `make check` (ruff, mypy, pytest) plus that phase's acceptance tests.
- **Review and decisions:** the author approved every default, threshold and interface change, set the spending caps for live API runs, and reviewed every change; every line is explainable in the debrief.
