"""Step 4a — offline haiku detection on a pipeline packet.

No model, no network: every group of three consecutive OCR lines is scored on

* syllable pattern — how far the three lines are from 5-7-5, using the
  min/max ranges from :mod:`syllables` (so "fire" may be 1 or 2);
* layout — a haiku in a journal is almost always its own short stanza: three
  short lines set apart by blank space, much narrower than the prose column.
  The packet carries paragraph membership, line widths and inter-line gaps,
  and those move the score more than the syllable count does, because OCR
  errors and English ambiguity make the count alone unreliable;
* hygiene — dates, page numbers, headings, mostly-numeric or low-confidence
  lines can never be part of a haiku.

The result is a JSON document with, for every accepted haiku, the three lines,
the per-word syllable breakdown (the "explanation of syllable count
validation" the AI prompt also asks for), a score, the reasons, and the source
line ids / bounding box so it can be traced back to the page image.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import TOOL_NAME, __version__
from .packet import Packet, PacketLine, read_packet
from .syllables import backend_name, count_line, explain_line

TARGET = (5, 7, 5)

_MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE_PATTERNS = [
    re.compile(r"^\W*(?:mon|tues|tue|wednes|wed|thurs|thu|fri|satur|sat|sun)(?:day)?\b", re.I),
    re.compile(rf"\b{_MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?\b", re.I),
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTHS}\b", re.I),
    re.compile(rf"\b{_MONTHS}\s+(?:19|20)\d{{2}}\b", re.I),
    re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b"),
    re.compile(r"\b(?:19|20)\d{2}[/.\-]\d{1,2}[/.\-]\d{1,2}\b"),
    re.compile(r"^\W*(?:19|20)\d{2}\W*$"),
]
_TIME_RE = re.compile(r"\b\d{1,2}[:.]\d{2}\s*(?:am|pm|h)?\b", re.I)
_LEADING_MARKS = re.compile(r"^[\W_]+", re.U)                       # bullets, dashes, quotes, ~~ artefacts
_TRAILING_MARKS = re.compile(r"[\s\"'“”‘’)\]\-–—~_=|*]+$")           # keep sentence punctuation


@dataclass
class LineAnalysis:
    line: PacketLine
    text: str                      # cleaned of leading bullets / quotes
    syl_lo: int
    syl_hi: int
    breakdown: List[Tuple[str, Tuple[int, int]]]
    word_count: int
    letter_ratio: float
    excluded: List[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return not self.excluded

    def deviation(self, target: int) -> int:
        if self.syl_lo <= target <= self.syl_hi:
            return 0
        return min(abs(self.syl_lo - target), abs(self.syl_hi - target))

    def chosen(self, target: int) -> int:
        if self.syl_lo <= target <= self.syl_hi:
            return target
        return self.syl_lo if abs(self.syl_lo - target) <= abs(self.syl_hi - target) else self.syl_hi


@dataclass
class Options:
    tolerance_per_line: int = 1
    tolerance_total: int = 2
    min_score: float = 0.5
    min_confidence: float = 20.0      # OCR word confidence; lines below are ignored
    max_words_per_line: int = 10
    include_free_form: bool = True    # isolated 3-line stanzas that are not 5-7-5
    include_rejected: bool = False


def is_date_like(text: str) -> bool:
    t = text.strip()
    if any(rx.search(t) for rx in _DATE_PATTERNS):
        return True
    if _TIME_RE.search(t) and len(t.split()) <= 4:
        return True
    return False


def analyse_line(line: PacketLine, opts: Options) -> LineAnalysis:
    text = _TRAILING_MARKS.sub("", _LEADING_MARKS.sub("", line.text)).strip()
    (lo, hi), words = count_line(text)
    letters = sum(ch.isalpha() for ch in text)
    non_space = sum(not ch.isspace() for ch in text)
    ratio = letters / non_space if non_space else 0.0
    a = LineAnalysis(line=line, text=text, syl_lo=lo, syl_hi=hi, breakdown=words,
                     word_count=len(words), letter_ratio=round(ratio, 2))
    if not text or a.word_count == 0:
        a.excluded.append("empty")
    if a.word_count > opts.max_words_per_line:
        a.excluded.append(f"{a.word_count} words (prose)")
    if is_date_like(text):
        a.excluded.append("date/time")
    if text and ratio < 0.6:
        a.excluded.append(f"letters {ratio:.0%} (numbers/punctuation)")
    if re.fullmatch(r"\W*\d+\W*", text or ""):
        a.excluded.append("page number")
    if line.conf is not None and line.conf < opts.min_confidence:
        a.excluded.append(f"ocr confidence {line.conf:.0f}")
    if line.kind == "ocr_header":
        a.excluded.append("header")
    if hi == 0:
        a.excluded.append("no syllables")
    if lo > 12:
        a.excluded.append(f"{lo}+ syllables")
    return a


@dataclass
class Candidate:
    lines: Tuple[LineAnalysis, LineAnalysis, LineAnalysis]
    deviation: int
    per_line_deviation: Tuple[int, int, int]
    score: float
    form: str
    validation: str
    notes: List[str]

    @property
    def ids(self) -> List[str]:
        return [a.line.id for a in self.lines]


def _structure(cands: Sequence[LineAnalysis], packet: Packet) -> Tuple[float, List[str]]:
    a, b, c = cands
    score = 0.0
    notes: List[str] = []
    same_par = a.line.par_id == b.line.par_id == c.line.par_id
    if same_par and a.line.par_size == 3:
        score += 0.20
        notes.append("isolated 3-line stanza")
    elif same_par:
        par = next((p for p in packet.paragraphs if p.id == a.line.par_id), None)
        short_block = par is not None and all((ln.words or len(ln.text.split())) <= 7 for ln in par.lines)
        if short_block:
            score -= 0.05
            notes.append(f"inside a {a.line.par_size}-line block of short lines")
        else:
            score -= 0.30
            notes.append(f"embedded in a {a.line.par_size}-line paragraph")
    elif a.line.par_size == b.line.par_size == c.line.par_size == 1:
        score += 0.10
        notes.append("three consecutive single-line paragraphs")
    else:
        score -= 0.25
        notes.append("crosses a paragraph boundary")

    page_w = packet.page_text_width(a.line.page)
    if page_w and all(x.line.bbox for x in cands):
        ratios = [(x.line.bbox[2] - x.line.bbox[0]) / page_w for x in cands]
        if max(ratios) < 0.65:
            score += 0.15
            notes.append(f"narrow lines (max {max(ratios):.0%} of page text width)")
        elif max(ratios) > 0.9:
            score -= 0.20
            notes.append(f"full-width line ({max(ratios):.0%} of page text width) reads like wrapped prose")

    counts = [x.word_count for x in cands]
    if max(counts) >= 9:
        score -= 0.10
        notes.append("a line has 9+ words")
    elif max(counts) <= 6:
        score += 0.05

    inner_periods = sum(len(re.findall(r"[.!?]\s+[A-Z]", x.text)) for x in cands)
    if inner_periods:
        score -= min(0.2, 0.1 * inner_periods)
        notes.append("sentence breaks inside lines")

    if a.line.gap_before is not None and a.line.gap_before >= 0.9:
        score += 0.05
        notes.append("blank space before")
    after = _next_line(packet, c.line)
    if after is None or (after.gap_before is not None and after.gap_before >= 0.9):
        score += 0.05
        notes.append("blank space after" if after is not None else "end of page")

    confs = [x.line.conf for x in cands if x.line.conf is not None]
    if confs and statistics.fmean(confs) < 50:
        score -= 0.10
        notes.append(f"low OCR confidence ({statistics.fmean(confs):.0f})")
    return score, notes


def _next_line(packet: Packet, line: PacketLine) -> Optional[PacketLine]:
    lines = [ln for ln in packet.lines() if ln.page == line.page]
    for i, ln in enumerate(lines):
        if ln.id == line.id:
            return lines[i + 1] if i + 1 < len(lines) else None
    return None


def evaluate_triple(cands: Tuple[LineAnalysis, LineAnalysis, LineAnalysis], packet: Packet, opts: Options) -> Optional[Candidate]:
    if not all(a.usable for a in cands):
        return None
    devs = tuple(a.deviation(t) for a, t in zip(cands, TARGET))
    total = sum(devs)
    structure, notes = _structure(cands, packet)
    matches = max(devs) <= opts.tolerance_per_line and total <= opts.tolerance_total
    isolated = cands[0].line.par_id == cands[2].line.par_id and cands[0].line.par_size == 3

    if matches:
        score = 1.0 - 0.15 * total + structure
        if total == 0:
            form, validation = "5-7-5", "exact"
        else:
            form, validation = "5-7-5 (approximate)", f"approximate (off by {total})"
            score = min(score, 0.95)
            notes.insert(0, "syllable count off by " + ", ".join(
                f"{d:+d}".replace("+", "±") if d else "0" for d in devs))
    elif opts.include_free_form and isolated:
        mids = [a.chosen(t) for a, t in zip(cands, TARGET)]
        if 8 <= sum(mids) <= 17 and max(a.syl_hi for a in cands) <= 9 and max(a.word_count for a in cands) <= 6:
            score = min(0.55 + structure, 0.8)
            form, validation = "free-form 3-line", "not 5-7-5 (short modern form)"
            notes.insert(0, f"syllables {'-'.join(str(m) for m in mids)}")
        else:
            return None
    else:
        return None
    return Candidate(lines=cands, deviation=total, per_line_deviation=devs,  # type: ignore[arg-type]
                     score=round(max(0.0, min(1.0, score)), 3), form=form, validation=validation, notes=notes)


def find_candidates(packet: Packet, opts: Options) -> Tuple[List[Candidate], Dict[str, LineAnalysis]]:
    analyses: Dict[str, LineAnalysis] = {ln.id: analyse_line(ln, opts) for ln in packet.lines()}
    cands: List[Candidate] = []
    by_page: Dict[int, List[PacketLine]] = {}
    for ln in packet.lines():
        by_page.setdefault(ln.page, []).append(ln)
    for lines in by_page.values():
        for i in range(len(lines) - 2):
            triple = (analyses[lines[i].id], analyses[lines[i + 1].id], analyses[lines[i + 2].id])
            c = evaluate_triple(triple, packet, opts)
            if c is not None:
                cands.append(c)
    return cands, analyses


def select_non_overlapping(cands: List[Candidate], min_score: float) -> Tuple[List[Candidate], List[Candidate]]:
    accepted: List[Candidate] = []
    rejected: List[Candidate] = []
    used: set = set()
    for c in sorted(cands, key=lambda c: (-c.score, c.deviation, c.lines[0].line.n)):
        ids = set(c.ids)
        if c.score < min_score:
            c.notes.append(f"score {c.score} below threshold {min_score}")
            rejected.append(c)
        elif ids & used:
            c.notes.append("overlaps a higher-scoring candidate")
            rejected.append(c)
        else:
            used |= ids
            accepted.append(c)
    accepted.sort(key=lambda c: (c.lines[0].line.page, c.lines[0].line.n))
    return accepted, rejected


def _union_bbox(lines: Sequence[PacketLine]):
    boxes = [ln.bbox for ln in lines if ln.bbox]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def candidate_to_dict(c: Candidate, idx: int) -> Dict[str, Any]:
    lines = [a.line for a in c.lines]
    confs = [ln.conf for ln in lines if ln.conf is not None]
    confidence = "high" if c.score >= 0.85 else "medium" if c.score >= 0.65 else "low"
    return {
        "id": f"haiku_{idx}",
        "form": c.form,
        "lines": [a.text for a in c.lines],
        "syllables": [a.chosen(t) for a, t in zip(c.lines, TARGET)],
        "syllable_ranges": [[a.syl_lo, a.syl_hi] for a in c.lines],
        "deviation": c.deviation,
        "validation": c.validation,
        "explanation": [explain_line(a.text) for a in c.lines],
        "score": c.score,
        "confidence": confidence,
        "notes": c.notes,
        "source": {
            "page": lines[0].page,
            "line_ids": [ln.id for ln in lines],
            "line_numbers": [ln.n for ln in lines],
            "paragraphs": sorted({ln.par_id for ln in lines}, key=lambda p: [ln.par_id for ln in lines].index(p)),
            "bbox": _union_bbox(lines),
            "ocr_text": [ln.raw or ln.text for ln in lines],
            "ocr_confidence": round(statistics.fmean(confs), 1) if confs else None,
        },
    }


def extract_haikus(packet: Packet, opts: Optional[Options] = None) -> Dict[str, Any]:
    opts = opts or Options()
    cands, analyses = find_candidates(packet, opts)
    accepted, rejected = select_non_overlapping(cands, opts.min_score)
    result: Dict[str, Any] = {
        "schema": f"{TOOL_NAME}/haikus/1.0",
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "engine": {
            "name": "heuristic",
            "tool": f"{TOOL_NAME}/{__version__}",
            "syllables": backend_name(),
            "tolerance_per_line": opts.tolerance_per_line,
            "tolerance_total": opts.tolerance_total,
            "min_score": opts.min_score,
            "include_free_form": opts.include_free_form,
        },
        "packet": packet.path,
        "preservation": {k: v.get("text") for k, v in packet.preservation.items()
                         if k in ("xena_file", "master_file", "original_file", "input_source_uri")},
        "haikus": [candidate_to_dict(c, i + 1) for i, c in enumerate(accepted)],
        "stats": {
            "lines": len(analyses),
            "lines_usable": sum(1 for a in analyses.values() if a.usable),
            "candidates": len(cands),
            "accepted": len(accepted),
            "rejected": len(rejected),
        },
    }
    if opts.include_rejected:
        result["candidates_rejected"] = [candidate_to_dict(c, i + 1) for i, c in enumerate(rejected)]
        result["lines_excluded"] = [
            {"id": a.line.id, "text": a.line.text, "reasons": a.excluded}
            for a in analyses.values() if a.excluded
        ]
    return result


def extract_from_file(packet_path: "str | Path", opts: Optional[Options] = None) -> Dict[str, Any]:
    return extract_haikus(read_packet(packet_path), opts)


def haikus_to_xml(result: Dict[str, Any]) -> str:
    import xml.etree.ElementTree as ET

    root = ET.Element("haikus", schema=result["schema"], generated=result["generated"],
                      engine=result["engine"]["name"], packet=result.get("packet", ""))
    for h in result["haikus"]:
        he = ET.SubElement(root, "haiku", id=h["id"], form=h["form"], validation=h["validation"],
                           score=str(h["score"]), confidence=h["confidence"])
        for text, syl, expl, lid in zip(h["lines"], h["syllables"], h["explanation"], h["source"]["line_ids"]):
            le = ET.SubElement(he, "line", syllables=str(syl), source=lid, explanation=expl)
            le.text = text
        src = h["source"]
        se = ET.SubElement(he, "source", page=str(src["page"]))
        if src.get("bbox"):
            se.set("bbox", " ".join(str(v) for v in src["bbox"]))
        if src.get("ocr_confidence") is not None:
            se.set("ocr_confidence", str(src["ocr_confidence"]))
        for note in h["notes"]:
            ET.SubElement(he, "note").text = note
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def write_result(result: Dict[str, Any], path: "str | Path", fmt: str = "json") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "xml":
        path.write_text(haikus_to_xml(result), encoding="utf-8")
    else:
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
