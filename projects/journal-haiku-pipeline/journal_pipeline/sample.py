"""Synthetic journal pages, for the demo and the test-suite.

There are no real journal scans in this repository, so ``make-sample`` renders
a plausible page — a dated entry, paragraphs of prose, haikus set apart as
indented three-line stanzas, a to-do note — with Pillow's bundled font.
``messy=True`` adds paper tint, noise, blur and a slight rotation so the OCR
step has something realistic to chew on.  The planted haikus are returned so a
test can check they come out the other end.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont


@dataclass
class SamplePage:
    path: str
    haikus: List[List[str]]
    lines: List[str] = field(default_factory=list)


PAGE_1 = [
    ("date", "Tuesday, 14 March 2023"),
    ("prose", "Rain again this morning. Walked down to the harbour before work and watched the "
              "fishing boats come in. The gulls were louder than usual, and the coffee from the "
              "kiosk was terrible, as always. Still, I felt lighter than I have all week."),
    ("haiku", ["Rain on the harbour", "the gulls argue over scraps", "my coffee goes cold"]),
    ("prose", "Spent the afternoon sorting through Dad's boxes in the garage. Found the old brass "
              "compass he carried in the war, wrapped in a handkerchief. It still points north."),
    ("haiku", ["the old brass compass", "still finds north in my palm now", "father's steady hand"]),
    ("prose", "Note to self: call the plumber about the kitchen tap, and buy stamps before Friday."),
]

PAGE_2 = [
    ("date", "Wednesday, 15 March 2023"),
    ("prose", "Clear and cold. The frost was thick on the car and I scraped it with a library card "
              "because the scraper has vanished again. Ten minutes late to the meeting, nobody noticed."),
    ("haiku", ["frost on the windshield", "a library card scrapes it", "ten minutes of dawn"]),
    ("prose", "Long call with Maria in the evening about the house. We are going to list it in May. "
              "She sounded tired but certain, which is more than I can say for myself."),
    ("prose", "Page 42 of the Bashō translation tonight. The frog again."),
    ("haiku", ["a late frost, late spring", "the kettle takes its own time", "so I take mine too"]),
]

PAGES = [PAGE_1, PAGE_2]


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSerif.ttf", "DejaVuSans.ttf", "LiberationSerif-Regular.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1 bundles a TrueType font
    except TypeError:  # pragma: no cover - very old Pillow
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_page(
    spec: Sequence[Tuple[str, object]],
    path: "str | Path",
    *,
    width: int = 1700,
    height: int = 2200,
    font_size: int = 40,
    messy: bool = False,
    seed: int = 1,
) -> SamplePage:
    """Render a page spec to *path* (PNG or JPEG by extension)."""
    rnd = random.Random(seed)
    paper = (250, 247, 240) if messy else (255, 255, 255)
    img = Image.new("RGB", (width, height), paper)
    draw = ImageDraw.Draw(img)
    body = _font(font_size)
    date_font = _font(int(font_size * 1.1))
    margin = int(width * 0.09)
    indent = int(width * 0.16)
    line_h = int(font_size * 1.55)
    y = int(height * 0.06)
    ink = (30, 30, 40)
    rendered: List[str] = []
    haikus: List[List[str]] = []

    if messy:  # faint ruled lines like a notebook
        for ry in range(y - 10, height - margin, line_h):
            draw.line([(margin // 2, ry + line_h - 8), (width - margin // 2, ry + line_h - 8)],
                      fill=(214, 220, 232), width=2)

    for kind, payload in spec:
        if kind == "date":
            draw.text((margin, y), str(payload), font=date_font, fill=ink)
            rendered.append(str(payload))
            y += int(line_h * 1.6)
        elif kind == "prose":
            for ln in _wrap(draw, str(payload), body, width - 2 * margin):
                draw.text((margin, y), ln, font=body, fill=ink)
                rendered.append(ln)
                y += line_h
            y += int(line_h * 0.9)
        elif kind == "haiku":
            lines = list(payload)  # type: ignore[arg-type]
            haikus.append(lines)
            for ln in lines:
                draw.text((indent, y), ln, font=body, fill=ink)
                rendered.append(ln)
                y += line_h
            y += int(line_h * 0.9)

    if messy:
        img = img.rotate(rnd.uniform(-0.8, 0.8), resample=Image.Resampling.BICUBIC, expand=False, fillcolor=paper)
        noise = Image.effect_noise(img.size, 14).convert("L")
        noise_rgb = Image.merge("RGB", (noise, noise, noise))
        img = Image.blend(img, noise_rgb, 0.08)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        # uneven lighting: darker bottom-right corner
        shade = Image.linear_gradient("L").rotate(35, expand=False).resize(img.size)
        shade = shade.point(lambda p: 255 - p // 6)
        img = Image.composite(img, Image.new("RGB", img.size, (170, 160, 150)), shade)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"dpi": (200, 200)}
    if path.suffix.lower() in (".jpg", ".jpeg"):
        save_kwargs["quality"] = 88
    img.save(path, **save_kwargs)
    return SamplePage(path=str(path), haikus=haikus, lines=rendered)


def make_samples(out_dir: "str | Path", *, count: int = 2, messy: bool = False, ext: str = "jpg") -> List[SamplePage]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pages: List[SamplePage] = []
    for i in range(count):
        spec = PAGES[i % len(PAGES)]
        pages.append(render_page(spec, out / f"journal_page_{i + 1:02d}.{ext}", messy=messy, seed=i + 1))
    return pages
