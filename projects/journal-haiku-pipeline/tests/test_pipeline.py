"""End-to-end tests through the CLI.

The OCR-dependent tests run only when a Tesseract backend *and* English
language data are available (tesseract CLI on PATH, or tesserocr with
$TESSDATA_PREFIX / a discoverable eng.traineddata); otherwise they skip and
the transcript-import path is exercised instead.
"""

import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from journal_pipeline.cli import main
from journal_pipeline.ocr import OcrUnavailable, available_languages, detect_backend, resolve_tessdata
from journal_pipeline.sample import make_samples


def ocr_ready() -> bool:
    try:
        backend = detect_backend("auto")
    except OcrUnavailable:
        return False
    langs = available_languages(backend, resolve_tessdata(None))
    return "eng" in langs


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            rc = main(list(argv))
        except SystemExit as exc:  # argparse / SystemExit("error: ...")
            if isinstance(exc.code, int):
                rc = exc.code
            else:                  # the interpreter would print the message itself
                err.write(str(exc.code) + "\n")
                rc = 1
    return rc, out.getvalue(), err.getvalue()


class SampleAndStepCommands(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_make_sample_and_preserve_unwrap(self):
        rc, _, err = run_cli("make-sample", "-o", str(self.dir / "in"), "--count", "1", "--clean", "--ext", "png")
        self.assertEqual(rc, 0, err)
        planted = json.loads((self.dir / "in" / "planted_haikus.json").read_text())
        self.assertEqual(len(planted["journal_page_01.png"]), 2)

        rc, _, err = run_cli("preserve", str(self.dir / "in"), "-o", str(self.dir / "pres"), "--master", "tiff")
        self.assertEqual(rc, 0, err)
        xena = self.dir / "pres" / "journal_page_01.xena"
        self.assertTrue(xena.exists())
        self.assertTrue((self.dir / "pres" / "journal_page_01.tif").exists())

        rc, out, err = run_cli("unwrap", str(xena), "-o", str(self.dir / "back.tif"))
        self.assertEqual(rc, 0, err)
        info = json.loads(out)
        self.assertEqual(info["payload_element"], "binary-object")
        self.assertEqual((self.dir / "back.tif").read_bytes(), (self.dir / "pres" / "journal_page_01.tif").read_bytes())
        self.assertIn("verified", err)

    def test_packet_extract_prompt_from_text_transcript(self):
        transcript = self.dir / "page.txt"
        transcript.write_text("Tuesday, 14 March 2023\n\nRain on the harbour\nthe gulls argue over scraps\n"
                              "my coffee goes cold\n\nNote to self: buy stamps before Friday.\n", encoding="utf-8")
        packet = self.dir / "page.packet.xml"
        rc, _, err = run_cli("packet", "--transcript", str(transcript), "-o", str(packet))
        self.assertEqual(rc, 0, err)
        root = ET.parse(packet).getroot()
        self.assertEqual(root.find("ocr").get("transcript_format"), "text")

        rc, out, err = run_cli("extract", str(packet))
        self.assertEqual(rc, 0, err)
        result = json.loads(out)
        self.assertEqual([h["lines"] for h in result["haikus"]],
                         [["Rain on the harbour", "the gulls argue over scraps", "my coffee goes cold"]])

        rc, out, _ = run_cli("extract", str(packet), "--format", "xml")
        self.assertEqual(rc, 0)
        self.assertEqual(ET.fromstring(out).find("haiku/line").text, "Rain on the harbour")

        rc, out, _ = run_cli("prompt", str(packet))
        self.assertEqual(rc, 0)
        self.assertIn("=== SYSTEM PROMPT ===", out)
        self.assertIn("<pipeline_packet", out)

        rc, out, err = run_cli("extract", str(packet), "--engine", "openai", "--dry-run", "--api-key", "x")
        self.assertEqual(rc, 0, err)
        self.assertTrue(json.loads(out)["dry_run"])

    def test_run_with_imported_transcripts_needs_no_tesseract(self):
        make_samples(self.dir / "in", count=1, messy=False, ext="png")
        tdir = self.dir / "transcripts"
        tdir.mkdir()
        (tdir / "journal_page_01.txt").write_text(
            "Tuesday, 14 March 2023\n\nRain again this morning. Walked down to the harbour before work\n"
            "and watched the fishing boats come in.\n\nRain on the harbour\nthe gulls argue over scraps\n"
            "my coffee goes cold\n\nthe old brass compass\nstill finds north in my palm now\nfather's steady hand\n",
            encoding="utf-8")
        rc, _, err = run_cli("run", str(self.dir / "in"), "-o", str(self.dir / "out"), "--transcripts", str(tdir))
        self.assertEqual(rc, 0, err)
        manifest = json.loads((self.dir / "out" / "manifest.json").read_text())
        page = manifest["pages"][0]
        self.assertTrue(Path(page["xena"]).exists())
        self.assertTrue(page["transcript"].endswith("journal_page_01.txt"))
        self.assertEqual(len(page["haikus"]), 2)
        self.assertTrue((self.dir / "out" / "haikus.md").exists())
        self.assertIn("father's steady hand", (self.dir / "out" / "haikus.md").read_text())

    def test_missing_input_and_bad_config(self):
        rc, _, err = run_cli("preserve", str(self.dir / "nope.jpg"), "-o", str(self.dir / "o"))
        self.assertEqual(rc, 1)
        self.assertIn("does not exist", err)
        (self.dir / "x.png").write_bytes(b"")
        rc, _, err = run_cli("ocr", str(self.dir / "x.png"), "-o", str(self.dir / "o"), "--config", "novalue")
        self.assertEqual(rc, 1)
        self.assertIn("KEY=VALUE", err)


@unittest.skipUnless(ocr_ready(), "no Tesseract backend with English data available")
class RealOcrPipeline(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_full_run_finds_the_planted_haikus(self):
        pages = make_samples(self.dir / "in", count=2, messy=True, ext="jpg")
        rc, _, err = run_cli("run", str(self.dir / "in"), "-o", str(self.dir / "out"), "--profile", "print")
        self.assertEqual(rc, 0, err)
        manifest = json.loads((self.dir / "out" / "manifest.json").read_text())
        self.assertEqual(len(manifest["pages"]), 2)
        for sample, page in zip(pages, manifest["pages"]):
            self.assertIsNone(page.get("error"))
            self.assertGreater(page["ocr_confidence"], 60)
            found = [[ln.lower() for ln in h["lines"]] for h in page["haikus"]]
            for planted in sample.haikus:
                # OCR may drop a character; require the first two lines to come through
                self.assertTrue(any(f[0] == planted[0].lower() and f[1] == planted[1].lower() for f in found),
                                (planted, found))
            packet = ET.parse(page["packet"]).getroot()
            self.assertEqual(packet.find("ocr").get("coordinate_space"), "master")
            self.assertTrue(packet.find("ocr").get("engine", "").startswith("tesseract"))
            # every haiku is traceable to hOCR line ids present in the packet
            ids = {ln.get("id") for ln in packet.iter("line")}
            for h in page["haikus"]:
                self.assertTrue(set(h["source"]["line_ids"]) <= ids)
                self.assertIsNotNone(h["source"]["bbox"])
        self.assertTrue((self.dir / "out" / "journal_page_01" / "journal_page_01.hocr").exists())
        self.assertTrue((self.dir / "out" / "journal_page_01" / "journal_page_01.ocr.json").exists())

    def test_handwriting_profile_runs(self):
        make_samples(self.dir / "in", count=1, messy=True, ext="jpg")
        rc, _, err = run_cli("ocr", str(self.dir / "in"), "-o", str(self.dir / "ocr"), "--profile", "handwriting")
        self.assertEqual(rc, 0, err)
        meta = json.loads((self.dir / "ocr" / "journal_page_01.ocr.json").read_text())
        self.assertEqual(meta["options"]["psm"], 6)
        self.assertEqual(meta["options"]["oem"], 1)
        self.assertTrue(any(step.startswith("local-mean binarisation") for step in meta["transform"]["steps"]))
        text = (self.dir / "ocr" / "journal_page_01.txt").read_text().lower()
        self.assertIn("harbour", text)


if __name__ == "__main__":
    unittest.main()
