"""Speech checks.

``audio_stats`` (tier 0, local): duration, silences, clipping, broadband noise,
speaking rate vs this language's median rate in the dataset.

``asr`` (tier 1): back-transcribes the audio with Indic-Transcribe in <= 30 s
chunks cut at pauses, aligns the transcript word-by-word with the text that was
spoken, and turns alignment gaps into candidates:

* text words with no transcript counterpart -> omission (truncation if at the end)
* transcript words with no text counterpart that repeat neighbouring text -> repetition
* transcript n-grams that occur more often than in the text -> repetition
* a transcript that matches the text badly everywhere -> garbled

Separating ASR mistakes from real speech errors:

* a real omission is a *contiguous* run of missing words; ASR noise is scattered
  substitutions, so only runs of >= ``asr_min_deleted_words`` count;
* duration must agree: a real omission makes the audio shorter than this
  language's speaking rate predicts, a real repetition makes it longer;
* every omission/repetition candidate gets a second-opinion transcription with
  different chunk boundaries. If the missing words appear in the second
  transcript (or the repetition does not), the candidate is dismissed as checker
  noise and logged in ``dismissed`` with both transcripts' evidence.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from .. import audio as A
from .. import markup
from ..config import lang_info, langs
from ..models import ItemResult
from ..normalize import normalize_text, word_tokens
from ..spans import char_error_rate, similarity, word_alignment
from .base import Check, SkipCheck


def speakable(text: str) -> str:
    """Mask markup with spaces so offsets stay identical to the original text."""
    chars = list(text)

    def blank(a: int, b: int) -> None:
        for k in range(a, b):
            if chars[k] != "\n":
                chars[k] = " "

    for s in markup.math_segments(text):
        blank(s.start, s.end)
    for m in markup.LINK_RE.finditer(text):
        blank(m.start(2) - 2, m.end())  # keep link text, drop "](url)"
        blank(m.start(), m.start() + 1)
    for m in markup.URL_RE.finditer(text):
        blank(m.start(), m.end())
    for m in re.finditer(r"^\s*(?:#{1,6}|[-*+>]|\d+[.)])\s", text, re.M):
        blank(m.start(), m.end())
    for m in re.finditer(r"[|*_`#~]|^\s*:?-{3,}:?\s*$", text, re.M):
        blank(m.start(), m.end())
    return "".join(chars)


def speakable_for_tts(text: str) -> str:
    return re.sub(r"\s+", " ", speakable(text)).strip()


def _time_to_char(t: float, st: A.AudioStats, n_chars: int) -> int:
    span = max(1e-6, st.duration_s - st.lead_silence_s - st.trail_silence_s)
    frac = (t - st.lead_silence_s) / span
    return int(max(0.0, min(1.0, frac)) * n_chars)


def _snap(text: str, a: int, b: int) -> tuple[int, int]:
    """Widen a character span to whole words."""
    while a > 0 and not text[a - 1].isspace():
        a -= 1
    while b < len(text) and not text[b].isspace():
        b += 1
    return a, max(a, b)


def _rate(ctx, lang: str) -> tuple[float, int]:
    return ctx.stats.chars_per_second.get(lang, (langs()["priors"]["chars_per_second"], 0))


def spoken_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", speakable(text)))


class AudioStatsCheck(Check):
    name = "audio_stats"
    area = "speech"
    tier = 0
    description = "Duration vs speaking rate, long or edge silences, clipping and broadband noise from the waveform."

    def applies(self, r, ctx):
        return bool(r.item.audio)

    def run(self, r: ItemResult, ctx) -> None:
        x, sr = ctx.load_audio(r.item.audio)
        st = A.analyse(x, sr)
        r.state["audio_stats"] = st
        r.metrics["audio"] = st.summary()
        text = r.item.translation or ""
        n = len(text)
        p = ctx.params
        if st.duration_s < 0.2 or st.active_s < 0.1:
            self.signal(
                r,
                "speech_garbled",
                0.95,
                f"Audio is empty or silent ({st.duration_s:.2f} s, {st.active_s:.2f} s of sound)",
                severity="critical",
                span=(0, n) if n else None,
            )
            return
        ls = st.longest_silence
        if ls and ls[1] - ls[0] >= p["audio_long_silence_s"]:
            gap = ls[1] - ls[0]
            span = _snap(text, *(2 * [_time_to_char((ls[0] + ls[1]) / 2, st, n)])) if n else None
            self.signal(
                r,
                "speech_garbled",
                min(0.85, 0.55 + 0.1 * (gap - p["audio_long_silence_s"])),
                f"Silence of {gap:.1f} s inside the speech at {ls[0]:.1f}-{ls[1]:.1f} s",
                severity="major",
                span=span,
                details={"time_s": [round(ls[0], 2), round(ls[1], 2)]},
            )
        for edge, length in (("leading", st.lead_silence_s), ("trailing", st.trail_silence_s)):
            if length >= p["audio_edge_silence_s"]:
                span = (0, 0) if edge == "leading" else (n, n)
                self.signal(
                    r,
                    "speech_garbled",
                    0.5,
                    f"{length:.1f} s of {edge} silence",
                    severity="minor",
                    span=span if n else None,
                )
        if st.clip_ratio >= p["audio_clip_ratio"]:
            a, b = st.clip_regions[0] if st.clip_regions else (0.0, st.duration_s)
            span = (_time_to_char(a, st, n), max(_time_to_char(b, st, n), _time_to_char(a, st, n) + 1)) if n else None
            self.signal(
                r,
                "speech_garbled",
                min(0.9, 0.6 + 20 * st.clip_ratio),
                f"Clipping: {st.clip_ratio:.2%} of samples at full scale (first at {a:.1f} s)",
                severity="major",
                span=_snap(text, *span) if span else None,
                details={"clip_regions_s": [[round(u, 2), round(v, 2)] for u, v in st.clip_regions[:5]]},
            )
        for a, b in st.noise_runs[:3]:
            span = _snap(text, _time_to_char(a, st, n), _time_to_char(b, st, n)) if n else None
            self.signal(
                r,
                "speech_garbled",
                min(0.85, 0.6 + 0.2 * (b - a)),
                f"{b - a:.1f} s of broadband noise at {a:.1f}-{b:.1f} s",
                severity="major",
                span=span,
                details={"time_s": [round(a, 2), round(b, 2)]},
            )
        if text:
            rate, k = _rate(ctx, r.item.lang)
            expected = spoken_chars(text) / rate
            ratio = st.active_s / max(expected, 1e-6)
            r.metrics["duration_ratio"] = round(ratio, 3)
            r.state["duration_ratio"] = ratio
            if ratio < p["duration_short_ratio"]:
                self.signal(
                    r,
                    "speech_omission",
                    0.3,
                    f"Speech lasts {st.active_s:.1f} s, {ratio:.0%} of the {expected:.1f} s expected for this text at {rate:.1f} chars/s (n={k})",
                    span=None,
                )
            elif ratio > p["duration_long_ratio"]:
                self.signal(
                    r,
                    "speech_repetition",
                    0.25,
                    f"Speech lasts {st.active_s:.1f} s, {ratio:.0%} of the {expected:.1f} s expected for this text (n={k})",
                    span=None,
                )


class AsrCheck(Check):
    name = "asr"
    area = "speech"
    tier = 1
    description = "Back-transcription with Indic-Transcribe (<=30 s chunks), word alignment, second-opinion re-transcription for candidates."

    def applies(self, r, ctx):
        return bool(r.item.audio and r.item.translation)

    def _transcribe(self, ctx, x, sr, plan, lang) -> str:
        parts = []
        for a, b in plan:
            parts.append(ctx.bodhan.transcribe(A.wav_bytes(x[a:b], sr), lang))
        return " ".join(p for p in parts if p)

    def run(self, r: ItemResult, ctx) -> None:
        info = lang_info(r.item.lang)
        text = self.translation(r)
        x, sr = ctx.load_audio(r.item.audio)
        hyp = self._transcribe(ctx, x, sr, A.chunk_plan(x, sr), info.asr_lang)
        r.state["transcript"] = hyp
        spk = speakable(text)
        ref_toks = word_tokens(spk)
        if not ref_toks:
            raise SkipCheck("no speakable words in the text")
        ref = [normalize_text(t.text, asr_fold=True) for t in ref_toks]
        hyp_words = [normalize_text(t.text, asr_fold=True) for t in word_tokens(hyp)]
        cer = char_error_rate(" ".join(ref), " ".join(hyp_words))
        r.metrics["asr_cer"] = round(cer, 4)
        r.metrics["asr_words"] = len(hyp_words)
        p = ctx.params
        cands = self._candidates(r, ctx, text, ref_toks, ref, hyp_words, damp=1.0)
        # Garbled = poor match *outside* the contiguous gaps already explained as omission/repetition,
        # so a clean truncation is not double-reported as unintelligible speech.
        gap_words = {k for c in cands if c["category"] == "speech_omission" for k in range(*c["words"])}
        residual_ref = [w for k, w in enumerate(ref) if k not in gap_words]
        residual_cer = char_error_rate(" ".join(residual_ref), " ".join(hyp_words)) if residual_ref else 0.0
        r.metrics["asr_residual_cer"] = round(residual_cer, 4)
        garbled = residual_cer >= p["asr_garbled_cer"]
        if garbled:
            self.signal(
                r,
                "speech_garbled",
                min(0.85, 0.45 + 0.5 * (residual_cer - p["asr_garbled_cer"])),
                f"Transcript matches the text poorly even outside missing/repeated stretches "
                f"(character error rate {residual_cer:.0%}): speech may be unintelligible",
                severity="major",
                span=(0, len(text)),
                details={"cer": round(cer, 3), "residual_cer": round(residual_cer, 3)},
            )
            for c in cands:
                c["score"] *= 0.5  # alignment gaps are unreliable when the whole transcript is poor
        if not cands:
            return
        alt_plan = A.alt_chunk_plan(x, sr)
        alt_hyp = self._transcribe(ctx, x, sr, alt_plan, info.asr_lang)
        alt_words = [normalize_text(t.text, asr_fold=True) for t in word_tokens(alt_hyp)]
        alt_ok = self._matched_mask(ref, alt_words)
        alt_counts = Counter(zip(alt_words, alt_words[1:], alt_words[2:]))
        ratio = r.state.get("duration_ratio")
        for c in cands:
            i1, i2 = c["words"]
            if c["category"] == "speech_omission":
                recovered = sum(alt_ok[i1:i2]) / max(1, i2 - i1)
                if recovered >= p["asr_second_opinion_recovery"]:
                    r.dismissed.append(
                        {
                            "check": self.name,
                            "category": c["category"],
                            "span": list(c["span"]),
                            "reason": f"second transcription (different chunking) contains {recovered:.0%} of the 'missing' words: likely an ASR miss",
                        }
                    )
                    continue
                c["score"] += 0.15
                c["evidence"] += f"; confirmed by a second transcription ({recovered:.0%} recovered)"
                if ratio is not None and ratio < 0.92:
                    c["score"] += 0.1
                    c["evidence"] += f"; audio is shorter than expected ({ratio:.0%})"
                elif ratio is not None and ratio > 1.05 and i2 < len(ref):
                    c["score"] -= 0.15
                    c["evidence"] += f"; but audio length is normal ({ratio:.0%})"
            else:
                g = c.get("ngram")
                if g is not None and alt_counts[g] < 2:
                    r.dismissed.append(
                        {
                            "check": self.name,
                            "category": c["category"],
                            "span": list(c["span"]),
                            "reason": "repeated phrase not present in a second transcription: likely an ASR artefact",
                        }
                    )
                    continue
                c["score"] += 0.1
                if ratio is not None and ratio > 1.08:
                    c["score"] += 0.1
                    c["evidence"] += f"; audio is longer than expected ({ratio:.0%})"
            self.signal(
                r,
                c["category"],
                c["score"],
                c["evidence"],
                severity=c["severity"],
                span=c["span"],
                details=c.get("details", {}),
            )

    @staticmethod
    def _matched_mask(ref: list[str], hyp: list[str]) -> list[bool]:
        ok = [False] * len(ref)
        for tag, i1, i2, j1, j2 in word_alignment(ref, hyp):
            if tag == "equal":
                for k in range(i1, i2):
                    ok[k] = True
            elif tag == "replace":
                for k, m in zip(range(i1, i2), range(j1, j2)):
                    ok[k] = similarity(ref[k], hyp[m]) >= 0.6
        return ok

    def _candidates(self, r, ctx, text, ref_toks, ref, hyp, damp: float) -> list[dict]:
        p = ctx.params
        ops = word_alignment(ref, hyp)
        # merge consecutive non-equal blocks (allowing a 1-word 'equal' island inside a gap)
        gaps, cur = [], None
        for k, (tag, i1, i2, j1, j2) in enumerate(ops):
            if tag != "equal" or (cur and i2 - i1 == 1 and k + 1 < len(ops) and ops[k + 1][0] != "equal"):
                cur = [i1, i2, j1, j2] if cur is None else [cur[0], i2, cur[2], j2]
            else:
                if cur:
                    gaps.append(cur)
                cur = None
        if cur:
            gaps.append(cur)
        out: list[dict[str, Any]] = []
        n_ref = len(ref)
        for i1, i2, j1, j2 in gaps:
            missing = (i2 - i1) - (j2 - j1)
            extra = -missing
            if missing > 0:
                miss_chars = sum(len(w) for w in ref[i1:i2]) - sum(len(w) for w in hyp[j1:j2])
                at_end = i2 == n_ref
                need = p["asr_tail_min_words"] if at_end else p["asr_min_deleted_words"]
                if missing >= need and miss_chars >= p["asr_min_deleted_chars"]:
                    span = (ref_toks[i1].start, ref_toks[i2 - 1].end)
                    frac = (i2 - i1) / max(1, n_ref)
                    kind = "truncated: the end of the text is not spoken" if at_end else "not spoken"
                    out.append(
                        {
                            "category": "speech_omission",
                            "words": (i1, i2),
                            "span": span,
                            "score": damp * min(0.7, 0.35 + 0.05 * missing + (0.1 if at_end else 0.0)),
                            "severity": "critical" if frac > 0.3 else "major",
                            "evidence": f"{missing} words {kind} (text words {i1}-{i2 - 1} have no counterpart in the transcript): {text[span[0] : span[1]][:80]!r}",
                            "details": {"missing_words": missing, "at_end": at_end},
                        }
                    )
            elif extra >= p["asr_min_repeated_words"]:
                ins = " ".join(hyp[j1 + (i2 - i1) : j2]) if i2 > i1 else " ".join(hyp[j1:j2])
                k = extra
                before = " ".join(ref[max(0, i1 - k) : i1])
                after = " ".join(ref[i2 : i2 + k])
                best = max(similarity(ins, before), similarity(ins, after))
                if best >= p["asr_repeat_similarity"]:
                    a_idx = max(0, i1 - k) if similarity(ins, before) >= similarity(ins, after) else i2
                    b_idx = min(n_ref, a_idx + k) - 1
                    span = (ref_toks[a_idx].start, ref_toks[max(a_idx, b_idx)].end)
                    out.append(
                        {
                            "category": "speech_repetition",
                            "words": (a_idx, b_idx + 1),
                            "span": span,
                            "score": damp * min(0.65, 0.4 + 0.05 * extra),
                            "severity": "major",
                            "evidence": f"Transcript has {extra} extra words repeating the neighbouring text ({best:.0%} similar): {text[span[0] : span[1]][:80]!r}",
                            "ngram": tuple(hyp[j1 : j1 + 3]) if extra >= 3 else None,
                        }
                    )
        # repeated trigrams that the text does not repeat (catches loops the gap logic splits up)
        ref_c = Counter(zip(ref, ref[1:], ref[2:]))
        hyp_c = Counter(zip(hyp, hyp[1:], hyp[2:]))
        for g, c in hyp_c.items():
            if c >= 2 and c > ref_c.get(g, 0) and len("".join(g)) >= 8:
                pos = next((k for k in range(len(ref) - 2) if tuple(ref[k : k + 3]) == g), None)
                if pos is None:
                    continue
                span = (ref_toks[pos].start, ref_toks[pos + 2].end)
                if any(
                    o["category"] == "speech_repetition" and o["span"][0] <= span[1] and span[0] <= o["span"][1]
                    for o in out
                ):
                    continue
                out.append(
                    {
                        "category": "speech_repetition",
                        "words": (pos, pos + 3),
                        "span": span,
                        "score": damp * 0.45,
                        "severity": "major",
                        "evidence": f"Phrase spoken {c} times but written {ref_c.get(g, 0)} time(s): {text[span[0] : span[1]][:80]!r}",
                        "ngram": g,
                    }
                )
        return out


def audio_path_ok(path: str | None) -> bool:
    if not path:
        return False
    return Path(path).is_file()
