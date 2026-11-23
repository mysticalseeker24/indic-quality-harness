# Submission: from this repo to the Bodhan Cookbook PR

## Why a snapshot export (not `git subtree`)

- The Cookbook squash-merges, so commit history in the PR has no lasting value there; your full history stays public in this repo, linked from the PR.
- A snapshot exports **only tracked files at one commit**, so nothing that ever passed through history (an early test file, a large audio file, a key committed by mistake and later removed) can leak into a public PR.
- `.gitattributes` `export-ignore` keeps personal-repo-only files out (`.github/`, `CLAUDE.md`, `docs/dev/`, and `.gitattributes` itself, which names them) (D30).
- The PR description records this repo's commit SHA for traceability.

## Steps

```bash
# 0. In this repo: everything green and committed
make check && git status --short   # must be empty
SRC_SHA=$(git rev-parse HEAD)

# 1. Fork https://github.com/Bodhan-AI/Bodhan-AI-Cookbook on GitHub, then:
git clone https://github.com/mysticalseeker24/Bodhan-AI-Cookbook.git ~/code/Bodhan-AI-Cookbook
cd ~/code/Bodhan-AI-Cookbook
git checkout -b assignment/quality-harness-mysticalseeker24

# 2. Export the snapshot into the recipe folder
DEST=examples/translation_speech_quality_harness
mkdir -p $DEST
git -C ~/code/indic-quality-harness archive --format=tar $SRC_SHA | tar -x -C $DEST

# 3. Validate exactly as their CI does, and test from a clean state
pip install -r requirements-dev.txt && make check          # Cookbook root gate
cd $DEST && python -m venv /tmp/v && . /tmp/v/bin/activate && pip install -r requirements-dev.txt && pytest -q && cd -
docker build -t bodhan-eval $DEST && docker run --rm bodhan-eval --help

# 4. Commit and push
git add $DEST
git commit -m "feat(examples): add translation and speech quality harness (source: mysticalseeker24/indic-quality-harness@$SRC_SHA)"
git push -u origin assignment/quality-harness-mysticalseeker24
```

5. Open the PR to `Bodhan-AI/Bodhan-AI-Cookbook:main`, title **`[Agentic Eng Assignment] Quality harness — Saksham Mishra`**, body = the assignment's template (below) followed by the Cookbook's PR checklist.
6. Make this personal repo public. Reply on Barry's email thread with the PR link and `git rev-parse HEAD` of the fork branch. **That commit is what gets graded; don't push to the branch afterwards.**

## Before-you-submit checklist (assignment + Cookbook)

- [ ] Clean clone → documented setup → exact command works (Docker too)
- [ ] Only Bodhan models for translation/TTS/ASR; no learned QE; LLM never writes Indic text (tests in TESTING.md §7 pass)
- [ ] No keys, `.env`, audio or `outputs/` in the diff; Cookbook validator passes
- [ ] README: checks, setup, usage, limitations; links architecture diagram, flow chart, design notes, sample report, demo video, hosted audio
- [ ] Demo dataset ≥100 items hi/ta/bn with injected errors and a labelled subset (own labels marked `annotator: saksham`)
- [ ] Sample report (text files) committed and linked
- [ ] Tests pass locally; `make check` at the Cookbook root passes
- [ ] Demo video ≤5 min, viewable without sign-in, linked from README and PR
- [ ] PR description complete (template below); AI-assistance section filled in

## PR description template (from the assignment)

```markdown
## Summary
## How to run
## Architecture
## Harness design
## Where the LLM is used, and why
## Bodhan models used
## Results
## Demo video
## Trade-offs and known limitations
## Cost and runtime
## AI assistance
```
