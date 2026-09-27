"""Step 2 — OCR with Tesseract, keeping the hOCR layout output.

Backends (auto-detected, or forced with ``backend=``):

``cli``        the ``tesseract`` executable — exactly the
               ``tesseract page.png out -l eng --psm 6 hocr txt`` invocation.
``tesserocr``  the ``tesserocr`` Python binding.  Its Linux/macOS wheels bundle
               libtesseract, so it works where you cannot ``apt install``;
               you still need a ``*.traineddata`` file (see README).

Both produce identical hOCR.  Missing engine -> :class:`OcrUnavailable` with
instructions; the rest of the pipeline can still run on transcripts produced
elsewhere (``packet --transcript``).

Preprocessing
-------------
Tesseract's LSTM models were trained on clean print at ~300 dpi with dark
text on white.  Phone photos of a journal are none of that, so by default
each page is: EXIF-rotated -> greyscale -> auto-contrast -> up-scaled so the
page is at least ``min_width`` px wide -> given a white border.  Optional
local-mean binarisation (``binarize=True``) evens out lighting and suppresses
faint ruled lines / bleed-through; it is on in the ``handwriting`` profile and
off in ``print`` (Tesseract's own Otsu threshold is fine for clean scans).

The exact transform (scale factor + border) is recorded so that hOCR
coordinates can be mapped back to the preservation master.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageChops, ImageFilter, ImageOps

from . import TOOL_NAME, __version__


class OcrUnavailable(RuntimeError):
    """No usable Tesseract backend."""


class OcrError(RuntimeError):
    pass


INSTALL_HINT = """No Tesseract backend found. Options:
  * install the CLI:   sudo apt install tesseract-ocr tesseract-ocr-eng   (Debian/Ubuntu)
                       brew install tesseract                            (macOS)
                       https://github.com/UB-Mannheim/tesseract/wiki    (Windows)
  * or the wheel:      pip install tesserocr   (+ an eng.traineddata, see README "Language data")
  * or skip OCR here:  transcribe with another engine (Transkribus, Kraken, TrOCR, a cloud HTR)
                       and feed the .hocr/.xml(ALTO)/.txt in with  --transcripts DIR
"""

PROFILES: Dict[str, Dict[str, Any]] = {
    # Printed / typed pages, or the default when unsure.
    "print": dict(psm=3, oem=None, binarize=False, autocontrast=True, min_width=2000, border=24),
    # Neat handwriting.  PSM 6 = "single uniform block of text": journal pages
    # are one column, and PSM 3's layout analysis tends to shred hand-written
    # lines into stray blocks.  OEM 1 = LSTM only (the legacy engine is
    # hopeless on handwriting).  Local binarisation, bigger upscale.
    "handwriting": dict(psm=6, oem=1, binarize=True, autocontrast=True, min_width=2600, border=32),
    # Feed the image through untouched (you already preprocessed it).
    "none": dict(psm=3, oem=None, binarize=False, autocontrast=False, min_width=0, border=0),
}

_HOCR_HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
  <meta name='ocr-system' content='{system}'/>
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/>
 </head>
 <body>
"""
_HOCR_TAIL = " </body>\n</html>\n"


@dataclass
class OcrOptions:
    lang: str = "eng"
    psm: int = 3
    oem: Optional[int] = None
    dpi: Optional[int] = None
    tessdata_dir: Optional[str] = None
    user_words: Optional[str] = None
    user_patterns: Optional[str] = None
    config: Dict[str, str] = field(default_factory=dict)   # -c key=value pairs
    backend: str = "auto"                                   # auto | cli | tesserocr
    profile: str = "print"
    # preprocessing
    grayscale: bool = True
    autocontrast: bool = True
    binarize: bool = False
    binarize_offset: int = 35         # grey levels darker than the local mean that count as ink
    min_width: int = 2000
    max_scale: float = 4.0
    border: int = 24
    keep_preprocessed: bool = True

    @classmethod
    def from_profile(cls, profile: str, **overrides: Any) -> "OcrOptions":
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r}; choose from {', '.join(PROFILES)}")
        kwargs = dict(PROFILES[profile])
        kwargs["profile"] = profile
        kwargs.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**kwargs)


@dataclass
class OcrResult:
    image: str                 # image actually OCRed (preprocessed copy or the source)
    source_image: str
    hocr: str
    txt: str
    meta: str                  # sidecar json
    engine: str
    backend: str
    transform: Dict[str, Any]  # scale, border -> map hOCR coords back to source_image
    options: Dict[str, Any]


# --------------------------------------------------------------------------- #
# backend detection
# --------------------------------------------------------------------------- #
def cli_available() -> Optional[str]:
    exe = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    return exe


def tesserocr_available() -> bool:
    try:
        import tesserocr  # noqa: F401  (probe only)
    except Exception:
        return False
    return bool(tesserocr)


def detect_backend(preferred: str = "auto") -> str:
    if preferred == "cli":
        if not cli_available():
            raise OcrUnavailable("tesseract executable not found on PATH (set TESSERACT_CMD)\n" + INSTALL_HINT)
        return "cli"
    if preferred == "tesserocr":
        if not tesserocr_available():
            raise OcrUnavailable("tesserocr is not importable (pip install tesserocr)\n" + INSTALL_HINT)
        return "tesserocr"
    if cli_available():
        return "cli"
    if tesserocr_available():
        return "tesserocr"
    raise OcrUnavailable(INSTALL_HINT)


TESSDATA_CANDIDATES = (
    "~/.local/share/tessdata",
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tessdata",
    "/usr/local/share/tessdata",
    "/opt/homebrew/share/tessdata",
    "/opt/local/share/tessdata",
    "C:/Program Files/Tesseract-OCR/tessdata",
)


def resolve_tessdata(tessdata_dir: Optional[str], lang: str = "eng") -> Optional[str]:
    """Explicit dir > $TESSDATA_PREFIX > well-known locations holding <lang>.traineddata > backend default."""
    if tessdata_dir:
        return str(Path(tessdata_dir).expanduser())
    env = os.environ.get("TESSDATA_PREFIX")
    if env:
        return env
    first = lang.split("+")[0]
    for cand in TESSDATA_CANDIDATES:
        d = Path(cand).expanduser()
        if (d / f"{first}.traineddata").is_file():
            return str(d)
    return None


def engine_version(backend: str) -> str:
    try:
        if backend == "cli":
            out = subprocess.run([cli_available() or "tesseract", "--version"], capture_output=True, text=True, timeout=20)
            first = (out.stdout or out.stderr).strip().splitlines()[0]
            return first.strip()
        import tesserocr
        return "tesseract " + tesserocr.tesseract_version().split()[1]
    except Exception:
        return "tesseract"


def available_languages(backend: str, tessdata_dir: Optional[str]) -> List[str]:
    try:
        if backend == "cli":
            cmd = [cli_available() or "tesseract", "--list-langs"]
            if tessdata_dir:
                cmd += ["--tessdata-dir", tessdata_dir]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            lines = (out.stdout + out.stderr).splitlines()
            return [ln.strip() for ln in lines[1:] if ln.strip() and not ln.startswith("List of")]
        import tesserocr
        return list(tesserocr.get_languages(tessdata_dir or "")[1])
    except Exception:
        return []


# --------------------------------------------------------------------------- #
# preprocessing
# --------------------------------------------------------------------------- #
def local_threshold(gray: Image.Image, radius: int = 25, offset: int = 35) -> Image.Image:
    """Adaptive (local-mean) binarisation using only Pillow primitives.

    A pixel is ink when it is darker than the mean of its neighbourhood by
    *offset* grey levels.  Handles uneven lighting and shadows across a page;
    the default offset keeps faint ruled notebook lines and bleed-through
    (typically 15-30 levels below paper) out while pencil (60+) stays in.
    Lower it for very faint pencil, raise it for heavy show-through.
    """
    blurred = gray.filter(ImageFilter.BoxBlur(radius))
    # diff = gray - blurred + 128 (clamped)
    diff = ImageChops.subtract(gray, blurred, scale=1.0, offset=128)
    return diff.point(lambda p: 255 if p > 128 - offset else 0).convert("L")


def preprocess(img: Image.Image, opts: OcrOptions) -> tuple[Image.Image, Dict[str, Any]]:
    """Return ``(image_for_ocr, transform)``; transform maps OCR coords back to the input."""
    transform: Dict[str, Any] = {"scale": 1.0, "border": 0, "steps": []}
    img = ImageOps.exif_transpose(img) or img
    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")
    if opts.grayscale:
        img = ImageOps.grayscale(img)
        transform["steps"].append("grayscale")
    if opts.autocontrast and not opts.binarize:
        # (skipped when binarising: the local threshold is contrast-invariant, and
        # stretching first only makes faint ruled lines dark enough to survive it)
        img = ImageOps.autocontrast(img, cutoff=1)
        transform["steps"].append("autocontrast(cutoff=1)")
    if opts.min_width and img.width < opts.min_width:
        scale = min(opts.max_scale, opts.min_width / img.width)
        if scale > 1.01:
            new_size = (round(img.width * scale), round(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            transform["scale"] = round(scale, 4)
            transform["steps"].append(f"upscale x{scale:.2f} (LANCZOS)")
    if opts.binarize:
        if img.mode != "L":
            img = ImageOps.grayscale(img)
        img = local_threshold(img, offset=opts.binarize_offset)
        transform["steps"].append(f"local-mean binarisation (offset {opts.binarize_offset})")
    if opts.border:
        img = ImageOps.expand(img, border=opts.border, fill=255 if img.mode == "L" else (255, 255, 255))
        transform["border"] = opts.border
        transform["steps"].append(f"white border {opts.border}px")
    transform["ocr_image_size"] = [img.width, img.height]
    return img, transform


def map_bbox_to_source(bbox, transform: Dict[str, Any]):
    """Inverse of :func:`preprocess` for a ``(x0, y0, x1, y1)`` box."""
    if bbox is None:
        return None
    scale = float(transform.get("scale", 1.0)) or 1.0
    border = int(transform.get("border", 0))
    return tuple(max(0, round((v - border) / scale)) for v in bbox)


# --------------------------------------------------------------------------- #
# running tesseract
# --------------------------------------------------------------------------- #
def _cli_command(exe: str, image: Path, out_base: Path, opts: OcrOptions) -> List[str]:
    cmd = [exe, str(image), str(out_base), "-l", opts.lang, "--psm", str(opts.psm)]
    if opts.oem is not None:
        cmd += ["--oem", str(opts.oem)]
    if opts.dpi:
        cmd += ["--dpi", str(opts.dpi)]
    tessdata = resolve_tessdata(opts.tessdata_dir, opts.lang)
    if tessdata:
        cmd += ["--tessdata-dir", tessdata]
    if opts.user_words:
        cmd += ["--user-words", opts.user_words]
    if opts.user_patterns:
        cmd += ["--user-patterns", opts.user_patterns]
    for k, v in opts.config.items():
        cmd += ["-c", f"{k}={v}"]
    cmd += ["hocr", "txt"]
    return cmd


def _run_cli(image: Path, out_base: Path, opts: OcrOptions) -> None:
    exe = cli_available()
    assert exe
    cmd = _cli_command(exe, image, out_base, opts)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise OcrError(f"tesseract failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr.strip()}")
    hocr = out_base.with_suffix(".hocr")
    if not hocr.exists():
        raise OcrError(f"tesseract produced no hOCR at {hocr}\n{proc.stderr.strip()}")


def _run_tesserocr(image: Path, out_base: Path, opts: OcrOptions) -> None:
    import tesserocr

    kwargs: Dict[str, Any] = {"lang": opts.lang, "psm": int(opts.psm)}   # PSM/OEM are plain ints
    tessdata = resolve_tessdata(opts.tessdata_dir, opts.lang)
    if tessdata:
        kwargs["path"] = tessdata
    if opts.oem is not None:
        kwargs["oem"] = int(opts.oem)
    try:
        api = tesserocr.PyTessBaseAPI(**kwargs)
    except RuntimeError as exc:
        raise OcrUnavailable(
            f"tesserocr could not initialise language {opts.lang!r} "
            f"(tessdata={tessdata or 'default'}): {exc}\n"
            "Point --tessdata-dir / $TESSDATA_PREFIX at a directory containing eng.traineddata."
        ) from exc
    try:
        if opts.user_words:
            api.SetVariable("user_words_file", opts.user_words)
        if opts.user_patterns:
            api.SetVariable("user_patterns_file", opts.user_patterns)
        for k, v in opts.config.items():
            api.SetVariable(k, str(v))
        api.SetImageFile(str(image))
        try:
            api.SetInputName(str(image))
        except Exception:
            pass
        if opts.dpi:
            api.SetSourceResolution(int(opts.dpi))
        body = api.GetHOCRText(0)
        text = api.GetUTF8Text()
    finally:
        api.End()
    system = "tesseract " + tesserocr.tesseract_version().split()[1]
    out_base.with_suffix(".hocr").write_text(
        _HOCR_HEAD.format(system=system) + body + "\n" + _HOCR_TAIL, encoding="utf-8"
    )
    out_base.with_suffix(".txt").write_text(text, encoding="utf-8")


def ocr_image(
    image_path: "str | Path",
    out_dir: "str | Path",
    opts: Optional[OcrOptions] = None,
    *,
    stem: Optional[str] = None,
) -> OcrResult:
    """OCR one image -> ``<stem>.hocr``, ``<stem>.txt``, ``<stem>.ocr.json`` in *out_dir*."""
    opts = opts or OcrOptions()
    src = Path(image_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = stem or src.stem
    backend = detect_backend(opts.backend)

    with Image.open(src) as img:
        img.load()
        ocr_img, transform = preprocess(img, opts)

    ocr_input = out / f"{stem}.ocr-input.png"
    if transform["steps"]:
        ocr_img.save(ocr_input, format="PNG", compress_level=3)
        image_for_ocr = ocr_input
    else:
        image_for_ocr = src
        if ocr_input.exists():
            ocr_input.unlink()

    out_base = out / stem
    if backend == "cli":
        _run_cli(image_for_ocr, out_base, opts)
    else:
        _run_tesserocr(image_for_ocr, out_base, opts)

    hocr = out_base.with_suffix(".hocr")
    txt = out_base.with_suffix(".txt")
    if not txt.exists():
        txt.write_text("", encoding="utf-8")
    engine = engine_version(backend)
    meta_path = out / f"{stem}.ocr.json"
    meta = {
        "schema": f"{TOOL_NAME}/ocr/1.0",
        "tool": {"name": TOOL_NAME, "version": __version__},
        "engine": engine,
        "backend": backend,
        "source_image": str(src.resolve()),
        "ocr_image": str(image_for_ocr.resolve()),
        "hocr": str(hocr.resolve()),
        "txt": str(txt.resolve()),
        "options": {k: v for k, v in asdict(opts).items() if k != "keep_preprocessed"},
        "transform": transform,
        "coordinate_space": "ocr_image",
    }
    if backend == "cli":
        meta["command"] = _cli_command(cli_available() or "tesseract", image_for_ocr, out_base, opts)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if not opts.keep_preprocessed and image_for_ocr == ocr_input:
        ocr_input.unlink()
        meta["ocr_image"] = None

    return OcrResult(
        image=str(image_for_ocr), source_image=str(src), hocr=str(hocr), txt=str(txt), meta=str(meta_path),
        engine=engine, backend=backend, transform=transform, options=meta["options"],
    )


def load_ocr_meta(path: "str | Path") -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
