# Judge model bake-off (OpenRouter, $10 budget)

Purpose: pick the development/demo judge model with evidence, and show the harness works across providers (Bodhan will run it with an LLM of their choice). All candidates are current models listed on OpenRouter in November 2026 — **re-check slugs and prices on openrouter.ai/models before running**; prices below are list prices seen on 23 Nov 2026 where known.

## Panel

| Slot | Model (slug to confirm) | List price in/out per 1M | Why |
|---|---|---|---|
| Frontier, closed | `openai/gpt-6.1-sol` | $2 / $10 | Newest GPT-6 Sol upgrade (Sep 2026), strong instruction following |
| Frontier, closed | Anthropic Claude Sonnet 5.5 (or Opus 5.5 if affordable) | check | Strong rubric adherence; second closed vendor |
| Frontier, closed | Google Gemini 4 Argon, or `~google/gemini-pro-latest` | Pro latest: $2 / $12 | Gemini is strong on Indic scripts; third vendor |
| Fast, closed | GPT-6 Luna or Gemini 3.8 Flash | low | Cheap candidates for the default |
| Open weights | DeepSeek V4.1 Flash; Kimi K3.1 Pro | low | Most-used open models right now; shows provider-neutrality |
| Deliberately weak | a small open model | very low | Simulates a cheap grader LLM; harness must degrade gracefully |

## Budget arithmetic

A judge call ≈ 2,500 input tokens (rubric + numbered tokens + back-translation + findings) and 250–800 output tokens (more for reasoning models — cap reasoning with `--llm-extra-body '{"reasoning": {"effort": "low"}}'`).

- Frontier at $2/$10: ≈ $0.005 input + ≈ $0.003–0.008 output ≈ **$0.01–0.013 per call**.
- Bake-off: 40 labelled items × 2 replicas (+ ~10 % tie-breakers) ≈ 90 calls/model → **≈ $1.0–1.2 per frontier model**, ≈ $0.05–0.2 per fast/open model.
- Plan: 3 frontier + 3 fast/open + 1 weak ≈ **$4–4.5**. Development loop on a fast model ≈ $0.5. Full demo run (≈180 items × ~2.2 calls) on a fast model ≈ $0.3–1. Reserve ≈ $3 for reruns and the exam.
- Put the static rubric first (system message) so provider prompt caching can apply; the cache makes every rerun free.

## Procedure

1. Build the labelled bake-off set: 40 items (≈13 per hi/ta/bn) + 10 items in one held-out language, ~half clean, errors across all 7 translation categories (from the injector plus Saksham's own labels).
2. `python -m bodhan_eval.bakeoff --dataset data/bakeoff.jsonl --models <slug1>,<slug2>,... --replicas 2 --max-usd 4.5 --out outputs/bakeoff` (tool built in P3; it runs tiers 0–1 once — shared via cache — then only the judge per model).
3. Table to produce (goes into README and the PR):

| Model | Judge-alone P / R per category | Order consistency | Repeat consistency | Invalid output % | Tokens/item | $/100 items | Harness recall / false alarms with this judge |
|---|---|---|---|---|---|---|---|

4. Choose the default: best "harness recall at ≤10 % false alarms" per dollar. Name it in the PR ("tested with …") and list the others.
