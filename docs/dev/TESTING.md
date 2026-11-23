# Test plan

Goal: nothing fails in Bodhan's fresh container, and no number in the report is wrong. Offline tests (no keys, no network) run on every commit; live tests are tiny, paid and marked `@pytest.mark.live`.

Layout: `tests/unit/test_<module>.py`, `tests/e2e/`, `tests/fixtures/` (small JSONL, stub-server response tables, synthetic audio generated at test time, never committed as audio).

## 1. Unit tests — core utilities

- **normalize**: every Indic digit system (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Gurmukhi, Odia, Arabic-Indic, Extended Arabic-Indic) → ASCII; NFC with nukta as one vs two code points; ZWJ/ZWNJ removed; quotes/dashes/danda unified; `to_original()` round-trips spans; `ascii_digits` is length-preserving; `canonical_number` for `1,00,000`, `100,000`, `3.50`, `007`, `२५`; `stem` equates boil/boils/boiling, time/times, stop/stopped; `segments` keeps decimals intact and splits on danda.
- **spans**: overlap incl. zero-width tolerance; `tokens_to_span`/`span_to_token_range` inverse; `word_alignment` opcodes on known lists; CER edge cases (empty).
- **markup**: `$`, `$$`, `\(`, `\[`, `\begin{env}`; escaped `\$`; tables with/without outer pipes; separator rows; `has_markup` false for plain prose; `unbalanced_dollars`; brace balance; `\text{}` contents ignored by `math_key`.
- **cache**: same input → same key; any param change → new key; blob round-trip; thread safety (parallel puts).
- **budget**: refuses before crossing the cap; reservations released on failure; cache hits counted in `used` not `spent`.
- **config/dataset**: bad JSON line, non-object line, missing fields, duplicate `(id, lang)`, unknown lang, `hi-IN` normalised, relative audio path resolved, missing audio noted, labels with unknown type counted, `span_on` handling, the three calibration line shapes.

## 2. Unit tests — every check: must-catch and must-not-flag tables

| Check | Must catch | Must NOT flag |
|---|---|---|
| script | whole text English; one sentence English; Tamil text for `hi`; Marathi text for `hi`; Bengali text for `as` | kept names/acronyms (`Isaac Newton`, `DNA`, `H2O`); LaTeX, code, URLs; a single kept technical word |
| format | table row lost a pipe; separator row missing; heading `#` dropped; stray `$`; changed formula; unbalanced braces; unmatched `**`; link URL altered | translated table headers; translated `\text{}`; digits-only formula change (owned by numbers); plain prose |
| numbers | digit changed; decimal changed; number dropped; number added; `km`→`m` via back-translation; month changed | `२५` vs `25`; `1,00,000` vs `100,000`; number written as a word when the back-translation has it; source "three" → target `3`; `H2O`; list numbering |
| back-translation | whole sentence missing; clause missing; extra sentence; meaning drift | paraphrase; sentence merge/split (2:1); reordered sentences; synonyms |
| entities | name replaced by another name; garbled transliteration | name kept in Latin; correct transliteration; translated-by-meaning names confirmed by back-translation |
| length | extreme ratio vs language median | normal variance; languages with too few items use the prior |
| judge (parsing) | valid JSON → signals with exact spans | bad JSON; out-of-range or reversed indices; unknown category; missing location for non-omission; Indic text in explanation → masked |
| audio_stats | 2 s internal silence; edge silence; clipping; noise burst; empty audio | natural short pauses; quiet but clean speech |
| asr | deletion run mid-text; truncated tail; repeated phrase; looped trigram; poor transcript everywhere → garbled (also around a number) | scattered substitutions; numbers spoken as words (incl. a short item whose number is read in another language, D38); nukta/candrabindu spelling variants; a truncation must not also raise garbled; words lost or repeated at chunk ends are dismissed by the second opinion |

Each row is a separate parametrised test case with a readable id.

Speech rows (`tests/unit/test_check_tables_speech.py`, `tests/unit/test_speech_time.py`) use tone-words: each vocabulary word is a tone and the stub's transcription decodes the tones it receives (`testing.stub_server.tone_speech`, fixture `transcribe: {lang: {tone_words: [...], errors: [...]}}`). Tests therefore choose exactly what is spoken, at what speed and where the pauses are, while chunking, alignment and the second opinion run for real; `errors` makes the ASR drop or repeat the last words of requests of a given length, which is how chunk-dependent ASR misses are simulated.

## 3. Fusion and calibration

- One judge replica alone → `uncertain`; two agreeing replicas → flag; deterministic proof alone → flag; judge + back-translation → flag.
- Clustering across translation span vs source span; category precedence on ties; narrowest span chosen; unlocated signal joins its category's cluster (K8).
- `match_item` ranks; `evaluate` arithmetic on a hand-computed 6-item case; `tune` picks the expected threshold on a crafted case; categories below `min_labels_to_tune` keep defaults; CV returns None on tiny sets.

- Injector (`tests/unit/test_inject.py`, `test_inject_speech.py`): every method on several seeds (edit where the label says, undo gives the original, digit system kept, list markers and H2O untouched); `--with-models` methods against the stub's echoing translate; tier-0 round trips (format, script and numbers flag text edits; `audio_stats` flags inserted silence and clipping, at the label); speech edits on tone-words, so each test knows which words were cut, repeated or hidden; byte-identical reruns; an item's fate independent of other items; existing labels pass through; stale audio dropped or re-synthesised.
- Scorecard (`tests/unit/test_score.py`): a hand-computed 7-item case (detected, localised, wrong category, missing from the report, clean with a false alarm, unlabelled skipped), review-queue catch, `--exclude`.
- Review sheet (`tests/unit/test_review.py`): suspected items first then a seeded sample, deterministic CSV with BOM, back-translation via the stub, import: `ok` = labelled clean, aliases accepted, error text located (or listed when not found), unknown verdicts listed, output works as `--calibration`.
- Loop (`tests/e2e/test_inject_loop.py`): inject the clean suite → exact command with no keys (tier 0 only) → `calibration.json` has the labels → scorecard: tier-0 categories 100 % recall; on clean items only the known no-back-translation case fires (a number written as a word).

## 4. Clients and the stub server (no network)

- Translate 200 / 413 (split and rejoin) / 429 with `retry-after` / 500 then success / retries exhausted → `BodhanError`; `truncated: true` recorded.
- TTS 422 → not retried, error recorded; WAV returned and cached as blob.
- ASR: >30 s audio is chunked (assert each request ≤ 30 s).
- LLM: `json_schema` rejected → falls back to `json_object` → falls back to plain; empty content → retry with more tokens; non-JSON → `None` handled. (`tests/unit/test_clients.py`: per-model format memory, an unrelated 400 lowers nothing, extra body, provider cost, cache tag, cached format.)
- Concurrency and retries (`tests/unit/test_concurrency.py`), each scenario run for both the Bodhan and the LLM client: a 429 halves the limit and successes restore it; a burst of 429s from one window halves once; `Retry-After` honoured and capped; one 429 pauses every new request to the service; 429s are waited out beyond `max_retries` until the patience runs out; 5xx backs off with jitter without halving; retries exhausted cleanly (no reservation left, no spend); retries never double-count cost; the SDK sends exactly one request per attempt.
- Judge (`tests/unit/test_judge.py`): the §2 parsing table; tie-break replica only on disagreement; minority finding → review queue; jury; repeat sample (identical request, no extra evidence); windows map indices back; replicas never see each other's verdicts. Bake-off (`tests/unit/test_bakeoff.py`): estimate, refusal before any call, table, byte-identical cached rerun, stop at `--max-usd`.
- Missing keys → `ServiceUnavailable` → checks skipped, run continues.

## 5. End-to-end (offline, exact command)

- 10-item dataset: hi, ta, bn items with and without translation/audio/reference/labels; one unknown language code; one broken JSON line; one missing audio file; one Markdown table + LaTeX item.
- Run `python -m bodhan_eval --dataset … --langs hi,ta,bn,xx --out tmp/report --calibration …` as a subprocess against the stub server.
- Assert: exit code 0; the 5 files exist; schema of each `items.jsonl` line; bad line counted; skipped checks have reasons; flags have spans inside the text; LLM output never contains Indic (scan judge evidence).
- Rerun → byte-identical report files; `run_meta.json` shows ₹0 spent.
- `--baseline` run on a modified dataset → `diff.md` lists exactly the planted regression and improvement.
- `--generate` path with stub TTS → audio written, `generated.jsonl` valid.

## 6. Generalisation and robustness matrix (P7, offline where possible)

| Axis | Values |
|---|---|
| Languages | hi, ta, bn (dev); te, mr, gu (held out); `ks-Deva`, `sd-Arab`, unknown `xx` |
| LLM | 4–6 models from the bake-off incl. one weak/cheap model; LLM unset |
| Labels | inline `labels`; `--calibration` full items; id-only label lines; unknown type strings; spans on source; no labels |
| Audio | WAV 24 kHz; WAV 16 kHz; MP3; >30 s; missing; empty/silent |
| Content | single sentence; multi-paragraph; Markdown table; LaTeX-heavy; lists/headings |
| Run modes | plain; `--generate`; `--baseline`; tight `--max-cost-inr` (must stop cleanly, report skipped checks) |

**Leave-one-language-out**: calibrate on two dev languages, score the third; report the drop. **Clean-item false-alarm suite**: tricky clean items (numbers in words, transliterated terms, reordered sentences, translated table headers) must stay ≤ 10 % flagged.

## 7. Rule-compliance guards (protect against automatic fail)

- AST scan: only `clients.py` imports `requests`/`openai`; no imports of other speech/translation/QE libraries (deny-list: whisper, faster_whisper, transformers, comet, googletrans, deep_translator, langdetect, fasttext, sarvam…).
- Model-id literals in `src/` ⊆ the Cookbook rules list.
- Judge prompt contains token indices and the "never write Indian-script text" rule; `strip_indic` applied to all LLM prose.
- Injector runs with an LLM client that raises on any call, and no file in `inject/` imports one (`test_with_models_resynthesises_audio_and_never_touches_the_llm`, `test_injector_source_never_imports_the_llm_client`).
- Secret scan: run the Cookbook validator (`make validate`) and grep for `sk-` patterns in the repo.
- `.env`, audio, `outputs/` not tracked (`git ls-files` check in CI).

## 8. Live tests (paid, tiny, `-m live`)

- 3 items × hi/ta/bn with `--generate`, `--max-cost-inr 3`: translations returned, audio plays, ASR text non-empty, cost meter within ±20 % of the console usage.
- Judge with the chosen default model on 5 items: valid JSON, sensible flags.

## 9. Performance

- Stub server with 300–800 ms simulated latency, 200 items × 3 languages with speech: total wall time projected under 30 minutes at default concurrency. Record the number in README "Cost and runtime".
