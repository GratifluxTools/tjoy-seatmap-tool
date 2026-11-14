"""T・ジョイ版のテスト(座席の読み取り・設備表示・出力名・公式風/プレーン・SVG・WebP・中止)。"""
import collections
import glob
import io
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

from tests.make_sample_har import make_har, main as make_sample  # noqa: E402
from tjoy_seatmap import assets  # noqa: E402
from tjoy_seatmap.pipeline import build_seatmaps, make_fontset, write_outputs  # noqa: E402
from tjoy_seatmap.scene import Options  # noqa: E402
from tjoy_seatmap.seatparse import facilities_of, parse_seat_html  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
SVG_NS = "{http://www.w3.org/2000/svg}"


def fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def write_har(html, slug, screen, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(make_har(html, slug, screen), f, ensure_ascii=False)
    return path


class SeatPageTests(unittest.TestCase):
    def test_counts_match_page_for_all_fixtures(self):
        for f in sorted(glob.glob(os.path.join(FIX, "seat_*.html"))):
            r = parse_seat_html(open(f, encoding="utf-8").read())
            self.assertEqual(r["stated"][0], len(r["box"].seats), os.path.basename(f))
            self.assertEqual(r["warnings"], [], os.path.basename(f))

    def test_seat_kinds(self):
        r1 = parse_seat_html(fixture("seat_tokorozawa_1.html"))
        c1 = collections.Counter(p.seat.kind for p in r1["box"].seats)
        self.assertEqual(c1, {"normal": 315, "executive": 13, "reclining": 6})
        r4 = parse_seat_html(fixture("seat_tokorozawa_4.html"))
        c4 = collections.Counter(p.seat.kind for p in r4["box"].seats)
        self.assertEqual(c4, {"normal": 175, "pair": 12, "trio": 21})
        r11 = parse_seat_html(fixture("seat_tokorozawa_11.html"))
        c11 = collections.Counter(p.seat.kind for p in r11["box"].seats)
        self.assertEqual(c11, {"normal": 119, "premier": 17, "counter": 7})

    def test_seat_type_5_is_normal(self):
        r4 = parse_seat_html(fixture("seat_tokorozawa_4.html"))
        wide = [p for p in r4["box"].seats if p.seat.type_code == "5"]
        self.assertTrue(wide)
        self.assertTrue(all(p.seat.kind == "normal" for p in wide))

    def test_fees(self):
        r11 = parse_seat_html(fixture("seat_tokorozawa_11.html"))
        self.assertTrue(all(p.seat.fee == 500 for p in r11["box"].seats if p.seat.kind == "premier"))
        self.assertTrue(all(p.seat.fee == 200 for p in r11["box"].seats if p.seat.kind == "counter"))

    def test_facilities_from_title_brackets(self):
        self.assertEqual(facilities_of(fixture("seat_tokorozawa_1.html")), "Dolby Atmos®")
        self.assertEqual(facilities_of(fixture("seat_tokorozawa_2.html")), "IMAX®")
        # 字幕は特別設備ではないので表示しない / 映画名は含めない
        self.assertEqual(facilities_of(fixture("seat_tokorozawa_11.html")), "")
        self.assertEqual(facilities_of(fixture("seat_shinjuku_3.html")), "")

    def test_facility_names_follow_official_notation(self):
        from tjoy_seatmap.seatparse import _facility_name
        cases = {
            "Dolby Cinema": "Dolby Cinema®",
            "ドルビーシネマ": "Dolby Cinema®",
            "Dolby Atmos": "Dolby Atmos®",
            "ScreenX with Dolby Atmos": "ScreenX with Dolby Atmos®",
            "ScreenX": "ScreenX",
            "IMAX Laser": "IMAX®レーザー",
            "IMAXデジタル": "IMAX®デジタルシアター",
            "MX4D": "MX4D®",
            "T-LEX": "T-LEX®",
            "字幕": None,
        }
        for tag, want in cases.items():
            self.assertEqual(_facility_name(tag), want, tag)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sample = make_sample(os.path.join(self.tmp.name, "tjoy_tokorozawa_4.har"))
        self.fonts = make_fontset(None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sample_end_to_end(self):
        maps = build_seatmaps([self.sample], log=lambda m: None)
        self.assertEqual(len(maps), 1)
        sm = maps[0]
        self.assertEqual(sm.stem, "tjoy_tokorozawa_4")
        self.assertEqual(sm.theater_name("ja"), "T・ジョイ エミテラス所沢")
        self.assertEqual(sm.title("ja"), "T・ジョイ エミテラス所沢 シアター4")
        self.assertEqual(sm.subtitle("ja"), "全席空席表示  /  208席 + 車いす席 4席")
        self.assertIsNotNone(sm.bg)

    def test_film_title_is_not_shown(self):
        p = write_har(fixture("seat_tokorozawa_1.html"), "t-joy_emiterrace_tokorozawa", 1,
                      os.path.join(self.tmp.name, "tjoy_tokorozawa_1.har"))
        sm = build_seatmaps([p], log=lambda m: None)[0]
        self.assertIn("Dolby Atmos®", sm.subtitle("ja"))
        self.assertNotIn("ゴジラ", sm.subtitle("ja"))
        self.assertNotIn("ゴジラ", sm.title("ja"))

    def test_facility_shown_in_all_outputs(self):
        p = write_har(fixture("seat_tokorozawa_2.html"), "t-joy_emiterrace_tokorozawa", 2,
                      os.path.join(self.tmp.name, "tjoy_tokorozawa_2.har"))
        sm = build_seatmaps([p], log=lambda m: None)[0]
        out = os.path.join(self.tmp.name, "out")
        opts = Options(style="plain")
        write_outputs(sm, out, ["svg"], opts, 2.0, self.fonts, with_json=True)
        data = json.load(open(os.path.join(out, "tjoy_tokorozawa_2.json"), encoding="utf-8"))
        self.assertIn("IMAX®", data["subtitle"])
        self.assertEqual(data["facility"], "IMAX®")

    def test_official_and_plain_outputs_and_names(self):
        sm = build_seatmaps([self.sample], log=lambda m: None)[0]
        out = os.path.join(self.tmp.name, "out")
        fm = ["png", "svg"]
        files = []
        for style in ("official", "plain"):
            for obj in (True, False):
                files += write_outputs(sm, out, fm, Options(style=style, svg_objects=obj), 2.0, self.fonts)
        names = sorted(set(os.path.basename(f) for f in files))
        self.assertEqual(names, [
            "tjoy_tokorozawa_4_official.png",
            "tjoy_tokorozawa_4_official_hasObject.svg",
            "tjoy_tokorozawa_4_official_noObject.svg",
            "tjoy_tokorozawa_4_plane.png",
            "tjoy_tokorozawa_4_plane_hasObject.svg",
            "tjoy_tokorozawa_4_plane_noObject.svg",
        ])

    def test_svg_objects_each_seat_is_a_group(self):
        sm = build_seatmaps([self.sample], log=lambda m: None)[0]
        out = os.path.join(self.tmp.name, "obj")
        write_outputs(sm, out, ["svg"], Options(style="official", svg_objects=True), 2.0, self.fonts)
        path = os.path.join(out, "tjoy_tokorozawa_4_official_hasObject.svg")
        root = ET.parse(path).getroot()
        seats = [g for g in root.iter(SVG_NS + "g") if g.get("class") == "seat"]
        self.assertEqual(len(seats), 208)
        self.assertIsNotNone(root.find(f".//{SVG_NS}g[@id='seat-A-6']"))
        self.assertTrue(any(r.get("fill-opacity") == "0" for r in root.iter(SVG_NS + "rect")))

    def test_official_png_keeps_map_width_and_adds_header_and_legend(self):
        sm = build_seatmaps([self.sample], log=lambda m: None)[0]
        out = os.path.join(self.tmp.name, "off")
        files = write_outputs(sm, out, ["png"], Options(style="official"), 1.0, self.fonts)
        img = Image.open(files[0]).convert("RGB")
        self.assertEqual(img.width, sm.bg.width)           # 座席表画像の幅のまま
        self.assertGreater(img.height, sm.bg.height)       # 上の見出し・下の凡例の分だけ高い

    def test_plain_png_is_nonempty(self):
        sm = build_seatmaps([self.sample], log=lambda m: None)[0]
        out = os.path.join(self.tmp.name, "pl")
        files = write_outputs(sm, out, ["png"], Options(style="plain"), 2.0, self.fonts)
        im = Image.open(files[0])
        self.assertGreater(im.width, 500)

    def test_webp_is_lossless_copy_of_png(self):
        from tjoy_seatmap.pipeline import render_image, save_webp
        sm = build_seatmaps([self.sample], log=lambda m: None)[0]
        opts = Options(style="plain")
        img = render_image(sm, opts, 1.0, self.fonts)
        buf = io.BytesIO()
        save_webp(img, buf)  # file-like にも書けることを確認
        back = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
        self.assertEqual(list(img.convert("RGB").getdata())[:1000], list(back.getdata())[:1000])

    def test_cancel_stops_before_next_file(self):
        sm = build_seatmaps([self.sample], log=lambda m: None)[0]
        out = os.path.join(self.tmp.name, "cancel")

        class Stop(Exception):
            pass

        def progress(path, finished):
            if not finished:
                raise Stop()

        with self.assertRaises(Stop):
            write_outputs(sm, out, ["png", "svg"], Options(style="plain"), 1.0, self.fonts, progress=progress)
        self.assertEqual(os.listdir(out) if os.path.isdir(out) else [], [])

    def test_missing_map_disables_official_but_not_plain(self):
        # 新宿3番は同梱の座席表画像が無い。公式風は作らず、プレーンだけ作る
        p = write_har(fixture("seat_shinjuku_3.html"), "shinjuku_wald9", 3,
                      os.path.join(self.tmp.name, "tjoy_shinjuku_3.har"))
        sm = build_seatmaps([p], log=lambda m: None)[0]
        self.assertIsNone(sm.bg)
        self.assertTrue(any("公式の座席表画像がありません" in w for w in sm.warnings))
        out = os.path.join(self.tmp.name, "nomap")
        files = write_outputs(sm, out, ["png"], Options(style="official"), 1.0, self.fonts)
        self.assertEqual([os.path.basename(f) for f in files], ["tjoy_shinjuku_3_plane.png"])

    def test_manual_theater_name(self):
        sm = build_seatmaps([self.sample], log=lambda m: None)[0]
        sm.theater_override = "テスト劇場"
        self.assertEqual(sm.theater_name("ja"), "テスト劇場")

    def test_unknown_site_gets_generic_name(self):
        # 座席表画像の劇場コードを未登録の 999 に差し替えると、劇場名は「T・ジョイ (site 999)」になる
        html = fixture("seat_tokorozawa_4.html").replace("/200_04_", "/999_04_")
        p = write_har(html, "t-joy_unknown", 4, os.path.join(self.tmp.name, "tjoy_unknown_4.har"))
        sm = build_seatmaps([p], log=lambda m: None)[0]
        self.assertFalse(sm.theater_known)
        self.assertEqual(sm.theater_name("ja"), "T・ジョイ (site 999)")

    def test_assets_present(self):
        info = assets.self_check()
        self.assertGreaterEqual(info["embedded_icons"], 7)
        self.assertGreaterEqual(info["bundled_maps"], 5)

    def test_icon_assets_exist(self):
        here = os.path.join(os.path.dirname(__file__), "..")
        for n in ("icon-256.png", "icon.ico", "icon.svg", "icon-1024.png"):
            self.assertTrue(os.path.exists(os.path.join(here, "assets", "icon", n)), n)


if __name__ == "__main__":
    unittest.main()
