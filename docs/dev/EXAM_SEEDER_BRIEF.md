# Independent exam — pointer

The exam project lives **outside this repo** in `~/code/iqh-exam` (from the `iqh-exam/` folder of the starter zip). Its own `CLAUDE.md` holds the full brief; its prompts are in `PROMPTS.md` §E.

Why: errors seeded by the same session that wrote the detectors are biased towards what the detectors catch. A separate Claude Code project that never sees this code seeds errors from the public spec alone, in languages we never tuned on (te, mr, gu), so its score is an honest estimate of Bodhan's blind run.

Rules for this repo: never read `../iqh-exam`; when Saksham provides the four exam file paths in Phase 7, pass them to the CLI, run once, report the numbers as they come out, and do not tune anything in response.
