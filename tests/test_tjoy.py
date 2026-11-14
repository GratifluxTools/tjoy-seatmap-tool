import collections
import glob
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tjoy_seatmap.seatpage import parse_seat_page  # noqa: E402
from tjoy_seatmap.schedule import parse_schedule  # noqa: E402
from tjoy_seatmap.render import render_plain_png, render_plain_svg, render_official_svg, to_webp_bytes  # noqa: E402
from tjoy_seatmap.cli import main as cli_main  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name, slug=None):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return parse_seat_page(f.read(), source=name, slug=slug)


class SeatPageTests(unittest.TestCase):
    def test_counts_match_page_for_all_screens(self):
        for f in sorted(glob.glob(os.path.join(FIX, "seat_*.html"))):
            with open(f, encoding="utf-8") as fh:
                s = parse_seat_page(fh.read(), source=f)
            self.assertEqual(s.seat_count_page, len(s.seats), os.path.basename(f))
            self.assertFalse(any("不一致" in w for w in s.warnings), os.path.basename(f))

    def test_shinjuku_3(self):
        s = load("seat_shinjuku_3.html")
        self.assertEqual(s.theater_name, "新宿バルト9")
        self.assertEqual(s.theater_key, "shinjuku")
        self.assertEqual(s.screen_no, 3)
        self.assertEqual(len(s.seats), 148)
        self.assertEqual(set(x.kind for x in s.seats), {"normal"})
        self.assertEqual(s.wheelchair_page, 1)
        self.assertEqual(s.show_time, "23:45～25:40")

    def test_tokorozawa_1_special_seats(self):
        s = load("seat_tokorozawa_1.html")
        c = collections.Counter(x.kind for x in s.seats)
        self.assertEqual(c, {"normal": 315, "executive": 13, "reclining": 6})
        ex = [x for x in s.seats if x.kind == "executive"]
        self.assertTrue(all(x.fee == 1000 for x in ex))
        rc = [x for x in s.seats if x.kind == "reclining"]
        self.assertTrue(all(x.fee == 200 and x.row == "A" for x in rc))

    def test_tokorozawa_11_premier_counter(self):
        s = load("seat_tokorozawa_11.html")
        c = collections.Counter(x.kind for x in s.seats)
        self.assertEqual(c, {"normal": 119, "premier": 17, "counter": 7})
        self.assertTrue(all(x.fee == 500 for x in s.seats if x.kind == "premier"))
        self.assertTrue(all(x.fee == 200 for x in s.seats if x.kind == "counter"))

    def test_tokorozawa_4_pair_trio(self):
        s = load("seat_tokorozawa_4.html")
        c = collections.Counter(x.kind for x in s.seats)
        self.assertEqual(c, {"normal": 175, "pair": 12, "trio": 21})

    def test_seat_type_5_is_normal_seat(self):
        # 席種コード5（幅50px・肘掛け付き）は通常席として扱う
        s = load("seat_tokorozawa_4.html")
        fifty = [x for x in s.seats if x.type_code == "5"]
        self.assertTrue(fifty)
        self.assertTrue(all(x.kind == "normal" for x in fifty))
        self.assertTrue(all(x.w == 50 for x in fifty))


class ScheduleTests(unittest.TestCase):
    def test_shinjuku_schedule(self):
        with open(os.path.join(FIX, "schedule_shinjuku.html"), encoding="utf-8") as f:
            r = parse_schedule(f.read(), slug="shinjuku_wald9")
        self.assertEqual(r["theater_name"], "新宿バルト9")
        kinds = collections.Counter(x["kind"] for x in r["showings"])
        self.assertEqual(kinds["film"] + kinds["event"], len(r["showings"]))
        self.assertTrue(all(x["title"] for x in r["showings"]))
        self.assertEqual(sum(1 for x in r["showings"] if x["bookable"]), 22)


class RenderTests(unittest.TestCase):
    def test_plain_png_webp_svg(self):
        s = load("seat_tokorozawa_4.html")
        img = render_plain_png(s)
        self.assertGreater(img.width, 500)
        self.assertTrue(to_webp_bytes(img)[:4] == b"RIFF")
        svg = render_plain_svg(s)
        root = ET.fromstring(svg.split("?>", 1)[1])
        seats = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                 if (g.get("class") or "").startswith("seat ")]
        self.assertEqual(len(seats), 208)
        self.assertIsNotNone(root.find(".//{http://www.w3.org/2000/svg}g[@id='seat-I-1']"))

    def test_official_svg_embeds_image_with_seat_objects(self):
        from PIL import Image
        import io
        s = load("seat_tokorozawa_4.html")
        buf = io.BytesIO()
        Image.new("RGB", (1305, 945), (255, 255, 255)).save(buf, "PNG")
        svg = render_official_svg(s, buf.getvalue())
        root = ET.fromstring(svg.split("?>", 1)[1])
        ns = "{http://www.w3.org/2000/svg}"
        self.assertEqual(root.get("viewBox").split()[2], "1305")
        self.assertEqual(len(root.findall(f".//{ns}image")), 1)
        seats = [g for g in root.iter(ns + "g") if (g.get("class") or "").startswith("seat ")]
        self.assertEqual(len(seats), 208)

    def test_cli_writes_png_and_svg(self):
        with tempfile.TemporaryDirectory() as d:
            # HARでない入力は座席ページとして読まれないので、HAR を組み立てて検証する
            import json
            with open(os.path.join(FIX, "seat_tokorozawa_1.html"), encoding="utf-8") as fh:
                html = fh.read()
            har = {"log": {"entries": [
                {"request": {"url": "https://tjoy.jp/t-joy_emiterrace_tokorozawa/reservation/index/65865/C4978060/1/2026-11-12?type=film", "method": "GET"},
                 "response": {"status": 302, "content": {"mimeType": "text/html", "text": ""}}},
                {"request": {"url": "https://tjoy.jp/t-joy_emiterrace_tokorozawa/reservation/choice_seat", "method": "GET"},
                 "response": {"status": 200, "content": {"mimeType": "text/html", "text": html}}},
            ]}}
            har_path = os.path.join(d, "toho_test_1.har")
            with open(har_path, "w", encoding="utf-8") as f:
                json.dump(har, f, ensure_ascii=False)
            out = os.path.join(d, "out")
            rc = cli_main([har_path, "-s", "plain", "-o", out])
            self.assertEqual(rc, 0)
            names = sorted(os.listdir(out))
            self.assertEqual(names, ["toho_test_1_plane.png",
                                     "toho_test_1_plane_hasObject.svg",
                                     "toho_test_1_plane_noObject.svg"])


if __name__ == "__main__":
    unittest.main()
