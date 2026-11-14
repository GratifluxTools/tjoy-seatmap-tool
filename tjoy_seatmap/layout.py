"""表示の配置（Scene）を作る。

- plain（プレーン）: TOHO版と同じ見た目。席番号・行記号・SCREEN帯・凡例。
- official（公式風）: 公式の座席表画像を中央に置き、上に劇場名・スクリーン番号・副題、下に凡例を付ける。
  背景色は公式画像の四隅の色から取り、画像の外側と違和感が出ないようにする。
単位は 1画素=1単位（公式風は公式画像の画素、プレーンは設計単位）。
"""
from PIL import Image

from .scene import Begin, End, ImageItem, Line, Rect, Scene, Text
from .seatpage import KIND_ORDER

CELL = 0.5          # 元画像の座標 → プレーンの設計単位（席1つ ≈ 20単位）
MARGIN = 16
LABEL_W = 20
HEADER_H = 50
SCREEN_H = 14

# 席種 → (塗り, 枠線, 文字色)。参考の配色（一般=白、プレミア=黄、ラグジュアリー=ピンク、車いす=青）に合わせる
STYLE = {
    "normal": ("#FFFFFF", "#6B7785", "#33404D"),
    "pair": ("#FFFFFF", "#6B7785", "#33404D"),
    "trio": ("#FFFFFF", "#6B7785", "#33404D"),
    "executive": ("#F5C542", "#A97C00", "#4A3600"),
    "premier": ("#F2994A", "#B8651B", "#4A2300"),
    "reclining": ("#E58FB8", "#A93F77", "#4A1230"),
    "counter": ("#6FCF97", "#2E8B57", "#0F3B22"),
}
LEGEND_NAME = {
    "normal": "一般席", "pair": "ペアシート", "trio": "トリオシート", "premier": "プレミアシート",
    "executive": "エグゼクティブシート", "reclining": "リクライニングシート", "counter": "カウンターシート",
}


def _seat_cells(screen):
    """各座席の描画用の矩形 (seat, x, y, w, h)。ペア/トリオは1席ずつ分割する。"""
    groups = {}
    for s in screen.seats:
        if s.group and s.kind in ("pair", "trio"):
            groups.setdefault(s.group, []).append(s)
    cells = []
    for s in screen.seats:
        if s.group and s.kind in ("pair", "trio"):
            members = sorted(groups[s.group], key=lambda m: m.number)
            n = len(members)
            idx = members.index(s)
            gx1 = min(m.x1 for m in members)
            gx2 = max(m.x2 for m in members)
            w = (gx2 - gx1) / n
            cells.append((s, gx1 + w * idx, s.y1, w, s.h))
        else:
            cells.append((s, s.x1, s.y1, s.w, s.h))
    return cells


def _subtitle(screen):
    """副題: 全席空席表示 / 席数 + 車いす席数（作品名は出さない）"""
    wc = screen.wheelchair_page or 0
    return f"全席空席表示  /  {len(screen.seats)}席 + 車いす席 {wc}席"


def _title(screen):
    """見出し: 劇場名 + スクリーン番号（例: T・ジョイ エミテラス所沢 シアター4）"""
    name = screen.theater_name
    if not name.startswith("T・ジョイ") and "ジョイ" not in name:
        name = f"T・ジョイ {name}"
    return f"{name}  {screen.screen_label}"


def _legend_entries(screen):
    """凡例の項目（席種・席数）。料金は表示しない。"""
    counts = {}
    for s in screen.seats:
        counts[s.kind] = counts.get(s.kind, 0) + 1
    return [(k, f"{LEGEND_NAME[k]} {counts[k]}") for k in KIND_ORDER if counts.get(k)]


def _legend_items(screen, W, y0, text_scale, box, gap_h):
    """凡例を、幅 W に収まるように折り返して中央そろえで配置する。戻り値は次の y。"""
    items = []
    entries = []
    for k, name in _legend_entries(screen):
        width = box + box * 0.45 + len(name) * text_scale * 0.95 + box * 1.1
        entries.append((k, name, width))
    avail = W - 2 * MARGIN
    rows, used = [[]], 0
    for e in entries:
        if rows[-1] and used + e[2] > avail:
            rows.append([])
            used = 0
        rows[-1].append(e)
        used += e[2]
    y = y0
    for row in rows:
        total = sum(e[2] for e in row)
        x = (W - total) / 2
        for k, name, width in row:
            fill, stroke, _t = STYLE[k]
            items.append(Rect(x, y, box, box, r=box * 0.25, fill=fill, stroke=stroke, sw=0.7))
            items.append(Text(x + box * 1.45, y + box / 2, name, text_scale, "start", "#33404D"))
            x += width
        y += gap_h
    return items, y


def _seat_objects(screen, ox, oy, scale_x, scale_y, items):
    """座席の選択用オブジェクト（透明な矩形）を items に追加する。scale は座標の倍率。"""
    cells = _seat_cells(screen)
    rows = {}
    for c in cells:
        rows.setdefault(c[0].row, []).append(c)
    used = set()
    items.append(Begin("layer-seats", {"class": "layer"}, "座席"))
    for row in sorted(rows, key=lambda r: min(c[2] for c in rows[r])):
        items.append(Begin(f"row-{row}", {"class": "row", "data-row": row}, f"{row}列"))
        for s, x, y, w, h in sorted(rows[row], key=lambda c: c[0].number):
            sid = f"seat-{s.row}-{s.number}"
            base, n = sid, 2
            while sid in used:
                sid, n = f"{base}-{n}", n + 1
            used.add(sid)
            label = f"{s.row}-{s.number}  {LEGEND_NAME[s.kind]}" + (f" (+{s.fee:,}円)" if s.fee else "")
            items.append(Begin(sid, {"class": f"seat seat-{s.kind}", "data-row": s.row,
                                     "data-number": str(s.number), "data-kind": s.kind,
                                     "data-type": s.type_code, "data-fee": str(s.fee)}, label))
            items.append(Rect(ox + x * scale_x, oy + y * scale_y, w * scale_x, h * scale_y,
                              fill="#000000", opacity=0))
            items.append(End())
        items.append(End())
    items.append(End())


def build_official_scene(screen, official_bytes, show_title=True, show_legend=True):
    """公式風: 公式画像を中央に、上下に情報帯を付ける。座標は公式画像の画素のまま。"""
    import io
    im = Image.open(io.BytesIO(official_bytes))
    im.load()
    im = im.convert("RGB")
    w, h = im.size
    bg = "#%02X%02X%02X" % im.getpixel((0, 0))   # 公式画像の左上の色を背景に使う
    lum = 0.299 * im.getpixel((0, 0))[0] + 0.587 * im.getpixel((0, 0))[1] + 0.114 * im.getpixel((0, 0))[2]
    fg = "#222222" if lum > 128 else "#F2F2F2"
    sub_fg = "#555555" if lum > 128 else "#C9CDD2"
    head = round(w * 0.105) if show_title else 0
    unit = w / 1000.0
    items = []
    if show_title:
        items.append(Text(w / 2, head * 0.36, _title(screen), 22 * unit * 1.25, "middle", fg, True))
        items.append(Text(w / 2, head * 0.74, _subtitle(screen), 13 * unit * 1.25, "middle", sub_fg))
    oy = head
    items.append(Begin("layer-background", {"class": "layer"}, "公式座席表"))
    items.append(ImageItem(0, oy, w, h, official_bytes, "image/png" if im.format == "PNG" else "image/jpeg", im))
    items.append(End())
    _seat_objects(screen, 0, oy, 1.0, 1.0, items)
    H = oy + h
    if show_legend:
        box = 15 * unit * 1.25
        gap = box * 1.9
        legend_items, y_end = _legend_items(screen, w, H + head * 0.22, 14 * unit * 1.25, box, gap)
        items.append(Begin("layer-legend", {"class": "layer"}, "凡例"))
        items.extend(legend_items)
        items.append(End())
        H = y_end + head * 0.2
    return Scene(w, H, items, bg=bg)


def build_plain_scene(screen, show_title=True, show_legend=True, show_numbers=True):
    cells = _seat_cells(screen)
    minx = min(c[1] for c in cells)
    maxx = max(c[1] + c[3] for c in cells)
    miny = min(c[2] for c in cells)
    maxy = max(c[2] + c[4] for c in cells)
    span_w = (maxx - minx) * CELL
    seat_top = (HEADER_H if show_title else 0) + SCREEN_H + 22
    ox = MARGIN + LABEL_W - minx * CELL
    oy = seat_top - miny * CELL
    W = span_w + 2 * (MARGIN + LABEL_W)
    grid_bottom = oy + maxy * CELL

    items = []
    if show_title:
        items.append(Text(W / 2, 16, _title(screen), 15, "middle", "#1E2A36", True))
        items.append(Text(W / 2, 34, _subtitle(screen), 8.5, "middle", "#5B6670"))
        items.append(Line(MARGIN, HEADER_H - 4, W - MARGIN, HEADER_H - 4, "#D5DAE0", 0.7))

    sx = ox + minx * CELL
    sy = seat_top - SCREEN_H - 4
    items.append(Begin("layer-screen", {"class": "layer"}, "スクリーン"))
    items.append(Rect(sx, sy, span_w, 11, r=4, fill="#3A4652"))
    items.append(Text(W / 2, sy + 5.5, "SCREEN  スクリーン", 7.5, "middle", "#FFFFFF", True))
    items.append(End())

    items.append(Begin("layer-seats", {"class": "layer"}, "座席"))
    rows = {}
    for c in cells:
        rows.setdefault(c[0].row, []).append(c)
    used = set()
    for row in sorted(rows, key=lambda r: min(c[2] for c in rows[r])):
        items.append(Begin(f"row-{row}", {"class": "row", "data-row": row}, f"{row}列"))
        for s, x, y, w, h in sorted(rows[row], key=lambda c: c[0].number):
            sid = f"seat-{s.row}-{s.number}"
            base, n = sid, 2
            while sid in used:
                sid, n = f"{base}-{n}", n + 1
            used.add(sid)
            fill, stroke, tcol = STYLE.get(s.kind, STYLE["normal"])
            label = f"{s.row}-{s.number}  {LEGEND_NAME[s.kind]}" + (f" (+{s.fee:,}円)" if s.fee else "")
            items.append(Begin(sid, {"class": f"seat seat-{s.kind}", "data-row": s.row,
                                     "data-number": str(s.number), "data-kind": s.kind,
                                     "data-type": s.type_code, "data-fee": str(s.fee)}, label))
            rx = ox + x * CELL + 0.5
            ry = oy + y * CELL + 0.5
            rw = w * CELL - 1
            rh = h * CELL - 1
            items.append(Rect(rx, ry, rw, rh, r=min(rw, rh) * 0.22, fill=fill, stroke=stroke, sw=0.7))
            if show_numbers:
                size = min(rw * 0.52, rh * 0.5, 9.0)
                items.append(Text(rx + rw / 2, ry + rh / 2 + 0.3, str(s.number), size, "middle", tcol))
            items.append(End())
        items.append(End())
    items.append(End())

    items.append(Begin("layer-row-labels", {"class": "layer"}, "行記号"))
    for row, cs in rows.items():
        lx = min(c[1] for c in cs)
        rx_ = max(c[1] + c[3] for c in cs)
        cy = oy + (min(c[2] for c in cs) + max(c[2] + c[4] for c in cs)) / 2 * CELL
        items.append(Text(ox + lx * CELL - 6, cy, row, 9, "end", "#4E5A66", True))
        items.append(Text(ox + rx_ * CELL + 6, cy, row, 9, "start", "#4E5A66", True))
    items.append(End())

    H = grid_bottom + 26
    if show_legend:
        items.append(Begin("layer-legend", {"class": "layer"}, "凡例"))
        legend_items, y_end = _legend_items(screen, W, H, 8, 12, 18)
        items.extend(legend_items)
        items.append(End())
        H = y_end + 4
    return Scene(W, H + MARGIN - 4, items)
