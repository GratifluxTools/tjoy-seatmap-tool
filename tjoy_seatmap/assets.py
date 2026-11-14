"""素材(公式の座席表画像・席種アイコン)の読み込み。HARに記録されたものを優先する。

優先順位: HARの記録 -> 同梱 (assets/screens/<劇場コード>_<NN>.png) -> ローカルキャッシュ -> (fetch=True のときのみ)T・ジョイサイトから取得
"""
from __future__ import annotations

import base64
import io
import os
import sys

from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))


def _dirs():
    bd = getattr(sys, "_MEIPASS", None)
    if bd:
        yield os.path.join(bd, "tjoy_seatmap", "assets")
    yield os.path.join(_HERE, "assets")


def _read(*parts):
    for d in _dirs():
        p = os.path.join(d, *parts)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
    return None


def cache_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "tjoy-seatmap", "screens")


def to_image(data: bytes):
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        return im
    except Exception:
        return None


def _fetch(url: str, timeout: float = 15.0):
    """座席表画像をT・ジョイのサイトから取得する(fetch=True のときだけ呼ぶ。通信が発生する)。"""
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tjoy-seatmap"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        return data if to_image(data) is not None else None
    except Exception:
        return None


def map_image_bytes(site_cd: str, screen_no: int | None, resources: dict | None = None,
                    fetch: bool = False, map_url: str | None = None):
    """公式の座席表画像(PNG/JPEG)のバイト列。無ければ None。"""
    if screen_no is None:
        return None
    nn = f"{int(screen_no):02d}"
    key = f"map:{site_cd}:{nn}"
    if resources and resources.get(key):
        return resources[key]
    name = f"{site_cd}_{nn}.png"
    b = _read("screens", name)
    if b:
        return b
    cached = os.path.join(cache_dir(), name)
    if os.path.exists(cached):
        with open(cached, "rb") as f:
            return f.read()
    if fetch and map_url:
        b = _fetch(map_url)
        if b:
            try:
                os.makedirs(cache_dir(), exist_ok=True)
                with open(cached, "wb") as f:
                    f.write(b)
            except OSError:
                pass
            return b
    return None


_icon_cache: dict = {}


def seat_icon(name: str, resources: dict | None = None):
    """席種アイコン(凡例の見本用)を PIL画像(RGBA)で返す。HARの記録 -> 埋め込み の順。"""
    if resources and resources.get(f"icon:{name}"):
        im = to_image(resources[f"icon:{name}"])
        if im is not None:
            return im.convert("RGBA")
    if name not in _icon_cache:
        try:
            from .seat_icons import ICONS
            data = base64.b64decode(ICONS[name]) if name in ICONS else None
        except Exception:
            data = None
        im = to_image(data) if data else None
        _icon_cache[name] = im.convert("RGBA") if im is not None else None
    return _icon_cache[name]


def self_check() -> dict:
    """同梱アセットが実行環境から読めるか(exe化の確認用)。"""
    from .seat_icons import ICONS

    maps = 0
    for d in _dirs():
        sd = os.path.join(d, "screens")
        if os.path.isdir(sd):
            maps = len([n for n in os.listdir(sd) if n.endswith(".png")])
            break
    ok_icons = sum(1 for n in ICONS if seat_icon(n) is not None)
    return {"embedded_icons": ok_icons, "bundled_maps": maps}
