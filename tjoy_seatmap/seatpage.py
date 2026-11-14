"""座席ページ(/reservation/choice_seat のHTML)を座席データに変換する。

座席は画像マップ <area id="A-12" data-coords="x1,y1,x2,y2" type-seat="1" add-change="0" seat-group="null">。
席種はフロアの凡例アイコンと照合した対応（所沢・新宿の実データで確認）:
  1  通常席（幅40px）        5  通常席（幅50px・肘掛け付き。フロアマップで確認）
  2  エグゼクティブ（+1000）  3  プレミア（+500）
  11 リクライニング（+200）  14 カウンター（+200）
  type 1 で seat-group が2件/3件 → ペア / トリオ
"""
import re
import unicodedata
from bs4 import BeautifulSoup
from collections import Counter
from dataclasses import dataclass, field

from .theaters import theater_info

# 席種コード → (kind, 表示名)
TYPE_KINDS = {
    "1": ("normal", "通常席"),
    "5": ("normal", "通常席"),
    "2": ("executive", "エグゼクティブシート"),
    "3": ("premier", "プレミアシート"),
    "11": ("reclining", "リクライニングシート"),
    "14": ("counter", "カウンターシート"),
}
KIND_ORDER = ["normal", "pair", "trio", "premier", "executive", "reclining", "counter"]
KIND_LABEL = {
    "normal": "通常席", "pair": "ペアシート", "trio": "トリオシート", "premier": "プレミアシート",
    "executive": "エグゼクティブシート", "reclining": "リクライニングシート", "counter": "カウンターシート",
}
ID_RE = re.compile(r"^([A-Za-z]+)-(\d+)$")


@dataclass
class Seat:
    id: str
    row: str
    number: int
    x1: int
    y1: int
    x2: int
    y2: int
    type_code: str
    fee: int
    group: str | None
    kind: str
    sold: bool = False  # 元ページの予約済み表示（描画では空席扱い）

    @property
    def w(self):
        return self.x2 - self.x1

    @property
    def h(self):
        return self.y2 - self.y1


@dataclass
class SeatScreen:
    source: str
    slug: str | None
    theater_name: str
    theater_key: str
    screen_no: int
    screen_label: str
    film_title: str | None
    show_date: str | None
    show_time: str | None
    seats: list = field(default_factory=list)
    seat_count_page: int | None = None
    wheelchair_page: int | None = None
    background_url: str | None = None
    reservation: dict | None = None
    warnings: list = field(default_factory=list)

    @property
    def kinds_present(self):
        present = {s.kind for s in self.seats}
        return [k for k in KIND_ORDER if k in present]


def _norm(s):
    return unicodedata.normalize("NFKC", s or "")


def _count_table(text):
    """ページ内の『シアターN  M席 +（車椅子K席）』の一覧を {N: (M, K)} で返す。"""
    out = {}
    for m in re.finditer(r"シアター\s*(\d+)\s*(\d+)席\s*\+\s*\(車椅子(\d+)席\)", _norm(text)):
        out[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
    return out


def parse_seat_page(html, source="", slug=None, reservation=None):
    soup = BeautifulSoup(html, "html.parser")
    text = _norm(soup.get_text(" "))

    # 上映情報（「上映日 11/12（木）10:15～12:45 劇場 <名> シアター １」）
    m = re.search(r"上映日\s*([\d/]+)\(.\)\s*(\d{1,2}:\d{2})\s*~\s*(\d{1,2}:\d{2})\s*劇場\s*(.+?)\s*シアター\s*(\d+)", text)
    if not m:
        raise ValueError(f"上映情報が見つかりません: {source}")
    show_date = m.group(1)
    show_time = f"{m.group(2)}～{m.group(3)}"
    theater_name_page = m.group(4).strip()
    screen_no = int(m.group(5))
    slug = slug or (reservation or {}).get("slug")
    info = theater_info(slug, theater_name_page)

    film = soup.select_one(".seat-info-content-ttl")
    film_title = film.get_text(strip=True) if film else None

    bg = soup.select_one("img.js-map")
    bg_url = bg.get("src") if bg else None

    counts = _count_table(text)
    expected, wheel = counts.get(screen_no, (None, None))

    seats = []
    for a in soup.find_all("area"):
        aid = a.get("id") or ""
        mm = ID_RE.match(aid)
        if not mm or not a.get("data-coords"):
            continue
        x1, y1, x2, y2 = (int(v) for v in a["data-coords"].split(","))
        tcode = a.get("type-seat") or "1"
        group = a.get("seat-group")
        if group in (None, "", "null"):
            group = None
        seats.append(Seat(
            id=aid, row=mm.group(1), number=int(mm.group(2)),
            x1=x1, y1=y1, x2=x2, y2=y2,
            type_code=tcode, fee=int(a.get("add-change") or 0),
            group=group, kind=TYPE_KINDS.get(tcode, ("normal", "通常席"))[0],
            sold=(a.get("class") == "sold-out"),
        ))

    # ペア・トリオ（同じ seat-group の人数で判定）
    gcount = Counter(s.group for s in seats if s.group)
    for s in seats:
        if s.group and s.type_code == "1":
            if gcount[s.group] == 2:
                s.kind = "pair"
            elif gcount[s.group] == 3:
                s.kind = "trio"

    scr = SeatScreen(
        source=source, slug=slug, theater_name=theater_name_page or info["name"],
        theater_key=info["key"], screen_no=screen_no, screen_label=f"シアター{screen_no}",
        film_title=film_title, show_date=show_date, show_time=show_time,
        seats=seats, seat_count_page=expected, wheelchair_page=wheel,
        background_url=bg_url, reservation=reservation,
    )
    if expected is not None and expected != len(seats):
        scr.warnings.append(f"座席数の不一致: ページ {expected}席 / 座標 {len(seats)}件")
    if expected is None:
        scr.warnings.append("ページの座席数表記が見つかりません")
    if not bg_url:
        scr.warnings.append("背景画像のURLが見つかりません（自動描画になります）")
    return scr
