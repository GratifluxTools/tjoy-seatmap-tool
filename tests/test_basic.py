import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_sample_har  # noqa: E402
from tjoy_seatmap import theaters  # noqa: E402
from tjoy_seatmap.pipeline import build_seatmaps, make_fontset, write_outputs  # noqa: E402
from tjoy_seatmap.scene import Options  # noqa: E402
from tjoy_seatmap.schedule import ScheduleIndex  # noqa: E402
from tjoy_seatmap.seatpage import parse_seat_page  # noqa: E402


class SeatPageTest(unittest.TestCase):
    def test_parse_areas_and_kinds(self):
        pg = parse_seat_page(make_sample_har.seat_html())
        self.assertEqual(len(pg.seats), 5)
        kinds = {p.seat.seat_id: p.seat.kind for p in pg.seats}
        self.assertEqual(kinds["A-1"], "normal")
        self.assertEqual(kinds["B-1"], "normal")  # 席種5も通常席
        self.assertEqual(kinds["G-1"], "executive")
        self.assertEqual(kinds["A-12"], "reclining")
        self.assertEqual(pg.screen_no, "1")
        self.assertEqual(pg.theater_code, "200")
        self.assertEqual(pg.stated, (5, 1))
        p = pg.seats[0]
        self.assertEqual((p.x, p.y, p.w, p.h), (20, 20, 40, 40))


class GroupKindTest(unittest.TestCase):
    def test_pair_trio_and_premium(self):
        from tjoy_seatmap.seatpage import kind_of
        self.assertEqual(kind_of("1", 2), "pair")
        self.assertEqual(kind_of("1", 3), "trio")
        self.assertEqual(kind_of("1", None), "normal")
        self.assertEqual(kind_of("5", 2), "normal")  # 席種5は通常席
        self.assertEqual(kind_of("3"), "premium")
        self.assertEqual(kind_of("14"), "counter")
        self.assertEqual(kind_of("2"), "executive")

    def test_seat_group_sizes_from_page(self):
        html = ('<map><area id="A-1" type-seat="1" seat-group="07" data-coords="0,0,10,10">'
                '<area id="A-2" type-seat="1" seat-group="07" data-coords="20,0,30,10">'
                '<area id="B-1" type-seat="1" seat-group="null" data-coords="0,20,10,30"></map>')
        kinds = {p.seat.seat_id: p.seat.kind for p in parse_seat_page(html).seats}
        self.assertEqual(kinds, {"A-1": "pair", "A-2": "pair", "B-1": "normal"})


class FacilityTest(unittest.TestCase):
    def test_facility_table_rows(self):
        from tjoy_seatmap.schedule import ScheduleIndex, parse_facility_table
        html = ('<table class="table-information"><tr><td><a data-target="#screen01">シアター1</a></td>'
                '<td>334+（6）</td><td>Dolby Atmos</td></tr>'
                '<tr><td><a data-target="#screen02">シアター2</a></td><td>232+（6）</td><td>IMAXレーザー</td></tr>'
                '<tr><td><a data-target="#screen03">シアター3</a></td><td>206+（4）</td><td>SCREENX</td></tr>'
                '<tr><td><a data-target="#screen04">シアター4</a></td><td>208+（4）</td><td></td></tr></table>')
        self.assertEqual(parse_facility_table(html),
                         {"1": "Dolby Atmos", "2": "IMAXレーザー", "3": "ScreenX", "4": ""})
        idx = ScheduleIndex()
        self.assertTrue(idx.add_facility_page(html, "200"))
        self.assertEqual(idx.facility("200", "2"), "IMAXレーザー")
        self.assertTrue(idx.has_facility_info("200"))
        self.assertFalse(idx.has_facility_info("320"))
        # 表が揃っている劇場は、施設案内HARが無くても設備を出す
        self.assertEqual(idx.facility("360", "9"), "ScreenX with Dolby Atmos")
        self.assertEqual(idx.facility("140", "6"), "Dolby Cinema")
        self.assertTrue(idx.has_facility_info("140"))

    def test_multiple_facilities_in_one_note(self):
        from tjoy_seatmap.schedule import canonical_facilities as c
        self.assertEqual(c("SCREENX/Dolby Atmos"), "ScreenX with Dolby Atmos")
        self.assertEqual(c("IMAXレーザー"), "IMAXレーザー")
        self.assertEqual(c("IMAX"), "IMAX")
        self.assertEqual(c("T-LEX"), "T-LEX")
        self.assertEqual(c("MX4D"), "MX4D")
        self.assertEqual(c(""), "")


class ScheduleTest(unittest.TestCase):
    def test_theater_and_screen_names(self):
        s = ScheduleIndex()
        s.add_theater_page(make_sample_har.theater_html(), "200")
        self.assertEqual(s.theater_name("200"), "T・ジョイ エミテラス所沢")
        self.assertEqual(s.lookup("200", "1")["name"], "シアター1")


class TheaterNameTest(unittest.TestCase):
    def test_builtin_and_override(self):
        self.assertEqual(theaters.name_for("320"), "T・ジョイ梅田")
        self.assertEqual(theaters.name_for("999", override="手動名"), "手動名")
        self.assertIn("999", theaters.name_for("999"))


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.seat = os.path.join(self.tmp.name, "tjoy_tokorozawa_1.har")
        self.theater = os.path.join(self.tmp.name, "tjoy_schedule.har")
        make_sample_har.make(self.seat, self.theater)

    def test_build_and_outputs_without_background(self):
        maps = build_seatmaps([self.seat], [self.theater], log=lambda m: None)
        self.assertEqual(len(maps), 1)
        sm = maps[0]
        self.assertEqual(sm.n_seats, 5)
        self.assertEqual(sm.n_wheelchair, 1)
        # HARに背景本体は無いが、同梱の座席図(200_01)を使う
        self.assertEqual(sm.bg.size, (1761, 1000))
        self.assertEqual(sm.title("ja"), "T・ジョイ エミテラス所沢 シアター1")
        out = os.path.join(self.tmp.name, "out")
        files = write_outputs(sm, out, ("png", "svg"), Options(style="official", lang="ja"), 1.0, make_fontset())
        self.assertTrue(any(f.endswith("_official.png") for f in files), files)
        self.assertTrue(any(f.endswith("_official_noObject.svg") for f in files), files)

    def test_plain_when_no_background(self):
        sm = build_seatmaps([self.seat], [self.theater], log=lambda m: None)[0]
        sm.bg = None  # 背景が無い画面 (例: 新宿3番)
        out = os.path.join(self.tmp.name, "plain")
        files = write_outputs(sm, out, ("png",), Options(style="official", lang="ja"), 1.0, make_fontset())
        self.assertTrue(files[0].endswith("_plane.png"), files)

    def test_json_seat_list(self):
        sm = build_seatmaps([self.seat], [self.theater], log=lambda m: None)[0]
        out = os.path.join(self.tmp.name, "json")
        files = write_outputs(sm, out, (), Options(), 1.0, make_fontset(), with_json=True)
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["seats"], 5)
        self.assertEqual({s["kind"] for s in data["seat_list"]}, {"normal", "executive", "reclining"})


if __name__ == "__main__":
    unittest.main()
