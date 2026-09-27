"""Command-line interface: ``python3 -m journal_pipeline <command> ...``."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import TOOL_NAME, __version__

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".heic", ".heif", ".jp2"}
TRANSCRIPT_EXTS = {".hocr", ".html", ".htm", ".xhtml", ".xml", ".txt"}


def log(msg: str, *, quiet: bool = False) -> None:
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


def _natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def collect_images(inputs: List[str]) -> List[Path]:
    out: List[Path] = []
    for raw in inputs:
        p = Path(raw).expanduser()
        if p.is_dir():
            out.extend(sorted((c for c in p.iterdir() if c.suffix.lower() in IMAGE_EXTS and c.is_file()),
                              key=_natural_key))
        elif p.is_file():
            out.append(p)
        else:
            raise SystemExit(f"error: {raw} does not exist")
    if not out:
        raise SystemExit("error: no images found (looked for " + ", ".join(sorted(IMAGE_EXTS)) + ")")
    return out


def find_transcript(transcripts_dir: Optional[Path], stem: str) -> Optional[Path]:
    if not transcripts_dir:
        return None
    for ext in (".hocr", ".html", ".xhtml", ".htm", ".xml", ".txt"):
        cand = transcripts_dir / f"{stem}{ext}"
        if cand.exists():
            return cand
    return None


# --------------------------------------------------------------------------- #
# shared option groups
# --------------------------------------------------------------------------- #
def add_preserve_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("step 1 — preservation")
    g.add_argument("--master", choices=("png", "tiff"), default="png",
                   help="lossless master format: png (what Xena itself produces, default) or uncompressed tiff")
    g.add_argument("--keep-orientation", action="store_true",
                   help="do not apply the EXIF orientation tag to the master pixels")


def add_ocr_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("step 2 — OCR")
    g.add_argument("--profile", choices=("print", "handwriting", "none"), default="print",
                   help="preprocessing + Tesseract preset (default: print)")
    g.add_argument("--lang", "-l", default=None, help="Tesseract language(s), e.g. eng or eng+fra (default eng)")
    g.add_argument("--psm", type=int, default=None, help="page segmentation mode (overrides profile)")
    g.add_argument("--oem", type=int, default=None, help="OCR engine mode: 0 legacy, 1 LSTM, 3 default")
    g.add_argument("--dpi", type=int, default=None, help="tell Tesseract the source resolution")
    g.add_argument("--tessdata-dir", default=None, help="directory holding *.traineddata (or set $TESSDATA_PREFIX)")
    g.add_argument("--user-words", default=None, help="file of extra vocabulary (names, places)")
    g.add_argument("--user-patterns", default=None, help="Tesseract user-patterns file")
    g.add_argument("--config", "-c", action="append", default=[], metavar="KEY=VALUE",
                   help="extra Tesseract variable, repeatable (e.g. -c preserve_interword_spaces=1)")
    g.add_argument("--backend", choices=("auto", "cli", "tesserocr"), default="auto")
    g.add_argument("--binarize", dest="binarize", action="store_true", default=None,
                   help="force local-mean binarisation on")
    g.add_argument("--no-binarize", dest="binarize", action="store_false", help="force it off")
    g.add_argument("--binarize-offset", type=int, default=None, metavar="N",
                   help="ink = darker than local mean by N grey levels (default 35; lower for faint pencil)")
    g.add_argument("--min-width", type=int, default=None, help="upscale pages narrower than this many px")
    g.add_argument("--border", type=int, default=None, help="white border added before OCR (px)")
    g.add_argument("--discard-preprocessed", action="store_true",
                   help="do not keep the <stem>.ocr-input.png working image")


def add_extract_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("step 4 — haiku extraction")
    g.add_argument("--tolerance", type=int, default=1, help="max syllable deviation per line (default 1)")
    g.add_argument("--tolerance-total", type=int, default=2, help="max total deviation over 3 lines (default 2)")
    g.add_argument("--min-score", type=float, default=0.5, help="acceptance threshold 0-1 (default 0.5)")
    g.add_argument("--min-confidence", type=float, default=20.0, help="ignore OCR lines below this word confidence")
    g.add_argument("--no-free-form", action="store_true", help="only report 5-7-5 (±tolerance) candidates")
    g.add_argument("--include-rejected", action="store_true", help="also list rejected candidates / excluded lines")
    g.add_argument("--format", choices=("json", "xml"), default="json", help="output format for haiku files")


def add_llm_args(p: argparse.ArgumentParser, *, as_engine: bool) -> None:
    g = p.add_argument_group("LLM extraction (optional)")
    if as_engine:
        g.add_argument("--engine", choices=("heuristic", "openai", "anthropic"), default="heuristic",
                       help="heuristic (offline, default) or an LLM provider")
    else:
        g.add_argument("--llm", choices=("openai", "anthropic"), default=None,
                       help="additionally run LLM extraction with this provider")
    g.add_argument("--model", default=None, help="model name (default per provider / $JOURNAL_LLM_MODEL)")
    g.add_argument("--base-url", default=None, help="API base URL (OpenAI-compatible servers, e.g. Ollama)")
    g.add_argument("--api-key", default=None, help="API key (default from environment)")
    g.add_argument("--json-mode", action="store_true", help="request response_format=json_object (OpenAI-style)")
    g.add_argument("--timeout", type=float, default=180.0, help="HTTP timeout in seconds")
    g.add_argument("--dry-run", action="store_true", help="write the request that would be sent, do not call the API")


def ocr_options_from_args(args: argparse.Namespace):
    from .ocr import OcrOptions

    config: Dict[str, str] = {}
    for item in args.config or []:
        if "=" not in item:
            raise SystemExit(f"error: --config expects KEY=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        config[k.strip()] = v.strip()
    return OcrOptions.from_profile(
        args.profile, lang=args.lang, psm=args.psm, oem=args.oem, dpi=args.dpi,
        tessdata_dir=args.tessdata_dir, user_words=args.user_words, user_patterns=args.user_patterns,
        config=config or None, backend=args.backend, binarize=args.binarize, binarize_offset=args.binarize_offset,
        min_width=args.min_width,
        border=args.border, keep_preprocessed=(not args.discard_preprocessed) or None,
    )


def extract_options_from_args(args: argparse.Namespace):
    from .haiku import Options

    return Options(
        tolerance_per_line=args.tolerance, tolerance_total=args.tolerance_total, min_score=args.min_score,
        min_confidence=args.min_confidence, include_free_form=not args.no_free_form,
        include_rejected=args.include_rejected,
    )


def llm_client_from_args(args: argparse.Namespace, provider: str):
    from .llm import LLMClient

    return LLMClient(provider, model=args.model, api_key=args.api_key, base_url=args.base_url,
                     timeout=args.timeout, json_mode=args.json_mode)


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_preserve(args: argparse.Namespace) -> int:
    from .preserve import PreservationError, preserve_image

    out = Path(args.output)
    rc = 0
    for img in collect_images(args.inputs):
        try:
            res = preserve_image(img, out, master_format=args.master, apply_exif_orientation=not args.keep_orientation)
        except PreservationError as exc:
            log(f"[preserve] FAIL {img}: {exc}")
            rc = 1
            continue
        log(f"[preserve] {img.name} -> {Path(res.master).name} ({res.width}x{res.height} {res.mode}), "
            f"{Path(res.xena).name}, sha256 {res.sha256_master[:12]}…", quiet=args.quiet)
        for w in res.warnings:
            log(f"[preserve]   warning: {w}", quiet=args.quiet)
    return rc


def cmd_unwrap(args: argparse.Namespace) -> int:
    from .preserve import PreservationError, read_xena_meta, unwrap_xena

    xena = Path(args.xena)
    meta = read_xena_meta(xena)
    expected = None
    prov = xena.with_name(xena.stem + ".provenance.json")
    if prov.exists():
        expected = json.loads(prov.read_text(encoding="utf-8")).get("master", {}).get("sha256")
    ext = meta.get("payload_extension") or ("png" if meta.get("payload_element") == "png" else "bin")
    out = Path(args.output) if args.output else xena.with_name(f"{xena.stem}.unwrapped.{ext}")
    try:
        info = unwrap_xena(xena, out, expected_sha256=expected)
    except PreservationError as exc:
        log(f"[unwrap] FAIL: {exc}")
        return 1
    log(f"[unwrap] {xena.name}: {meta.get('payload_element')} payload -> {out} ({info['bytes']} bytes, "
        f"sha256 {info['sha256'][:12]}…{' verified' if expected else ''})", quiet=args.quiet)
    print(json.dumps({**meta, **info}, indent=2))
    return 0


def cmd_ocr(args: argparse.Namespace) -> int:
    from .ocr import OcrError, OcrUnavailable, ocr_image

    opts = ocr_options_from_args(args)
    out = Path(args.output)
    rc = 0
    for img in collect_images(args.inputs):
        try:
            res = ocr_image(img, out, opts)
        except OcrUnavailable as exc:
            log(f"[ocr] {exc}")
            return 2
        except OcrError as exc:
            log(f"[ocr] FAIL {img}: {exc}")
            rc = 1
            continue
        log(f"[ocr] {img.name} -> {Path(res.hocr).name} ({res.engine}, {res.backend}, psm {opts.psm})", quiet=args.quiet)
    return rc


def cmd_packet(args: argparse.Namespace) -> int:
    from .packet import build_packet_files

    out = build_packet_files(args.transcript, args.output, provenance_path=args.provenance,
                             ocr_meta_path=args.ocr_meta, xena_path=args.xena)
    log(f"[packet] {out}", quiet=args.quiet)
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    from .haiku import extract_haikus, write_result
    from .packet import read_packet

    opts = extract_options_from_args(args)
    packets = [Path(p) for p in args.packets]
    rc = 0
    for pk in packets:
        packet = read_packet(pk)
        if args.engine == "heuristic":
            result = extract_haikus(packet, opts)
        else:
            from .llm import LLMError, extract_with_llm

            try:
                result = extract_with_llm(packet, llm_client_from_args(args, args.engine), dry_run=args.dry_run)
            except LLMError as exc:
                log(f"[extract] LLM FAIL {pk.name}: {exc}")
                rc = 1
                continue
        if args.output:
            dest = Path(args.output)
            if len(packets) > 1 or dest.is_dir() or not dest.suffix:
                dest.mkdir(parents=True, exist_ok=True)
                dest = dest / (pk.name.replace(".packet.xml", "") + f".haikus.{args.format}")
            write_result(result, dest, args.format)
            log(f"[extract] {pk.name}: {len(result.get('haikus', []))} haiku(s) -> {dest}", quiet=args.quiet)
        else:
            from .haiku import haikus_to_xml

            print(haikus_to_xml(result) if args.format == "xml" else json.dumps(result, indent=2, ensure_ascii=False))
    return rc


def cmd_prompt(args: argparse.Namespace) -> int:
    from .llm import render_prompt
    from .packet import read_packet

    text = render_prompt(read_packet(args.packet))
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        log(f"[prompt] {args.output}", quiet=args.quiet)
    else:
        print(text)
    return 0


def cmd_make_sample(args: argparse.Namespace) -> int:
    from .sample import make_samples

    pages = make_samples(args.output, count=args.count, messy=not args.clean, ext=args.ext)
    for p in pages:
        log(f"[sample] {p.path} ({len(p.haikus)} haikus planted)", quiet=args.quiet)
    (Path(args.output) / "planted_haikus.json").write_text(
        json.dumps({Path(p.path).name: p.haikus for p in pages}, indent=2) + "\n", encoding="utf-8")
    return 0


def _merge_results(stem: str, heuristic: Dict[str, Any], llm: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Union of haikus from both engines keyed by source line ids."""
    merged: List[Dict[str, Any]] = []
    seen: Dict[tuple, Dict[str, Any]] = {}
    for h in heuristic.get("haikus", []):
        key = tuple(h["source"]["line_ids"])
        entry = {"page_stem": stem, "lines": h["lines"], "syllables": h["syllables"], "form": h["form"],
                 "validation": h["validation"], "score": h["score"], "source": h["source"],
                 "found_by": ["heuristic"], "explanation": h["explanation"]}
        seen[key] = entry
        merged.append(entry)
    for h in (llm or {}).get("haikus", []):
        key = tuple(h["source"]["line_ids"])
        if key in seen:
            seen[key]["found_by"].append("llm")
            seen[key]["llm_lines"] = h["lines"]
            seen[key]["llm_validation"] = h["local_validation"]
            if h.get("ocr_corrections"):
                seen[key]["ocr_corrections"] = h["ocr_corrections"]
        else:
            entry = {"page_stem": stem, "lines": h["lines"], "syllables": h.get("local_syllables"),
                     "form": h.get("form"), "validation": h.get("local_validation"), "score": h.get("confidence"),
                     "source": h["source"], "found_by": ["llm"], "explanation": h.get("local_explanation"),
                     "ocr_corrections": h.get("ocr_corrections") or []}
            seen[key] = entry
            merged.append(entry)
    return merged


def _digest_markdown(manifest: Dict[str, Any]) -> str:
    out = [f"# Haikus extracted — {manifest['generated']}", ""]
    total = sum(len(p["haikus"]) for p in manifest["pages"])
    out.append(f"{len(manifest['pages'])} page(s), {total} haiku(s). Engines: "
               + ", ".join(manifest["engines"]) + ".")
    out.append("")
    for page in manifest["pages"]:
        out.append(f"## {page['stem']}")
        out.append("")
        out.append(f"- source: `{page['source']}`")
        out.append(f"- master: `{page['master']}`  ·  xena: `{page['xena']}`")
        if page.get("ocr_confidence") is not None:
            out.append(f"- OCR mean word confidence: {page['ocr_confidence']}")
        if page.get("error"):
            out.append(f"- **error:** {page['error']}")
        out.append("")
        if not page["haikus"]:
            out.append("_no haiku found_")
            out.append("")
        for i, h in enumerate(page["haikus"], 1):
            label = (h.get("form") or "haiku").replace(" (approximate)", "")
            out.append(f"### {i}. {label} — {h.get('validation')} · score {h.get('score')} · {'+'.join(h['found_by'])}")
            out.append("")
            for ln in h["lines"]:
                out.append(f"    {ln}")
            out.append("")
            for e in h.get("explanation") or []:
                out.append(f"- {e}")
            src = h["source"]
            loc = f"page {src.get('page')}, lines {src.get('line_ids')}"
            if src.get("bbox"):
                loc += f", bbox {src['bbox']}"
            out.append(f"- {loc}")
            for c in h.get("ocr_corrections") or []:
                out.append(f"- OCR `{c['ocr']}` → model `{c['model']}`")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def cmd_run(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone

    from .haiku import extract_haikus, write_result
    from .hocr import load_transcript
    from .ocr import OcrError, OcrUnavailable, detect_backend, ocr_image
    from .packet import build_packet, read_packet, write_packet
    from .preserve import PreservationError, preserve_image

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    images = collect_images(args.inputs)
    transcripts_dir = Path(args.transcripts).expanduser() if args.transcripts else None
    ocr_opts = ocr_options_from_args(args)
    ex_opts = extract_options_from_args(args)

    need_ocr = any(find_transcript(transcripts_dir, img.stem) is None for img in images)
    backend = None
    if need_ocr:
        try:
            backend = detect_backend(ocr_opts.backend)
        except OcrUnavailable as exc:
            log(f"[run] {exc}")
            return 2

    llm_client = llm_client_from_args(args, args.llm) if args.llm else None
    engines = ["heuristic"] + ([f"llm:{llm_client.provider}/{llm_client.model}"] if llm_client else [])
    manifest: Dict[str, Any] = {
        "schema": f"{TOOL_NAME}/manifest/1.0",
        "tool": f"{TOOL_NAME}/{__version__}",
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "output_dir": str(out.resolve()),
        "master_format": args.master,
        "ocr": {"backend": backend, "profile": ocr_opts.profile, "lang": ocr_opts.lang, "psm": ocr_opts.psm},
        "engines": engines,
        "pages": [],
    }
    rc = 0
    for img in images:
        stem = img.stem
        page_dir = out / stem
        page_dir.mkdir(parents=True, exist_ok=True)
        entry: Dict[str, Any] = {"stem": stem, "source": str(img), "haikus": []}
        manifest["pages"].append(entry)
        try:
            # 1. preserve
            pres = preserve_image(img, page_dir, master_format=args.master,
                                  apply_exif_orientation=not args.keep_orientation)
            entry.update(master=pres.master, xena=pres.xena, provenance=pres.provenance,
                         sha256_master=pres.sha256_master, warnings=pres.warnings)
            log(f"[1/4 preserve] {img.name}: {Path(pres.master).name} + {Path(pres.xena).name}", quiet=args.quiet)

            # 2. OCR (or import a transcript)
            imported = find_transcript(transcripts_dir, stem)
            if imported:
                transcript = imported
                ocr_meta_path = None
                log(f"[2/4 ocr] {img.name}: using supplied transcript {imported.name}", quiet=args.quiet)
            else:
                ocr_res = ocr_image(pres.master, page_dir, ocr_opts, stem=stem)
                transcript = Path(ocr_res.hocr)
                ocr_meta_path = Path(ocr_res.meta)
                log(f"[2/4 ocr] {img.name}: {transcript.name} ({ocr_res.engine}, {ocr_res.backend})", quiet=args.quiet)
            entry["transcript"] = str(transcript)

            # 3. packet
            doc = load_transcript(transcript)
            prov = json.loads(Path(pres.provenance).read_text(encoding="utf-8"))
            meta = json.loads(ocr_meta_path.read_text(encoding="utf-8")) if ocr_meta_path else None
            root = build_packet(doc, provenance=prov, ocr_meta=meta, xena_path=pres.xena, transcript_path=str(transcript))
            packet_path = write_packet(root, page_dir / f"{stem}.packet.xml")
            entry["packet"] = str(packet_path)
            entry["ocr_confidence"] = doc.mean_confidence()
            entry["lines"] = len(doc.lines())
            log(f"[3/4 packet] {img.name}: {packet_path.name} ({len(doc.lines())} lines, "
                f"conf {doc.mean_confidence()})", quiet=args.quiet)

            # 4. extract
            packet = read_packet(packet_path)
            heuristic = extract_haikus(packet, ex_opts)
            hpath = write_result(heuristic, page_dir / f"{stem}.haikus.{args.format}", args.format)
            entry["haikus_heuristic"] = str(hpath)
            llm_result = None
            if llm_client:
                from .llm import LLMError, extract_with_llm

                try:
                    llm_result = extract_with_llm(packet, llm_client, dry_run=args.dry_run)
                    lpath = write_result(llm_result, page_dir / f"{stem}.haikus.llm.json", "json")
                    entry["haikus_llm"] = str(lpath)
                except LLMError as exc:
                    entry["llm_error"] = str(exc)
                    log(f"[4/4 extract] {img.name}: LLM failed: {exc}")
                    rc = 1
            entry["haikus"] = _merge_results(stem, heuristic, llm_result)
            log(f"[4/4 extract] {img.name}: {len(entry['haikus'])} haiku(s)", quiet=args.quiet)
            for h in entry["haikus"]:
                log("             " + " / ".join(h["lines"]), quiet=args.quiet)
        except (PreservationError, OcrError) as exc:
            entry["error"] = str(exc)
            log(f"[run] FAIL {img.name}: {exc}")
            rc = 1
        except OcrUnavailable as exc:
            entry["error"] = str(exc)
            log(f"[run] {exc}")
            return 2

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    all_haikus = {
        "schema": f"{TOOL_NAME}/haikus-collection/1.0",
        "generated": manifest["generated"],
        "engines": engines,
        "haikus": [h for p in manifest["pages"] for h in p["haikus"]],
    }
    (out / "haikus.json").write_text(json.dumps(all_haikus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "haikus.md").write_text(_digest_markdown(manifest), encoding="utf-8")
    log(f"[run] done: {len(all_haikus['haikus'])} haiku(s) from {len(images)} page(s) -> {out / 'haikus.md'}",
        quiet=args.quiet)
    return rc


def cmd_doctor(args: argparse.Namespace) -> int:
    """Report which optional pieces are available."""
    import PIL

    from .ocr import available_languages, cli_available, engine_version, resolve_tessdata, tesserocr_available
    from .syllables import cmu_available

    print(f"{TOOL_NAME} {__version__}")
    print(f"python  : {sys.version.split()[0]}")
    print(f"Pillow  : {PIL.__version__}")
    cli = cli_available()
    print(f"tesseract CLI : {cli or 'not found'}" + (f"  ({engine_version('cli')})" if cli else ""))
    print(f"tesserocr     : {'available (' + engine_version('tesserocr') + ')' if tesserocr_available() else 'not installed'}")
    tessdata = resolve_tessdata(args.tessdata_dir, "eng")
    backend = "cli" if cli else ("tesserocr" if tesserocr_available() else None)
    if backend:
        langs = available_languages(backend, tessdata)
        print(f"tessdata      : {tessdata or 'backend default'} -> languages: {', '.join(langs) or 'NONE FOUND'}")
    print(f"cmudict       : {'installed (exact syllables for dictionary words)' if cmu_available() else 'not installed (rule-based syllables)'}")
    import os
    print(f"OPENAI_API_KEY    : {'set' if os.environ.get('OPENAI_API_KEY') else 'unset'}")
    print(f"ANTHROPIC_API_KEY : {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'unset'}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="journal_pipeline",
        description="Journal images -> Xena preservation envelope -> Tesseract hOCR -> AI-ready XML packet -> haikus.",
    )
    p.add_argument("--version", action="version", version=f"{TOOL_NAME} {__version__}")
    p.add_argument("-q", "--quiet", action="store_true", help="less progress output")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("run", help="all four steps over images or a directory")
    s.add_argument("inputs", nargs="+", help="image files and/or directories")
    s.add_argument("-o", "--output", required=True, help="output directory")
    s.add_argument("--transcripts", default=None,
                   help="directory of ready-made <stem>.hocr/.xml/.txt transcripts (skips Tesseract for those pages)")
    add_preserve_args(s)
    add_ocr_args(s)
    add_extract_args(s)
    add_llm_args(s, as_engine=False)
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("preserve", help="step 1: lossless master + Xena envelope + provenance")
    s.add_argument("inputs", nargs="+")
    s.add_argument("-o", "--output", required=True)
    add_preserve_args(s)
    s.set_defaults(func=cmd_preserve)

    s = sub.add_parser("unwrap", help="decode the payload of a .xena file and verify its checksum")
    s.add_argument("xena")
    s.add_argument("-o", "--output", default=None)
    s.set_defaults(func=cmd_unwrap)

    s = sub.add_parser("ocr", help="step 2: Tesseract -> hOCR (+ txt)")
    s.add_argument("inputs", nargs="+")
    s.add_argument("-o", "--output", required=True)
    add_ocr_args(s)
    s.set_defaults(func=cmd_ocr)

    s = sub.add_parser("packet", help="step 3: merge a transcript with preservation metadata into one XML")
    s.add_argument("--transcript", required=True, help=".hocr, ALTO .xml or plain .txt")
    s.add_argument("--provenance", default=None, help="<stem>.provenance.json from step 1")
    s.add_argument("--ocr-meta", default=None, help="<stem>.ocr.json from step 2 (maps coordinates to the master)")
    s.add_argument("--xena", default=None, help="path of the .xena envelope to reference")
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_packet)

    s = sub.add_parser("extract", help="step 4: find haikus in packet(s)")
    s.add_argument("packets", nargs="+")
    s.add_argument("-o", "--output", default=None, help="file (single packet) or directory")
    add_extract_args(s)
    add_llm_args(s, as_engine=True)
    s.set_defaults(func=cmd_extract)

    s = sub.add_parser("prompt", help="print the system prompt + packet to paste into a chat UI")
    s.add_argument("packet")
    s.add_argument("-o", "--output", default=None)
    s.set_defaults(func=cmd_prompt)

    s = sub.add_parser("make-sample", help="render synthetic journal pages to try the pipeline on")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--count", type=int, default=2)
    s.add_argument("--clean", action="store_true", help="no paper texture / rotation / noise")
    s.add_argument("--ext", choices=("jpg", "png", "tif"), default="jpg")
    s.set_defaults(func=cmd_make_sample)

    s = sub.add_parser("doctor", help="show which optional components are available")
    s.add_argument("--tessdata-dir", default=None)
    s.set_defaults(func=cmd_doctor)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
