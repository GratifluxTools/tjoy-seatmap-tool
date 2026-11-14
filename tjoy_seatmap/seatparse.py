"""座席ページ(choice_seat のHTML)から、座席の配置・席種・ページ表記の情報を取り出す。"""
from __future__ import annotations

import html as htmllib
import re
import unicodedata
from collections import Counter

from .layout import Box, Placed
from .seatmodel import TYPE_KINDS, Seat

AREA_RE = re.compile(r"<area\b([^>]*)>", re.I)
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
ID_RE = re.compile(r"^([A-Za-z]+)-(\d+)$")
INFO_RE = re.compile(
    r"上映日\s*([\d/]+)\(.\)\s*(\d{1,2}:\d{2})\s*~\s*(\d{1,2}:\d{2})\s*劇場\s*(.+?)\s*シアター\s*(\d+)"
)
COUNT_RE = re.compile(r"シアター\s*(\d+)\s*(\d+)席\s*\+\s*\(車椅子(\d+)席\)")


class SeatPageError(ValueError):
    pass


def _text(raw: str) -> str:
    t = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return unicodedata.normalize("NFKC", htmllib.unescape(re.sub(r"\s+", " ", t)))


TITLE_RE = re.compile(r'class="[^"]*seat-info-content-ttl[^"]*"[^>]*>(.*?)</', re.S)
TAG_RE = re.compile(r"【([^】]+)】")


FACILITY_RULES = [
    # (判定する語のすべて, 表示名)。上から順に判定し、最初に当たったものを使う
    (("screenx", "atmos"), "ScreenX with Dolby Atmos®"),
    (("screenx",), "ScreenX"),
    (("imax", "レーザー"), "IMAX®レーザー"),
    (("imax", "laser"), "IMAX®レーザー"),
    (("imax", "デジタル"), "IMAX®デジタルシアター"),
    (("imax", "digital"), "IMAX®デジタルシアター"),
    (("imax",), "IMAX®"),  # 座席ページの表記だけでは レーザー/デジタル を区別できない
    (("dolbycinema",), "Dolby Cinema®"),
    (("ドルビーシネマ",), "Dolby Cinema®"),
    (("dolbyatmos",), "Dolby Atmos®"),
    (("ドルビーアトモス",), "Dolby Atmos®"),
    (("mx4d",), "MX4D®"),
    (("t-lex",), "T-LEX®"),
    (("tlex",), "T-LEX®"),
]


def _facility_name(tag: str):
    key = re.sub(r"\s+", "", tag).lower()
    for words, name in FACILITY_RULES:
        if all(w in key for w in words):
            return name
    return None


def facilities_of(raw_html: str) -> str:
    """上映回の特別設備を、映画名欄の【 】から取り出し、公式の表記で返す(例: IMAX®レーザー Dolby Atmos®)。

    映画名の本体は表示しない。字幕など特別設備でない注記は含めない。「ご案内」の文章は
    全体の案内で上映回ごとの情報ではないので使わない。同じ設備は1つにまとめる。
    """
    m = TITLE_RE.search(raw_html)
    if not m:
        return ""
    title = _text(m.group(1))
    out = []
    for tag in TAG_RE.findall(title):
        name = _facility_name(tag)
        if name and name not in out:
            out.append(name)
    return " ".join(out)


def parse_seat_html(raw_html: str) -> dict:
    """座席ページを解析する。戻り値: theater_name / screen_no / show_date / show_time /
    seats (Placed のリスト) / stated (席数, 車いす席数 または None) / map_url / warnings"""
    text = _text(raw_html)
    m = INFO_RE.search(text)
    if not m:
        raise SeatPageError("上映日・劇場名・シアター番号が見つかりません(座席選択画面のHTMLか確認してください)")
    show_date, t0, t1, theater_name, screen_no = m.group(1), m.group(2), m.group(3), m.group(4).strip(), int(m.group(5))

    # 座席数の表記 (全シアターの一覧から、このシアターの分を取る)
    stated = None
    for cm in COUNT_RE.finditer(text):
        if int(cm.group(1)) == screen_no:
            stated = (int(cm.group(2)), int(cm.group(3)))

    seats, groups = [], Counter()
    raw_seats = []
    for am in AREA_RE.finditer(raw_html):
        attrs = dict(ATTR_RE.findall(am.group(1)))
        sid = attrs.get("id", "")
        idm = ID_RE.match(sid)
        if not idm or not attrs.get("data-coords"):
            continue  # 席以外の <area> は無視
        x1, y1, x2, y2 = (int(float(v)) for v in attrs["data-coords"].split(","))
        group = attrs.get("seat-group")
        group = None if group in (None, "", "null") else group
        if group:
            groups[group] += 1
        raw_seats.append((sid, idm.group(1).upper(), int(idm.group(2)), (x1, y1, x2, y2), attrs, group))

    for sid, row, num, (x1, y1, x2, y2), attrs, group in raw_seats:
        tcode = attrs.get("type-seat", "1")
        kind = TYPE_KINDS.get(tcode, "normal")
        if group and kind == "normal":
            kind = {2: "pair", 3: "trio"}.get(groups[group], "normal")
        seats.append((group, row, num, x1, y1, x2, y2, Seat(
            seat_id=sid, row=row, num=num, kind=kind, blocked=False,
            state="sold-out" if attrs.get("class") == "sold-out" else "1",
            fee=int(attrs.get("add-change") or 0), type_code=tcode,
        )))

    # ペア/トリオは同じ座標を共有しているので、1席ぶんに分割して描く
    by_group = {}
    for item in seats:
        if item[0]:
            by_group.setdefault(item[0], []).append(item)
    placed = []
    for group, row, num, x1, y1, x2, y2, seat in seats:
        if group and seat.kind in ("pair", "trio"):
            members = sorted(by_group[group], key=lambda it: it[2])
            n = len(members)
            idx = [it[7].seat_id for it in members].index(seat.seat_id)
            gx1 = min(it[3] for it in members)
            gx2 = max(it[5] for it in members)
            w = (gx2 - gx1) / n
            placed.append(Placed(gx1 + w * idx, y1, w, y2 - y1, seat))
        else:
            placed.append(Placed(x1, y1, x2 - x1, y2 - y1, seat))

    warnings = []
    if stated is not None and stated[0] != len(placed):
        warnings.append(f"ページ表記({stated[0]}席)と座標の件数({len(placed)}席)が一致しません")
    if stated is None:
        warnings.append("ページの座席数表記が見つかりません")
    mm = re.search(r'src="([^"]*/images/_up/theater/\d{3}_\d{2}_[^"]*)"', raw_html)
    box_w = max((p.x + p.w for p in placed), default=0.0)
    box_h = max((p.y + p.h for p in placed), default=0.0)
    return {
        "theater_name": theater_name,
        "screen_no": screen_no,
        "show_date": show_date,
        "show_time": f"{t0}～{t1}",
        "box": Box(box_w, box_h, placed),
        "stated": stated,
        "map_url": mm.group(1) if mm else None,
        "facility": facilities_of(raw_html),
        "warnings": warnings,
    }
