# Judge model bake-off (OpenRouter, $10 budget)

Purpose: pick the development/demo judge model with evidence, and show the harness works across providers (Bodhan will run it with an LLM of their choice). All candidates are current models listed on OpenRouter in November 2026 — **re-check slugs and prices on openrouter.ai/models before running**; prices below are list prices seen on 23 Nov 2026 where known.

## Panel (confirmed by Saksham, 23 Nov 2026; D33)

Prices from OpenRouter's `/api/v1/models` listing on 23 Nov 2026. Requests use the plain `id`; the rankings page shows the dated `canonical_slug`. All eight list `structured_outputs` (strict `json_schema`) and `reasoning`.

| Slot | Model id | Canonical slug | List $ in / out per 1M | Est. $ for 50 items (500–1,000 output tokens/call) | Why |
|---|---|---|---|---|---|
| Frontier, closed | `openai/gpt-6.2-sol` | `-20261117` | 2 / 10 | 0.90–1.50 | Newest GPT-6 Sol (17 Nov), same price as 6.1 |
| Frontier, closed | `anthropic/claude-sonnet-5.5` | `-20260928` | 2 / 10 | 0.90–1.50 | Strong rubric adherence; second closed vendor |
| Frontier, closed | `google/gemini-4-hydrogen` | `-20261112` | 1.5 / 7.5 | 0.67–1.12 | Gemini is strong on Indic scripts; third vendor |
| Frontier, closed | `google/gemini-4-neon` | `-20261118` | 3 / 15 | 1.35–2.25 | Newest Gemini 4; the top of the Gemini range |
| Fast, closed | `openai/gpt-6-luna` | `-20260922` | 0.10 / 0.50 | 0.05–0.08 | Cheap default candidate; interim judge until the bake-off |
| Open weights | `deepseek/deepseek-v4.1-flash` | `-20260910` | 0.05 / 0.199 | 0.02–0.03 | Most-used open model; provider-neutrality |
| Open weights | `moonshotai/kimi-k3.1-pro` | `-20261023` | 0.24 / 8.40 | 0.54–1.04 | Second open family (expensive output) |
| Deliberately weak | `meta-llama/llama-3.1-8b-instruct` | — | 0.02 / 0.04 | ≈ 0.01 | Simulates a cheap grader LLM; harness must degrade gracefully |

Estimate (the tool's own estimator on 50 proxy paragraphs of ~55 words; 2 replicas + 15 % tie-breaks + 10 % repeats = 120 calls/model): **$4.4 at 500 output tokens/call, $7.5 at 1,000**. Real charges can exceed list price (OpenRouter picks among providers; DeepSeek was billed 2.8× list in the mini run), so run with `--max-usd 8` and consider `--llm-extra-body '{"reasoning": {"effort": "low"}, "provider": {"sort": "price"}}'`. The tool stops taking items when the real spend reaches the cap.

## Status

- **P3 gate (23 Nov): mini bake-off** on the 5 live-smoke items (1 injected number error), Luna and DeepSeek V4.1 Flash, reasoning effort low. It proves the tool end to end on the real API; with one error it does not rank models.

| Model | Judge-alone P / R | Order consistency | Repeat consistency | Invalid output | Tokens/item | $/100 items (list) | Harness recall / false alarms | Format |
|---|---|---:|---:|---:|---:|---:|---|---|
| `openai/gpt-6-luna` | 100 % / 100 % | 100 % | 100 % (n=2) | 0 % | 2492 | 0.027 | 100 % / 0 % | json_schema |
| `deepseek/deepseek-v4.1-flash` | 100 % / 100 % | 100 % | 100 % (n=2) | 0 % | 2567 | 0.017 | 100 % / 0 % | json_schema |

  Spend: Luna $0 (all answers cached from the smoke run, which cost $0.0014 as reported by OpenRouter), DeepSeek $0.0025 reported ($0.0009 at list price).
- **Full run (23 Nov, after P5):** 8 models, 50 items of `data/bakeoff.jsonl` (25 clean, 10 Telugu), reasoning effort low, $5.76 reported (cap $8). Results in README; harness recall / false alarms: Kimi K3.1 Pro 96 / 4 %, Luna 96 / 8 %, Gemini 4 Hydrogen 93 / 0 %, Gemini 4 Neon 100 / 12 %, DeepSeek V4.1 Flash 96 / 12 % (15 % invalid), Sonnet 5.5 93 / 20 %, GPT-6.2 Sol 100 / 28 %, Llama 3.1 8B 85 / 92 %. **Default: `moonshotai/kimi-k3.1-pro`** (chosen by Saksham): Luna wins the per-dollar rule, but Kimi has half the false alarms and 94 % order consistency vs 72 %, despite labels that favour Luna (the real-error labels came from Luna's flags).
- **Full run: after P5**, when the injector and Saksham's labels give the labelled set below (DATASET_PLAN step 5). Show the estimate on the real set again before running.

## Budget arithmetic

A judge call ≈ 2,500 input tokens (rubric + numbered tokens + back-translation + findings) and 250–800 output tokens (more for reasoning models — cap reasoning with `--llm-extra-body '{"reasoning": {"effort": "low"}}'`).

- Frontier at $2/$10: ≈ $0.005 input + ≈ $0.003–0.008 output ≈ **$0.01–0.013 per call**.
- Bake-off: 40 labelled items × 2 replicas (+ ~10 % tie-breakers) ≈ 90 calls/model → **≈ $1.0–1.2 per frontier model**, ≈ $0.05–0.2 per fast/open model.
- Plan: 3 frontier + 3 fast/open + 1 weak ≈ **$4–4.5**. Development loop on a fast model ≈ $0.5. Full demo run (≈180 items × ~2.2 calls) on a fast model ≈ $0.3–1. Reserve ≈ $3 for reruns and the exam.
- Put the static rubric first (system message) so provider prompt caching can apply; the cache makes every rerun free.

## Procedure

1. Build the labelled bake-off set: 40 items (≈13 per hi/ta/bn) + 10 items in one held-out language, ~half clean, errors across all 7 translation categories (from the injector plus Saksham's own labels).
2. `python -m bodhan_eval.bakeoff --dataset data/bakeoff.jsonl --models openai/gpt-6.2-sol,anthropic/claude-sonnet-5.5,google/gemini-4-hydrogen,google/gemini-4-neon,openai/gpt-6-luna,deepseek/deepseek-v4.1-flash,moonshotai/kimi-k3.1-pro,meta-llama/llama-3.1-8b-instruct --max-usd 8 --llm-extra-body '{"reasoning": {"effort": "low"}}' --out outputs/bakeoff` (add `--dry-run` first to see the estimate). It runs tiers 0–1 once — shared via cache — then only the judge per model; prices come from the OpenRouter listing unless `--price model=IN/OUT` is given.
3. Table to produce (goes into README and the PR):

| Model | Judge-alone P / R per category | Order consistency | Repeat consistency | Invalid output % | Tokens/item | $/100 items | Harness recall / false alarms with this judge |
|---|---|---|---|---|---|---|---|

4. Choose the default: best "harness recall at ≤10 % false alarms" per dollar. Name it in the PR ("tested with …") and list the others.
