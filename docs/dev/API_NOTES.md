# Verified API and Cookbook facts

Checked on 22 Nov 2026 against https://console.bodhan.ai/api-docs/ and the Bodhan-AI-Cookbook repository (`CONTRIBUTING.md`, `scripts/bodhan_checks.py`, `scripts/bodhan_api_rules.json`). Re-check before submitting.

## Bodhan endpoints (base `https://api.bodhan.ai`, header `Authorization: Bearer <key>`)

| Capability | Endpoint | Request | Response / limits |
|---|---|---|---|
| Translation | `POST /translate` (plain JSON, not `/v1`) | `text`, `target_language` (no source-language field; source is auto-detected). `temperature`, `max_tokens`, `stream` are **rejected**. Optional `script`: native/roman/codemix, `max_output_tokens`. | `translation`, `target_language`, `script`, **`truncated` (check it)**, `usage` (only output tokens billed). 413 `payload_too_large` → split. |
| Transliteration | `POST /transliterate` | `text`, `language` (Indic only), `script` (`roman` default, use `native`) | `transliteration`, `truncated`, `usage` |
| Speech synthesis | `POST /v1/audio/speech` | `model: "indic-speak"`, `input` (keep to 1–2 sentences, ~30 s; long text is **not** split for you), `voice` (**required**), `instructions` = JSON **string** `{"lang": ..., "style": optional}` | WAV PCM16, 24 kHz, mono. 422 on empty input / unknown voice, lang or style. |
| Speech recognition | `POST /v1/audio/transcriptions` (multipart) | `file`, `model: "indic-transcribe"`, `language` (recommended) | `{"text": ...}`. **Max 30 s audio per request**, billed per second. 415 if duration unmeasurable; M4A/AAC/WebM/AMR refused. |

Error envelope: `{"error": {"message", "code", "request_id"}}`. Codes: `invalid_request_error`, `unsupported_language`, `invalid_script`, `unsupported_script_for_language`, `invalid_api_key_error` (401), `payload_too_large` (413), `rate_limit_exceeded_error` (429 — back off, don't loop), `internal_error` (5xx). Rate-limit headers: `x-ratelimit-limit-requests`, `x-ratelimit-limit-parallel-requests` (no numbers published).

**Live findings, 23 Nov 2026 (key probe, ~₹0.01):**
- `POST /translate` and `POST /transliterate` return `404 {"detail":"Not Found"}` without an `x-request-id` header, so the request never reaches the gateway route, although the docs still call them "the product surface". The docs' second transport works: `POST /v1/chat/completions` with `model: "indic-translate"`, one user message holding the text, and `target_language` (plus optional `script`) as top-level fields. The answer is in `choices[0].message.content`, and `finish_reason: "length"` means truncated. Transliteration works the same way with `model: "indic-transliterate"`, `language`, `script`. The docs say both transports give identical output, so the cache key stays transport-independent. Clients fall back on 404 (D24).
- Keys are scoped per model: `GET /v1/models` lists only the key's own model. Transliteration therefore needs its own key; the translate key does not cover it. A key used on another model gets HTTP 403 (live: translate key on `indic-transliterate`). The harness reads the optional `BODHAN_TRANSLITERATE_KEY` and stops sending a refused key for the rest of the run (D29). Verified live: transliteration with its own key, ₹0.00006.
- `/v1/audio/speech` (WAV, RIFF) and `/v1/audio/transcriptions` work as documented.

**Live speech smoke, 23 Nov 2026 (9 items hi/bn/ta, `--generate`, ₹0.26):**
- Indic-Speak returns mono 16-bit 24 kHz WAV, speech level ≈ −19 dBFS, no clipping, natural pauses. 1.4–4.9 s for 1–2 short sentences.
- Indic-Speak answered **HTTP 429 with `Retry-After: 58`** under 6 parallel requests: the speak limit halved to 3 and the retry after 58 s succeeded (K11 working live). Expect TTS rate limits at modest parallelism; the 60 s `Retry-After` cap is about right.
- Indic-Transcribe reproduced the generated hi and bn text exactly (CER 0) and ta within 2 % CER, on single chunks.
- **Digits are read out as words, and in Tamil in English**: "365" became "three hundred and sixty five", transcribed in Tamil script (த்ரீ ஹண்ட்ரட் அண்ட் சிக்ஸ்டி ஃபைவ்). The asr check treats a numeral read out as words as explained (D38); whether the number spoken is the right one is not checked. Possibly worth reporting to Bodhan as a speech-quality observation (code-mixed numerals in Tamil).

Prices (from the assignment): Indic-Translate ₹0.20 / 10k output tokens; Indic-Speak ₹6 / 10k input characters; Indic-Transcribe ₹0.10 / audio minute.

Languages: translation targets include `as bn brx doi en gu hi kn kok ks ks-Deva mai ml mni mni-Beng mr ne or pa sa sat sd sd-Arab ta te ur`. TTS `lang` uses base codes (no `ks-Deva`/`mni-Beng`/`sd-Arab` — map to `ks`/`mni`/`sd`). The docs do **not** define the "13 production-tier" languages, so `--langs` accepts every code in `data/langs.json` and degrades gracefully on unknown codes.

Voices (female / male): as Prastuti/Ankur · bn Ishita/Sourav · brx Gwrbw/Sansuma · doi Preeti/Sham · gu Dhara/Parth · hi Kavya, Suhani/Amit · kn Deepika/Adarsh · kok Anjali/Sandeep · ks Zoon/Ishfaq · mai Vaidehi/Madhukar · ml Lakshmi/Kiran · mni Thoibi/Chaoba · mr Anagha/Chinmay · ne Srijana/Sagar · or Itishree/Akash · pa Kaur/Manpreet · sa Bharati/Aryaman · sat Phulmani/Sibu · sd Moomal/Rano · ta Anitha/Arun · te Sravani/Vamsi · ur Saba/Zaid. Styles: AIR style news, Customer Care, TV style news, advertisements, anger, children's stories, disgust, educational lecture, fear, happy, news, sad, single person narration audiobook, surprise.

## Cookbook validator constraints (CI blocks the PR on errors)

- Recipe folder `examples/<snake_case>/` with `README.md` containing `## Setup` and `## Run` (warning if missing); no template placeholders.
- Python recipe needs `requirements.txt` with every line pinned `name==version` (lines starting with `-` such as `-e .` are skipped).
- `.env.example` must exist **and contain `BODHAN_API_KEY`**; `.gitignore` must ignore `.env`.
- Notebooks must have outputs cleared; names snake_case and should match the folder.
- Model-id literals (`"model": "x"`, `model="x"`, `-F model=x`) must be in `scripts/bodhan_api_rules.json`: `indic-transcribe`, `indic-translate`, `indic-transliterate`, `indic-speak`, `indic-ocr`. Any other `indic-*`/`bodhan-*` id is an error.
- Secret scan over every text file, including docs and tests: OpenAI-style `sk-` keys, AWS/Google/GitHub/Slack tokens, private key blocks, JWTs, and `BODHAN_API_KEY = <literal>` without a placeholder word. Use placeholders like `<your key>`.
- Repo-root `ruff` excludes `examples/`, so lint ourselves.
- CONTRIBUTING suggests branch `recipe/<name>` and PR title `feat(examples): …`; the assignment overrides both: branch `assignment/quality-harness-mysticalseeker24`, title `[Agentic Eng Assignment] Quality harness — Saksham Mishra`.
- Cookbook licence: Apache-2.0. Keep dataset text licence-compatible (see DATASET_PLAN.md).

## OpenRouter (judge testing)

- OpenAI-compatible base URL `https://openrouter.ai/api/v1`; model slugs like `openai/gpt-6.1-sol`.
- `response_format` supports `json_object` and `json_schema` (strict) on most models; unsupported models return an error → our fallback chain handles it. `provider.require_parameters` and the response-healing plugin are OpenRouter-only: optional, never required.
- Reasoning models bill reasoning tokens as output; cap them (`--llm-extra-body '{"reasoning": {"effort": "low"}}'`) and keep `max_tokens` sane.
- **Checked 23 Nov 2026.** `GET /api/v1/models` (public, no key) lists every model with `pricing.prompt` / `pricing.completion` (USD per token, as strings), `supported_parameters` (`structured_outputs` = strict `json_schema`) and a `canonical_slug` with a date suffix (`openai/gpt-6.1-sol` → `openai/gpt-6.1-sol-20260929`). The rankings page shows the canonical slug; requests use the plain `id`. `bakeoff.py` reads prices from this listing when no `--price` is given.
- Responses carry `usage.cost` (USD actually charged); the client records it (`run_meta.json`, `bakeoff_spend.json`). It can exceed list price: DeepSeek V4.1 Flash was charged $0.0025 for 12 calls whose list price was $0.0009 (OpenRouter picks among providers; `provider: {"sort": "price"}` in `--llm-extra-body` prefers the cheapest). Budget guards therefore use max(reported, list price).
- Live smoke (23 Nov, 5 items): `openai/gpt-6-luna` and `deepseek/deepseek-v4.1-flash` both accepted strict `json_schema`; 0 invalid answers.
