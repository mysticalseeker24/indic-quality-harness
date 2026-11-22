"""Tier-1 translation checks that use a Bodhan round trip.

``back_translation``
    Back-translates the target *segment by segment* with Indic-Translate (target -> en),
    then aligns source sentences to back-translated segments with a small dynamic
    program (match / skip-source / skip-target / 2:1 merges) on content-word overlap.
    A skipped source sentence is an omission candidate, a skipped target segment an
    addition candidate; inside matched pairs, clause coverage finds partial omissions.
    Because back-translation makes its own mistakes, a candidate is only raised when the
    missing content is absent from the *whole* back-translation, and scores stay below
    the flag threshold unless the evidence is strong; the judge or a second check must
    corroborate weaker ones (see fusion.py).

``numbers``
    Digits after normalisation (२५ == 25), compared as multisets; unit and month words
    compared through the back-translation. Deterministic; the back-translation is only
    consulted to explain away numbers the translation wrote out in words.

``entities``
    Names and technical terms from the source must appear in the translation, either in
    Latin script or as their Indic-Transliterate rendering; otherwise the back-translation
    must mention them. Also checks the same term is rendered the same way across items.
"""

from __future__ import annotations

import re
from collections import Counter

from rapidfuzz import fuzz

from ..models import ItemResult, Signal
from ..normalize import (
    ENGLISH_NUMBER_WORDS,
    ascii_digits,
    canonical_number,
    content_words,
    normalize_text,
    segments,
    word_tokens,
)
from ..spans import best_window_match
from .base import Check, SkipCheck

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fuzzy_in(word: str, bag: set[str]) -> bool:
    if word in bag:
        return True
    if len(word) < 4:
        return False
    return any(len(b) >= 4 and b[0] == word[0] and fuzz.ratio(word, b) >= 85 for b in bag)


def coverage(words: list[str], bag: set[str]) -> float:
    if not words:
        return 1.0
    return sum(_fuzzy_in(w, bag) for w in words) / len(words)


def sim(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 0.5
    if not a or not b:
        return 0.0
    return 0.5 * (coverage(a, set(b)) + coverage(b, set(a)))


_CLAUSE_SPLIT = re.compile(r"[,;:]\s+|\s+(?:and|but|while|whereas|because|which|although|so that|whereas)\s+", re.I)


def clauses(text: str, offset: int, min_words: int) -> list[tuple[int, int]]:
    """Split an English sentence into clauses with at least ``min_words`` content words each."""
    cuts = [0] + [m.end() for m in _CLAUSE_SPLIT.finditer(text)] + [len(text)]
    raw = [(cuts[k], cuts[k + 1]) for k in range(len(cuts) - 1) if cuts[k + 1] > cuts[k]]
    merged: list[tuple[int, int]] = []
    for a, b in raw:
        if merged and len(content_words(text[merged[-1][0] : merged[-1][1]])) < min_words:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    if len(merged) > 1 and len(content_words(text[merged[-1][0] : merged[-1][1]])) < min_words:
        last = merged.pop()
        merged[-1] = (merged[-1][0], last[1])
    return [(offset + a, offset + b) for a, b in merged]


def align(src: list[list[str]], tgt: list[list[str]], skip: float = -0.15, merge_pen: float = 0.05):
    """Monotonic sentence alignment. Returns a list of (src_indices, tgt_indices) groups; either may be empty."""
    n, m = len(src), len(tgt)
    neg = float("-inf")
    f = [[neg] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[int, int] | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    f[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if f[i][j] == neg:
                continue
            moves = [(1, 0, skip), (0, 1, skip)]
            if i < n and j < m:
                moves.append((1, 1, sim(src[i], tgt[j])))
            if i + 1 < n and j < m:
                moves.append((2, 1, sim(src[i] + src[i + 1], tgt[j]) - merge_pen))
            if i < n and j + 1 < m:
                moves.append((1, 2, sim(src[i], tgt[j] + tgt[j + 1]) - merge_pen))
            for di, dj, gain in moves:
                ni, nj = i + di, j + dj
                if ni > n or nj > m:
                    continue
                if f[i][j] + gain > f[ni][nj]:
                    f[ni][nj] = f[i][j] + gain
                    back[ni][nj] = (di, dj)
    groups = []
    i, j = n, m
    while i > 0 or j > 0:
        step = back[i][j]
        assert step is not None, "every cell except (0, 0) is reachable by a skip move"
        di, dj = step
        groups.append((list(range(i - di, i)), list(range(j - dj, j))))
        i, j = i - di, j - dj
    return list(reversed(groups))


UNIT_FAMILIES = {
    "length": [
        "km",
        "kilometr",
        "kilomet",
        "metr",
        "meter",
        "cm",
        "centimetr",
        "centimet",
        "mm",
        "millimetr",
        "mil",
        "inch",
        "foot",
        "feet",
    ],
    "mass": ["kg", "kilogram", "gram", "milligram", "mg", "tonn", "ton", "pound"],
    "volume": ["litr", "liter", "ml", "millilitr", "milliliter"],
    "time": ["second", "minut", "hour", "day", "week", "month", "year", "decad", "century", "centuri"],
    "temperature": ["celsiu", "fahrenheit", "kelvin"],
    "currency": ["rupe", "rupee", "dollar", "paisa", "pais"],
    "month": [
        "january",
        "february",
        "march",
        "april",
        "may",
        "jun",
        "juli",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ],
    "weekday": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
}
_UNIT_LOOKUP = {u: fam for fam, us in UNIT_FAMILIES.items() for u in us}


def units_in(words: list[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for w in words:
        fam = _UNIT_LOOKUP.get(w)
        if fam:
            out.setdefault(fam, set()).add(w)
    return out


# ---------------------------------------------------------------------------
# back-translation
# ---------------------------------------------------------------------------


class BackTranslationCheck(Check):
    name = "back_translation"
    tier = 1
    description = "Segment-wise back-translation with Indic-Translate, sentence alignment and clause coverage -> omission/addition/meaning-drift candidates."

    def applies(self, r, ctx):
        return bool(r.item.translation and r.item.translation.strip()) and r.item.lang != "en"

    def run(self, r: ItemResult, ctx) -> None:
        tgt, src = self.translation(r), r.item.source
        segs = [(a, b) for a, b in segments(tgt) if re.search(r"[^\W\d_]", tgt[a:b])]
        if not segs:
            raise SkipCheck("no translatable text")
        bt = []
        for a, b in segs:
            res = ctx.bodhan.translate(tgt[a:b], "en")
            bt.append(res["translation"])
        r.state["bt_segments"] = [((a, b), t) for (a, b), t in zip(segs, bt)]
        bt_text = " ".join(bt)
        r.state["bt_text"] = bt_text
        bt_words = [w for w, _, _ in content_words(bt_text)]
        r.state["bt_words"] = bt_words
        r.state["bt_numbers"] = {w for w in bt_words if w[:1].isdigit()}

        src_sents = [(a, b) for a, b in segments(src) if re.search(r"[A-Za-z]", src[a:b])]
        src_words = [[w for w, _, _ in content_words(src[a:b])] for a, b in src_sents]
        tgt_words = [[w for w, _, _ in content_words(t)] for t in bt]
        all_src = {w for ws in src_words for w in ws}
        all_bt = set(bt_words)
        r.metrics["bt_coverage"] = round(coverage([w for ws in src_words for w in ws], all_bt), 4)

        min_words = self.param(ctx, "bt_clause_min_content_words")
        max_cov = self.param(ctx, "bt_clause_max_coverage")
        self.extra_min = self.param(ctx, "bt_extra_min_content_words")
        self.extra_share = self.param(ctx, "bt_extra_min_share")
        groups = align(src_words, tgt_words)
        sims = []
        for si, ti in groups:
            if si and not ti:  # source sentence(s) with no counterpart
                for k in si:
                    words = src_words[k]
                    cov = coverage(words, all_bt)
                    if len(words) >= min_words and cov <= max_cov:
                        pos = self._insertion_point(groups, si, segs, len(tgt))
                        a, b = src_sents[k]
                        self.signal(
                            r,
                            "omission",
                            0.6 if cov < 0.2 else 0.45,
                            f"Source sentence has no counterpart in the back-translation (coverage {cov:.0%}): {src[a:b][:100]!r}",
                            severity="major",
                            span=(pos, pos),
                            source_span=(a, b),
                            details={"coverage": round(cov, 3)},
                        )
            elif ti and not si:  # target segment(s) with no source counterpart
                for k in ti:
                    words = tgt_words[k]
                    cov = coverage(words, all_src)
                    if len(words) >= min_words and cov <= max_cov:
                        a, b = segs[k]
                        self.signal(
                            r,
                            "addition",
                            0.6 if cov < 0.2 else 0.45,
                            f"Translated segment has no counterpart in the source; it back-translates to {bt[k][:100]!r}",
                            severity="major",
                            span=(a, b),
                            details={"coverage": round(cov, 3)},
                        )
            else:
                s_ws = [w for k in si for w in src_words[k]]
                t_ws = [w for k in ti for w in tgt_words[k]]
                pair_sim = sim(s_ws, t_ws)
                sims.append(pair_sim)
                tspan = (segs[ti[0]][0], segs[ti[-1]][1])
                sspan = (src_sents[si[0]][0], src_sents[si[-1]][1])
                self._partial(r, src, s_ws, t_ws, sspan, tspan, all_bt, all_src, bt, ti, min_words, max_cov, pair_sim)
        if sims:
            r.metrics["bt_min_sentence_sim"] = round(min(sims), 4)

    @staticmethod
    def _insertion_point(groups, si, segs, n):
        idx = groups.index(next(g for g in groups if g[0] == si))
        for g in reversed(groups[:idx]):
            if g[1]:
                return segs[g[1][-1]][1]
        for g in groups[idx + 1 :]:
            if g[1]:
                return segs[g[1][0]][0]
        return n

    def _partial(self, r, src, s_ws, t_ws, sspan, tspan, all_bt, all_src, bt, ti, min_words, max_cov, pair_sim):
        local_bt = set(t_ws)
        for a, b in clauses(src[sspan[0] : sspan[1]], sspan[0], min_words):
            words = [w for w, _, _ in content_words(src[a:b])]
            if len(words) < min_words or len(words) == len(s_ws):
                continue  # single-clause sentence: handled by sentence-level logic
            cov_local = coverage(words, local_bt)
            cov_global = coverage(words, all_bt)
            if cov_local <= max_cov and cov_global <= max_cov + 0.15:
                self.signal(
                    r,
                    "omission",
                    0.45 if cov_global < 0.2 else 0.35,
                    f"Clause missing from back-translation of the matching sentence (coverage {cov_local:.0%}): {src[a:b][:100]!r}",
                    severity="major",
                    span=tspan,
                    source_span=(a, b),
                    details={"coverage": round(cov_local, 3)},
                )
        extra = [w for w in t_ws if not _fuzzy_in(w, set(s_ws)) and not _fuzzy_in(w, all_src)]
        if len(extra) >= self.extra_min and len(extra) / max(1, len(t_ws)) >= self.extra_share:
            self.signal(
                r,
                "addition",
                0.35,
                f"Back-translation contains content absent from the source: {', '.join(extra[:8])}",
                severity="major",
                span=tspan,
                details={"extra_words": extra[:12]},
            )
        if pair_sim < 0.25 and len(s_ws) >= 4:
            self.signal(
                r,
                "mistranslation",
                0.3,
                f"Back-translation of this sentence shares little meaning with the source (similarity {pair_sim:.0%}): {' '.join(bt[k] for k in ti)[:100]!r}",
                severity="major",
                span=tspan,
                source_span=sspan,
                details={"similarity": round(pair_sim, 3)},
            )
        s_units, t_units = units_in(s_ws), units_in(t_ws)
        for fam, su in s_units.items():
            tu = t_units.get(fam, set())
            if len(su) == 1 and tu and not (su & tu):
                self.signal(
                    r,
                    "number",
                    0.5,
                    f"{fam.title()} word changed: source says {sorted(su)[0]!r}, back-translation says {sorted(tu)[0]!r}",
                    severity="major",
                    span=tspan,
                    source_span=sspan,
                )


# ---------------------------------------------------------------------------
# numbers
# ---------------------------------------------------------------------------

NUM_RE = re.compile(r"(?<![A-Za-z\d.,])\d+(?:[.,]\d+)*")


def extract_numbers(text: str) -> list[tuple[str, int, int]]:
    """Canonical numbers with spans. Works on any Unicode digits; skips digits glued to Latin letters (H2O, CO2)."""
    t = ascii_digits(text)
    out = []
    for m in NUM_RE.finditer(t):
        raw = m.group(0).rstrip(".,")
        out.append((canonical_number(raw), m.start(), m.start() + len(raw)))
    return out


class NumberCheck(Check):
    name = "numbers"
    tier = 0
    description = "Digits, decimals and grouped numbers compared after normalisation (२५ == 25, 1,00,000 == 100000); unit/month words via back-translation."

    def applies(self, r, ctx):
        return bool(r.item.translation)

    def run(self, r: ItemResult, ctx) -> None:
        src, tgt = r.item.source, self.translation(r)
        s_nums, t_nums = extract_numbers(src), extract_numbers(tgt)
        word_vals = {
            canonical_number(str(v)) for w, v in ENGLISH_NUMBER_WORDS.items() if re.search(rf"\b{w}\b", src, re.I)
        }
        r.metrics["numbers_source"] = len(s_nums)
        if not s_nums and not t_nums:
            return
        s_c, t_c = Counter(v for v, _, _ in s_nums), Counter(v for v, _, _ in t_nums)
        missing = list((s_c - t_c).elements())
        extra = list((t_c - s_c).elements())
        bt_nums = r.state.get("bt_numbers", set())
        # take specific occurrences: the last unmatched ones in reading order
        miss_occ = self._occurrences(s_nums, missing)
        extra_occ = self._occurrences(t_nums, extra)
        # pair missing<->extra by relative position: a changed number
        pairs = []
        for e in list(extra_occ):
            if not miss_occ:
                break
            rel_e = e[1] / max(1, len(tgt))
            m = min(miss_occ, key=lambda x: abs(x[1] / max(1, len(src)) - rel_e))
            pairs.append((m, e))
            miss_occ.remove(m)
            extra_occ.remove(e)
        for (mv, ms, me), (ev, es, ee) in pairs:
            score = 0.9 if ev not in bt_nums or mv not in bt_nums else 0.6
            self.signal(
                r,
                "number",
                score,
                f"Number changed: source {src[ms:me]!r} -> translation {tgt[es:ee]!r}",
                severity="major",
                span=(es, ee),
                source_span=(ms, me),
            )
        for mv, ms, me in miss_occ:
            if mv in bt_nums:
                self.signal(
                    r,
                    "number",
                    0.2,
                    f"Source number {src[ms:me]!r} is not in digits in the translation, but the back-translation has it (probably written in words)",
                    severity="minor",
                    span=None,
                    source_span=(ms, me),
                )
            else:
                self.signal(
                    r,
                    "number",
                    0.6,
                    f"Source number {src[ms:me]!r} is missing from the translation",
                    severity="major",
                    span=None,
                    source_span=(ms, me),
                )
        for ev, es, ee in extra_occ:
            if ev in word_vals:
                continue  # source said it in words ("three"), translation used digits
            self.signal(
                r,
                "number",
                0.65,
                f"Translation contains a number not in the source: {tgt[es:ee]!r}",
                severity="major",
                span=(es, ee),
            )

    @staticmethod
    def _occurrences(nums, values):
        need = Counter(values)
        out = []
        for v, a, b in reversed(nums):
            if need[v] > 0:
                out.append((v, a, b))
                need[v] -= 1
        return sorted(out, key=lambda x: x[1])


# ---------------------------------------------------------------------------
# entities and terms
# ---------------------------------------------------------------------------

_SENT_START = re.compile(r"(?:^|[.!?:]\s+|\n\s*(?:[#>*+-]+\s*|\d+[.)]\s*|\|\s*)?)$")
_COMMON_CAPS = {
    "the",
    "a",
    "an",
    "in",
    "on",
    "at",
    "this",
    "that",
    "it",
    "we",
    "i",
    "if",
    "when",
    "for",
    "to",
    "of",
    "and",
    "is",
}


def source_entities(source: str, limit: int = 8) -> list[tuple[str, int, int]]:
    """Proper names, acronyms and formula-like tokens from English text."""
    found: list[tuple[str, int, int]] = []
    for m in re.finditer(
        r"\b(?:[A-Z][a-zA-Z]+(?:[ -][A-Z][a-zA-Z]+)*|[A-Z]{2,}[a-z]?s?|[A-Za-z]*\d+[A-Za-z]+[A-Za-z\d]*|[a-z]+[A-Z][A-Za-z]+)\b",
        source,
    ):
        word = m.group(0)
        start = m.start()
        if word.lower() in _COMMON_CAPS:
            continue
        at_start = bool(_SENT_START.search(source[:start]))
        if at_start and " " not in word and not word.isupper() and not any(c.isdigit() for c in word):
            # sentence-initial capital: only an entity if it is also capitalised elsewhere
            if not re.search(rf"(?<![.!?]\s)(?<!^)\b{re.escape(word)}\b", source[start + len(word) :]):
                continue
        if re.fullmatch(r"\d+[a-z]{1,2}", word):  # 3rd, 21st
            continue
        found.append((word, start, m.end()))
    seen, out = set(), []
    for w, a, b in found:
        if w not in seen:
            seen.add(w)
            out.append((w, a, b))
    return out[:limit]


class EntityCheck(Check):
    name = "entities"
    tier = 1
    description = "Names/terms from the source must appear in Latin or as their Indic-Transliterate form, or be confirmed by the back-translation."

    def applies(self, r, ctx):
        return bool(r.item.translation) and r.item.lang != "en"

    def run(self, r: ItemResult, ctx) -> None:
        src, tgt = r.item.source, self.translation(r)
        ents = source_entities(src)
        if not ents:
            raise SkipCheck("no names or terms in source")
        thr = self.param(ctx, "entity_match_similarity")
        tgt_tokens = [normalize_text(t.text, asr_fold=True) for t in word_tokens(tgt)]
        tok_objs = word_tokens(tgt)
        bt_text = r.state.get("bt_text", "")
        bt_tokens = [t.text.lower() for t in word_tokens(bt_text)]
        renderings = r.state.setdefault("entity_renderings", {})
        translit_ok = ctx.bodhan.available("translate")
        for word, a, b in ents:
            if word.lower() in tgt.lower():
                renderings[word] = word
                continue
            best = (0.0, -1, -1)
            if translit_ok:
                try:
                    native = normalize_text(ctx.bodhan.transliterate(word, r.item.lang), asr_fold=True)
                except Exception as e:  # transliteration is an aid; fall back to the back-translation
                    native, translit_ok = "", False
                    r.checks.setdefault(self.name, {}).setdefault("notes", []).append(f"transliterate failed: {e}")
                if native:
                    best = best_window_match(native, tgt_tokens)
                    if best[0] >= thr:
                        renderings[word] = " ".join(tok_objs[k].text for k in range(best[1], best[2] + 1))
                        continue
            if bt_tokens and best_window_match(word.lower(), bt_tokens)[0] >= 85:
                continue  # translated by meaning; the back-translation confirms it
            near = ""
            if best[1] >= 0:
                near = f"; closest translation words {tgt[tok_objs[best[1]].start : tok_objs[best[2]].end]!r} ({best[0]:.0f}% similar)"
            score = 0.55 if (" " in word or word.isupper() or any(c.isdigit() for c in word)) else 0.45
            if not bt_text:
                score -= 0.1
            span = (tok_objs[best[1]].start, tok_objs[best[2]].end) if best[1] >= 0 and best[0] >= 50 else None
            self.signal(
                r,
                "term",
                score,
                f"Term {word!r} not found in the translation (no Latin form, no transliteration match{near}) and not in the back-translation",
                severity="major",
                span=span,
                source_span=(a, b),
            )


def consistency_signals(results: list[ItemResult]) -> None:
    """Dataset-level: the same source term should be rendered the same way in every item of a language."""
    by_key: dict[tuple[str, str], list[tuple[ItemResult, str]]] = {}
    for r in results:
        for term, rendering in r.state.get("entity_renderings", {}).items():
            if rendering != term:  # only transliterated renderings can disagree
                by_key.setdefault((r.item.lang, term), []).append((r, rendering))
    for (lang, term), uses in by_key.items():
        if len(uses) < 3:
            continue
        variants = Counter(normalize_text(v, asr_fold=True) for _, v in uses)
        top, top_n = variants.most_common(1)[0]
        for r, v in uses:
            nv = normalize_text(v, asr_fold=True)
            if nv != top and fuzz.ratio(nv, top) < 80 and top_n >= 2:
                pos = (r.item.translation or "").find(v)
                span = (pos, pos + len(v)) if pos >= 0 else None
                r.signals.append(
                    Signal(
                        check="term_consistency",
                        category="term",
                        score=0.35,
                        evidence=f"{term!r} is rendered differently here than in {top_n} other {lang} items",
                        severity="minor",
                        span=span,
                    )
                )
