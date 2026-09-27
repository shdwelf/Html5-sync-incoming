"""journal-haiku-pipeline — journal photos -> Xena preservation envelope -> OCR -> haiku extraction.

Four stages, each usable on its own from the CLI (``python3 -m journal_pipeline``):

1. ``preserve``  normalise an image to a lossless master (PNG, or uncompressed TIFF)
                 and wrap it in a Xena "Default Package Wrapper" XML envelope.
2. ``ocr``       run Tesseract (CLI or ``tesserocr``) and keep the hOCR layout output.
3. ``packet``    merge preservation metadata + transcript into one clean XML packet.
4. ``extract``   find haikus — offline syllable heuristics, and/or an LLM.

``run`` executes all four in sequence over a directory of images.
"""

__version__ = "1.0.0"
TOOL_NAME = "journal-haiku-pipeline"
