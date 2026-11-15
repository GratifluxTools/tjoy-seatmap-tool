"""T・ジョイの座席ページ(choice_seat)から座席一覧を取り出す。

T・ジョイの座席表は、背景画像(座席図そのもの)の上に <map> の <area> を重ねた構造。
各 <area> が1席で、data-coords が背景画像上の矩形(x1,y1,x2,y2 / 画素)、type-seat が席種コード。
背景画像には空席状態の座席・車いす席・通路・非常口がすでに描かれている。
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .hario import BG_URL_RE
from .layout import Box, Placed
from .seatmodel import Seat

AREA_RE = re.compile(r"<area\b[^>]*>")
ATTR_RE = re.compile(r'([\w\-]+)="([^"]*)"')
ID_RE = re.compile(r"^(?P<row>[A-Za-z]+)-(?P<num>\d+)$")
STATED_RE = re.compile(r"id=\"screen(\d{2})\"[\s\S]*?(\d+)席\s*\+\s*（車椅子(\d+)席）")

# 席種コード -> 種別名。画像と配置から確認済みのもの (スクリーン1/2/3/4/11)。
#   1  : 一般席(seat-groupが無い席)   5 : 一般席(利用者確認済み)
#   2  : エグゼクティブシート(所沢1,2,3)   3 : プレミアシート(所沢11)
#   11 : リクライニングシート(最前列, 所沢1,2)   14 : カウンターシート(最後列, 所沢11)
#   1+seat-group : ペアシート(2席) / トリオシート(3席)(所沢4)
TYPE_KIND = {
    "1": "normal",
    "5": "normal",
    "2": "executive",
    "3": "premium",
    "11": "reclining",
    "14": "counter",
}
# 席種1で seat-group が付く席はペア(2席)/トリオ(3席)。所沢4で確認。
GROUP_KIND = {2: "pair", 3: "trio"}


def kind_of(code: str, group_size: int | None = None) -> str:
    if str(code) == "1" and group_size:
        return GROUP_KIND.get(group_size, "normal")
    return TYPE_KIND.get(str(code), f"type{code}")


@dataclass
class ParsedSeatPage:
    theater_code: str  # 200 / 140 / 320 / 360 など (背景画像のファイル名由来)
    screen_no: str | None  # "1", "11" など
    bg_url: str | None  # 背景画像のURL (HTMLに書かれているもの)
    seats: list  # Placed (画素座標)
    stated: tuple | None  # (席数, 車いす席数) ページ表記


def parse_areas(html: str) -> list:
    rows = []
    for a in AREA_RE.findall(html):
        attrs = dict(ATTR_RE.findall(a))
        coords = attrs.get("data-coords") or attrs.get("coords")
        if not coords or attrs.get("shape", "rect") != "rect":
            continue
        try:
            x1, y1, x2, y2 = (float(v) for v in coords.split(","))
        except ValueError:
            continue
        rows.append((attrs, x1, y1, x2, y2))
    # seat-group の人数(同じグループIDの席数)
    group_size = Counter()
    for attrs, *_ in rows:
        g = attrs.get("seat-group", "")
        if g and g != "null":
            group_size[g] += 1
    out = []
    for attrs, x1, y1, x2, y2 in rows:
        sid = attrs.get("id", "")
        m = ID_RE.match(sid)
        row, num = (m.group("row").upper(), int(m.group("num"))) if m else (sid, 0)
        code = attrs.get("type-seat", "")
        g = attrs.get("seat-group", "")
        size = group_size.get(g) if g and g != "null" else None
        seat = Seat(seat_id=sid, row=row, num=num, kind=kind_of(code, size), blocked=False, state=code)
        out.append(Placed(x=x1, y=y1, w=x2 - x1, h=y2 - y1, seat=seat))
    return out


def parse_seat_page(html: str) -> ParsedSeatPage:
    bg_url = None
    theater_code, screen_no = "", None
    m = BG_URL_RE.search(html)
    if m:
        theater_code, screen_no = m.group(1), str(int(m.group(2)))
        full = re.search(r"https?://cdn\.tjoy\.jp/images/_up/theater/\d+_\d{2}_\d+\.png", html)
        bg_url = full.group(0) if full else None
    stated = None
    if screen_no is not None:
        for num, seats, wheel in STATED_RE.findall(html):
            if str(int(num)) == screen_no:
                stated = (int(seats), int(wheel))
                break
    return ParsedSeatPage(
        theater_code=theater_code,
        screen_no=screen_no,
        bg_url=bg_url,
        seats=parse_areas(html),
        stated=stated,
    )
