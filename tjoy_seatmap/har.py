"""HAR / ZIP / フォルダ / テキスト(HARの拡張子違い) から対象エントリを取り出す。"""
import base64
import io
import json
import os
import re
import zipfile
from dataclasses import dataclass


@dataclass
class Capture:
    source: str        # ファイル名（zip内の場合は zip!name）
    url: str
    status: int
    mime: str
    text: str | None   # 本文(HTML等)。無い場合 None


def _load_har_bytes(data, name):
    text = data.decode("utf-8-sig")
    h = json.loads(text)
    for e in h["log"]["entries"]:
        r, s = e["request"], e["response"]
        c = s.get("content", {}) or {}
        body = c.get("text")
        if body and c.get("encoding") == "base64":
            try:
                body = base64.b64decode(body).decode("utf-8", errors="replace")
            except Exception:
                body = None
        yield Capture(name, r["url"], s.get("status", 0), c.get("mimeType", ""), body)


def iter_captures(paths):
    """パス（har/txt/zip/フォルダ）を列挙して Capture を返す。"""
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in sorted(names):
                    files.append(os.path.join(root, n))
        else:
            files.append(p)
    for f in files:
        low = f.lower()
        if low.endswith(".zip"):
            with zipfile.ZipFile(f) as z:
                for n in z.namelist():
                    if n.lower().endswith((".har", ".txt")) and not n.endswith("/"):
                        yield from _load_har_bytes(z.read(n), f"{os.path.basename(f)}!{n}")
        elif low.endswith((".har", ".txt", ".json")):
            with open(f, "rb") as fh:
                try:
                    yield from _load_har_bytes(fh.read(), os.path.basename(f))
                except (ValueError, KeyError):
                    continue  # HARでないテキストは無視


RESERVE_RE = re.compile(
    r"/([^/]+)/reservation/index/(\d+)/([A-Za-z0-9]+)/(\d+)/(\d{4}-\d{2}-\d{2})\?type=(\w+)"
)


def find_seat_pages(captures):
    """座席ページ(HTML)と、それに対応する予約リダイレクト(302)の情報を組にして返す。"""
    results = []
    pending = None  # 直前の予約URL情報
    for c in captures:
        m = RESERVE_RE.search(c.url)
        if m:
            pending = {
                "slug": m.group(1), "performance_id": m.group(2), "film_code": m.group(3),
                "screen_no": int(m.group(4)), "date": m.group(5), "type": m.group(6), "source": c.source,
            }
            continue
        if "/reservation/choice_seat" in c.url and c.text and "js-map-seat" in c.text:
            slug = re.search(r"https?://[^/]+/([^/]+)/reservation/choice_seat", c.url)
            results.append({
                "source": c.source,
                "slug": slug.group(1) if slug else None,
                "html": c.text,
                "reservation": pending,
            })
            pending = None
    return results


def find_schedule_pages(captures):
    """劇場トップ(スケジュール)のHTMLを返す。"""
    out = []
    for c in captures:
        if c.text and 'id="schedule-content"' in c.text and c.status == 200:
            m = re.search(r"https?://[^/]+/([^/?#]+)", c.url)
            out.append({"source": c.source, "slug": m.group(1) if m else None, "html": c.text})
    return out
