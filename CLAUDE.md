# CLAUDE.md — indic-quality-harness (`bodhan_eval`)

You are building an agentic evaluation harness for Bodhan AI's Indic-Translate and Indic-Speak outputs. It is Saksham Mishra's take-home submission for Bodhan's Agentic AI Engineer role and will be graded mostly by running it **blind on a hidden dataset** (~200 items, 4–5 languages incl. one never demoed, ~half clean). He must be able to explain every line in a 60-minute debrief and add a new check live, so **clarity beats cleverness**.

## 0. Start of every session (do this first, every time)

1. Read this file, then **`docs/dev/HANDOFF.md`** (the latest state, written by the previous session), then the files HANDOFF lists under "Read next".
2. Reply with a 5-line status: current phase, last thing finished, what is in progress, the next task, any open question for Saksham. Then **wait for his "go"** before editing anything.
3. Reference docs, read when relevant: `docs/SPEC.md` (assignment, source of truth) · `docs/ARCHITECTURE.md` · `docs/dev/BUILD_PLAN.md` (phases, gates, module status, known issues K1–K12) · `docs/dev/TESTING.md` · `docs/dev/API_NOTES.md` · `docs/dev/CONVENTIONS.md` · `docs/dev/DECISIONS.md` · `docs/dev/PROMPTS.md` (Saksham's prompt playbook).

## 1. Checkpoints and handoff (so no context is lost between chats)

You cannot see your own context usage precisely, so checkpoint on these triggers:
- at **every phase gate** (always);
- when Saksham types **`checkpoint`** (he watches `/context` and does this at ~50–60 %);
- when the session has been long: roughly 25+ files read or edited, or several large test runs/outputs in this chat. In that case, finish the current small step, then **say so and propose a checkpoint** instead of starting a new task.

**Checkpoint procedure** (do all steps, in order):
1. Bring code to a consistent state: `make check` passes, or the failing part is written down precisely in HANDOFF.
2. Update `docs/dev/HANDOFF.md` (overwrite the "Current state" section; append one line to "Session log"): phase and task status, what changed this session (files), decisions made (also append to `DECISIONS.md`), open problems and exact error messages, paid runs and costs so far, the next 3 tasks, files to read next.
3. Update the status table in `docs/dev/BUILD_PLAN.md` and any docs affected.
4. Commit: `chore(checkpoint): <phase> — <one line>` (local commit only; push only if Saksham says so).
5. Print the **continuation prompt** in a fenced block, exactly in this shape, and also save it under "Next session prompt" in HANDOFF.md:
   ```
   Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
   Next up: <specific next task, e.g. "Phase 2: fix K3 and K8, then the format-check test table">.
   ```
6. Tell Saksham: "Checkpoint saved. Start a new chat in this project and paste the prompt above."

## 2. Ask Saksham first (stop and wait for an explicit yes)

- Changing the CLI contract, output file schemas, the taxonomy, the judge rubric, default thresholds, or `bodhan_eval.api` signatures.
- Adding, removing or upgrading any dependency.
- Any real API run expected to cost more than **₹5** on Bodhan or **$0.50** on the LLM; always show the estimate first. (Smaller live smoke tests: say the estimate, then run.)
- Deleting files or directories, large refactors (more than ~3 modules), rewriting git history, force-pushing, or pushing to any remote.
- Editing data or labels Saksham created (`annotator: "saksham"`).
- Anything that would read, write or depend on the exam folder.
- Moving to the next phase (show the gate result first).

## 3. Human milestones — prompt Saksham at these exact moments

| When | What you say / ask |
|---|---|
| Phase 1 gate passed | "Time to start the **independent exam project** in parallel (separate folder, separate Claude Code project). Its starter is the `iqh-exam/` folder in the starter zip (copy it to `~/code/iqh-exam`); prompts are in PROMPTS.md §E. It never sees this repo." Then continue here when he says go. |
| Before the first paid run | Confirm `.env` is filled (keys present, never print them) and the spend cap. |
| Phase 3, before the bake-off | Show the model list and cost estimate (LLM_BAKEOFF.md); wait for approval. |
| Phase 5, after the clean `--generate` run | Ask Saksham to label real errors (export a review CSV for him), and to confirm the demo dataset sources/licences (DATASET_PLAN.md). |
| Phase 7 start | Ask whether the exam set is ready; run it **once**, report numbers as they are. |
| Phase 7, before export to the Cookbook | **"Please make github.com/mysticalseeker24/indic-quality-harness public now (Settings → General → Danger Zone → Change visibility). First I will scan the full git history for secrets."** Run the history secret scan (PROMPTS.md §F2), report, and wait for him to confirm the repo is public. |
| Before opening the PR | Show the final PR description and the checklist from SUBMISSION.md; wait for approval. |

## 4. Hard rules — breaking any of these fails the submission

1. **Only Bodhan models** for translation, transliteration, speech synthesis and speech recognition, including round trips: `indic-translate` (`POST /translate`), `indic-transliterate` (`POST /transliterate`), `indic-speak` (`POST /v1/audio/speech`), `indic-transcribe` (`POST /v1/audio/transcriptions`). Never import or call any other MT/ASR/TTS system or learned language-ID model.
2. **No learned quality-estimation models** (COMET, xCOMET, MetricX, BLEURT…). sacrebleu chrF++/BLEU are allowed.
3. **The LLM never writes, rewrites or "corrects" Indian-language text.** It reads and classifies only; the judge answers with token indices; LLM prose passes through `clients.strip_indic`. No post-editing steps.
4. **The injector makes Indic errors programmatically**, or perturbs the *English* and re-translates with Indic-Translate. It never calls the LLM.
5. **Nothing special-cased to demo data.** Generic defaults (`data/defaults.json`) or run-time calibration only; language behaviour only via `data/langs.json`.
6. **No secrets in the repo.** Keys only from env (`BODHAN_TRANSLATE_KEY`, `BODHAN_SPEAK_KEY`, `BODHAN_TRANSCRIBE_KEY`, optional `BODHAN_TRANSLITERATE_KEY` (D29), fallback `BODHAN_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`). Never print key values. No realistic-looking fake keys in tests/docs. Never commit `.env`, audio or `outputs/`.
7. Model ids exactly as in the Cookbook rules file (`indic-translate`, `indic-transliterate`, `indic-speak`, `indic-transcribe`, `indic-ocr`); never Core/Flex names as ids.
8. Never open, read or search the exam folder (`../iqh-exam/`). The only allowed use: in Phase 7, pass the exact file paths Saksham gives you to the CLI, run once, and report the numbers without tuning anything in response.

## 5. The command (never change required flags)

```
python -m bodhan_eval --dataset path/to/data.jsonl --langs hi,ta,bn --out ./report \
  [--generate] [--baseline ./previous_report] [--calibration labels.jsonl] [--max-cost-inr 50]
```
Outputs: `summary.md`, `summary.json`, `items.jsonl`, `calibration.json`, `diff.md` (only with `--baseline`). Extra flags/files are fine.

## 6. Commands

```
make setup | test | lint | fmt | typecheck | check | test-live | e2e | docker
make validate COOKBOOK=/path/to/Bodhan-AI-Cookbook
```
Real runs: always `--max-cost-inr`, always `--out outputs/<name>`.

## 7. Architecture in one screen

```
dataset.py → generate.py (only --generate) → pipeline.py
   pre-pass: per-language stats from the data (length ratio, speaking rate)
   per item, cheap → costly:
     tier 0  checks/deterministic.py   script/language, format (MD/table/LaTeX), length, reference chrF++
     tier 1  checks/roundtrip.py       back-translation (segment-wise + DP alignment), numbers, entities (transliteration)
     tier 2  checks/judge.py           LLM judge, token-index spans, replicas with re-ordered prompts
     speech  checks/speech.py          waveform stats (tier 0); chunked ASR + word alignment + second opinion (tier 1)
   dataset-level checks (term consistency)
→ fusion.py (cluster signals, noisy-OR, per-category thresholds → flags / review queue)
→ calibrate.py (labels → precision/recall, per-category threshold tuning, 2-fold CV)
→ report.py / diff.py (+ extras)
Shared: cache.py (SQLite, content-addressed), budget.py (reserve-before-spend), clients.py (retries, concurrency, fallbacks)
```
Contract: **checks emit `Signal`s; only `fusion.py` creates `Flag`s.**

## 8. Coding conventions (full version: `docs/dev/CONVENTIONS.md`)

- Python ≥ 3.10, `from __future__ import annotations`, type hints on every function, `mypy` clean, `ruff` clean (format + lint).
- Pure functions in the core (normalize, spans, markup, fusion, calibrate); I/O only in clients, dataset, report, audio loading. No module-level mutable state.
- Dataclasses for data; JSON outputs with `sort_keys=True`, floats rounded to 4 dp; **no timestamps, durations or absolute paths in the five report files** (determinism).
- A bad item never stops a run: exceptions become per-check `status` with a reason.
- New check = subclass `Check` + registry entry + must-catch and must-not-flag tests + a row in ARCHITECTURE.md.
- Docstrings say *why*; magic numbers live in `data/defaults.json` with a comment.
- Tests first for deterministic logic; `make check` green before every commit.
- Conventional commits (`feat|fix|test|docs|refactor|chore(scope): summary`), one logical change each.
- The library API (`bodhan_eval.api`) stays independent of the CLI: Saksham will reuse it as a QA gate in his dubbing / narrated-lesson project.
