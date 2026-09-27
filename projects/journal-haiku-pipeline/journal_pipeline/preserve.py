"""Step 1 — normalise an image to a lossless master and wrap it in a Xena envelope.

What Xena actually produces
---------------------------
Xena (XML Electronic Normalising of Archives, National Archives of Australia)
normalises raster images to **PNG** and writes a ``.xena`` file that is plain
XML in the "Default Package Wrapper" layout documented at
https://sourceforge.net/p/xena/wiki/Default_package_wrapper/ ::

    <xena>
      <meta_data>
        <meta_data_wrapper_name>Default Package Wrapper</meta_data_wrapper_name>
        <normaliser_name>...</normaliser_name>
        <input_source_uri>file:/...</input_source_uri>
      </meta_data>
      <content>
        <png:png xmlns:png="http://preservation.naa.gov.au/png/1.0"
                 png:description="The following data represents a Base64 encoding of a PNG image file ( ISO Standard 15948 )."
                 png:extension="png">
          ...base64, 76 columns...
        </png:png>
      </content>
    </xena>

This module reproduces that layout byte-for-byte in structure, so the output
can be opened by the Xena viewer / unwrapped by any Xena-aware tool.

TIFF option
-----------
Many preservation policies (FADGI, LoC) ask for uncompressed baseline TIFF.
``master_format="tiff"`` writes exactly that, and because Xena publishes no
TIFF schema the payload is wrapped with Xena's generic ``binary-object``
schema (http://preservation.naa.gov.au/binary-object/1.0), which is what Xena
itself uses for formats it has no dedicated normaliser for.

Fixity
------
The ``meta_data`` block of the default wrapper is a fixed three-element
sequence, so checksums, EXIF, colour-profile and tool information go into a
sidecar ``<stem>.provenance.json`` — and are echoed into the AI packet later.
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from xml.sax.saxutils import escape, quoteattr

import PIL
from PIL import ExifTags, Image, ImageChops, ImageOps

from . import TOOL_NAME, __version__

XENA_NS = "http://preservation.naa.gov.au/xena/1.0"
PNG_NS = "http://preservation.naa.gov.au/png/1.0"
BINARY_NS = "http://preservation.naa.gov.au/binary-object/1.0"
WRAPPER_NAME = "Default Package Wrapper"

PNG_DESCRIPTION = "The following data represents a Base64 encoding of a PNG image file ( ISO Standard 15948 )."
TIFF_DESCRIPTION = (
    "The following data represents a Base64 encoding of an uncompressed baseline TIFF 6.0 image file "
    "(normalised preservation master; Xena publishes no TIFF schema, so the generic binary-object "
    "schema is used)."
)

MASTER_FORMATS = ("png", "tiff")

_PNG_MODE_MAP = {
    "CMYK": "RGB", "YCbCr": "RGB", "LAB": "RGB", "HSV": "RGB",
    "I;16B": "I;16", "I;16L": "I;16", "I;16N": "I;16", "F": "I;16", "PA": "RGBA",
}
_TIFF_MODE_MAP = {
    "YCbCr": "RGB", "LAB": "RGB", "HSV": "RGB", "I;16B": "I;16", "I;16L": "I;16", "I;16N": "I;16",
}


class PreservationError(RuntimeError):
    pass


@dataclass
class PreservationResult:
    source: str
    master: str
    xena: str
    provenance: str
    master_format: str
    sha256_source: str
    sha256_master: str
    width: int
    height: int
    mode: str
    orientation_applied: Optional[int] = None
    warnings: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: "str | Path", chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0) \
        .isoformat().replace("+00:00", "Z")


def _jsonable(value: Any, limit: int = 4096) -> Any:
    if isinstance(value, bytes):
        if len(value) > limit:
            return f"<{len(value)} bytes>"
        try:
            return value.decode("ascii").rstrip("\x00")
        except UnicodeDecodeError:
            return "base64:" + base64.b64encode(value).decode("ascii")
    if isinstance(value, (list, tuple)):
        return [_jsonable(v, limit) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v, limit) for k, v in value.items()}
    if hasattr(value, "numerator") and hasattr(value, "denominator") and not isinstance(value, int):
        try:
            return float(value)
        except (TypeError, ValueError, ZeroDivisionError):
            return str(value)
    if isinstance(value, str):
        return value.rstrip("\x00")
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


def extract_exif(img: Image.Image) -> Dict[str, Any]:
    """Flatten IFD0 + Exif IFD + GPS IFD into a name -> value dict (all JSON-safe)."""
    out: Dict[str, Any] = {}
    try:
        exif = img.getexif()
    except Exception:  # pragma: no cover - corrupt EXIF
        return out
    for tag_id, value in exif.items():
        out[ExifTags.TAGS.get(tag_id, f"0x{tag_id:04x}")] = _jsonable(value)
    for ifd_name, ifd_id, names in (
        ("Exif", 0x8769, ExifTags.TAGS),          # Exif IFD pointer
        ("GPSInfo", 0x8825, ExifTags.GPSTAGS),    # GPS IFD pointer
    ):
        try:
            ifd = exif.get_ifd(ifd_id)
        except Exception:
            continue
        if not ifd:
            continue
        sub: Dict[str, Any] = {}
        for tag_id, value in ifd.items():
            sub[names.get(tag_id, f"0x{tag_id:04x}")] = _jsonable(value)
        if sub:
            out[ifd_name] = sub
    out.pop("ExifOffset", None)
    if not isinstance(out.get("GPSInfo"), dict):   # bare IFD offset, no decoded GPS block
        out.pop("GPSInfo", None)
    return out


def _normalise_mode(img: Image.Image, master_format: str) -> tuple[Image.Image, Optional[str]]:
    mapping = _PNG_MODE_MAP if master_format == "png" else _TIFF_MODE_MAP
    target = mapping.get(img.mode)
    if target is None:
        return img, None
    original = img.mode
    try:
        img = img.convert("I").convert(target) if img.mode == "F" else img.convert(target)
    except (ValueError, OSError):
        img = img.convert("L")
    return img, original


def _write_base64(fh, path: Path, line_len: int = 76) -> None:
    """Stream *path* as MIME base64 (76-column lines), like Xena does."""
    bytes_per_line = line_len // 4 * 3           # 57 bytes -> 76 chars
    chunk = bytes_per_line * 1024
    with open(path, "rb") as src:
        while True:
            block = src.read(chunk)
            if not block:
                break
            fh.write(base64.encodebytes(block).decode("ascii"))


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def normalise_image(
    source: "str | Path",
    out_dir: "str | Path",
    *,
    master_format: str = "png",
    apply_exif_orientation: bool = True,
    stem: Optional[str] = None,
) -> tuple[Path, Dict[str, Any], list]:
    """Write the lossless master and return ``(master_path, technical_metadata, warnings)``."""
    if master_format not in MASTER_FORMATS:
        raise PreservationError(f"master_format must be one of {MASTER_FORMATS}, got {master_format!r}")
    src = Path(source)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = stem or src.stem
    warnings: list = []

    try:
        img = Image.open(src)
        img.load()
    except Exception as exc:
        hint = ""
        if src.suffix.lower() in (".heic", ".heif"):
            hint = " (HEIC/HEIF needs `pip install pillow-heif` and `import pillow_heif; pillow_heif.register_heif_opener()`)"
        raise PreservationError(f"cannot open {src}: {exc}{hint}") from exc

    src_format = img.format or src.suffix.lstrip(".").upper()
    src_mode = img.mode
    src_size = img.size
    n_frames = getattr(img, "n_frames", 1)
    if n_frames > 1:
        warnings.append(f"{src.name}: {n_frames} frames/pages; only the first is normalised")

    exif_all = extract_exif(img)
    orientation = None
    try:
        orientation = img.getexif().get(0x0112)
    except Exception:
        orientation = None
    icc = img.info.get("icc_profile")
    dpi = img.info.get("dpi")
    xmp = img.info.get("xmp")
    exif_bytes = img.info.get("exif")

    applied = None
    if apply_exif_orientation and orientation and orientation != 1:
        transposed = ImageOps.exif_transpose(img)
        if transposed is not None:
            img = transposed
            applied = int(orientation)
            exif_bytes = img.info.get("exif", exif_bytes)

    img, converted_from = _normalise_mode(img, master_format)
    if converted_from:
        warnings.append(f"{src.name}: mode {converted_from} converted to {img.mode} for {master_format.upper()}")

    ext = "png" if master_format == "png" else "tif"
    master = out / f"{stem}.{ext}"
    save_kwargs: Dict[str, Any] = {}
    if dpi:
        try:
            save_kwargs["dpi"] = (float(dpi[0]), float(dpi[1]))
        except (TypeError, IndexError, ValueError):
            pass
    if icc:
        save_kwargs["icc_profile"] = icc

    exif_embedded = False
    if master_format == "png":
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        try:
            img.save(master, format="PNG", optimize=False, compress_level=6, **save_kwargs)
            exif_embedded = bool(exif_bytes)
        except Exception:
            save_kwargs.pop("exif", None)
            img.save(master, format="PNG", optimize=False, compress_level=6, **save_kwargs)
            warnings.append(f"{src.name}: EXIF could not be embedded in the PNG; kept in provenance only")
    else:
        # Only carry EXIF from non-TIFF sources: a source TIFF's IFD0 holds strip
        # offsets and layout tags that must not be copied into a new file.
        if exif_bytes and src_format != "TIFF":
            save_kwargs["exif"] = exif_bytes
        try:
            img.save(master, format="TIFF", compression=None, **save_kwargs)
            exif_embedded = "exif" in save_kwargs
        except Exception:
            save_kwargs.pop("exif", None)
            img.save(master, format="TIFF", compression=None, **save_kwargs)
            warnings.append(f"{src.name}: EXIF could not be embedded in the TIFF; kept in provenance only")

    # Pixel-level fixity: the master must decode to exactly what we intended to write.
    with Image.open(master) as check:
        check.load()
        if check.size != img.size or check.mode != img.mode:
            raise PreservationError(f"{master}: re-read mismatch ({check.mode} {check.size} vs {img.mode} {img.size})")
        if ImageChops.difference(check.convert("RGB"), img.convert("RGB")).getbbox() is not None:
            raise PreservationError(f"{master}: pixel data changed during normalisation")
        if master_format == "tiff":
            compression = check.tag_v2.get(259)  # type: ignore[attr-defined]
            if compression not in (None, 1):
                raise PreservationError(f"{master}: expected uncompressed TIFF, got compression={compression}")

    tech = {
        "source": {
            "path": str(src.resolve()),
            "uri": src.resolve().as_uri(),
            "filename": src.name,
            "bytes": src.stat().st_size,
            "sha256": sha256_file(src),
            "format": src_format,
            "mime": Image.MIME.get(src_format, f"image/{src_format.lower()}"),
            "mode": src_mode,
            "width": src_size[0],
            "height": src_size[1],
            "frames": n_frames,
            "last_modified": _iso_mtime(src),
        },
        "master": {
            "path": str(master.resolve()),
            "filename": master.name,
            "format": "PNG" if master_format == "png" else "TIFF",
            "mime": "image/png" if master_format == "png" else "image/tiff",
            "compression": "deflate (lossless)" if master_format == "png" else "none (baseline TIFF 6.0)",
            "bytes": master.stat().st_size,
            "sha256": sha256_file(master),
            "mode": img.mode,
            "mode_converted_from": converted_from,
            "width": img.size[0],
            "height": img.size[1],
            "dpi": save_kwargs.get("dpi"),
            "icc_profile_embedded": bool(icc),
            "icc_profile_bytes": len(icc) if icc else 0,
            "exif_embedded": exif_embedded,
            "exif_orientation_applied": applied,
        },
        "exif": exif_all,
        "xmp": (xmp.decode("utf-8", "replace") if isinstance(xmp, bytes) else xmp)
        if xmp and len(xmp) <= 65536 else (f"<{len(xmp)} bytes>" if xmp else None),
    }
    return master, tech, warnings


def write_xena(
    master: "str | Path",
    source: "str | Path",
    xena_path: "str | Path",
    *,
    master_format: str = "png",
    normaliser_name: Optional[str] = None,
) -> Path:
    """Wrap *master* in a Xena Default-Package-Wrapper envelope at *xena_path*."""
    master = Path(master)
    source = Path(source)
    xena_path = Path(xena_path)
    normaliser = normaliser_name or f"{TOOL_NAME}.preserve.PillowTo{'Png' if master_format == 'png' else 'Tiff'}Normaliser/{__version__}"

    if master_format == "png":
        open_tag = (
            f'<png:png xmlns:png={quoteattr(PNG_NS)} png:description={quoteattr(PNG_DESCRIPTION)} '
            f'png:extension="png">'
        )
        close_tag = "</png:png>"
    else:
        open_tag = (
            f'<binary-object:binary-object xmlns:binary-object={quoteattr(BINARY_NS)} '
            f'binary-object:description={quoteattr(TIFF_DESCRIPTION)} binary-object:extension="tif">'
        )
        close_tag = "</binary-object:binary-object>"

    with open(xena_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write("<xena>\n<meta_data>\n")
        fh.write(f"<meta_data_wrapper_name>{escape(WRAPPER_NAME)}</meta_data_wrapper_name>\n")
        fh.write(f"<normaliser_name>{escape(normaliser)}</normaliser_name>\n")
        fh.write(f"<input_source_uri>{escape(source.resolve().as_uri())}</input_source_uri>\n")
        fh.write("</meta_data>\n<content>\n")
        fh.write(open_tag + "\n")
        _write_base64(fh, master)
        fh.write(close_tag + "\n")
        fh.write("</content>\n</xena>\n")
    return xena_path


def preserve_image(
    source: "str | Path",
    out_dir: "str | Path",
    *,
    master_format: str = "png",
    apply_exif_orientation: bool = True,
    stem: Optional[str] = None,
) -> PreservationResult:
    """Full step 1: master + Xena envelope + provenance sidecar."""
    src = Path(source)
    out = Path(out_dir)
    stem = stem or src.stem
    master, tech, warnings = normalise_image(
        src, out, master_format=master_format, apply_exif_orientation=apply_exif_orientation, stem=stem
    )
    xena_path = write_xena(master, src, out / f"{stem}.xena", master_format=master_format)
    provenance_path = out / f"{stem}.provenance.json"
    provenance = {
        "schema": f"{TOOL_NAME}/provenance/1.0",
        "created": _utc_now(),
        "tool": {
            "name": TOOL_NAME,
            "version": __version__,
            "python": platform.python_version(),
            "pillow": PIL.__version__,
            "platform": platform.platform(),
        },
        "source": tech["source"],
        "master": tech["master"],
        "xena": {
            "path": str(xena_path.resolve()),
            "filename": xena_path.name,
            "bytes": xena_path.stat().st_size,
            "sha256": sha256_file(xena_path),
            "wrapper": WRAPPER_NAME,
            "wrapper_namespace": XENA_NS,
            "payload_namespace": PNG_NS if master_format == "png" else BINARY_NS,
            "payload_element": "png:png" if master_format == "png" else "binary-object:binary-object",
            "payload_sha256": tech["master"]["sha256"],
            "input_source_uri": tech["source"]["uri"],
        },
        "exif": tech["exif"],
        "xmp": tech["xmp"],
        "warnings": warnings,
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return PreservationResult(
        source=str(src),
        master=str(master),
        xena=str(xena_path),
        provenance=str(provenance_path),
        master_format=master_format,
        sha256_source=tech["source"]["sha256"],
        sha256_master=tech["master"]["sha256"],
        width=tech["master"]["width"],
        height=tech["master"]["height"],
        mode=tech["master"]["mode"],
        orientation_applied=tech["master"]["exif_orientation_applied"],
        warnings=warnings,
    )


# --------------------------------------------------------------------------- #
# reading envelopes back
# --------------------------------------------------------------------------- #
def read_xena_meta(xena_path: "str | Path") -> Dict[str, Any]:
    """Return wrapper metadata + payload element info without decoding the payload."""
    import xml.etree.ElementTree as ET

    meta: Dict[str, Any] = {"path": str(Path(xena_path).resolve())}
    for event, el in ET.iterparse(str(xena_path), events=("start", "end")):
        tag = el.tag.rsplit("}", 1)[-1]
        if event == "end" and tag in ("meta_data_wrapper_name", "normaliser_name", "input_source_uri"):
            meta[tag] = (el.text or "").strip()
        elif event == "start" and tag == "content":
            meta["_in_content"] = True
        elif event == "start" and meta.get("_in_content") and "payload_element" not in meta:
            if el.tag.startswith("{"):
                ns, local = el.tag[1:].split("}", 1)
            else:
                ns, local = "", el.tag
            meta["payload_element"] = local
            meta["payload_namespace"] = ns
            for k, v in el.attrib.items():
                key = k.rsplit("}", 1)[-1]
                meta[f"payload_{key}"] = v
        if event == "end":
            el.clear()
    meta.pop("_in_content", None)
    return meta


def unwrap_xena(xena_path: "str | Path", out_path: "str | Path", *, expected_sha256: Optional[str] = None) -> Dict[str, Any]:
    """Decode the base64 payload of a ``.xena`` file back to a binary file and verify it."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(str(xena_path))
    root = tree.getroot()
    content = next((el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "content"), None)
    if content is None or len(content) == 0:
        raise PreservationError(f"{xena_path}: no <content> payload found")
    payload = content[0]
    data = base64.b64decode("".join((payload.text or "").split()), validate=False)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise PreservationError(f"{xena_path}: payload sha256 {digest} != expected {expected_sha256}")
    return {"path": str(out), "bytes": len(data), "sha256": digest,
            "payload_element": payload.tag.rsplit("}", 1)[-1]}


def preservation_summary(result: PreservationResult) -> Dict[str, Any]:
    return asdict(result)
