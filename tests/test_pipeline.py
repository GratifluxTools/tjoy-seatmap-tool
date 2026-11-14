import os
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tjoy_seatmap.pipeline import attach_official, load_screens, write_outputs, self_check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "sample", "sample.har")


class PipelineTests(unittest.TestCase):
    def test_load_sample(self):
        res = load_screens([SAMPLE])
        self.assertEqual(len(res.items), 1)
        it = res.items[0]
        self.assertEqual(it.screen.screen_no, 4)
        self.assertEqual(len(it.screen.seats), 208)
        self.assertIn("シアター4", it.label)
        self.assertEqual(it.stem, "sample")

    def test_load_folder_and_dedupe(self):
        # 同じファイルを2回渡しても重複しない
        res = load_screens([SAMPLE, SAMPLE])
        self.assertEqual(len(res.items), 1)
        self.assertTrue(any("重複" in w for w in res.warnings))

    def test_plain_png_svg_webp(self):
        res = load_screens([SAMPLE])
        with tempfile.TemporaryDirectory() as d:
            files, skipped = write_outputs(res.items, d, ["png", "svg", "webp"], styles=("plain",))
            names = sorted(os.path.basename(f) for f in files)
            self.assertEqual(names, ["sample_plane.png",
                                     "sample_plane.webp",
                                     "sample_plane_hasObject.svg",
                                     "sample_plane_noObject.svg"])
            self.assertEqual(skipped, [])

    def test_official_without_image_is_skipped(self):
        res = load_screens([SAMPLE])
        with tempfile.TemporaryDirectory() as d:
            files, skipped = write_outputs(res.items, d, ["png", "svg"], styles=("official",))
            self.assertEqual(files, [])
            self.assertEqual(len(skipped), 1)

    def test_official_png_contains_official_image_in_center(self):
        from PIL import Image, ImageChops, ImageStat
        res = load_screens([SAMPLE])
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            path = os.path.join(src, "tjoy_tokorozawa_screen04.png")
            Image.new("RGB", (300, 200), (200, 0, 0)).save(path, "PNG")
            self.assertEqual(attach_official(res.items, src), [])
            files, skipped = write_outputs(res.items, out, ["png"], styles=("official",))
            self.assertEqual(skipped, [])
            result = Image.open(files[0]).convert("RGB")
            official = Image.open(path).convert("RGB")
            # 上下に情報帯が付くので、幅は同じ・高さは増える。中央の画像部分は公式画像と一致する
            self.assertEqual(result.width, official.width)
            self.assertGreater(result.height, official.height)
            head = result.height - official.height
            top = result.crop((0, 0, result.width, head))
            self.assertNotEqual(top.getextrema(), ((0, 0), (0, 0), (0, 0)))  # 見出しがある
            band = result.crop((0, head, official.width, head + official.height))
            diff = ImageStat.Stat(ImageChops.difference(band, official)).mean
            self.assertLess(max(diff), 6)

    def test_cancel_stops_early(self):
        res = load_screens([SAMPLE])
        with tempfile.TemporaryDirectory() as d:
            files, _ = write_outputs(res.items, d, ["png"], styles=("plain",), cancelled=lambda: True)
            self.assertEqual(files, [])

    def test_official_match_by_renamed_and_cdn_names(self):
        from tjoy_seatmap.pipeline import match_official
        res = load_screens([SAMPLE])
        it = res.items[0]  # 所沢 シアター4
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "tjoy_tokorozawa_screen04.png"), "wb").close()
            self.assertTrue(match_official(d, it).endswith("tjoy_tokorozawa_screen04.png"))
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "200_04_20240700.png"), "wb").close()
            self.assertTrue(match_official(d, it).endswith("200_04_20240700.png"))
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "200_01_20240802.png"), "wb").close()
            self.assertIsNone(match_official(d, it))

    def test_self_check(self):
        info = self_check()
        self.assertEqual(info["render"], "ok")


if __name__ == "__main__":
    unittest.main()
