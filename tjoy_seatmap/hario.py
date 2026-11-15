"""HARファイルの読み込みと、座席ページ/背景画像/劇場ページの抽出。"""
from __future__ import annotations

import base64
import codecs
import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import Iterator

SEAT_URL_RE = re.compile(r"tjoy\.jp/(?:[^/?#]+)/reservation/choice_seat")
BG_URL_RE = re.compile(r"/images/_up/theater/(\d+)_(\d{2})_\d+\.png")
MODAL_MAP_RE = re.compile(r"/img/front/images/theater/(\d+)/map_(\d{2})\.png")
THEATER_PAGE_RE = re.compile(r"^https?://tjoy\.jp/([^/?#]+)/?$")


@dataclass
class SeatPage:
    html: str
    url: str
    source: str  # 入力ファイル名(表示用)
    resources: dict = field(default_factory=dict)  # (劇場コード, 画面番号) -> 背景画像のバイト列

    @property
    def slug(self) -> str:
        m = re.search(r"tjoy\.jp/([^/?#]+)/reservation/", self.url)
        return m.group(1) if m else ""


def iter_har_blobs(paths) -> Iterator[tuple]:
    """.har / .zip(中の.har) / ディレクトリ(再帰)から (表示名, bytes) を列挙する。"""
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for fn in sorted(files):
                    yield from iter_har_blobs([os.path.join(root, fn)])
        elif p.lower().endswith(".zip"):
            with zipfile.ZipFile(p) as zf:
                for info in sorted(zf.infolist(), key=lambda i: i.filename):
                    if info.is_dir() or not info.filename.lower().endswith((".har", ".txt")):
                        continue
                    base = os.path.basename(info.filename)
                    if base.startswith("._"):  # macOSのメタデータ
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


def entry_text(entry: dict) -> str:
    content = entry.get("response", {}).get("content", {}) or {}
    text = content.get("text") or ""
    if content.get("encoding") == "base64" and text:
        raw = base64.b64decode(text)
        return raw.decode(_charset_of(content.get("mimeType", "")), errors="replace")
    return text


def entry_bytes(entry: dict):
    """画像などのバイナリ本体。HARに本体が無い(Fiddlerの上限で省略)場合は None。"""
    content = entry.get("response", {}).get("content", {}) or {}
    text = content.get("text")
    if not text:
        return None
    if content.get("encoding") == "base64":
        return base64.b64decode(text)
    return text.encode("utf-8")


def find_background_resources(har: dict) -> dict:
    """HAR内の座席表背景画像 (劇場コード, 画面番号) -> bytes。本体が無いものは含めない。"""
    out = {}
    for e in har.get("log", {}).get("entries", []):
        url = e.get("request", {}).get("url", "").split("?")[0]
        m = BG_URL_RE.search(url) or MODAL_MAP_RE.search(url)
        if not m or e.get("response", {}).get("status") != 200:
            continue
        data = entry_bytes(e)
        if data:
            out[(m.group(1), str(int(m.group(2))))] = data
    return out


def find_seat_pages(har: dict, source: str = "") -> list:
    pages = []
    for e in har.get("log", {}).get("entries", []):
        url = e.get("request", {}).get("url", "")
        if not SEAT_URL_RE.search(url):
            continue
        html = entry_text(e)
        if "<area" not in html or "seat-select" not in html:
            continue
        pages.append(SeatPage(html=html, url=url, source=source))
    return pages
