"""Tier-2 check: the LLM judge.

Design choices, all aimed at the "judge reliability" and "LLM never writes
Indian-language text" requirements:

* The translation is shown as numbered whitespace tokens and the judge answers
  with token *indices*. It never has to write Indic text to say where an error is,
  and a span it gives can always be mapped exactly back to the translation.
  Indices out of range are rejected, so hallucinated locations are dropped.
* Explanations are English; any Indic characters that still appear in them are
  masked by ``strip_indic`` before they reach the report.
* Temperature 0, and every answer is cached by its exact prompt.
* The judge is asked ``replicas`` times with the same information presented in a
  different order (source-first vs translation-first, findings before/after the
  back-translation). Each replica contributes evidence with weight
  ``replica_weight``; one replica alone stays below the default flag threshold,
  so a single unconfirmed judgement lands in the review queue rather than in the
  flags. Agreement between replicas is reported as judge consistency.
* The judge sees the deterministic findings and the back-translation, which
  counters its tendency to accept fluent output, but is told both can be wrong.
"""

from __future__ import annotations

from importlib import resources

from ..clients import strip_indic
from ..config import canonical_category, canonical_severity, category_area, lang_info
from ..models import ItemResult
from ..normalize import ws_tokens
from ..spans import span_to_token_range, tokens_to_span
from .base import Check, SkipCheck

ALLOWED = {"omission", "addition", "mistranslation", "number", "term", "format", "wrong_language"}


def rubric(lang_name: str) -> str:
    text = resources.files("bodhan_eval.data").joinpath("judge_rubric.md").read_text(encoding="utf-8")
    return text.replace("{lang_name}", lang_name)


def numbered(tokens) -> str:
    return " ".join(f"[{k}]{t.text}" for k, t in enumerate(tokens))


class JudgeCheck(Check):
    name = "judge"
    tier = 2
    description = "LLM judge with a written MQM-style rubric; answers with token-index spans; asked twice with re-ordered prompts."

    def applies(self, r, ctx):
        return bool(r.item.translation and r.item.translation.strip()) and ctx.options.get("judge", True)

    def run(self, r: ItemResult, ctx) -> None:
        if not ctx.llm.available():
            raise SkipCheck("LLM not configured (LLM_MODEL / LLM_API_KEY)")
        info = lang_info(r.item.lang)
        s_tok, t_tok = ws_tokens(r.item.source), ws_tokens(self.translation(r))
        if len(t_tok) > 1500:
            raise SkipCheck("translation too long for the judge prompt")
        findings = self._findings(r, s_tok, t_tok)
        bt = r.state.get("bt_segments", [])
        bt_text = "\n".join(f"- {text}" for _, text in bt) or "(not available)"
        blocks = {
            "SOURCE": f"SOURCE (English):\n{numbered(s_tok)}",
            "TRANSLATION": f"TRANSLATION ({info.name}):\n{numbered(t_tok)}",
            "BT": f"BACK-TRANSLATION (noisy, per segment):\n{bt_text}",
            "FINDINGS": f"AUTOMATIC FINDINGS (may be false alarms):\n{findings}",
        }
        orders = [
            ["SOURCE", "TRANSLATION", "BT", "FINDINGS"],
            ["TRANSLATION", "SOURCE", "FINDINGS", "BT"],
            ["FINDINGS", "SOURCE", "BT", "TRANSLATION"],
        ]
        replicas = int(ctx.judge_cfg["replicas"])
        weight = float(ctx.judge_cfg["replica_weight"])
        verdicts: list[list[str] | None] = []
        invalid = 0
        for k in range(replicas):
            order = orders[k % len(orders)]
            user = "\n\n".join(blocks[b] for b in order) + "\n\nReturn the JSON now."
            messages = [{"role": "system", "content": rubric(info.name)}, {"role": "user", "content": user}]
            obj = ctx.llm.chat_json(messages, max_tokens=int(ctx.judge_cfg["max_tokens"]))
            if obj is None or not isinstance(obj.get("errors"), list):
                invalid += 1
                verdicts.append(None)
                continue
            cats = set()
            for e in obj["errors"]:
                sig = self._to_signal(r, e, s_tok, t_tok, weight, k)
                if sig is None:
                    invalid += 1
                else:
                    cats.add(sig.category)
            verdicts.append(sorted(cats))
        r.state["judge_verdicts"] = verdicts
        r.metrics["judge_invalid"] = invalid
        valid = [v for v in verdicts if v is not None]
        if len(valid) >= 2:
            r.metrics["judge_agree_binary"] = len({bool(v) for v in valid}) == 1
            r.metrics["judge_agree_categories"] = len({tuple(v) for v in valid}) == 1

    def _findings(self, r, s_tok, t_tok) -> str:
        lines = []
        for s in r.signals:
            if category_area(s.category) != "translation" or s.score < 0.3:
                continue
            where = []
            if s.span and s.span[1] > s.span[0]:
                rng = span_to_token_range(t_tok, s.span)
                if rng:
                    where.append(f"translation tokens {rng[0]}-{rng[1]}")
            if s.source_span:
                rng = span_to_token_range(s_tok, s.source_span)
                if rng:
                    where.append(f"source tokens {rng[0]}-{rng[1]}")
            lines.append(f"- [{s.category}] {s.evidence} ({', '.join(where) or 'location unknown'})")
        return "\n".join(lines[:20]) or "(none)"

    def _to_signal(self, r, e: dict, s_tok, t_tok, weight: float, replica: int):
        if not isinstance(e, dict):
            return None
        cat = canonical_category(str(e.get("category", "")))
        if cat not in ALLOWED:
            return None

        def rng(v, toks):
            if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, int) for x in v)):
                return None
            a, b = v
            if a < 0 or b < a or a >= len(toks):
                return None
            return tokens_to_span(toks, a, min(b, len(toks) - 1))

        span = rng(e.get("target_tokens"), t_tok)
        sspan = rng(e.get("source_tokens"), s_tok)
        if span is None and sspan is None and cat not in ("omission", "wrong_language", "format"):
            return None  # an error we cannot localise is not actionable
        try:
            conf = float(e.get("confidence", 0.7))
        except (TypeError, ValueError):
            conf = 0.7
        conf = max(0.0, min(1.0, conf))
        explanation = strip_indic(str(e.get("explanation", ""))[:300])
        return self.signal(
            r,
            cat,
            weight * (0.7 + 0.3 * conf),
            f"Judge (replica {replica + 1}): {explanation}",
            severity=canonical_severity(e.get("severity")),
            span=span,
            source_span=sspan,
            details={"replica": replica, "confidence": round(conf, 3)},
        )
