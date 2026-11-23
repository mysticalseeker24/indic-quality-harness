# Decision log

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 22 Nov | Plain Python + thread pool, no orchestration framework | Deterministic, explainable line by line, no hidden retries; spec allows "none" |
| D2 | 22 Nov | `requests` for Bodhan, `openai` SDK for the judge | `/translate` and `/transliterate` are not OpenAI-shaped; spec requires an OpenAI-compatible client for the LLM |
| D3 | 22 Nov | Checks emit signals; fusion creates flags (noisy-OR + per-category thresholds) | Separates checker noise from real errors; one place to calibrate; easy to add a check live |
| D4 | 22 Nov | Judge answers with token indices | LLM never writes Indic text; exact spans; hallucinated spans rejected |
| D5 | 23 Nov | Judge replicas: 2 re-ordered prompts, 3rd only on disagreement; optional jury and repeat-consistency sample | Reliability where it matters, cost only where needed |
| D6 | 22 Nov | Language behaviour only in `langs.json`; unknown codes degrade gracefully | Hidden set includes an undemoed language; "13 production-tier" list is not documented |
| D7 | 22 Nov | Emit both `span` (translation) and `source_span`; accept `span_on` in labels | Spec does not say which side label spans refer to |
| D8 | 22 Nov | Report "cost of outputs used" (deterministic); money actually spent only in `run_meta.json` | Identical report on cached rerun while staying honest about cost |
| D9 | 22 Nov | Folder `examples/translation_speech_quality_harness`; data in `data/` | Cookbook naming rules; template `.gitignore` ignores `sample_data/*` |
| D10 | 23 Nov | Do all stretch goals incl. voice comparison, after the core | Overdeliver without risking the 75 core points |
| D11 | 23 Nov | Build in `mysticalseeker24/indic-quality-harness` (private until submission); export a snapshot to the fork | Clean public PR, no history leaks, portfolio repo keeps full history |
| D12 | 23 Nov | Independent exam set built by a separate Claude Code project that never sees the detectors | Honest estimate of the hidden-set score |
| D13 | 23 Nov | Judge models: current OpenRouter models only; bake-off decides the default within $10 | Evidence over guesswork; provider-neutral |
| D14 | 23 Nov | Dataset: own writing on NCERT-syllabus topics + CC BY-SA excerpts; no verbatim NCERT text | NCERT text is all-rights-reserved; the PR is public |
| D15 | 23 Nov | Library API (`bodhan_eval.api`) alongside the CLI | Reuse as the QA gate in the dubbing / narrated-lesson project |
| D16 | 23 Nov | Multi-chat workflow: HANDOFF.md + checkpoint protocol + ask-first list + human milestones in CLAUDE.md; prompts in PROMPTS.md | No context lost between Claude Code chats; Saksham approves every major change, paid run and the public-repo step |
| D17 | 23 Nov | `--judge-max-replicas`, `--judge-models`, `--judge-repeat-sample`, `--llm-extra-body` arrive in P3 together with their features | No CLI flags that silently do nothing |
| D18 | 23 Nov | A minimal `diff.md` already in P1 (full version in P6) | `--baseline` is part of the graded command and must always produce the file |
| D19 | 23 Nov | Check status `not_applicable` is separate from `skipped`; a check that raises contributes no signals | Skip counts stay meaningful; half-finished evidence never reaches fusion |
| D20 | 23 Nov | `id`+`lang` label lines match only that pair (no fallback to id-only); an unreadable `--calibration` file is a note, not exit 1 | Labels never land on the wrong language; a bad label file does not stop a graded run |
| D21 | 23 Nov | The stub server ships in the package (`bodhan_eval.testing.stub_server`) | One stub for tests and offline demos; the harness itself has no test-only code paths |
| D22 | 23 Nov | `--langs all` means no language filter (unknown codes included) | "Accept any language" with graceful degradation |
| D23 | 23 Nov | Commit messages carry no tool attribution trailers; history rewritten once and force-pushed with Saksham's explicit yes | Saksham's request: commits are authored by him only |
| D24 | 23 Nov | When a Bodhan text route answers 404, the client switches to the documented chat transport (`/v1/chat/completions`, model `indic-translate` / `indic-transliterate`) for the rest of the run | The hosted `/translate` and `/transliterate` were 404 on 23 Nov while the chat transport worked (API_NOTES); the docs promise identical output, so cache keys stay valid |
| D25 | 23 Nov | Check-table bar: tier-0 must-catch rows must flag on their own; back-translation, entities and length rows must reach the review queue (>= 0.3) and need corroboration to flag | Matches the fusion design: deterministic proof flags alone, noisy round-trip evidence does not |
| D26 | 23 Nov | `entity_match_similarity` 72 -> 85 (**needs Saksham's ack: it is a default**) | A garbled name scored 75 and passed as found; real spelling variants score 90+, and looser ones still fall through to the back-translation check |
| D27 | 23 Nov | Units compared as canonical units per family, plus "one measurement family lost, another gained" | `km` vs `kilometres` was a false alarm; litres -> kilograms was missed |
| D28 | 23 Nov | Unlocated signals join the strongest cluster of their category (K8) | Corroborates the most likely problem instead of lifting a weak candidate over the threshold |
| D29 | 23 Nov | Optional `BODHAN_TRANSLITERATE_KEY` (fallbacks: `BODHAN_API_KEY`, then `BODHAN_TRANSLATE_KEY`); a key refused with 401/403 is not sent again in the run; transliteration spend stays on the `translate` cost line (Saksham's yes, 23 Nov) | Keys are scoped per model: the translate key gets 403 on `indic-transliterate` (live, 23 Nov). With only the three documented keys the entity check still works from the Latin form and the back-translation, at the price of one refused request; `summary.json` keeps its cost keys |
