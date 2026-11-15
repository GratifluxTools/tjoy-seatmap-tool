"""座席表の背景画像(公式の座席図)を探す。

優先順: HARに本体が記録されていればそれ -> 同梱分 -> ローカルキャッシュ -> (fetch=True のときのみ)T・ジョイのサイトから取得。
座席の位置・席種は背景画像ではなく座席ページのHTMLから取るので、背景は見た目のための素材。
"""
from __future__ import annotations

import io
import os
import urllib.request

from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))


def _bundled_dirs():
    yield os.path.join(_HERE, "assets", "screens")
    try:  # PyInstaller などで同梱されたとき
        import sys

        bd = getattr(sys, "_MEIPASS", None)
        if bd:
            yield os.path.join(bd, "tjoy_seatmap", "assets", "screens")
    except Exception:
        pass


def cache_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "tjoy-seatmap", "screens")


def _name(code: str, screen_no: str) -> str:
    return f"{code}_{int(screen_no):02d}.png"


def bundled(code: str, screen_no: str):
    for d in _bundled_dirs():
        p = os.path.join(d, _name(code, screen_no))
        if os.path.isfile(p):
            with open(p, "rb") as f:
                return f.read()
    return None


def _fetch(url: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tjoy-seatmap"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (公式の画像URLのみ)
        return r.read()


def background(code: str, screen_no: str, resources: dict | None = None, bg_url: str | None = None, fetch: bool = False):
    """背景画像のバイト列。見つからなければ None。"""
    if resources:
        b = resources.get((code, str(int(screen_no))))
        if b:
            return b
    b = bundled(code, screen_no)
    if b:
        return b
    cached = os.path.join(cache_dir(), _name(code, screen_no))
    if os.path.isfile(cached):
        with open(cached, "rb") as f:
            return f.read()
    if fetch and bg_url and bg_url.startswith("https://cdn.tjoy.jp/"):
        try:
            data = _fetch(bg_url)
        except OSError:
            return None
        try:
            os.makedirs(cache_dir(), exist_ok=True)
            with open(cached, "wb") as f:
                f.write(data)
        except OSError:
            pass
        return data
    return None


def to_image(data: bytes):
    try:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None


def self_check() -> dict:
    """同梱の背景画像が読めるかを数える(exe/バイナリのビルド確認用)。"""
    n = 0
    for d in _bundled_dirs():
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.lower().endswith(".png") and to_image(open(os.path.join(d, fn), "rb").read()) is not None:
                    n += 1
            break
    return {"bundled_seat_maps": n}
