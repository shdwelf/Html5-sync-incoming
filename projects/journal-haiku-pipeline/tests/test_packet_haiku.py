import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from journal_pipeline.haiku import Options, extract_haikus, haikus_to_xml, is_date_like
from journal_pipeline.hocr import parse_hocr, parse_text
from journal_pipeline.packet import build_packet, packet_plain_text, read_packet, write_packet

# A page laid out like a journal: date, wrapped prose (full width), an indented
# 3-line stanza, more prose, a stanza with an OCR slip, and a page number.
PAGE_W = 1700


def hocr_page(paragraphs):
    """paragraphs: list of lists of (text, x0, width) -> minimal hOCR text."""
    y = 100
    out = ["<html xmlns='http://www.w3.org/1999/xhtml'><body>",
           f"<div class='ocr_page' id='page_1' title='bbox 0 0 {PAGE_W} 2200'>"]
    pi = li = wi = 0
    for par in paragraphs:
        pi += 1
        out.append(f"<div class='ocr_carea' id='block_1_{pi}'><p class='ocr_par' id='par_1_{pi}'>")
        for text, x0, width in par:
            li += 1
            out.append(f"<span class='ocr_line' id='line_1_{li}' title='bbox {x0} {y} {x0 + width} {y + 40}'>")
            x = x0
            step = max(1, width // max(1, len(text.split())))
            for w in text.split():
                wi += 1
                out.append(f"<span class='ocrx_word' id='word_1_{wi}' title='bbox {x} {y} {x + step - 5} {y + 40}; x_wconf 91'>{w}</span>")
                x += step
            out.append("</span>")
            y += 60
        out.append("</p></div>")
        y += 60  # paragraph gap
    out.append("</div></body></html>")
    return "\n".join(out)


JOURNAL = [
    [("Tuesday, 14 March 2023", 150, 600)],
    [("Rain again this morning. Walked down to the harbour before work", 150, 1380),
     ("and watched the fishing boats come in. The gulls were louder than", 150, 1380),
     ("usual, and the coffee from the kiosk was terrible, as always. Still, I", 150, 1380),
     ("felt lighter than I have all week.", 150, 650)],
    [("Rain on the harbour", 280, 420),
     ("the gulls argue over scraps", 280, 560),
     ("my coffee goes cold", 280, 400)],
    [("Spent the afternoon sorting through Dad's boxes in the garage.", 150, 1300),
     ("Found the old brass compass he carried in the war, wrapped in a", 150, 1380),
     ("handkerchief. It still points north.", 150, 700)],
    [("the old brass compass", 280, 450),
     ("still finds north in my palm now", 280, 650),
     ("fathers steady hand", 280, 420)],          # OCR dropped the apostrophe
    [("42", 800, 60)],
]


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.doc = parse_hocr(hocr_page(JOURNAL))
        self.provenance = {
            "source": {"path": "/scans/p1.jpg", "uri": "file:///scans/p1.jpg", "sha256": "a" * 64,
                       "mime": "image/jpeg", "last_modified": "2023-03-14T08:12:44Z"},
            "master": {"path": "/out/p1.png", "sha256": "b" * 64, "mime": "image/png", "width": 1700, "height": 2200},
            "xena": {"path": "/out/p1.xena", "sha256": "c" * 64, "wrapper": "Default Package Wrapper",
                     "payload_element": "png:png"},
            "exif": {"Make": "Apple", "Model": "iPhone", "Exif": {"DateTimeOriginal": "2023:03:14 08:12:44"}},
        }
        self.ocr_meta = {"engine": "tesseract 5.5.1", "backend": "cli",
                         "options": {"lang": "eng", "psm": 6, "profile": "handwriting"},
                         "transform": {"scale": 2.0, "border": 20, "steps": ["grayscale", "upscale x2.00"]}}

    def test_packet_structure_and_coordinate_mapping(self):
        root = build_packet(self.doc, provenance=self.provenance, ocr_meta=self.ocr_meta, transcript_path="/out/p1.hocr")
        self.assertEqual(root.tag, "pipeline_packet")
        self.assertEqual([c.tag for c in root], ["preservation_source", "ocr", "ocr_transcript"])
        ps = root.find("preservation_source")
        self.assertEqual(ps.find("xena_file").text, "/out/p1.xena")
        self.assertEqual(ps.find("master_file").get("sha256"), "b" * 64)
        self.assertEqual(ps.find("captured").text, "2023:03:14 08:12:44")
        self.assertEqual(ps.find("camera").text, "Apple iPhone")
        ocr = root.find("ocr")
        self.assertEqual(ocr.get("engine"), "tesseract 5.5.1")
        self.assertEqual(ocr.get("psm"), "6")
        self.assertEqual(ocr.get("coordinate_space"), "master")
        self.assertEqual(ocr.get("mean_word_confidence"), "91.0")
        page = root.find("ocr_transcript/page")
        self.assertEqual((page.get("width"), page.get("height")), ("1700", "2200"))
        first = page.find("paragraph/line")
        # hOCR bbox 150 100 750 140 in the 2x + 20px-border working image -> (65, 40, 365, 60) on the master
        self.assertEqual(first.get("bbox"), "65 40 365 60")
        self.assertEqual(first.text, "Tuesday, 14 March 2023")
        self.assertEqual(root.find("ocr_transcript").get("lines"), "15")

    def test_edge_junk_is_trimmed_and_kept_in_raw(self):
        hocr = hocr_page([[("~~ Rain on the harbour ST", 280, 500)]]).replace(">~~<", " title='x_wconf 10'>~~<")
        hocr = hocr.replace("title='bbox 280 100 335 140; x_wconf 91'>~~", "title='bbox 280 100 335 140; x_wconf 10'>~~")
        hocr = hocr.replace("x_wconf 91'>ST", "x_wconf 5'>ST")
        root = build_packet(parse_hocr(hocr))
        line = root.find("ocr_transcript/page/paragraph/line")
        self.assertEqual(line.text, "Rain on the harbour")
        self.assertEqual(line.get("raw"), "~~ Rain on the harbour ST")
        untrimmed = build_packet(parse_hocr(hocr), clean_edges=False).find("ocr_transcript/page/paragraph/line")
        self.assertEqual(untrimmed.text, "~~ Rain on the harbour ST")
        self.assertIsNone(untrimmed.get("raw"))

    def test_packet_without_metadata_is_still_valid(self):
        root = build_packet(parse_text("just a line\n"))
        self.assertEqual(root.find("ocr_transcript/page/paragraph/line").text, "just a line")
        self.assertIsNone(root.find("ocr").get("coordinate_space"))

    def test_illegal_xml_characters_are_stripped(self):
        doc = parse_text("bad \x0b char \x01 here\n")  # \f would be a page break
        root = build_packet(doc)
        with tempfile.TemporaryDirectory() as td:
            path = write_packet(root, Path(td) / "p.packet.xml")
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
            ET.fromstring(text)  # must re-parse
            self.assertIn("bad char here", text)

    def test_write_and_read_roundtrip(self):
        root = build_packet(self.doc, provenance=self.provenance, ocr_meta=self.ocr_meta)
        with tempfile.TemporaryDirectory() as td:
            path = write_packet(root, Path(td) / "p.packet.xml")
            packet = read_packet(path)
        self.assertEqual(len(packet.paragraphs), 6)
        lines = packet.lines()
        self.assertEqual(lines[5].text, "Rain on the harbour")
        self.assertEqual(lines[5].par_size, 3)
        self.assertEqual(lines[5].conf, 91.0)
        self.assertEqual(packet.preservation["master_file"]["sha256"], "b" * 64)
        self.assertEqual(packet.ocr["engine"], "tesseract 5.5.1")
        self.assertIn("[line_1_6] Rain on the harbour", packet_plain_text(packet))


class HaikuDetectionTests(unittest.TestCase):
    def packet(self, paragraphs=JOURNAL, provenance=None):
        doc = parse_hocr(hocr_page(paragraphs))
        root = build_packet(doc, provenance=provenance)
        with tempfile.TemporaryDirectory() as td:
            path = write_packet(root, Path(td) / "p.packet.xml")
            return read_packet(path)

    def test_finds_both_stanzas_and_nothing_else(self):
        result = extract_haikus(self.packet(), Options(include_rejected=True))
        self.assertEqual(len(result["haikus"]), 2)
        first, second = result["haikus"]
        self.assertEqual(first["lines"], ["Rain on the harbour", "the gulls argue over scraps", "my coffee goes cold"])
        self.assertEqual(first["syllables"], [5, 7, 5])
        self.assertEqual(first["validation"], "exact")
        self.assertEqual(first["form"], "5-7-5")
        self.assertEqual(first["confidence"], "high")
        self.assertIn("isolated 3-line stanza", first["notes"])
        self.assertEqual(first["source"]["line_ids"], ["line_1_6", "line_1_7", "line_1_8"])
        self.assertEqual(first["source"]["bbox"], [280, 520, 840, 680])
        self.assertEqual(first["explanation"][0], "Rain(1) on(1) the(1) harbour(2) = 5")
        self.assertEqual(second["source"]["line_ids"], ["line_1_12", "line_1_13", "line_1_14"])
        self.assertEqual(second["validation"], "exact")
        # prose lines, the date and the page number never make it in
        excluded = {e["id"]: e["reasons"] for e in result["lines_excluded"]}
        self.assertIn("date/time", excluded["line_1_1"])
        self.assertIn("page number", excluded["line_1_15"])
        self.assertTrue(any("prose" in r for r in excluded["line_1_2"]))

    def test_tolerance_and_rejection(self):
        page = [[("a late frost, late spring", 280, 500),          # 5
                 ("the kettle takes its own time", 280, 600),     # 7
                 ("so do I, so do I", 280, 400)]]                 # 6  -> off by one
        result = extract_haikus(self.packet(page))
        self.assertEqual(len(result["haikus"]), 1)
        self.assertEqual(result["haikus"][0]["form"], "5-7-5 (approximate)")
        self.assertEqual(result["haikus"][0]["deviation"], 1)
        strict = extract_haikus(self.packet(page), Options(tolerance_per_line=0, tolerance_total=0, include_free_form=False))
        self.assertEqual(strict["haikus"], [])

    def test_free_form_only_when_isolated(self):
        stanza = [("one cold morning", 280, 300), ("the letter arrives", 280, 350), ("unopened", 280, 200)]  # 4-5-3
        result = extract_haikus(self.packet([stanza]))
        self.assertEqual(len(result["haikus"]), 1)
        self.assertEqual(result["haikus"][0]["form"], "free-form 3-line")
        # same lines buried inside a longer paragraph: not reported
        buried = [[("Went to the shops and thought about the letter all day long", 150, 1380)] + stanza
                  + [("and then the phone rang and it was Maria again about the house", 150, 1380)]]
        self.assertEqual(extract_haikus(self.packet(buried))["haikus"], [])
        self.assertEqual(extract_haikus(self.packet([stanza]), Options(include_free_form=False))["haikus"], [])

    def test_prose_that_happens_to_scan_is_penalised(self):
        # three consecutive full-width lines inside a 6-line paragraph with 5/7/5 syllables
        page = [[("I went to the shop", 150, 1380),
                 ("and bought some bread and milk", 150, 1380),
                 ("then I walked back home", 150, 1380),
                 ("The phone rang twice while I was out and I did not hear it", 150, 1380),
                 ("so I missed the call from the doctor about the test results", 150, 1380),
                 ("which is probably fine, they would have said if it was urgent.", 150, 1380)]]
        result = extract_haikus(self.packet(page), Options(include_rejected=True))
        self.assertEqual(result["haikus"], [])
        self.assertTrue(result["candidates_rejected"])
        self.assertLess(result["candidates_rejected"][0]["score"], 0.5)

    def test_low_confidence_lines_are_ignored(self):
        page = hocr_page([[("Rain on the harbour", 280, 420), ("the gulls argue over scraps", 280, 560),
                           ("my coffee goes cold", 280, 400)]]).replace("x_wconf 91", "x_wconf 10")
        doc = parse_hocr(page)
        with tempfile.TemporaryDirectory() as td:
            packet = read_packet(write_packet(build_packet(doc), Path(td) / "p.xml"))
        self.assertEqual(extract_haikus(packet)["haikus"], [])
        self.assertEqual(len(extract_haikus(packet, Options(min_confidence=0))["haikus"]), 1)

    def test_text_transcript_without_layout_still_works(self):
        doc = parse_text("Tuesday, 14 March 2023\n\nRain on the harbour\nthe gulls argue over scraps\nmy coffee goes cold\n\n"
                         "Note to self: buy stamps before Friday and call the plumber.\n")
        with tempfile.TemporaryDirectory() as td:
            packet = read_packet(write_packet(build_packet(doc), Path(td) / "p.xml"))
        result = extract_haikus(packet)
        self.assertEqual(len(result["haikus"]), 1)
        self.assertIsNone(result["haikus"][0]["source"]["bbox"])

    def test_xml_output(self):
        result = extract_haikus(self.packet())
        xml = haikus_to_xml(result)
        root = ET.fromstring(xml)
        self.assertEqual(len(root.findall("haiku")), 2)
        line = root.find("haiku/line")
        self.assertEqual(line.get("syllables"), "5")
        self.assertEqual(line.get("source"), "line_1_6")

    def test_date_detection(self):
        for s in ("Tuesday, 14 March 2023", "14/03/2023", "March 14", "3rd of June", "2023-03-14", "Wed", "1999", "7:45 am"):
            self.assertTrue(is_date_like(s), s)
        for s in ("Rain on the harbour", "ten minutes of dawn", "may the wind be kind"):
            self.assertFalse(is_date_like(s), s)


if __name__ == "__main__":
    unittest.main()
