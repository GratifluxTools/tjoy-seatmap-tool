"""HARファイルの読み込みと、T・ジョイの座席ページ/予約情報/画像の抽出。

取得するもの:
  - 座席ページ: https://tjoy.jp/<劇場>/reservation/choice_seat (HTML。座席は <area> の画像マップ)
  - 予約情報:   直前の 302 リダイレクト .../reservation/index/<上映ID>/<作品コード>/<スクリーン>/<日付>?type=..
  - 公式の座席表画像: 座席ページの img.js-map (cdn.tjoy.jp/images/_up/theater/<劇場コード>_<スクリーン>_<日付>.png)
  - 席種アイコン: /img/front/images/seat/icn_*.png (凡例に使う)
"""
from __future__ import annotations

import base64
import codecs
import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import Iterator

CHOICE_SEAT_RE = re.compile(r"https?://tjoy\.jp/([^/]+)/reservation/choice_seat")
RESERVE_RE = re.compile(
    r"https?://tjoy\.jp/([^/]+)/reservation/index/(\d+)/([A-Za-z0-9]+)/(\d+)/(\d{4}-\d{2}-\d{2})\?type=(\w+)"
)
MAP_URL_RE = re.compile(r"/images/_up/theater/(\d{3})_(\d{2})_[^/?#]*\.(?:png|jpe?g|gif)$")
ICON_URL_RE = re.compile(r"/img/front/images/seat/(icn_[\w.-]+\.png)$")
SEAT_PAGE_MARK = "js-map-seat"  # 座席ページ(画像マップ)の目印


@dataclass
class SeatPage:
    html: str
    params: dict
    url: str
    source: str  # 入力ファイル名(表示用)
    resources: dict = field(default_factory=dict)  # 'map:200:04' / 'icon:icn_type1.png' -> bytes

    @property
    def site_cd(self) -> str:
        return self.params.get("site_cd") or ""


def iter_har_blobs(paths) -> Iterator[tuple]:
    """.har / .txt(HARの拡張子違い) / .zip(中の.har) / フォルダ(再帰) から (表示名, bytes) を列挙する。"""
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for fn in sorted(files):
                    yield from iter_har_blobs([os.path.join(root, fn)])
        elif p.lower().endswith(".zip"):
            with zipfile.ZipFile(p) as zf:
                for info in sorted(zf.infolist(), key=lambda i: i.filename):
                    base = os.path.basename(info.filename)
                    if info.is_dir() or not base.lower().endswith((".har", ".txt")) or base.startswith("._"):
                        continue
                    yield base, zf.read(info)
        elif p.lower().endswith((".har", ".txt")):
            with open(p, "rb") as f:
                yield os.path.basename(p), f.read()


def parse_har(data: bytes) -> dict:
    return json.loads(data.decode("utf-8-sig"))


def _charset_of(mime: str) -> str:
    m = re.search(r"charset=([\w\-]+)", mime or "", re.I)
    name = (m.group(1) if m else "utf-8").strip()
    try:
        codecs.lookup(name)
        return name
    except LookupError:
        return "utf-8"


def entry_bytes(entry: dict) -> bytes:
    content = entry.get("response", {}).get("content", {}) or {}
    text = content.get("text") or ""
    if content.get("encoding") == "base64":
        return base64.b64decode(text) if text else b""
    return text.encode(_charset_of(content.get("mimeType", "")), errors="replace")


def entry_text(entry: dict) -> str:
    content = entry.get("response", {}).get("content", {}) or {}
    return entry_bytes(entry).decode(_charset_of(content.get("mimeType", "")), errors="replace")


def find_resources(har: dict) -> dict:
    """公式の座席表画像(map)と席種アイコン(icon)を取り出す。本体が記録されていないものは無視する。"""
    out = {}
    for e in har.get("log", {}).get("entries", []):
        url = e.get("request", {}).get("url", "").split("?")[0]
        if e.get("response", {}).get("status") != 200:
            continue
        m = MAP_URL_RE.search(url)
        if m:
            data = entry_bytes(e)
            if data:
                out[f"map:{m.group(1)}:{m.group(2)}"] = data
            continue
        m = ICON_URL_RE.search(url)
        if m:
            data = entry_bytes(e)
            if data:
                out[f"icon:{m.group(1)}"] = data
    return out


def _params_from_reserve(m) -> dict:
    return {
        "slug": m.group(1), "performance_id": m.group(2), "film_code": m.group(3),
        "screen_no": int(m.group(4)), "date": m.group(5), "type": m.group(6),
    }


def find_seat_pages(har: dict, source: str = "") -> list:
    """座席ページ(choice_seat)を、直前の予約リダイレクトの情報と組にして返す。"""
    pages = []
    pending = None
    resources = None
    for e in har.get("log", {}).get("entries", []):
        url = e.get("request", {}).get("url", "")
        m = RESERVE_RE.search(url)
        if m:
            pending = _params_from_reserve(m)
            continue
        m = CHOICE_SEAT_RE.search(url)
        if not m:
            continue
        html = entry_text(e)
        if SEAT_PAGE_MARK not in html:
            continue
        if resources is None:
            resources = find_resources(har)
        params = dict(pending or {})
        params.setdefault("slug", m.group(1))
        # 座席表画像のURLから劇場コードを取る(例: 200_04_xxx.png -> 200)
        mm = re.search(r'src="([^"]*/images/_up/theater/\d{3}_\d{2}_[^"]*)"', html)
        map_url = mm.group(1) if mm else None
        if map_url:
            code = MAP_URL_RE.search(map_url.split("?")[0])
            if code:
                params["site_cd"] = code.group(1)
                params["screen_no_map"] = int(code.group(2))
        params.setdefault("site_cd", params["slug"])
        pages.append(SeatPage(html=html, params=params, url=url, source=source, resources=resources))
        pending = None
    return pages
