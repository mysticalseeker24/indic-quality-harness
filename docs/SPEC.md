# Agentic Engineer Take-Home: Translation and Speech Quality Harness

Nov 13, 2026 · @Ishvinder

## Overview

Build an agentic evaluation harness that finds and explains quality problems in Bodhan's Indic-Translate and Indic-Speak outputs, and ship it as a pull request to the Bodhan AI Cookbook. This is one of four take-home assignments; pick the one that fits you best.

We will run your harness on a dataset you have never seen, seeded with errors only we know about. A harness tuned to its own demo data will not pass, however polished its reports look.

What we are assessing:

- **Orchestration judgment** — which checks are deterministic, which need a model round trip, and where an LLM judge truly adds signal.
- **Versatility** — new languages, content types and error types handled without code changes.
- **Evaluation rigour** — errors caught, false alarms avoided, and every flag backed by evidence.
- **Engineering hygiene** — reproducible setup, clear docs, cached and deterministic runs, tests, and graceful failure.

Expected effort is roughly 10–12 focused hours. We would rather see a few trustworthy checks than many noisy ones.

## The assignment: translation and speech quality harness

Your harness takes a dataset of English source texts, scores the Indic-Translate translations and Indic-Speak audio for each item, flags specific errors with evidence, and reports what changed between two runs. It must run unattended on a dataset it has never seen.

**What it must do**

1. Read a JSONL dataset whose items may include a reference translation, existing system outputs (text or audio) and human labels. Score supplied outputs, or generate missing ones with Indic-Translate and Indic-Speak when asked.
2. Check translations: reference-based scores where references exist, plus reference-free checks such as back-translation to English, number and entity preservation, and Markdown or LaTeX integrity.
3. Check speech: back-transcribe with Indic-Transcribe and compare with the input text, detect repetition and omission, and sanity-check duration, silence and clipping.
4. Run an LLM judge with a written rubric that names each error, its category and severity, and the exact span it refers to.
5. Calibrate against the human-labelled items: report precision and recall per error category, and tune thresholds from that, not by guesswork.
6. Include an error injector that creates labelled test cases from clean items, so you can measure your own harness.
7. Write a report: per-item flags with evidence, per-language and per-category summaries, cost, and a diff against a baseline run.

**Error types to cover.** The hidden set seeds errors from this list, plus clean items.

| Area | Error type | What it looks like |
| --- | --- | --- |
| Translation | Omission | A clause or sentence of the source is missing |
| Translation | Addition | Content that is not in the source |
| Translation | Mistranslation | A word or phrase with the wrong meaning |
| Translation | Number or unit | A digit, date, unit or quantity changed |
| Translation | Term or entity | A name or technical term rendered wrongly or inconsistently |
| Translation | Format | Broken Markdown, tables or LaTeX |
| Translation | Wrong language or script | Output in another language, or text left untranslated |
| Speech | Omission or truncation | Words or the end of the text not spoken |
| Speech | Repetition | A phrase spoken twice or looped |
| Speech | Garbled audio | Noise, long silences or unintelligible stretches |

**Languages.** Your demo dataset must cover Hindi, Tamil and Bengali, with at least 100 items in total. The `--langs` flag must accept any of Indic-Speak's 13 production-tier languages; we will test at least one you did not demo.

**The hard parts.** This is where we expect your agentic design to show:

- **No references.** Most real content has no reference translation, so reference-free checks must carry the load.
- **Noisy checkers.** Back-translation and back-transcription make their own mistakes. Separate system errors from checker errors before you flag anything.
- **Judge reliability.** LLM judges drift between runs, favour fluent output and vary by language. Measure consistency and calibrate.
- **Localization.** "Score 3.2" helps nobody. Say what is wrong and where.
- **Script and normalization.** Comparing "२५" with "25", Unicode variants and punctuation needs careful normalization before any error rate means anything.
- **Cost.** Speech synthesis is the expensive step. Cache everything and sample deliberately.

**Stretch goals (optional bonus)**

- MQM-style severity weighting with an aggregate quality score per language.
- A review queue: export uncertain items as a CSV for human labelling, then re-calibrate from the answers.
- A static HTML dashboard with filters by language, category and severity.
- A comparison mode for Indic-Speak voices or generation settings.
- A CI mode that exits non-zero when a regression passes a threshold.

## Ground rules

Every translation, speech-synthesis and speech-recognition call, including round-trip checks, must go to a Bodhan model. Breaking this rule fails the submission, however good the report.

| Model | Use it for | Open weights | Hosted price |
| --- | --- | --- | --- |
| Indic-Translate | Generating translations and back-translations | [indic-translate](https://huggingface.co/bodhan-ai/indic-translate) | ₹0.20 per 10,000 output tokens |
| Indic-Speak | Generating speech | [indic-speak](https://huggingface.co/bodhan-ai/indic-speak) | ₹6 per 10,000 input characters |
| Indic-Transcribe (Core or Flex) | Back-transcribing speech | [Core](https://huggingface.co/bodhan-ai/indic-transcribe-core), [Flex](https://huggingface.co/bodhan-ai/indic-transcribe-flex) | ₹0.10 per input audio minute |

**Access.** Use the hosted API or self-host the open weights; both count. The hosted API is OpenAI-compatible at `https://api.bodhan.ai/v1`, with keys issued per model from the [Bodhan console](https://console.bodhan.ai/) ([API docs](https://console.bodhan.ai/api-docs/)). New accounts get ₹10 of credit; tell us if you need more.

**Where the LLM fits.** Use any general-purpose LLM as the judge and the brain of the harness: reading outputs against sources, categorizing and localizing errors, deciding which items need a costly speech check, and explaining findings.

- The LLM may read Indian-language text to judge it, but must never write, rewrite or "correct" it. The harness evaluates; it does not fix.
- The error injector must create Indian-language errors programmatically (deleting spans, changing digits, swapping terms) or by perturbing the English source and re-translating, never by having the LLM write Indian-language text.
- Read the LLM endpoint from `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY`, using an OpenAI-compatible client. We will run your code against our own provider.

**Not allowed.** Any other speech-recognition, machine-translation or TTS system, and learned quality-estimation models such as COMET, so that the harness depends only on Bodhan models and the LLM.

**Allowed without asking.** String-based metrics such as chrF++ and BLEU (for example via sacrebleu), Unicode and Indic-script normalization libraries, ffmpeg and audio libraries for silence and clipping checks, and orchestration frameworks of your choice, or none.

**Also note**

- AI coding assistants are allowed and expected for this role. Say briefly how you used them; you must be able to explain every line in the debrief.
- Never commit keys. Ship a `.env.example` instead.
- Build your demo dataset from text you have the right to use, and keep generated audio out of git: link it from the README instead.
- Label every human annotation you add yourself, so we can tell your labels from ours.

## Technical requirements

We will run your harness with exactly this command, so keep the interface stable. Extra flags are fine; required ones must not change.

```
python -m bodhan_eval \
  --dataset path/to/data.jsonl \
  --langs hi,ta,bn \
  --out ./report \
  [--generate] [--baseline ./previous_report] [--calibration labels.jsonl] [--max-cost-inr 50]
```

`--generate` creates missing translations and audio with Bodhan models; without it, the harness scores only the outputs supplied in the dataset.

**Dataset format.** One JSON object per line. Only `id`, `source` and `lang` are required; the rest are optional.

```json
{"id": "sci-042", "source": "Water boils at 100 °C at sea level.", "lang": "hi", "reference": "<reference translation>", "translation": "<system translation>", "audio": "audio/sci-042.hi.wav", "labels": [{"type": "number", "severity": "major", "span": [14, 20]}]}
```

**Output layout.**

```
report/
  summary.md        # headline numbers, top failures, regressions
  summary.json      # metrics per language and per error category
  items.jsonl       # per item: checks run, flags with category, severity, span and evidence
  calibration.json  # checks and judge vs human labels: precision and recall per category
  diff.md           # only with --baseline: what improved, what regressed, with examples
```

**Configuration.** Read Bodhan keys from `BODHAN_TRANSLATE_KEY`, `BODHAN_SPEAK_KEY` and `BODHAN_TRANSCRIBE_KEY`, and the LLM settings described in Ground rules. No other secrets.

**Quality targets.** These are targets, not pass/fail gates. Report in `summary.md` where you miss them on your own injected data, and why.

| Check | Target |
| --- | --- |
| Detection recall | At least 80% of seeded errors flagged |
| False alarms | At most 10% of clean items flagged |
| Localization | The flagged span overlaps the seeded error for at least 70% of detections |
| Category accuracy | At least 70% of detected errors given the right category |
| Judge consistency | Re-judging an item gives the same verdict at least 90% of the time |
| Determinism | A rerun from cache produces an identical report at no model cost |
| Runtime | 200 items in 3 languages, with speech checks, in under 30 minutes on hosted APIs |

**Engineering expectations**

- One-command setup from a clean clone with pinned dependencies. Document system dependencies such as ffmpeg; a Dockerfile is recommended.
- Bad or partial items must not stop the run. Log them, skip them, and count them in the summary.
- Retries with backoff, a concurrency limit for API calls, and a cache of every model output keyed by its exact input.
- Structured logs per check and per item, so any flag can be traced to the evidence behind it.
- Unit tests for normalization, span alignment and each deterministic check, plus one end-to-end test on a 10-item dataset.

**Folder layout.** Follow the Cookbook's contribution guide. If it does not define one, use:

```
<your-recipe-folder>/
  README.md
  walkthrough.ipynb      # optional, short guided demo
  pyproject.toml
  .env.example
  data/demo.jsonl        # your demo dataset, text only
  src/bodhan_eval/
  tests/
```

## Submission

Submit by opening a pull request to the [Bodhan AI Cookbook](https://github.com/Bodhan-AI/Bodhan-AI-Cookbook), then replying on the email thread where you received this assignment with the PR link and the final commit SHA. We evaluate that exact commit; later pushes are ignored.

1. Fork the [Bodhan AI Cookbook](https://github.com/Bodhan-AI/Bodhan-AI-Cookbook) and read its [CONTRIBUTING.md](https://github.com/Bodhan-AI/Bodhan-AI-Cookbook/blob/main/CONTRIBUTING.md).
2. Create a branch named `assignment/quality-harness-<github-handle>`.
3. Add your recipe as one self-contained folder under `examples/`, following the Cookbook's template, and run `make check` before opening the PR.
4. Open a PR titled `[Agentic Eng Assignment] Quality harness — <your name>`, using the description template below.
5. Reply on the email thread where you received this assignment with the PR link and commit SHA, before the deadline.

The PR is public. Do not include anything confidential, and note that merging is up to the Cookbook maintainers and is separate from our hiring decision.

**What the PR must contain.** A complete description using the template below, plus documentation of your solution inside the recipe folder:

- An architecture diagram showing the checks, the judge, the cache and how they connect.
- A flow chart from dataset to report, showing which checks run in which order and when costly checks are triggered.
- Harness design notes: each check, the judge rubric, calibration against human labels, and how results combine into flags.
- A recorded demo video of five minutes or less, showing a full run on your demo dataset and a walk through the report.

Diagrams can be Mermaid in Markdown or images. Host the video anywhere we can open without signing in.

**PR description template**

```markdown
## Summary
What the harness does, in two or three sentences.

## How to run
Setup and the exact command, from a clean clone.

## Architecture
A diagram of the checks and how results combine, and one line per check.

## Harness design
A flow chart from dataset to report, the order of checks, and when costly checks run.

## Where the LLM is used, and why
The judge rubric, other LLM decision points, and how you measured the judge.

## Bodhan models used
Model, hosted or self-hosted, and any settings you tuned.

## Results
Recall, false alarms and localization on your injected data, per category and language.

## Demo video
Link to a recording of five minutes or less: a full run and the report.

## Trade-offs and known limitations
Error types you miss, and why.

## Cost and runtime
Per 100 items, with and without speech checks.

## AI assistance
Which coding tools you used and for what.
```

**Before you submit**

- [ ] Runs from a clean clone with the documented setup and command
- [ ] Only Bodhan models are used for translation, speech synthesis and speech recognition
- [ ] No API keys, tokens or generated audio in the repo
- [ ] README covers the checks, setup, usage and limitations, and links the architecture diagram, flow chart and design notes
- [ ] Demo dataset of at least 100 items across Hindi, Tamil and Bengali, with injected errors and a labelled subset
- [ ] A sample report from your demo dataset, linked from the README
- [ ] Tests pass locally
- [ ] Demo video of five minutes or less, linked from the README and the PR

## How we evaluate

We score each submission out of 100, mostly from running your harness on a hidden dataset seeded with known errors. Your demo report shows intent; the hidden run shows whether the checks generalize.

**The hidden test set** has about 200 items across four or five languages, including at least one you did not demo. Content ranges from short sentences to Markdown passages with tables and LaTeX. Roughly half the items are clean; the rest carry seeded errors from the list above at varying severity. A small human-labelled subset is provided for calibration, and we also supply two runs of the same items so we can check your baseline diff.

**Process**

1. **Setup check.** We build your commit in a fresh container from a clean clone. If setup fails, we contact you once and allow a setup-only fix within 24 hours.
2. **Hidden run.** We run the documented command on the hidden dataset, with our own Bodhan keys and our own LLM, once plain and once with `--baseline`.
3. **Scoring against our labels.** We measure recall, false alarms, localization and category accuracy per error type and language.
4. **Report review.** We judge whether `summary.md` and `diff.md` would let a model team act on the findings.
5. **Code and design review.** We read the code, the calibration output and your PR description.
6. **Debrief (60 minutes).** You walk us through the design, add a new error check live, and discuss what you would do next.

**Rubric**

| Dimension | Weight | What full marks looks like |
| --- | --- | --- |
| Versatility on the hidden set | 20 | Runs on the hidden dataset and unseen languages without code changes |
| Detection quality | 30 | High recall and few false alarms across categories, with correct spans and categories |
| Harness and agentic design | 25 | Cheap checks first, costly checks where they pay off, a calibrated judge, separation of checker noise from real errors |
| Engineering quality | 15 | Reproducible setup, deterministic cached runs, tests, useful logs, cost awareness |
| Documentation and reports | 10 | A model team can act on the report in 10 minutes; limitations are stated honestly |
| Stretch goals | +10 bonus | Working, documented extras from the stretch list |

**Automatic fail**

- Any non-Bodhan speech-recognition, translation or speech-synthesis system, or a learned quality-estimation model, anywhere in the harness.
- An LLM writing, rewriting or correcting Indian-language text.
- Thresholds or rules special-cased to your demo dataset.
- Secrets committed to the repository.

## Timeline, FAQ and help

You have 7 calendar days from receiving this document. Plan for about 10–12 hours of work; if you run short, stop and write what you would do next in the README.

Send questions about the assignment to <ishvinder@bodhan.ai>.

**Do I need a GPU?** No. The hosted APIs are enough; self-hosting the open weights is optional.

**Where do I get source text and labels?** Use openly licensed English text, such as educational content, generate translations and audio with Bodhan models, then inject errors. Label a small subset yourself and say so.

**Do I need reference translations?** No. Support them when present, but the harness must work without them.

**Which LLM will you run it with?** An OpenAI-compatible endpoint of our choice. Name the model you tested with in the PR, and avoid provider-only features unless you add a fallback.

**Can I submit just a notebook?** No. A runnable command is required; a short notebook walkthrough is welcome on top.

**What if the Bodhan API is slow or down while I work?** Note it in the PR with times; we account for outages. Cache results so reruns do not repeat paid calls.
