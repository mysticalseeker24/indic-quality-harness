# Demo dataset plan

Requirement: ≥100 items across Hindi, Tamil and Bengali, built from text we have the right to use, with injected errors and a labelled subset; generated audio kept out of git (hosted and linked).

## Licensing: what may go into a public Apache-2.0 repo

| Source | Status | Use |
|---|---|---|
| Saksham's own writing (incl. AI-assisted English) | ours | ✅ main source |
| NCERT textbooks | All rights reserved; the ePathshala licence allows sharing "as is", non-commercially, with attribution. Translating and injecting errors creates derivatives. | ❌ no verbatim text. ✅ Use NCERT **syllabus topics and facts** as a guide and write original sentences (facts are not copyrightable) |
| NROER (National Repository of Open Educational Resources) | CC BY-SA | ✅ short excerpts with attribution in `data/SOURCES.md` |
| Wikipedia / Wikibooks | CC BY-SA 4.0 | ✅ short excerpts with attribution |
| OpenStax | now CC BY-NC-SA (NonCommercial) | ⚠️ avoid in an Apache-2.0 repo |

**Chosen (D40, Saksham, 23 Nov): plan A.** Saksham lists NCERT chapters (class, subject, chapter); for each, passages come from Wikipedia (CC BY-SA 4.0), real human-written text. No English is drafted by us and no NCERT text enters the repo. Tables and formulas from the articles are kept as Markdown tables and LaTeX.

Record every non-original item's source, URL and licence in `data/SOURCES.md`; give the data its own notice (`data/LICENSE-DATA.md`: original items CC BY 4.0, excerpts under their source licence).

## Composition (target 60 English sources × 3 languages = 180 items)

| Content type | Share | Examples (NCERT classes 6–12 topics, original wording) |
|---|---|---|
| Short factual sentences | 35 % | science facts with numbers and units, dates in history, geography figures |
| Multi-sentence paragraphs | 25 % | processes (photosynthesis, water cycle), civics explanations |
| Markdown with lists/headings | 15 % | study notes, steps of an experiment |
| Markdown tables | 10 % | planets and moons, elements and symbols, rivers and lengths |
| LaTeX | 15 % | formulas (area, speed, Ohm's law), worked examples with inline and display math |

Must include: numbers in many forms (decimals, Indian grouping, percentages, dates, units), named people/places/terms (Newton, Ganga, photosynthesis, DNA), and sentences with multiple clauses (for omission tests).

## Pipeline

1. Build `data/sources_en.jsonl` from the Wikipedia passages for Saksham's NCERT chapter list: `{id, source, lang}` × 3 languages (same `id` across languages, e.g. `sci-012`), with `data/SOURCES.md` (article, URL, revision, licence) per id.
2. `python -m bodhan_eval --dataset data/sources_en.jsonl --langs hi,ta,bn --out outputs/clean --generate --max-cost-inr 40` → `outputs/clean/generated.jsonl` + audio.
3. Saksham reviews a sample of clean outputs; real Bodhan errors he finds become labels with `"annotator": "saksham"` (these are the most valuable labels).
4. `python -m bodhan_eval.inject --dataset outputs/clean/generated.jsonl --out data/demo.jsonl --rate 0.5 --seed 13 --audio-out outputs/demo_audio --with-models` (labels `annotator: injector:<method>`).
5. Split labels: `data/demo_labels.jsonl` (calibration subset, ~40 items) vs the rest (evaluation); also the bake-off set.
6. Commit text files only; upload audio as a GitHub Release asset or a Hugging Face dataset and link it from the README.
