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
