"""スケジュール(劇場トップ)HARから、劇場名と「シアター○」のスクリーン名を引く。

劇場トップの <title> が劇場名 (例: 'T・ジョイ梅田')。
スクリーン一覧のリンク <a data-target="#screen09">シアター９</a> から画面番号と表示名を取る。
劇場コードは劇場トップの URL スラッグから引く(theaters.py)。
"""
from __future__ import annotations

import html as htmllib
import re
import unicodedata

from . import theaters

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
SCREEN_LINK_RE = re.compile(r'data-target="#screen(\d{2})"[^>]*>\s*([^<]+?)\s*</a>')


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


# 利用者提供の特別設備名。備考欄の表記ゆれ(SCREENX 等)をこの名前に統一する。
FACILITY_NAMES = [
    "IMAX", "Dolby Atmos", "Dolby Cinema", "ScreenX", "ScreenX with Dolby Atmos",
    "IMAXレーザー", "MX4D", "T-LEX",
]
_FACILITY_KEYS = sorted(FACILITY_NAMES, key=len, reverse=True)  # 長い名前を先に照合


def canonical_facilities(text: str) -> str:
    """備考欄の文字列から特別設備名を全部拾い、' / ' で連結する(例: SCREENX/Dolby Atmos -> ScreenX / Dolby Atmos)。

    長い名前から照合し、一度拾った部分は除外する(IMAXレーザーを IMAX と二重に拾わないため)。
    """
    t = nfkc(htmllib.unescape(text))
    mask = list(t)
    found = []
    # 「SCREENX/Dolby Atmos」は ScreenX with Dolby Atmos を指す(利用者確認)
    combo = re.compile(r"screenx\s*/\s*dolby\s*atmos", re.I)
    for m in combo.finditer("".join(mask)):
        found.append((m.start(), "ScreenX with Dolby Atmos"))
        for i in range(m.start(), m.end()):
            mask[i] = "\0"
    for name in _FACILITY_KEYS:
        pat = re.compile(r"\s*".join(re.escape(ch) for ch in name.replace(" ", "")), re.I)
        for m in pat.finditer("".join(mask)):
            found.append((m.start(), name))
            for i in range(m.start(), m.end()):
                mask[i] = "\0"
    return " / ".join(name for _pos, name in sorted(found))


def canonical_facility(text: str) -> str:
    return canonical_facilities(text)


# 施設案内の表が手元に無い劇場の設備(利用者提供のスクリーンショット, 2026-11-15 時点)。
# 表が揃っている劇場のみ。キーは (劇場コード, 画面番号)。
BUILTIN_FACILITIES = {
    ("140", "6"): "Dolby Cinema",  # 新宿バルト9 シアター6
    ("360", "9"): "ScreenX with Dolby Atmos",  # T・ジョイ京都 シアター9
}
BUILTIN_FACILITY_THEATERS = {"140", "360"}


FACILITY_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
FACILITY_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def parse_facility_table(text: str) -> dict:
    """施設案内の「シアター情報」表から {画面番号: 特別設備名 or ""}。表が無ければ None。

    列は シアター / 座席数(車椅子) / 備考。シアター名のリンクが data-target="#screenNN"。
    """
    if "table-information" not in text:
        return None
    out = {}
    for tr in FACILITY_ROW_RE.findall(text):
        m = re.search(r'data-target="#screen(\d+)"', tr)
        if not m:
            continue
        tds = [TAG_RE.sub("", td) for td in FACILITY_TD_RE.findall(tr)]
        note = tds[2] if len(tds) > 2 else ""
        out[str(int(m.group(1)))] = canonical_facilities(note)
    return out


class ScheduleIndex:
    def __init__(self):
        self.theater_names = {}  # 劇場コード -> 劇場名
        self.screens = {}  # (劇場コード, 画面番号) -> {"name": ...}
        self.facilities = {}  # (劇場コード, 画面番号) -> 特別設備名 ("" は設備なし)
        self.facility_pages = set()  # 施設案内の表を読めた劇場コード

    def add_theater_page(self, text: str, code: str) -> None:
        m = TITLE_RE.search(text)
        if m:
            name = htmllib.unescape(m.group(1)).strip()
            if name:
                self.theater_names[code] = name
        for num, label in SCREEN_LINK_RE.findall(text):
            self.screens[(code, str(int(num)))] = {"name": nfkc(htmllib.unescape(label))}

    def add_facility_page(self, text: str, code: str) -> bool:
        table = parse_facility_table(text)
        if table is None:
            return False
        self.facility_pages.add(str(code))
        for num, fac in table.items():
            self.facilities[(str(code), str(int(num)))] = fac
        return True

    def facility(self, code: str, screen_no: str) -> str:
        if not screen_no:
            return ""
        key = (str(code), str(int(screen_no)))
        if key in self.facilities:
            return self.facilities[key]
        return BUILTIN_FACILITIES.get(key, "")

    def has_facility_info(self, code: str) -> bool:
        return str(code) in self.facility_pages or str(code) in BUILTIN_FACILITY_THEATERS

    def theater_name(self, code: str):
        return self.theater_names.get(str(code))

    def lookup(self, code: str, screen_no: str):
        return self.screens.get((str(code), str(int(screen_no)))) if screen_no else None


def theater_code_of_slug(slug: str) -> str | None:
    return theaters.CODE_OF_SLUG.get(slug)
