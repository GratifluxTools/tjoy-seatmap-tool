"""公式風の描画: 公式の座席図(背景画像)をそのまま使い、タイトル帯と凡例だけを足す。

座席図には空席状態の座席・車いす席・通路・非常口・行記号がすでに描かれているので、
座席は描き直さない。SVGの座席オブジェクト(--svg-objects)は、座席の位置に透明な矩形を重ねる。
"""
from __future__ import annotations

from collections import Counter

from .scene import Begin, End, Img, Rect, Scene, Text, layer_begin, seat_marker, text_width
from .styles import LEGEND_ORDER as KIND_ORDER
from .styles import label_of, style_of

HEAD_H = 92.0  # タイトル帯の高さ(劇場名・設備・席数を大きめの文字で入れる)
SW = 17.0  # 凡例の見本の大きさ
LEG_SIZE = 13.0  # 凡例の文字の大きさ(画像の見本に合わせて大きめ)
LEG_ROW = 40.0  # 凡例の行の高さ
WHITE = "#FFFFFF"
SOFT = "#D9DADC"
BAND = "#3A4652"
PAGE = "#FFFFFF"


def build_official(sm, opts) -> Scene:
    lang = opts.lang
    bg = sm.bg  # PIL RGBA
    bw, bh = bg.size
    W = float(bw)
    obj = opts.svg_objects

    counts = Counter()
    for p in sm.box.seats:
        counts[style_of(p.seat.kind)[0]] += 1
    groups = sorted(counts, key=lambda g: (KIND_ORDER.index(g) if g in KIND_ORDER else 50, g))

    # 凡例を折り返す
    entries = []
    for g in groups:
        _grp, fill, stroke, _t = style_of(g)
        txt = f"{label_of(g, lang)} {counts[g]}"
        entries.append((fill, stroke, txt, SW + 8 + text_width(txt, LEG_SIZE) + 28))
    if sm.n_wheelchair:
        wl = "車いす席" if lang == "ja" else "Wheelchair"
        txt = f"{wl} {sm.n_wheelchair}"
        entries.append(("#E3E5E8", "#9AA3AD", txt, SW + 8 + text_width(txt, LEG_SIZE) + 28))
    rows, cur, cw = [], [], 0.0
    for e in entries:
        if cur and cw + e[3] > W - 20:
            rows.append(cur)
            cur, cw = [], 0.0
        cur.append(e)
        cw += e[3]
    if cur:
        rows.append(cur)
    leg_h = 14 + LEG_ROW * len(rows) if (opts.show_legend and rows) else 0.0
    head_h = HEAD_H if opts.show_title else 0.0
    total_h = head_h + bh + leg_h

    out = []
    if obj:
        out.append(layer_begin("header", "タイトル"))
    out.append(Rect(0, 0, W, total_h, fill=PAGE))
    if opts.show_title:
        out.append(Rect(0, 0, W, head_h, fill=BAND))
        out.append(Text(W / 2, 38, sm.title(lang), 30, "middle", WHITE, True))
        out.append(Text(W / 2, 74, sm.subtitle(lang), 18, "middle", SOFT))
    if obj:
        out.append(End())

    if obj:
        out.append(layer_begin("background", "座席図"))
    out.append(Img(0, head_h, bw, bh, "__bg__"))
    if obj:
        out.append(End())

    if obj:
        out.append(layer_begin("seats", "座席"))
        used = set()
        by_row = {}
        for p in sm.box.seats:
            by_row.setdefault(p.seat.row, []).append(p)
        for row, ps in by_row.items():
            out.append(Begin(f"row-{row}", {"data-row": row}, f"{row}列"))
            for p in ps:
                out.append(seat_marker(p, used, False, lang))
                out.append(Rect(p.x, p.y + head_h, p.w, p.h, fill=None, stroke=None))
                out.append(End())
            out.append(End())
        out.append(End())

    if leg_h and opts.show_legend:
        if obj:
            out.append(layer_begin("legend", "凡例"))
        y = head_h + bh + 6
        for row in rows:
            total = sum(e[3] for e in row) - 28
            x = (W - total) / 2
            for fill, stroke, txt, wd in row:
                out.append(Rect(x, y + (LEG_ROW - SW) / 2, SW, SW, r=4, fill=fill, stroke=stroke, sw=1.2))
                out.append(Text(x + SW + 8, y + LEG_ROW / 2, txt, LEG_SIZE, "start", "#33404D"))
                x += wd
            y += LEG_ROW
        if obj:
            out.append(End())

    images = {"__bg__": bg}
    return Scene(W, total_h, out, bg=PAGE, images=images, ss=1, inline_images=obj)
