"""Transcript readers: hOCR (Tesseract), ALTO XML, and plain text.

All three produce the same :class:`Document` -> :class:`Page` -> :class:`Block`
-> :class:`Paragraph` -> :class:`Line` -> :class:`Word` tree, so the packet
builder and the haiku detector never care which OCR/HTR engine was used.

The hOCR reader is built on :mod:`html.parser` rather than an XML parser on
purpose: Tesseract emits XHTML with a DOCTYPE, other engines emit HTML5, and
some hand-edited files are not well-formed.  Matching on ``class`` names
(``ocr_page``, ``ocr_carea``, ``ocr_par``, ``ocr_line``, ``ocrx_word`` ...)
works for all of them and needs no namespace handling.
"""

from __future__ import annotations

import re
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

BBox = Tuple[int, int, int, int]


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Word:
    id: str
    text: str
    bbox: Optional[BBox] = None
    conf: Optional[float] = None


@dataclass
class Line:
    id: str
    text: str = ""
    bbox: Optional[BBox] = None
    words: List[Word] = field(default_factory=list)
    kind: str = "ocr_line"           # ocr_line | ocr_textfloat | ocr_header | ocr_caption | text
    # filled in by Document.finalise()
    n: int = 0                       # 1-based running number on the page
    page_no: int = 1
    block_id: str = ""
    par_id: str = ""
    par_size: int = 1                # number of lines in the enclosing paragraph
    par_index: int = 0               # 0-based position inside the paragraph
    gap_before: Optional[float] = None   # vertical gap to previous line / median line height

    @property
    def conf(self) -> Optional[float]:
        confs = [w.conf for w in self.words if w.conf is not None]
        return round(statistics.fmean(confs), 1) if confs else None

    @property
    def height(self) -> Optional[int]:
        return (self.bbox[3] - self.bbox[1]) if self.bbox else None

    @property
    def width(self) -> Optional[int]:
        return (self.bbox[2] - self.bbox[0]) if self.bbox else None


@dataclass
class Paragraph:
    id: str
    bbox: Optional[BBox] = None
    lines: List[Line] = field(default_factory=list)


@dataclass
class Block:
    id: str
    bbox: Optional[BBox] = None
    paragraphs: List[Paragraph] = field(default_factory=list)


@dataclass
class Page:
    no: int
    bbox: Optional[BBox] = None
    image: Optional[str] = None
    blocks: List[Block] = field(default_factory=list)

    def lines(self) -> List[Line]:
        return [ln for b in self.blocks for p in b.paragraphs for ln in p.lines]

    def paragraphs(self) -> List[Paragraph]:
        return [p for b in self.blocks for p in b.paragraphs]

    @property
    def width(self) -> Optional[int]:
        return (self.bbox[2] - self.bbox[0]) if self.bbox else None

    @property
    def height(self) -> Optional[int]:
        return (self.bbox[3] - self.bbox[1]) if self.bbox else None


@dataclass
class Document:
    pages: List[Page] = field(default_factory=list)
    source_format: str = "hocr"
    engine: Optional[str] = None
    source_path: Optional[str] = None

    def lines(self) -> List[Line]:
        return [ln for p in self.pages for ln in p.lines()]

    def text(self) -> str:
        """Plain-text rendering: one line per OCR line, blank line between paragraphs."""
        out: List[str] = []
        for page in self.pages:
            for par in page.paragraphs():
                for ln in par.lines:
                    out.append(ln.text)
                out.append("")
            out.append("\f")
        return "\n".join(out).rstrip("\f\n") + "\n"

    def mean_confidence(self) -> Optional[float]:
        confs = [w.conf for ln in self.lines() for w in ln.words if w.conf is not None]
        return round(statistics.fmean(confs), 1) if confs else None

    def finalise(self) -> "Document":
        """Drop empty lines/paragraphs, number lines, compute paragraph context and gaps."""
        for page in self.pages:
            for block in page.blocks:
                for par in block.paragraphs:
                    for ln in par.lines:
                        if ln.words and not ln.text:
                            ln.text = " ".join(w.text for w in ln.words if w.text)
                        ln.text = _clean_text(ln.text)
                    par.lines = [ln for ln in par.lines if ln.text]
                block.paragraphs = [p for p in block.paragraphs if p.lines]
            page.blocks = [b for b in page.blocks if b.paragraphs]

            lines = page.lines()
            heights = [ln.height for ln in lines if ln.height]
            median_h = statistics.median(heights) if heights else None
            prev: Optional[Line] = None
            n = 0
            for block in page.blocks:
                for par in block.paragraphs:
                    for idx, ln in enumerate(par.lines):
                        n += 1
                        ln.n = n
                        ln.page_no = page.no
                        ln.block_id = block.id
                        ln.par_id = par.id
                        ln.par_size = len(par.lines)
                        ln.par_index = idx
                        if prev is not None and prev.bbox and ln.bbox and median_h:
                            ln.gap_before = round((ln.bbox[1] - prev.bbox[3]) / median_h, 2)
                        prev = ln
        return self


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean_text(text: str) -> str:
    text = _CONTROL_RE.sub("", text or "")
    return re.sub(r"[ \t]+", " ", text).strip()


_ALNUM_RE = re.compile(r"[^\W_]", re.U)
_SHORT_REAL_WORDS = {"a", "i", "o", "an", "of", "in", "on", "to", "is", "it", "at", "be", "by", "do", "go",
                     "he", "me", "my", "no", "or", "so", "up", "us", "we", "if", "as", "am", "ok", "oh", "ah"}


def is_junk_word(word: Word, edge: bool = True) -> bool:
    """Ruled lines, margins and specks come out of Tesseract as low-confidence
    tokens like ``~~``, ``©``, ``-``, ``EE`` or ``0`` at the ends of a line."""
    text = word.text.strip()
    if not text:
        return True
    conf = word.conf if word.conf is not None else 100.0
    if not _ALNUM_RE.search(text):      # punctuation-only token at a line edge carries no text
        return True
    if edge and conf < 30 and len(text) <= 2 and text.lower() not in _SHORT_REAL_WORDS:
        return True
    return False


def clean_line_words(line: Line) -> Tuple[str, List[str]]:
    """Return ``(clean_text, dropped_tokens)`` with junk trimmed from both ends of the line."""
    if not line.words:
        return line.text, []
    words = list(line.words)
    dropped: List[str] = []
    while words and is_junk_word(words[0]):
        dropped.append(words.pop(0).text)
    while words and is_junk_word(words[-1]):
        dropped.append(words.pop().text)
    if not words:                               # the whole line was junk; keep it as-is, caller decides
        return line.text, []
    return _clean_text(" ".join(w.text for w in words)), dropped


# --------------------------------------------------------------------------- #
# hOCR
# --------------------------------------------------------------------------- #
_OCR_CLASSES = {
    "ocr_page", "ocr_carea", "ocr_par", "ocr_line", "ocr_textfloat", "ocr_header",
    "ocr_caption", "ocrx_word", "ocrx_block", "ocr_column",
}
_LINE_CLASSES = {"ocr_line", "ocr_textfloat", "ocr_header", "ocr_caption"}
_VOID_TAGS = {"br", "meta", "img", "link", "hr", "input", "base", "area", "col", "wbr"}


def parse_title(title: str) -> Dict[str, List[str]]:
    """``'bbox 1 2 3 4; x_wconf 91'`` -> ``{'bbox': ['1','2','3','4'], 'x_wconf': ['91']}``."""
    props: Dict[str, List[str]] = {}
    for part in (title or "").split(";"):
        toks = part.strip().split()
        if toks:
            props[toks[0]] = toks[1:]
    return props


def _bbox_from(props: Dict[str, List[str]]) -> Optional[BBox]:
    vals = props.get("bbox")
    if vals and len(vals) >= 4:
        try:
            x0, y0, x1, y1 = (int(float(v)) for v in vals[:4])
            return (x0, y0, x1, y1)
        except ValueError:
            return None
    return None


class _HocrParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.doc = Document(source_format="hocr")
        self._stack: List[Optional[Tuple[str, object]]] = []
        self._page: Optional[Page] = None
        self._block: Optional[Block] = None
        self._par: Optional[Paragraph] = None
        self._line: Optional[Line] = None
        self._word: Optional[Word] = None
        self._counter = 0

    def _auto_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"

    # -- element lifecycle --------------------------------------------------
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "meta" and a.get("name") == "ocr-system":
            self.doc.engine = a.get("content") or None
        if tag in _VOID_TAGS:
            return
        classes = set(a.get("class", "").split())
        cls = next((c for c in classes if c in _OCR_CLASSES), None)
        props = parse_title(a.get("title", ""))
        bbox = _bbox_from(props)
        node: object = None
        if cls == "ocr_page":
            no = len(self.doc.pages) + 1
            image = None
            if props.get("image"):
                image = " ".join(props["image"]).strip('"')
            self._page = Page(no=no, bbox=bbox, image=image)
            self.doc.pages.append(self._page)
            node = self._page
        elif cls in ("ocr_carea", "ocrx_block", "ocr_column"):
            self._ensure_page()
            self._block = Block(id=a.get("id") or self._auto_id("block"), bbox=bbox)
            self._page.blocks.append(self._block)  # type: ignore[union-attr]
            node = self._block
        elif cls == "ocr_par":
            self._ensure_block()
            self._par = Paragraph(id=a.get("id") or self._auto_id("par"), bbox=bbox)
            self._block.paragraphs.append(self._par)  # type: ignore[union-attr]
            node = self._par
        elif cls in _LINE_CLASSES:
            self._ensure_par()
            self._line = Line(id=a.get("id") or self._auto_id("line"), bbox=bbox, kind=cls)
            self._par.lines.append(self._line)  # type: ignore[union-attr]
            node = self._line
        elif cls == "ocrx_word":
            if self._line is None:
                self._ensure_par()
                self._line = Line(id=self._auto_id("line"))
                self._par.lines.append(self._line)  # type: ignore[union-attr]
            conf = None
            if props.get("x_wconf"):
                try:
                    conf = float(props["x_wconf"][0])
                except ValueError:
                    conf = None
            self._word = Word(id=a.get("id") or self._auto_id("word"), text="", bbox=bbox, conf=conf)
            self._line.words.append(self._word)
            node = self._word
        self._stack.append((tag, node))

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_TAGS:
            return
        # pop to the matching open tag (tolerates sloppy nesting)
        while self._stack:
            open_tag, node = self._stack.pop()
            if node is self._word:
                self._word = None
            elif node is self._line and node is not None:
                self._line = None
            elif node is self._par and node is not None:
                self._par = None
                self._line = None
            elif node is self._block and node is not None:
                self._block = None
                self._par = None
                self._line = None
            elif node is self._page and node is not None:
                self._page = None
                self._block = self._par = self._line = None
            if open_tag == tag:
                break

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._word is not None:
            self._word.text += data
        elif self._line is not None and data.strip():
            # text directly inside a line (engines that do not emit ocrx_word)
            self._line.text = (self._line.text + " " + data.strip()).strip()

    # -- structure guards ---------------------------------------------------
    def _ensure_page(self) -> None:
        if self._page is None:
            self._page = Page(no=len(self.doc.pages) + 1)
            self.doc.pages.append(self._page)

    def _ensure_block(self) -> None:
        self._ensure_page()
        if self._block is None:
            self._block = Block(id=self._auto_id("block"))
            self._page.blocks.append(self._block)  # type: ignore[union-attr]

    def _ensure_par(self) -> None:
        self._ensure_block()
        if self._par is None:
            self._par = Paragraph(id=self._auto_id("par"))
            self._block.paragraphs.append(self._par)  # type: ignore[union-attr]


def parse_hocr(text: str) -> Document:
    parser = _HocrParser()
    parser.feed(text)
    parser.close()
    doc = parser.doc
    for w in (w for ln in doc.lines() for w in ln.words):
        w.text = _clean_text(w.text)
    return doc.finalise()


# --------------------------------------------------------------------------- #
# ALTO XML (Transkribus, Kraken, ABBYY, eScriptorium exports)
# --------------------------------------------------------------------------- #
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _alto_bbox(el: ET.Element) -> Optional[BBox]:
    try:
        x = int(float(el.get("HPOS", "")))
        y = int(float(el.get("VPOS", "")))
        w = int(float(el.get("WIDTH", "")))
        h = int(float(el.get("HEIGHT", "")))
        return (x, y, x + w, y + h)
    except ValueError:
        return None


def parse_alto(text: str) -> Document:
    root = ET.fromstring(text)
    doc = Document(source_format="alto")
    for desc in root.iter():
        if _local(desc.tag) == "softwareName" and desc.text:
            doc.engine = desc.text.strip()
            break
    counter = 0
    for page_el in (e for e in root.iter() if _local(e.tag) == "Page"):
        page = Page(no=len(doc.pages) + 1)
        try:
            page.bbox = (0, 0, int(float(page_el.get("WIDTH", "0"))), int(float(page_el.get("HEIGHT", "0"))))
            if page.bbox[2] == 0:
                page.bbox = None
        except ValueError:
            page.bbox = None
        doc.pages.append(page)
        for tb in (e for e in page_el.iter() if _local(e.tag) == "TextBlock"):
            counter += 1
            block = Block(id=tb.get("ID") or f"block_{counter}", bbox=_alto_bbox(tb))
            par = Paragraph(id=(tb.get("ID") or f"block_{counter}") + "_par", bbox=block.bbox)
            block.paragraphs.append(par)
            page.blocks.append(block)
            for tl in (e for e in tb.iter() if _local(e.tag) == "TextLine"):
                counter += 1
                line = Line(id=tl.get("ID") or f"line_{counter}", bbox=_alto_bbox(tl))
                for s in (e for e in tl.iter() if _local(e.tag) == "String"):
                    counter += 1
                    conf = None
                    if s.get("WC"):
                        try:
                            conf = round(float(s.get("WC", "")) * 100, 1)
                        except ValueError:
                            conf = None
                    line.words.append(Word(id=s.get("ID") or f"word_{counter}",
                                           text=s.get("CONTENT", ""), bbox=_alto_bbox(s), conf=conf))
                par.lines.append(line)
    return doc.finalise()


# --------------------------------------------------------------------------- #
# Plain text (manual transcription, or another engine's .txt output)
# --------------------------------------------------------------------------- #
def parse_text(text: str) -> Document:
    doc = Document(source_format="text")
    page_no = 0
    for page_text in text.replace("\r\n", "\n").split("\f"):
        if not page_text.strip():
            continue
        page_no += 1
        page = Page(no=page_no)
        block = Block(id=f"block_{page_no}")
        page.blocks.append(block)
        doc.pages.append(page)
        par_no = 0
        line_no = 0
        current: Optional[Paragraph] = None
        for raw in page_text.split("\n"):
            if not raw.strip():
                current = None
                continue
            if current is None:
                par_no += 1
                current = Paragraph(id=f"par_{page_no}_{par_no}")
                block.paragraphs.append(current)
            line_no += 1
            current.lines.append(Line(id=f"line_{page_no}_{line_no}", text=raw.strip(), kind="text"))
    return doc.finalise()


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
def sniff_format(path: Path, head: str) -> str:
    suffix = path.suffix.lower()
    lowered = head.lower()
    if suffix in (".hocr", ".html", ".htm", ".xhtml") or "ocr_page" in lowered or "ocrx_word" in lowered:
        return "hocr"
    if suffix == ".xml" or lowered.lstrip().startswith("<?xml"):
        if "<alto" in lowered or "alto" in lowered[:600]:
            return "alto"
        if "pcgts" in lowered:
            raise ValueError(f"{path}: PAGE XML is not supported; export ALTO or hOCR instead")
        if "ocr_page" in lowered:
            return "hocr"
        return "alto"
    return "text"


def load_transcript(path: "str | Path") -> Document:
    """Read an hOCR / ALTO / plain-text transcript into a :class:`Document`."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    fmt = sniff_format(p, text[:4000])
    if fmt == "hocr":
        doc = parse_hocr(text)
    elif fmt == "alto":
        doc = parse_alto(text)
    else:
        doc = parse_text(text)
    doc.source_path = str(p)
    return doc


def iter_paragraph_lines(doc: Document) -> Iterator[Tuple[Page, Paragraph, Sequence[Line]]]:
    for page in doc.pages:
        for par in page.paragraphs():
            yield page, par, par.lines
