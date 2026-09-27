"""Step 3 — one clean XML packet per page: preservation metadata + transcript.

Layout (attributes omitted when unknown, e.g. plain-text transcripts have no
boxes or confidences)::

    <pipeline_packet version="1.0" generated="2026-09-20T13:00:00Z" tool="journal-haiku-pipeline/1.0.0">
      <preservation_source>
        <xena_file sha256="…">/abs/IMG_0001.xena</xena_file>
        <master_file format="image/png" sha256="…" width="3024" height="4032">/abs/IMG_0001.png</master_file>
        <original_file format="image/jpeg" sha256="…">/abs/IMG_0001.jpg</original_file>
        <input_source_uri>file:///abs/IMG_0001.jpg</input_source_uri>
        <captured>2023:03:14 08:12:44</captured>          <!-- EXIF DateTimeOriginal, if any -->
      </preservation_source>
      <ocr engine="tesseract 5.5.1" backend="cli" lang="eng" psm="6" transcript_file="…/IMG_0001.hocr"
           transcript_format="hocr" mean_word_confidence="87.2" coordinate_space="master">
        <preprocessing scale="1.3" border="24">grayscale; autocontrast(cutoff=1); …</preprocessing>
      </ocr>
      <ocr_transcript pages="1" lines="17">
        <page n="1" width="3024" height="4032">
          <paragraph id="par_1_1" block="block_1_1" bbox="…">
            <line id="line_1_1" n="1" bbox="…" conf="92.1" words="4" gap_before="0.4">Tuesday, 14 March 2023</line>
            <line id="line_1_2" n="2" … raw="~~ frost on the windshield 0 ST">frost on the windshield</line>
            …

Every ``<line>`` is a single OCR line with its text as element content, so an
LLM sees the layout (paragraph breaks are what separate a haiku from the prose
around it) without any hOCR/HTML noise, and can cite ``line`` ids back.
Coordinates are converted from the OCR working image back to the preservation
master when the ``.ocr.json`` sidecar is supplied.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import TOOL_NAME, __version__
from .hocr import Document, clean_line_words, load_transcript
from .ocr import map_bbox_to_source

PACKET_VERSION = "1.0"

_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def xml_safe(text: Optional[str]) -> str:
    """Strip characters that are illegal in XML 1.0 (OCR output loves \\f)."""
    return _XML_ILLEGAL.sub("", text or "")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _bbox_str(bbox) -> Optional[str]:
    return " ".join(str(int(v)) for v in bbox) if bbox else None


def _set(el: ET.Element, key: str, value: Any) -> None:
    if value is None or value == "":
        return
    el.set(key, xml_safe(str(value)))


# --------------------------------------------------------------------------- #
# building
# --------------------------------------------------------------------------- #
def build_packet(
    doc: Document,
    *,
    provenance: Optional[Dict[str, Any]] = None,
    ocr_meta: Optional[Dict[str, Any]] = None,
    xena_path: Optional[str] = None,
    transcript_path: Optional[str] = None,
    clean_edges: bool = True,
) -> ET.Element:
    """Build the packet tree.  With *clean_edges* (default) low-confidence junk
    tokens at the ends of a line (ruled-line and margin artefacts) are trimmed
    from the line text and the untouched OCR text is kept in ``raw``."""
    root = ET.Element("pipeline_packet", version=PACKET_VERSION, generated=_utc_now(),
                      tool=f"{TOOL_NAME}/{__version__}")

    # -- preservation_source ------------------------------------------------
    ps = ET.SubElement(root, "preservation_source")
    prov = provenance or {}
    xena = prov.get("xena", {})
    master = prov.get("master", {})
    source = prov.get("source", {})
    xf = ET.SubElement(ps, "xena_file")
    xf.text = xml_safe(xena_path or xena.get("path") or "")
    _set(xf, "sha256", xena.get("sha256"))
    _set(xf, "wrapper", xena.get("wrapper"))
    _set(xf, "payload_element", xena.get("payload_element"))
    if master:
        mf = ET.SubElement(ps, "master_file")
        mf.text = xml_safe(master.get("path"))
        _set(mf, "format", master.get("mime"))
        _set(mf, "sha256", master.get("sha256"))
        _set(mf, "width", master.get("width"))
        _set(mf, "height", master.get("height"))
    if source:
        of = ET.SubElement(ps, "original_file")
        of.text = xml_safe(source.get("path"))
        _set(of, "format", source.get("mime"))
        _set(of, "sha256", source.get("sha256"))
        _set(of, "last_modified", source.get("last_modified"))
        uri = ET.SubElement(ps, "input_source_uri")
        uri.text = xml_safe(source.get("uri"))
    exif = prov.get("exif") or {}
    captured = (exif.get("Exif") or {}).get("DateTimeOriginal") or exif.get("DateTime")
    if captured:
        ET.SubElement(ps, "captured").text = xml_safe(str(captured))
    camera = " ".join(str(exif.get(k)) for k in ("Make", "Model") if exif.get(k))
    if camera:
        ET.SubElement(ps, "camera").text = xml_safe(camera)

    # -- ocr ----------------------------------------------------------------
    ocr = ET.SubElement(root, "ocr")
    meta = ocr_meta or {}
    opts = meta.get("options") or {}
    transform = meta.get("transform") or {}
    _set(ocr, "engine", meta.get("engine") or doc.engine)
    _set(ocr, "backend", meta.get("backend"))
    _set(ocr, "lang", opts.get("lang"))
    _set(ocr, "psm", opts.get("psm"))
    _set(ocr, "oem", opts.get("oem"))
    _set(ocr, "profile", opts.get("profile"))
    _set(ocr, "transcript_file", transcript_path or doc.source_path)
    _set(ocr, "transcript_format", doc.source_format)
    _set(ocr, "mean_word_confidence", doc.mean_confidence())
    has_transform = bool(transform) and (transform.get("scale", 1.0) != 1.0 or transform.get("border", 0))
    coordinate_space = "master" if (has_transform or meta) else ("ocr_image" if doc.source_format != "text" else None)
    _set(ocr, "coordinate_space", coordinate_space)
    if transform:
        pre = ET.SubElement(ocr, "preprocessing")
        _set(pre, "scale", transform.get("scale"))
        _set(pre, "border", transform.get("border"))
        pre.text = xml_safe("; ".join(transform.get("steps") or []) or "none")

    # -- transcript ---------------------------------------------------------
    tr = ET.SubElement(root, "ocr_transcript")
    total_lines = 0
    for page in doc.pages:
        pg = ET.SubElement(tr, "page", n=str(page.no))
        if master.get("width") and master.get("height") and len(doc.pages) == 1:
            _set(pg, "width", master["width"])          # coordinates are in master space
            _set(pg, "height", master["height"])
        elif page.bbox:
            pb = map_bbox_to_source(page.bbox, transform) if has_transform else page.bbox
            if has_transform:                            # the border was mapped in on both sides
                border = int(transform.get("border", 0)) / (float(transform.get("scale", 1.0)) or 1.0)
                pb = (pb[0], pb[1], round(pb[2] - border), round(pb[3] - border))
            _set(pg, "width", pb[2] - pb[0])
            _set(pg, "height", pb[3] - pb[1])
        if page.image and page.image != "unknown":
            _set(pg, "image", page.image)
        for par in page.paragraphs():
            pe = ET.SubElement(pg, "paragraph", id=par.id)
            _set(pe, "block", par.lines[0].block_id if par.lines else None)
            _set(pe, "bbox", _bbox_str(map_bbox_to_source(par.bbox, transform) if has_transform else par.bbox))
            for ln in par.lines:
                total_lines += 1
                le = ET.SubElement(pe, "line", id=ln.id, n=str(ln.n))
                _set(le, "bbox", _bbox_str(map_bbox_to_source(ln.bbox, transform) if has_transform else ln.bbox))
                _set(le, "conf", ln.conf)
                _set(le, "words", len(ln.words) if ln.words else None)
                _set(le, "gap_before", ln.gap_before)
                if ln.kind not in ("ocr_line", "text"):
                    _set(le, "kind", ln.kind)
                text = ln.text
                if clean_edges:
                    text, dropped = clean_line_words(ln)
                    if dropped:
                        _set(le, "raw", ln.text)
                le.text = xml_safe(text)
    tr.set("pages", str(len(doc.pages)))
    tr.set("lines", str(total_lines))
    return root


def write_packet(root: ET.Element, path: "str | Path") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n", encoding="utf-8")
    return path


def build_packet_files(
    transcript: "str | Path",
    out_path: "str | Path",
    *,
    provenance_path: Optional["str | Path"] = None,
    ocr_meta_path: Optional["str | Path"] = None,
    xena_path: Optional["str | Path"] = None,
) -> Path:
    doc = load_transcript(transcript)
    prov = json.loads(Path(provenance_path).read_text(encoding="utf-8")) if provenance_path else None
    meta = json.loads(Path(ocr_meta_path).read_text(encoding="utf-8")) if ocr_meta_path else None
    root = build_packet(doc, provenance=prov, ocr_meta=meta,
                        xena_path=str(xena_path) if xena_path else None, transcript_path=str(transcript))
    return write_packet(root, out_path)


# --------------------------------------------------------------------------- #
# reading (for the extraction step and the LLM prompt)
# --------------------------------------------------------------------------- #
@dataclass
class PacketLine:
    id: str
    n: int
    text: str
    page: int
    par_id: str
    par_size: int
    par_index: int
    bbox: Optional[tuple] = None
    conf: Optional[float] = None
    words: Optional[int] = None
    gap_before: Optional[float] = None
    kind: Optional[str] = None
    raw: Optional[str] = None       # untrimmed OCR text when edge junk was removed


@dataclass
class PacketParagraph:
    id: str
    page: int
    lines: List[PacketLine] = field(default_factory=list)
    bbox: Optional[tuple] = None


@dataclass
class Packet:
    path: str
    paragraphs: List[PacketParagraph]
    pages: Dict[int, Dict[str, Any]]
    preservation: Dict[str, Any]
    ocr: Dict[str, Any]
    xml_text: str

    def lines(self) -> List[PacketLine]:
        return [ln for p in self.paragraphs for ln in p.lines]

    def line_by_id(self) -> Dict[str, PacketLine]:
        return {ln.id: ln for ln in self.lines()}

    def page_text_width(self, page: int) -> Optional[int]:
        widths = [ln.bbox[2] - ln.bbox[0] for ln in self.lines() if ln.page == page and ln.bbox]
        if not widths:
            return None
        widths.sort()
        return widths[int(len(widths) * 0.9)] if len(widths) > 4 else widths[-1]


def _parse_bbox(val: Optional[str]):
    if not val:
        return None
    try:
        parts = tuple(int(v) for v in val.split())
        return parts if len(parts) == 4 else None
    except ValueError:
        return None


def read_packet(path: "str | Path") -> Packet:
    p = Path(path)
    xml_text = p.read_text(encoding="utf-8")
    root = ET.fromstring(xml_text)
    preservation: Dict[str, Any] = {}
    ps = root.find("preservation_source")
    if ps is not None:
        for child in ps:
            preservation[child.tag] = {"text": (child.text or "").strip(), **child.attrib}
    ocr_el = root.find("ocr")
    ocr = dict(ocr_el.attrib) if ocr_el is not None else {}
    if ocr_el is not None and ocr_el.find("preprocessing") is not None:
        ocr["preprocessing"] = (ocr_el.find("preprocessing").text or "").strip()

    paragraphs: List[PacketParagraph] = []
    pages: Dict[int, Dict[str, Any]] = {}
    for pg in root.iter("page"):
        page_no = int(pg.get("n", "1"))
        pages[page_no] = dict(pg.attrib)
        for pe in pg.iter("paragraph"):
            par = PacketParagraph(id=pe.get("id", ""), page=page_no, bbox=_parse_bbox(pe.get("bbox")))
            line_els = list(pe.iter("line"))
            for idx, le in enumerate(line_els):
                par.lines.append(PacketLine(
                    id=le.get("id", ""), n=int(le.get("n", "0") or 0), text=(le.text or "").strip(),
                    page=page_no, par_id=par.id, par_size=len(line_els), par_index=idx,
                    bbox=_parse_bbox(le.get("bbox")),
                    conf=float(le.get("conf")) if le.get("conf") else None,
                    words=int(le.get("words")) if le.get("words") else None,
                    gap_before=float(le.get("gap_before")) if le.get("gap_before") else None,
                    kind=le.get("kind"),
                    raw=le.get("raw"),
                ))
            if par.lines:
                paragraphs.append(par)
    return Packet(path=str(p), paragraphs=paragraphs, pages=pages, preservation=preservation, ocr=ocr, xml_text=xml_text)


def packet_plain_text(packet: Packet, *, with_ids: bool = True) -> str:
    """Compact text view (one line per OCR line, blank line between paragraphs)."""
    out: List[str] = []
    for par in packet.paragraphs:
        for ln in par.lines:
            out.append(f"[{ln.id}] {ln.text}" if with_ids else ln.text)
        out.append("")
    return "\n".join(out).rstrip() + "\n"
