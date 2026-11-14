"""公式サイトと同じ見た目のシーン: 公式の座席表画像(座席が描き込み済み)を背景に使う。

TOHO版は背景と座席gifを重ねるが、T・ジョイの座席表画像は座席そのものが描かれているので、
ここでは座席を重ねず、画像の上下にタイトル帯と凡例を付ける。SVG の座席オブジェクトは透明な矩形。
背景色は画像の左上の色(公式画像の外側の色)に合わせる。
"""
from __future__ import annotations

from collections import Counter

from . import assets
from .layout import Box
from .scene import Begin, End, Img, Rect, Scene, Text, layer_begin, seat_marker, text_width
from .styles import label_of, style_of, LEGEND_ORDER

HEAD_H = 46.0
LEGEND_ROW_H = 32.0
ICON_FOR_KIND = {
    "normal": "icn_type1.png",
    "pair": "icn_type2.png",
    "trio": "icn_type6.png",
    "premier": "icn_type4-blue.png",
    "executive": "icn_type4-gold.png",
    "reclining": "icn_type7.png",
    "counter": "icn_type1.png",
    "blocked": "icn_seat_dis.png",
}


def _rgb_of(img) -> tuple:
    """背景色: 画像の左上の色(公式画像の外側)。"""
    r, g, b = img.convert("RGB").getpixel((0, 0))
    return r, g, b


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(rgb[:3])


def _swatch(kind: str, resources: dict | None):
    """凡例の見本(席種アイコン)。カウンターは通常席アイコンに茶色の台を付けて区別する。"""
    from PIL import ImageDraw

    im = assets.seat_icon(ICON_FOR_KIND.get(kind, "icn_type1.png"), resources)
    if im is None:
        return None
    im = im.copy()
    if kind == "counter":
        d = ImageDraw.Draw(im)
        d.rectangle([0, im.height - 3, im.width - 1, im.height - 1], fill=(140, 100, 60, 255))
    return im


def build_official(sm, opts) -> Scene:
    lang = opts.lang
    box: Box = sm.box
    bg = sm.bg.convert("RGB")  # 公式の座席表画像
    bw, bh = bg.size
    color = _hex(_rgb_of(bg))
    light = sum(_rgb_of(bg)) / 3 >= 128
    fg = "#222222" if light else "#FFFFFF"
    sub = "#555555" if light else "#D9DADC"
    W = float(bw)
    k = max(1.0, bw / 600.0)  # 画像が大きいほど、見出し・凡例も比例して大きくする(600px基準)
    head_h = HEAD_H * k if opts.show_title else 0.0

    # ---- 座席の選択用オブジェクト (SVG のみ。透明な矩形) ----
    images = {"__bg__": bg.convert("RGBA")}
    body = []
    body.append(Img(0, head_h, bw, bh, "__bg__"))
    if opts.svg_objects:
        body = [layer_begin("background", "公式座席表")] + body + [End()]
        used = set()
        by_row = {}
        for p in box.seats:
            by_row.setdefault(p.seat.row, []).append(p)
        seats = [layer_begin("seats", "座席")]
        for row, lst in by_row.items():
            seats.append(Begin(f"row-{row}", {"data-row": row}, f"{row}列"))
            for p in lst:
                seats.append(seat_marker(p, used, False, lang))
                seats.append(Rect(p.x, p.y + head_h, p.w, p.h, fill="#000000", opacity=0))
                seats.append(End())
            seats.append(End())
        seats.append(End())
        body += seats

    # ---- タイトル帯 (劇場名 + スクリーン番号 / 副題: 席数 + 設備注記) ----
    head = []
    if opts.show_title:
        head.append(Text(W / 2, 17 * k, sm.title(lang), 15 * k, "middle", fg, True))
        head.append(Text(W / 2, 34 * k, sm.subtitle(lang), 8.5 * k, "middle", sub))

    # ---- 凡例 (席種ごとの見本と席数。料金は表示しない) ----
    counts = Counter(p.seat.kind for p in box.seats)
    groups = [g for g in LEGEND_ORDER if counts.get(g)] + sorted(g for g in counts if g not in LEGEND_ORDER)
    entries = []
    for g in groups:
        key = f"legend:{g}"
        sw = _swatch(g, sm.resources)
        if sw is not None:
            images[key] = sw
        sw_w = (sw.width * k) if sw is not None else 15 * k
        sw_h = min(22 * k, sw.height * k) if sw is not None else 22 * k
        txt = f"{label_of(g, lang)} {counts[g]}"
        entries.append((key if sw is not None else None, sw_w, sw_h, txt,
                        sw_w + 6 * k + text_width(txt, 8.5 * k) + 16 * k))
    leg_rows, cur, cw = [], [], 0.0
    for e in entries:
        if cur and cw + e[4] > W - 20 * k:
            leg_rows.append(cur)
            cur, cw = [], 0.0
        cur.append(e)
        cw += e[4]
    if cur:
        leg_rows.append(cur)
    row_h = LEGEND_ROW_H * k
    leg_h = 10 * k + row_h * len(leg_rows) if (opts.show_legend and leg_rows) else 0.0

    total_h = head_h + bh + leg_h
    out = [Rect(0, 0, W, total_h, fill=color)]
    if opts.svg_objects and head:
        out += [layer_begin("header", "タイトル")] + head + [End()]
    else:
        out += head
    out += body
    y = head_h + bh + 6 * k
    if opts.svg_objects and leg_rows and opts.show_legend:
        out.append(layer_begin("legend", "凡例"))
    if opts.show_legend:
        for row in leg_rows:
            total = sum(e[4] for e in row) - 16 * k
            x = (W - total) / 2
            for key, sw_w, sw_h, txt, wd in row:
                if key:
                    out.append(Img(x, y + (22 * k - sw_h) / 2 + 3 * k, sw_w, sw_h, key))
                out.append(Text(x + sw_w + 6 * k, y + 14 * k, txt, 8.5 * k, "start", fg))
                x += wd
            y += row_h
    if opts.svg_objects and leg_rows and opts.show_legend:
        out.append(End())
    return Scene(W, total_h, out, bg=color, images=images, ss=1, inline_images=opts.svg_objects)
