import tempfile
import unittest
from pathlib import Path

from journal_pipeline.hocr import clean_line_words, load_transcript, parse_alto, parse_hocr, parse_text

# What tesseract 5 actually emits (XHTML namespace, DOCTYPE, title properties).
HOCR = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
  <meta name='ocr-system' content='tesseract 5.5.1'/>
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='image "p.png"; bbox 0 0 1000 1400; ppageno 0; scan_res 300 300'>
   <div class='ocr_carea' id='block_1_1' title="bbox 100 100 900 160">
    <p class='ocr_par' id='par_1_1' lang='eng' title="bbox 100 100 900 160">
     <span class='ocr_line' id='line_1_1' title="bbox 100 100 400 140; baseline 0 -8; x_size 40; x_descenders 8; x_ascenders 10">
      <span class='ocrx_word' id='word_1_1' title='bbox 100 100 190 140; x_wconf 96'>Tuesday,</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 200 100 240 140; x_wconf 90'>14</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 250 100 400 140; x_wconf 92'>March</span>
     </span>
    </p>
   </div>
   <div class='ocr_carea' id='block_1_2' title="bbox 200 300 700 460">
    <p class='ocr_par' id='par_1_2' lang='eng' title="bbox 200 300 700 460">
     <span class='ocr_line' id='line_1_2' title="bbox 200 300 600 340">
      <span class='ocrx_word' id='word_1_4' title='bbox 200 300 300 340; x_wconf 88'>Rain</span>
      <span class='ocrx_word' id='word_1_5' title='bbox 310 300 350 340; x_wconf 91'>on</span>
      <span class='ocrx_word' id='word_1_6' title='bbox 360 300 420 340; x_wconf 93'>the</span>
      <span class='ocrx_word' id='word_1_7' title='bbox 430 300 600 340; x_wconf 89'>harbour</span>
     </span>
     <span class='ocr_line' id='line_1_3' title="bbox 200 360 700 400">
      <span class='ocrx_word' id='word_1_8' title='bbox 200 360 700 400; x_wconf 85'>the gulls &amp; scraps</span>
     </span>
     <span class='ocr_line' id='line_1_4' title="bbox 200 420 500 460">
      <span class='ocrx_word' id='word_1_9' title='bbox 200 420 500 460; x_wconf 40'><strong>cold</strong></span>
     </span>
     <span class='ocr_line' id='line_1_5' title="bbox 200 480 500 500">
      <span class='ocrx_word' id='word_1_10' title='bbox 200 480 500 500; x_wconf 95'> </span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""

ALTO = """<?xml version="1.0" encoding="UTF-8"?>
<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#">
  <Description><OCRProcessing ID="p"><ocrProcessingStep><processingSoftware>
    <softwareName>kraken</softwareName></processingSoftware></ocrProcessingStep></OCRProcessing></Description>
  <Layout><Page ID="p1" WIDTH="1000" HEIGHT="1400" PHYSICAL_IMG_NR="1"><PrintSpace>
    <TextBlock ID="b1" HPOS="100" VPOS="100" WIDTH="500" HEIGHT="200">
      <TextLine ID="l1" HPOS="100" VPOS="100" WIDTH="400" HEIGHT="40">
        <String ID="s1" CONTENT="Rain" HPOS="100" VPOS="100" WIDTH="80" HEIGHT="40" WC="0.91"/>
        <SP/>
        <String ID="s2" CONTENT="on" HPOS="190" VPOS="100" WIDTH="40" HEIGHT="40" WC="0.80"/>
      </TextLine>
      <TextLine ID="l2" HPOS="100" VPOS="160" WIDTH="400" HEIGHT="40">
        <String ID="s3" CONTENT="the harbour" HPOS="100" VPOS="160" WIDTH="300" HEIGHT="40"/>
      </TextLine>
    </TextBlock>
  </PrintSpace></Page></Layout>
</alto>
"""


class HocrTests(unittest.TestCase):
    def test_parse_structure(self):
        doc = parse_hocr(HOCR)
        self.assertEqual(doc.engine, "tesseract 5.5.1")
        self.assertEqual(len(doc.pages), 1)
        page = doc.pages[0]
        self.assertEqual(page.bbox, (0, 0, 1000, 1400))
        self.assertEqual(page.image, "p.png")
        lines = page.lines()
        # the whitespace-only line is dropped
        self.assertEqual([ln.text for ln in lines],
                         ["Tuesday, 14 March", "Rain on the harbour", "the gulls & scraps", "cold"])
        self.assertEqual([ln.n for ln in lines], [1, 2, 3, 4])
        self.assertEqual(lines[1].bbox, (200, 300, 600, 340))
        self.assertEqual(lines[1].conf, 90.2)
        self.assertEqual(lines[1].par_id, "par_1_2")
        self.assertEqual(lines[1].par_size, 3)
        self.assertEqual(lines[3].par_index, 2)
        self.assertEqual(lines[3].words[0].text, "cold")  # nested <strong> handled
        self.assertEqual(lines[3].conf, 40.0)

    def test_gap_before_is_relative_to_median_line_height(self):
        doc = parse_hocr(HOCR)
        lines = doc.lines()
        self.assertIsNone(lines[0].gap_before)
        # line 1 ends at y=140, line 2 starts at 300 -> gap 160 / median height 40 = 4.0
        self.assertEqual(lines[1].gap_before, 4.0)
        self.assertEqual(lines[2].gap_before, 0.5)

    def test_text_and_confidence(self):
        doc = parse_hocr(HOCR)
        self.assertEqual(doc.mean_confidence(), 84.9)  # (96+90+92+88+91+93+89+85+40)/9
        self.assertEqual(doc.text().split("\n")[0], "Tuesday, 14 March")

    def test_hocr_without_words(self):
        doc = parse_hocr("<div class='ocr_page'><span class='ocr_line' title='bbox 1 2 3 4'>plain line</span></div>")
        self.assertEqual(doc.lines()[0].text, "plain line")


class JunkCleanupTests(unittest.TestCase):
    def line(self, *words):
        body = "".join(f"<span class='ocrx_word' title='bbox 0 0 1 1; x_wconf {c}'>{t}</span>" for t, c in words)
        return parse_hocr(f"<div class='ocr_page'><span class='ocr_line'>{body}</span></div>").lines()[0]

    def test_ruled_line_artefacts_are_trimmed_from_edges(self):
        ln = self.line(("~~", 34), ("frost", 90), ("on", 96), ("the", 96), ("windshield", 96), ("0", 0), ("ST", 10))
        self.assertEqual(clean_line_words(ln), ("frost on the windshield", ["~~", "ST", "0"]))
        ln = self.line(("©", 19), ("a", 8), ("library", 8), ("card", 96), ("-", 0), (")", 0))
        self.assertEqual(clean_line_words(ln), ("a library card", ["©", ")", "-"]))

    def test_real_short_words_and_inner_tokens_survive(self):
        ln = self.line(("I", 20), ("am", 25), ("-", 5), ("here", 90), ("so", 10))
        self.assertEqual(clean_line_words(ln), ("I am - here so", []))
        ln = self.line(("~~", 0), ("--", 0))       # all junk: left for the line filters to reject
        self.assertEqual(clean_line_words(ln), ("~~ --", []))


class AltoAndTextTests(unittest.TestCase):
    def test_parse_alto(self):
        doc = parse_alto(ALTO)
        self.assertEqual(doc.engine, "kraken")
        self.assertEqual(doc.source_format, "alto")
        lines = doc.lines()
        self.assertEqual([ln.text for ln in lines], ["Rain on", "the harbour"])
        self.assertEqual(lines[0].bbox, (100, 100, 500, 140))
        self.assertEqual(lines[0].conf, 85.5)
        self.assertIsNone(lines[1].conf)
        self.assertEqual(doc.pages[0].bbox, (0, 0, 1000, 1400))

    def test_parse_text_paragraphs_and_pages(self):
        doc = parse_text("Date\n\nline one\nline two\n\f\nnext page\n")
        self.assertEqual(len(doc.pages), 2)
        pars = doc.pages[0].paragraphs()
        self.assertEqual([[ln.text for ln in p.lines] for p in pars], [["Date"], ["line one", "line two"]])
        self.assertEqual(doc.pages[1].lines()[0].text, "next page")
        self.assertEqual(doc.lines()[1].par_size, 2)

    def test_load_transcript_sniffs_format(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "a.hocr").write_text(HOCR, encoding="utf-8")
            (d / "b.xml").write_text(ALTO, encoding="utf-8")
            (d / "c.txt").write_text("just text\n", encoding="utf-8")
            (d / "d.html").write_text(HOCR, encoding="utf-8")
            self.assertEqual(load_transcript(d / "a.hocr").source_format, "hocr")
            self.assertEqual(load_transcript(d / "b.xml").source_format, "alto")
            self.assertEqual(load_transcript(d / "c.txt").source_format, "text")
            self.assertEqual(load_transcript(d / "d.html").source_format, "hocr")
            self.assertEqual(load_transcript(d / "c.txt").source_path, str(d / "c.txt"))


if __name__ == "__main__":
    unittest.main()
