# journal-haiku-pipeline — journal photos → Xena archive → hOCR → XML packet → haikus

A command-line pipeline that takes photographs or scans of journal pages and

1. **preserves** each one as a lossless master wrapped in a Xena XML envelope
   (with SHA-256 fixity and a provenance sidecar),
2. **OCRs** it with Tesseract, keeping the hOCR layout output,
3. **packs** transcript + preservation metadata into one clean, AI-ready XML
   packet per page, and
4. **extracts the haikus** — offline by default (layout + syllable heuristics
   with an audit trail), or through an LLM (OpenAI-compatible or Anthropic API)
   whose answers are re-validated locally.

Python 3.9+, standard library + [Pillow](https://pypi.org/project/Pillow/).
Tesseract is used through the `tesseract` executable **or** the `tesserocr`
wheel; if neither is present you can still run everything else on transcripts
produced by another tool. No network access or API key is needed unless you
opt into the LLM step.

```bash
pip install -r requirements.txt          # Pillow (+ uncomment tesserocr / cmudict if you want them)
python3 -m journal_pipeline doctor       # what is available on this machine?

python3 -m journal_pipeline make-sample -o sample/         # two synthetic pages to try it on
python3 -m journal_pipeline run sample/ -o out/            # all four steps
cat out/haikus.md
```

The `run` command prints one line per stage and per page:

```
[1/4 preserve] journal_page_01.jpg: journal_page_01.png + journal_page_01.xena
[2/4 ocr]      journal_page_01.jpg: journal_page_01.hocr (tesseract 5.5.1, tesserocr)
[3/4 packet]   journal_page_01.jpg: journal_page_01.packet.xml (16 lines, conf 91.2)
[4/4 extract]  journal_page_01.jpg: 2 haiku(s)
               Rain on the harbour / the gulls argue over scraps / my coffee goes cold
               the old brass compass / still finds north in my palm now / father's steady hand
```

## Output layout

```
out/
  manifest.json                 every page, every file, every haiku (both engines)
  haikus.json                   flat list of all haikus with sources
  haikus.md                     human-readable digest with syllable working
  journal_page_01/
    journal_page_01.png         lossless master (or .tif with --master tiff)
    journal_page_01.xena        Xena envelope: metadata + base64 payload
    journal_page_01.provenance.json   checksums, EXIF, tool versions, warnings
    journal_page_01.ocr-input.png     the preprocessed image Tesseract actually saw
    journal_page_01.hocr        Tesseract hOCR (bounding boxes, confidences)
    journal_page_01.txt         plain text from the same run
    journal_page_01.ocr.json    engine, options, coordinate transform
    journal_page_01.packet.xml  step 3 — the AI-ready packet
    journal_page_01.haikus.json step 4 — heuristic result (or .xml with --format xml)
    journal_page_01.haikus.llm.json   only with --llm
```

## The four steps in detail

### 1. Preservation (`preserve`)

* Opens the image with Pillow, applies the EXIF orientation tag to the pixels
  (phones store portrait shots rotated) and records that it did so.
* Writes a **PNG** master by default — that is what the real Xena software
  produces for raster images. `--master tiff` writes an **uncompressed baseline
  TIFF** instead, for policies that require it. Either way the pixels are
  re-read and compared with the source before anything else happens.
* Wraps the master in a `.xena` file using the layout of Xena's *Default
  Package Wrapper* ([spec](https://sourceforge.net/p/xena/wiki/Default_package_wrapper/)):

  ```xml
  <xena>
    <meta_data>
      <meta_data_wrapper_name>Default Package Wrapper</meta_data_wrapper_name>
      <normaliser_name>journal-haiku-pipeline.preserve.PillowToPngNormaliser/1.0.0</normaliser_name>
      <input_source_uri>file:///scans/IMG_0001.jpg</input_source_uri>
    </meta_data>
    <content>
      <png:png xmlns:png="http://preservation.naa.gov.au/png/1.0"
               png:description="The following data represents a Base64 encoding of a PNG image file ( ISO Standard 15948 )."
               png:extension="png">iVBORw0KGgo...</png:png>
    </content>
  </xena>
  ```

  TIFF payloads use Xena's generic `binary-object` schema, because Xena has no
  TIFF schema. `unwrap` decodes a `.xena` back to the binary file and checks
  its SHA-256 against the sidecar.
* Because the wrapper's `meta_data` block is a fixed three-element sequence,
  everything else (source/master/envelope checksums and sizes, full EXIF and
  GPS, ICC/DPI, tool versions, warnings) goes in `<stem>.provenance.json` and
  is repeated inside the step-3 packet.

### 2. OCR (`ocr`)

Runs Tesseract with hOCR + text output, equivalent to
`tesseract page.png page -l eng --psm 6 hocr txt`, via whichever backend is
present (`--backend cli|tesserocr|auto`). Before OCR the page is prepared for
what the LSTM models were trained on — dark print on white at ~300 dpi:

| profile (`--profile`) | psm | oem | preprocessing |
|---|---|---|---|
| `print` (default) | 3 automatic layout | default | greyscale → autocontrast → upscale to ≥ 2000 px wide → white border |
| `handwriting` | 6 single block | 1 LSTM only | greyscale → upscale to ≥ 2600 px → local-mean binarisation (`--binarize-offset`, default 35) → border |
| `none` | 3 | default | nothing — you preprocessed already |

Every flag can be overridden individually (`--psm`, `--oem`, `--lang eng+fra`,
`--dpi`, `--user-words names.txt`, `-c preserve_interword_spaces=1`, …). The
scale factor and border are stored in `<stem>.ocr.json` so step 3 can map hOCR
coordinates back onto the preservation master.

### 3. Packet (`packet`)

Parses the hOCR with the standard-library HTML parser (Tesseract writes XHTML
with a DOCTYPE; class-name matching works for any engine's hOCR), keeps the
page → block → paragraph → line → word tree, and writes:

```xml
<pipeline_packet version="1.0" generated="…" tool="journal-haiku-pipeline/1.0.0">
  <preservation_source>
    <xena_file sha256="…" wrapper="Default Package Wrapper" payload_element="png:png">/out/p1/p1.xena</xena_file>
    <master_file format="image/png" sha256="…" width="3024" height="4032">/out/p1/p1.png</master_file>
    <original_file format="image/jpeg" sha256="…" last_modified="…">/scans/IMG_0001.jpg</original_file>
    <input_source_uri>file:///scans/IMG_0001.jpg</input_source_uri>
    <captured>2023:03:14 08:12:44</captured>
    <camera>Apple iPhone 13</camera>
  </preservation_source>
  <ocr engine="tesseract 5.5.1" backend="cli" lang="eng" psm="6" profile="handwriting"
       transcript_file="…/p1.hocr" transcript_format="hocr" mean_word_confidence="87.2" coordinate_space="master">
    <preprocessing scale="1.3" border="24">grayscale; upscale x1.30 (LANCZOS); …</preprocessing>
  </ocr>
  <ocr_transcript pages="1" lines="16">
    <page n="1" width="3024" height="4032">
      <paragraph id="par_1_3" block="block_1_3" bbox="278 537 833 700">
        <line id="line_1_6" n="6" bbox="280 537 690 570" conf="91.8" words="4" gap_before="1.84">Rain on the harbour</line>
        <line id="line_1_7" n="7" bbox="278 598 833 642" conf="91.2" words="5" gap_before="0.65">the gulls argue over scraps</line>
        <line id="line_1_8" n="8" bbox="278 661 679 700" conf="91.0" words="4" gap_before="0.45">my coffee goes cold</line>
      </paragraph>
      …
```

Each `<line>` is one physical line; paragraphs are the blank-space breaks the
layout analysis found; `gap_before` is the vertical gap in line-heights. Junk
tokens that ruled paper and margins produce (`~~`, `©`, `-`, `EE`, `0` with
low confidence at a line's ends) are trimmed and the untouched text kept in
`raw="…"`. Text is scrubbed of characters illegal in XML and escaped
properly. `packet` also accepts **ALTO XML** and **plain text** transcripts
from other engines.

### 4. Haiku extraction (`extract`)

**Heuristic engine (default, offline).** Every run of three consecutive lines
on a page is a candidate. Lines that are dates/times, page numbers, headings,
mostly digits/punctuation, over 10 words, or below the OCR-confidence floor
can never be part of one. Candidates are scored on

* the **5-7-5 fit** — syllables are counted per word as a *(min, max)* range
  (`fire` = 1–2, `every` = 2–3, `2023` = 5–6), and a line matches when the
  target lies in its range; `--tolerance 1 --tolerance-total 2` allow the
  usual off-by-one slack (OCR drops letters, English is ambiguous);
* the **layout** — an isolated 3-line stanza scores high, lines much narrower
  than the prose column score higher, three lines buried in a long paragraph
  or spanning the full page width score low;
* **hygiene** — sentence breaks inside a line, 9+ words, low OCR confidence.

Isolated three-line stanzas that are not 5-7-5 but short (≤ 17 syllables) are
reported as `free-form 3-line` (disable with `--no-free-form`). Every accepted
haiku carries its per-word syllable working, the reasons for its score, its
source line ids, bounding box and OCR confidence:

```json
{
  "form": "5-7-5", "validation": "exact", "score": 1.0, "confidence": "high",
  "lines": ["Rain on the harbour", "the gulls argue over scraps", "my coffee goes cold"],
  "syllables": [5, 7, 5], "syllable_ranges": [[5, 5], [7, 7], [5, 5]],
  "explanation": ["Rain(1) on(1) the(1) harbour(2) = 5", "the(1) gulls(1) argue(2) over(2) scraps(1) = 7", "my(1) coffee(2) goes(1) cold(1) = 5"],
  "notes": ["isolated 3-line stanza", "narrow lines (max 41% of page text width)", "blank space before", "blank space after"],
  "source": {"page": 1, "line_ids": ["line_1_6", "line_1_7", "line_1_8"], "bbox": [278, 537, 833, 700], "ocr_confidence": 91.3}
}
```

Syllables come from the CMU Pronouncing Dictionary when `cmudict` is installed
(`pip install cmudict`; all pronunciations → range) and otherwise from a
rule engine (vowel groups, silent-e, `-le`/`-ed`/`-es` endings, diphthong
splits, compounds, numbers, contractions, an exception table) that agrees
with CMU on ~94 % of random dictionary entries and better on everyday words.
`--include-rejected` lists the near-misses and why each line was excluded.

**LLM engine (optional).** `--llm openai` / `--llm anthropic` (on `run`) or
`--engine openai|anthropic` (on `extract`) sends the packet with the system
prompt in [`journal_pipeline/prompt.py`](journal_pipeline/prompt.py) — locate
haikus, ignore prose/dates, correct obvious OCR slips but never invent lines,
show syllable working, cite `line` ids, answer as JSON. Keys come from
`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`; `--base-url http://localhost:11434/v1`
points the OpenAI provider at Ollama, LM Studio, vLLM, llama.cpp (no key
needed for localhost). Each returned haiku is **re-validated locally**: syllables
are recounted, line ids resolved against the packet, OCR corrections diffed,
and `model_local_agree` records whether the model's count and ours match.
`--dry-run` writes the exact request without sending it; `prompt` prints the
system prompt + packet to paste into any chat UI by hand.

## Step-by-step invocation

```bash
python3 -m journal_pipeline preserve scans/ -o out/pres --master tiff
python3 -m journal_pipeline ocr out/pres/IMG_0001.tif -o out/ocr --profile handwriting --lang eng
python3 -m journal_pipeline packet --transcript out/ocr/IMG_0001.hocr \
        --provenance out/pres/IMG_0001.provenance.json --ocr-meta out/ocr/IMG_0001.ocr.json \
        -o out/IMG_0001.packet.xml
python3 -m journal_pipeline extract out/IMG_0001.packet.xml --include-rejected
python3 -m journal_pipeline extract out/IMG_0001.packet.xml --engine anthropic -o out/IMG_0001.haikus.llm.json
python3 -m journal_pipeline unwrap out/pres/IMG_0001.xena -o IMG_0001.restored.tif
```

## Tesseract and handwriting — what to expect, what to configure

Be realistic first: **Tesseract is a print OCR engine.** Its LSTM models were
trained on typeset text. On neat, well-separated block capitals or careful
print-style handwriting with 300 dpi scans you can get usable output (with
errors); on joined cursive it degrades to near-random words, no matter how it
is configured. Nothing in `--psm`/`--oem` land changes that — those are the
knobs for *layout* and *engine choice*, not for script style.

What does help, in order of impact:

1. **Image quality.** Scan or photograph flat, evenly lit, 300–400 dpi
   (a phone photo of an A5 page is 2500–4000 px wide — fine). The
   `handwriting` profile's local-mean binarisation removes shadows, paper
   texture and faint ruling; lower `--binarize-offset` (e.g. 20) for faint
   pencil, raise it (50) for heavy bleed-through.
2. **Segmentation.** `--psm 6` (one uniform block) for a single column of
   handwriting; `--psm 4` if lines vary a lot in length; `--psm 3` when the page
   mixes stanzas and prose blocks and you want paragraph breaks preserved (the
   heuristic detector uses those breaks — try both and compare `haikus.md`).
3. **Engine.** `--oem 1` (LSTM only). The legacy engine is hopeless here.
4. **Language data.** Use the `tessdata_best` `eng.traineddata` (float model,
   most accurate, slower) rather than `tessdata_fast`. Put it in a folder and
   pass `--tessdata-dir DIR` or set `TESSDATA_PREFIX`. Sources:
   `https://github.com/tesseract-ocr/tessdata_best`, or on Debian/Ubuntu
   `apt install tesseract-ocr-eng` puts it in `/usr/share/tesseract-ocr/5/tessdata`.
   The tool also looks in `~/.local/share/tessdata` and the usual system paths.
5. **Vocabulary.** `--user-words words.txt` with names, places and recurring
   words from the journal biases the beam search toward them; `-c
   preserve_interword_spaces=1` keeps spacing; `-c tessedit_char_blacklist=|~`
   drops symbols that ruled paper tends to produce.
6. **Fine-tuning** a Tesseract model on a few hundred lines of *this* writer's
   hand (`tesstrain`) is the real fix within the Tesseract world; it is a
   day's work and beyond this tool's scope.

If the journal is cursive, the effective route is a handwriting engine and
then this pipeline for everything around it: **Transkribus** or
**eScriptorium/Kraken** (export ALTO or hOCR), **TrOCR** (Hugging Face,
line-level), Google Document AI / Azure AI Vision / AWS Textract (they return
words with boxes; write them as plain text or hOCR). Feed the result in with

```bash
python3 -m journal_pipeline run scans/ -o out/ --transcripts transcripts/
```

where `transcripts/<image stem>.hocr|.xml|.txt` exists for each page — those
pages skip Tesseract and still get the Xena envelope, packet and extraction.
Plain-text transcripts should keep a blank line between paragraphs/stanzas;
the detector works without coordinates but is better with them.

### Installing a backend

| Platform | Command |
|---|---|
| Debian/Ubuntu | `sudo apt install tesseract-ocr tesseract-ocr-eng` |
| macOS | `brew install tesseract` |
| Windows | UB-Mannheim installer, then set `TESSERACT_CMD` if it is not on `PATH` |
| no root / no package manager | `pip install tesserocr` (wheels bundle libtesseract on Linux and macOS), then download `eng.traineddata` into a folder and pass `--tessdata-dir` |

## Tests

```bash
cd projects/journal-haiku-pipeline
python3 -m unittest discover -v
```

51 tests: syllable engine, hOCR/ALTO/text parsing, Xena envelope round-trip,
EXIF orientation, TIFF/PNG masters, packet building and coordinate mapping,
haiku scoring on synthetic layouts, LLM request/response handling with a fake
transport, and the CLI end to end. Two tests run real Tesseract on generated
pages and are skipped when no backend with English data is available.

## Limitations

* One page per image; multi-page TIFF/PDF input is not split (first frame only).
* Syllable counting is English-only. The rule engine is a heuristic; where it
  matters, install `cmudict`, and treat `approximate` results as "look at the
  page".
* The heuristic detector is tuned for haikus written as their own stanza. A
  haiku written inline inside a prose paragraph will be scored low; use the
  LLM engine or `--include-rejected` for those.
* Xena envelopes here follow the documented Default Package Wrapper; they are
  not produced by the Xena Java application itself and carry no NAA
  `naa:wrapper` metadata.
