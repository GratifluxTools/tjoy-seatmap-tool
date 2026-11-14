"""出力画面の描画。

- 公式風(official): 公式の座席表画像をそのまま使う。
    PNG = 公式画像の複製（ファイル名だけ変える）
    SVG = 公式画像を埋め込み、その上に座席ごとの透明な選択用オブジェクトを置く
- プレーン(plain): TOHO版と同じ見た目（席番号・行記号・SCREEN帯・凡例）。PNG / SVG。
"""
import base64
import io
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

from .fonts import find_cjk_font
from .layout import _seat_cells, build_official_scene, build_plain_scene
from .scene import Begin, ImageItem, Line, End, Rect, Text
from .seatpage import KIND_LABEL

FONT_STACK = "'Noto Sans CJK JP','Yu Gothic','Meiryo','Hiragino Sans',sans-serif"
_font_cache = {}


def _font(px):
    path = find_cjk_font()
    key = (path, px)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, px) if path else ImageFont.load_default(size=px)
        except Exception:
            _font_cache[key] = ImageFont.load_default(size=px)
    return _font_cache[key]


def official_png_bytes(official_bytes):
    """公式風PNG: 公式画像をそのまま返す（描き直さない）。"""
    return bytes(official_bytes)


def scene_to_png(scene, scale=2.0):
    """Scene を PNG にする（プレーン・公式風で共通）。2倍で描いて縮小する。"""
    SS = 2
    k = scale * SS
    W, H = int(round(scene.w * k)), int(round(scene.h * k))
    img = Image.new("RGB", (W, H), scene.bg)
    d = ImageDraw.Draw(img)
    anchor = {"start": "lm", "middle": "mm", "end": "rm"}
    for it in scene.items:
        if isinstance(it, Rect):
            if it.opacity == 0:
                continue  # 透明な選択用オブジェクトは描かない
            box = [it.x * k, it.y * k, (it.x + it.w) * k - 1, (it.y + it.h) * k - 1]
            kw = {"fill": it.fill}
            if it.stroke:
                kw.update(outline=it.stroke, width=max(1, int(round(it.sw * k))))
            if it.r:
                d.rounded_rectangle(box, radius=it.r * k, **kw)
            else:
                d.rectangle(box, **kw)
        elif isinstance(it, Line):
            d.line([it.x1 * k, it.y1 * k, it.x2 * k, it.y2 * k], fill=it.color,
                   width=max(1, int(round(it.w * k))))
        elif isinstance(it, Text):
            px = max(1, int(round(it.size * k)))
            d.text((it.x * k, it.y * k), it.s, fill=it.color, font=_font(px),
                   anchor=anchor[it.anchor],
                   stroke_width=max(0, int(round(k * 0.18))) if it.bold else 0,
                   stroke_fill=it.color)
        elif isinstance(it, ImageItem):
            src = it.img.convert("RGB").resize((max(1, int(round(it.w * k))), max(1, int(round(it.h * k)))),
                                               Image.LANCZOS)
            img.paste(src, (int(round(it.x * k)), int(round(it.y * k))))
    target = (int(round(scene.w * scale)), int(round(scene.h * scale)))
    return img.resize(target, Image.LANCZOS)


def render_plain_png(screen, scale=2.0, show_title=True, show_legend=True):
    return scene_to_png(build_plain_scene(screen, show_title=show_title, show_legend=show_legend), scale)


def render_official_png(screen, official_bytes, scale=1.0, show_title=True, show_legend=True):
    return scene_to_png(build_official_scene(screen, official_bytes, show_title, show_legend), scale)


def _f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _attrs(d):
    return "".join(f' {k}="{escape(str(v), {chr(34): "&quot;"})}"' for k, v in d.items())


def _items_to_svg(items, objects=True):
    """objects=False のとき、座席の <g id="seat-..."> を作らず、図形だけを並べる（参考の「オブジェクトなし」）。"""
    out = []
    stack = []  # Begin を出したか（End の対応用）
    for it in items:
        if isinstance(it, Begin):
            is_seat = it.id.startswith("seat-")
            if is_seat and not objects:
                stack.append(False)
                continue
            stack.append(True)
            if it.attrs.get("class") == "layer":
                attrs = ""
                extra = ' inkscape:groupmode="layer" inkscape:label="' + escape(it.title) + '"'
                out.append(f'<g id="{escape(it.id)}"{extra}>')
            else:
                cls = f' class="{it.attrs["class"]}"' if "class" in it.attrs else ""
                attrs = _attrs({k: v for k, v in it.attrs.items() if k != "class"})
                out.append(f'<g id="{escape(it.id)}"{cls}{attrs}>'
                           + (f"<title>{escape(it.title)}</title>" if it.title else ""))
        elif isinstance(it, End):
            if stack and stack.pop():
                out.append("</g>")
        elif isinstance(it, Rect):
            a = f'<rect x="{_f(it.x)}" y="{_f(it.y)}" width="{_f(it.w)}" height="{_f(it.h)}"'
            if it.r:
                a += f' rx="{_f(it.r)}"'
            a += f' fill="{it.fill or "none"}"'
            if it.opacity is not None:
                a += f' fill-opacity="{_f(it.opacity)}"'
            if it.stroke:
                a += f' stroke="{it.stroke}" stroke-width="{_f(it.sw)}"'
            out.append(a + "/>")
        elif isinstance(it, ImageItem):
            b64 = base64.b64encode(bytes(it.data)).decode("ascii")
            out.append(f'<image x="{_f(it.x)}" y="{_f(it.y)}" width="{_f(it.w)}" height="{_f(it.h)}" '
                       f'href="data:{it.mime};base64,{b64}"/>')
        elif isinstance(it, Line):
            out.append(f'<line x1="{_f(it.x1)}" y1="{_f(it.y1)}" x2="{_f(it.x2)}" y2="{_f(it.y2)}" '
                       f'stroke="{it.color}" stroke-width="{_f(it.w)}" stroke-linecap="round"/>')
        elif isinstance(it, Text):
            out.append(f'<text x="{_f(it.x)}" y="{_f(it.y)}" font-size="{_f(it.size)}" '
                       f'text-anchor="{it.anchor}" dominant-baseline="central" fill="{it.color}"'
                       + (' font-weight="bold"' if it.bold else "") + f">{escape(it.s)}</text>")
    return "\n".join(out)


def render_plain_svg(screen, show_title=True, show_legend=True, objects=True):
    """プレーンSVG。objects=True は座席ごとのオブジェクト（seat-A-1）、False は図形だけ。"""
    scene = build_plain_scene(screen, show_title=show_title, show_legend=show_legend)
    return _svg_doc(scene, _items_to_svg(scene.items, objects=objects))


def _svg_doc(scene, body):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            f'width="{_f(scene.w * 2)}" height="{_f(scene.h * 2)}" viewBox="0 0 {_f(scene.w)} {_f(scene.h)}" '
            f'font-family="{FONT_STACK}">\n'
            f'<rect width="100%" height="100%" fill="{scene.bg}"/>\n'
            f"{body}\n</svg>\n")


def render_official_svg(screen, official_bytes, objects=True, show_title=True, show_legend=True):
    """公式風SVG: 公式画像を中央に埋め込み、上に劇場名・副題、下に凡例。座席は透明なオブジェクト。"""
    scene = build_official_scene(screen, official_bytes, show_title, show_legend)
    return _svg_doc(scene, _items_to_svg(scene.items, objects=objects))


def to_webp_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "WEBP", lossless=True, method=6)
    return buf.getvalue()
