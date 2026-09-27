import base64
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from journal_pipeline.preserve import (
    BINARY_NS, PNG_NS, PreservationError, preserve_image, read_xena_meta, sha256_file, unwrap_xena,
)


def make_jpeg(path: Path, orientation: int = 1, size=(120, 80)) -> None:
    img = Image.new("RGB", size, (250, 250, 240))
    for x in range(10, 40):
        for y in range(10, 20):
            img.putpixel((x, y), (20, 20, 30))
    exif = Image.Exif()
    exif[0x0112] = orientation
    exif[0x010F] = "TestCam"
    exif[0x0110] = "Model X"
    exif[0x0132] = "2023:03:14 08:12:44"
    img.save(path, format="JPEG", quality=95, exif=exif.tobytes(), dpi=(300, 300))


class PreserveTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)
        self.src = self.dir / "IMG_0001.jpg"
        make_jpeg(self.src)

    def tearDown(self):
        self._td.cleanup()

    def test_png_master_and_xena_envelope(self):
        res = preserve_image(self.src, self.dir / "out", master_format="png")
        master = Path(res.master)
        self.assertEqual(master.name, "IMG_0001.png")
        self.assertEqual(res.sha256_master, sha256_file(master))
        with Image.open(master) as im:
            self.assertEqual(im.format, "PNG")
            self.assertEqual(im.size, (120, 80))
            dpi = im.info.get("dpi")
            self.assertAlmostEqual(dpi[0], 300, delta=0.01)  # PNG pHYs is in px/metre

        root = ET.parse(res.xena).getroot()
        self.assertEqual(root.tag, "xena")
        self.assertEqual([c.tag for c in root], ["meta_data", "content"])
        meta = root.find("meta_data")
        self.assertEqual([c.tag for c in meta], ["meta_data_wrapper_name", "normaliser_name", "input_source_uri"])
        self.assertEqual(meta.find("meta_data_wrapper_name").text, "Default Package Wrapper")
        self.assertEqual(meta.find("input_source_uri").text, self.src.resolve().as_uri())
        payload = root.find("content")[0]
        self.assertEqual(payload.tag, f"{{{PNG_NS}}}png")
        self.assertEqual(payload.get(f"{{{PNG_NS}}}extension"), "png")
        self.assertIn("ISO Standard 15948", payload.get(f"{{{PNG_NS}}}description"))
        # base64 is line-wrapped at 76 columns and decodes to the master byte-for-byte
        text_lines = [ln for ln in payload.text.splitlines() if ln]
        self.assertTrue(all(len(ln) <= 76 for ln in text_lines))
        self.assertEqual(base64.b64decode("".join(text_lines)), master.read_bytes())

        prov = json.loads(Path(res.provenance).read_text())
        self.assertEqual(prov["source"]["sha256"], sha256_file(self.src))
        self.assertEqual(prov["master"]["sha256"], res.sha256_master)
        self.assertEqual(prov["xena"]["payload_sha256"], res.sha256_master)
        self.assertEqual(prov["exif"]["Make"], "TestCam")
        self.assertEqual(prov["exif"]["DateTime"], "2023:03:14 08:12:44")
        self.assertIsNone(res.orientation_applied)

    def test_tiff_master_is_uncompressed_and_uses_binary_object(self):
        res = preserve_image(self.src, self.dir / "out", master_format="tiff")
        master = Path(res.master)
        self.assertEqual(master.suffix, ".tif")
        with Image.open(master) as im:
            self.assertEqual(im.format, "TIFF")
            self.assertEqual(im.info.get("compression"), "raw")
        root = ET.parse(res.xena).getroot()
        payload = root.find("content")[0]
        self.assertEqual(payload.tag, f"{{{BINARY_NS}}}binary-object")
        self.assertEqual(payload.get(f"{{{BINARY_NS}}}extension"), "tif")
        meta = read_xena_meta(res.xena)
        self.assertEqual(meta["payload_element"], "binary-object")
        self.assertEqual(meta["payload_namespace"], BINARY_NS)

    def test_exif_orientation_is_applied_and_recorded(self):
        rotated = self.dir / "IMG_0002.jpg"
        make_jpeg(rotated, orientation=6)  # 90° CW needed
        res = preserve_image(rotated, self.dir / "out")
        self.assertEqual(res.orientation_applied, 6)
        self.assertEqual((res.width, res.height), (80, 120))
        res2 = preserve_image(rotated, self.dir / "out2", apply_exif_orientation=False)
        self.assertIsNone(res2.orientation_applied)
        self.assertEqual((res2.width, res2.height), (120, 80))

    def test_unwrap_roundtrip_and_checksum(self):
        res = preserve_image(self.src, self.dir / "out")
        info = unwrap_xena(res.xena, self.dir / "back.png", expected_sha256=res.sha256_master)
        self.assertEqual(info["sha256"], res.sha256_master)
        self.assertEqual((self.dir / "back.png").read_bytes(), Path(res.master).read_bytes())
        with self.assertRaises(PreservationError):
            unwrap_xena(res.xena, self.dir / "back2.png", expected_sha256="0" * 64)

    def test_mode_conversion_warning(self):
        cmyk = self.dir / "cmyk.jpg"
        Image.new("CMYK", (30, 30), (0, 0, 0, 0)).save(cmyk, format="JPEG")
        res = preserve_image(cmyk, self.dir / "out")
        self.assertEqual(res.mode, "RGB")
        self.assertTrue(any("CMYK" in w for w in res.warnings))

    def test_unreadable_input(self):
        bad = self.dir / "bad.jpg"
        bad.write_bytes(b"not an image")
        with self.assertRaises(PreservationError):
            preserve_image(bad, self.dir / "out")


if __name__ == "__main__":
    unittest.main()
