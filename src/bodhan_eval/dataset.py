"""JSONL dataset and calibration-label loading. Bad lines are reported, never fatal."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import canonical_category, canonical_severity
from .models import Item, Label


@dataclass
class LoadReport:
    bad: list[dict] = field(default_factory=list)  # {"line", "id", "reason"}
    filtered_out: int = 0  # items whose lang is not in --langs
    notes: list[dict] = field(default_factory=list)  # non-fatal problems on kept items
    unknown_label_types: dict[str, int] = field(default_factory=dict)


def _span(v) -> tuple[int, int] | None:
    if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, int) for x in v) and 0 <= v[0] <= v[1]:
        return (int(v[0]), int(v[1]))
    return None


def parse_labels(raw, default_span_on: str, rep: LoadReport, where: str) -> list[Label] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        rep.notes.append({"item": where, "reason": "labels is not a list; ignored"})
        return None
    out = []
    for lab in raw:
        if not isinstance(lab, dict):
            continue
        raw_type = str(lab.get("type", ""))
        cat = canonical_category(raw_type)
        if cat is None:
            rep.unknown_label_types[raw_type] = rep.unknown_label_types.get(raw_type, 0) + 1
        span_on = str(lab.get("span_on") or default_span_on).lower()
        span_on = "source" if span_on == "source" else "translation"
        span = _span(lab.get("span"))
        if span is None and _span(lab.get("source_span")) is not None:
            span, span_on = _span(lab.get("source_span")), "source"
        out.append(
            Label(
                category=cat,
                raw_type=raw_type,
                severity=canonical_severity(lab.get("severity")),
                span=span,
                span_on=span_on,
                annotator=lab.get("annotator"),
            )
        )
    return out


def load_dataset(
    path: str | Path, langs: set[str] | None, label_span_on: str = "translation"
) -> tuple[list[Item], LoadReport]:
    path = Path(path)
    base = path.parent
    rep = LoadReport()
    items: list[Item] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                rep.bad.append({"line": n, "id": None, "reason": f"invalid JSON: {e.msg}"})
                continue
            if not isinstance(obj, dict):
                rep.bad.append({"line": n, "id": None, "reason": "line is not a JSON object"})
                continue
            iid, src, lang = obj.get("id"), obj.get("source"), obj.get("lang")
            if (
                iid is None
                or not isinstance(src, str)
                or not src.strip()
                or not isinstance(lang, str)
                or not lang.strip()
            ):
                rep.bad.append({"line": n, "id": iid, "reason": "missing or empty required field (id, source, lang)"})
                continue
            lang = lang.strip()
            if langs and lang not in langs:
                rep.filtered_out += 1
                continue
            key = f"{iid}::{lang}"
            if key in seen:
                rep.bad.append({"line": n, "id": iid, "reason": f"duplicate id for lang {lang}"})
                continue
            seen.add(key)
            audio = obj.get("audio")
            audio_path = None
            if isinstance(audio, str) and audio.strip():
                p = Path(audio)
                p = p if p.is_absolute() else (base / p)
                if p.is_file():
                    audio_path = str(p.resolve())
                else:
                    rep.notes.append({"item": key, "reason": f"audio file not found: {audio}"})
            trans = obj.get("translation")
            ref = obj.get("reference")
            items.append(
                Item(
                    id=str(iid),
                    lang=lang,
                    source=src,
                    reference=ref if isinstance(ref, str) and ref.strip() else None,
                    translation=trans if isinstance(trans, str) and trans.strip() else None,
                    audio=audio_path,
                    labels=parse_labels(obj.get("labels"), label_span_on, rep, key),
                    line_no=n,
                )
            )
    return items, rep


def apply_calibration_file(
    path: str | Path, items: list[Item], langs: set[str] | None, rep: LoadReport, label_span_on: str
) -> list[Item]:
    """Attach labels from ``--calibration``. Lines that carry their own source/outputs and are not in the
    dataset become calibration-only items (scored and used for calibration, kept out of the main summary)."""
    by_key = {it.key: it for it in items}
    by_id: dict[str, list[Item]] = {}
    for it in items:
        by_id.setdefault(it.id, []).append(it)
    extra_items, extra_rep = load_dataset(path, langs, label_span_on)
    rep.unknown_label_types.update(
        {k: rep.unknown_label_types.get(k, 0) + v for k, v in extra_rep.unknown_label_types.items()}
    )
    added = []
    for it in extra_items:
        if it.key in by_key:
            if it.labels is not None:
                by_key[it.key].labels = it.labels
        else:
            it.calibration_only = True
            added.append(it)
    # label-only lines (id + labels, no source) are rejected by load_dataset; handle them here
    with Path(path).open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict) or obj.get("source") or "labels" not in obj:
                continue
            iid, lang = str(obj.get("id")), obj.get("lang")
            targets = [by_key[f"{iid}::{lang}"]] if lang and f"{iid}::{lang}" in by_key else by_id.get(iid, [])
            if len(targets) != 1:
                rep.notes.append(
                    {"item": iid, "reason": f"calibration line {n}: cannot match to exactly one dataset item"}
                )
                continue
            targets[0].labels = parse_labels(obj.get("labels"), label_span_on, rep, targets[0].key)
    return added
