# Prompt playbook — start to end

How to use: open the repo folder as a Claude Code project and paste the prompts below in order. Claude Code follows `CLAUDE.md`, so it will (a) give a status and wait for your "go" at the start of every chat, (b) stop and ask before major changes, paid runs or phase changes, (c) checkpoint at every phase gate and print the exact prompt for the next chat.

**Your habits**
- Every 30–45 minutes, type `/context`. At **~50–60 %**, type `checkpoint`. Copy the printed prompt, start a **new chat in the same project**, paste it. (The generic resume prompt in §R always works too.)
- Answer its questions with a clear yes/no. Say `go` to let it proceed.
- Keep `.env` filled; never paste keys into the chat.

---

## §S — One-time setup (you, in a terminal)

```bash
git clone https://github.com/mysticalseeker24/indic-quality-harness.git ~/code/indic-quality-harness
unzip ~/Downloads/indic-quality-harness-starter.zip -d /tmp/iqh        # contains indic-quality-harness/ and iqh-exam/
cp -r /tmp/iqh/indic-quality-harness/. ~/code/indic-quality-harness/
cp -r /tmp/iqh/iqh-exam ~/code/iqh-exam                                # separate folder, used later (§E)
cd ~/code/indic-quality-harness
python3 -m venv .venv && source .venv/bin/activate && make setup
cp .env.example .env    # fill in Bodhan keys + LLM_BASE_URL / LLM_MODEL / LLM_API_KEY (OpenRouter)
ffmpeg -version | head -1
make lint && python -c "import bodhan_eval; print('ok')"
git add -A && git commit -m "chore: starter pack (draft modules, docs, plan)" && git push
```
Then open `~/code/indic-quality-harness` in Claude Code.

---

## §R — Resume prompt (works in any new chat)

```
Resume indic-quality-harness. Read CLAUDE.md, then docs/dev/HANDOFF.md and the files it lists under "Read next". Give me the 5-line status and wait for my go.
```

## §C — Checkpoint (when /context shows ~50–60 %, or before stopping for the day)

```
checkpoint
```

---

## §P1 — Phase 1: foundation and the runnable command

```
This is the first session. Read CLAUDE.md, docs/SPEC.md, docs/ARCHITECTURE.md, docs/dev/HANDOFF.md, docs/dev/BUILD_PLAN.md, docs/dev/TESTING.md and docs/dev/CONVENTIONS.md. Give me the 5-line status and your plan for Phase 1 as a short task list, then wait for my go.
Phase 1 scope: fix K12 (mypy), K4, K10 with tests; unit tests for normalize, spans, markup, cache, budget, dataset; testing/stub_server.py; pipeline.py; cli.py; minimal report.py; the offline 10-item e2e test through the exact command, including the determinism rerun. Stop at the Phase 1 gate, show `make check` output, checkpoint, and remind me about the exam project.
```

## §P2 — Phase 2: translation checks hardened

```
Phase 2. Fix K3, K6, K8. Build the must-catch / must-not-flag test tables for script, format, numbers, back-translation, entities and length exactly as in TESTING.md §2, plus the clean-item false-alarm suite. Fix any check that fails its table — explain each fix in one line before making it. Stop at the Phase 2 gate, show results, checkpoint.
```

## §P3 — Phase 3: judge, LLM layer, bake-off

```
Phase 3. Fix K1, K2, K11 with stub-server tests for every response-format fallback and judge-parsing case. Then build bakeoff.py. Before any paid call: show me the model list from LLM_BAKEOFF.md with current OpenRouter slugs I should confirm, the item count and the cost estimate, and wait for my approval. Run a 5-item live smoke test first (cheap model, --max-cost-inr 2). Stop at the gate, checkpoint.
```

After approval of the bake-off:
```
Run the bake-off as approved. Report the table from LLM_BAKEOFF.md, recommend a default judge model with reasons, and record the decision in DECISIONS.md after I confirm.
```

## §P4 — Phase 4: speech

```
Phase 4. Fix K5. Write the synthetic-audio and alignment tests from TESTING.md §2 (audio_stats, asr rows) and §4 (chunking > 30 s, MP3 via ffmpeg). Then propose a live smoke test: --generate on 3 items per language with speech; show the estimate, wait for my go. Stop at the gate, checkpoint.
```

## §P5 — Phase 5: injector, scorer, demo dataset, calibration

```
Phase 5. Build inject.py exactly as specified in BUILD_PLAN (several methods per category, three severities, labels with annotator "injector:<method>", no LLM calls — add the test that proves it) and score.py. Then draft data/sources_en.jsonl following DATASET_PLAN.md: original English on NCERT-syllabus topics (no verbatim NCERT text), plus CC BY-SA excerpts with attribution in data/SOURCES.md. Show me 10 sample sources and the content mix before writing all of them.
```
After sources are approved:
```
Run the clean --generate on the demo sources (show the estimate first). Then export a review CSV of 40 items for me to label real errors (my labels get annotator "saksham"). Wait for my labels.
```
After you return the labelled CSV:
```
I've filled the review CSV at <path>. Ingest it, run the injector, build data/demo.jsonl and data/demo_labels.jsonl, run the full demo with --calibration, and show me calibration.json headline numbers (in-sample and cross-validated) per category and language. Stop at the gate, checkpoint.
```

## §P6 — Phase 6: reports and extras

```
Phase 6. Build summary.md (as specified), diff.py, mqm.py, review.py, dashboard.py, voices.py, CI mode and api.py. Show me summary.md and diff.md from a real demo run vs a modified second run before polishing. Voice comparison: propose voices and sample size with a cost estimate first. Stop at the gate, checkpoint.
```

## §P7 — Phase 7: exam, robustness, packaging

```
Phase 7. First ask me whether the exam set in ../iqh-exam is ready (you may not read that folder yourself until I give you the exact file paths to pass to the CLI). Then run the robustness matrix from TESTING.md §6, the clean-clone test, docker build, and make validate against a local Cookbook clone. Write README sections Results, Limitations, Cost and runtime, AI assistance from real numbers only. Commit the sample report (text files). Checkpoint.
```
When the exam is ready:
```
The exam files are ready: dataset ../iqh-exam/exam/exam.jsonl, calibration ../iqh-exam/exam/calibration.jsonl, gold ../iqh-exam/exam/labels.jsonl, run B ../iqh-exam/exam/run_b/exam.jsonl. Run the exam once (estimate first), then the baseline diff on run B, then score.py. Report the numbers exactly as they come out, add them to README "Results" with a note that they come from an independent seeder, and do not change any threshold or rule in response.
```

---

## §F — Finalise and submit

**F1 — Pre-flight**
```
We are finalising. Run the full SUBMISSION.md checklist and show me what passes and what doesn't. Don't fix anything without telling me first.
```

**F2 — Make the repo public (it will prompt you; this is the prompt it runs)**
```
Before I make the repo public: scan the entire git history for secrets and large or forbidden files (keys, .env, audio, outputs, caches): `git log --all -p | grep -nE "sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9]{36,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"` and `git log --all --name-only --format= | sort -u | grep -E "\.env$|\.wav$|\.mp3$|outputs/|\.cache/"`. Report findings. If clean, tell me to make the repo public and wait for my confirmation.
```
You then: GitHub → repo **Settings → General → Danger Zone → Change repository visibility → Public**. Reply `repo is public`.

**F3 — Export, PR text, final commit**
```
Repo is public. Follow docs/dev/SUBMISSION.md: export the snapshot into my fork at ~/code/Bodhan-AI-Cookbook on branch assignment/quality-harness-mysticalseeker24, run make check at the Cookbook root and the recipe tests from a fresh venv, and draft the PR description from the assignment template using only real numbers. Show me everything before committing or pushing.
```
```
Approved. Commit and push the fork branch, then give me the final commit SHA and the exact PR title.
```
You then: open the PR on GitHub, add the demo video link, and reply on Barry's email thread with the PR link and the SHA. Don't push to that branch afterwards.

---

## §E — Independent exam project (separate folder, separate Claude Code project)

Start this when the main project prompts you at the Phase 1 gate. It runs in parallel and never sees the harness code.

**E0 — Setup (you):** `cd ~/code/iqh-exam && git init && cp .env.example .env` (fill the Bodhan keys), then open `~/code/iqh-exam` (copied in §S) as its own Claude Code project.

**E1 — Kick-off**
```
Read CLAUDE.md and SPEC.md. Give me a short plan: languages (include te, mr, gu plus hi, ta, bn), item count, content mix, seeding methods per error type and severities, and the cost estimate for generating clean translations and audio with Bodhan. Wait for my go.
```
**E2 — Clean outputs**
```
Go. Write the English sources (original text, varied content incl. Markdown tables and LaTeX), then generate clean translations and audio with Bodhan using a small script in this folder (budget cap ₹25). Show me 5 samples per language.
```
**E3 — Seed**
```
Write your seeding code from the spec alone and produce exam/exam.jsonl, exam/labels.jsonl, exam/calibration.jsonl, exam/run_b/ with run_b_changes.json, and SEEDING_NOTES.md. Show counts per type × language × severity.
```
**E4 — Hand over:** tell the main project the file paths (prompt in §P7). Don't share SEEDING_NOTES.md with the main project until after the exam has been scored.
