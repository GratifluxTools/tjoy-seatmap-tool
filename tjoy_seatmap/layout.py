"""座席の配置(Box)。座標は座席ページの画像マップ(公式座席表画像の画素座標)のまま使う。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Placed:
    x: float
    y: float
    w: float
    h: float
    seat: object


@dataclass
class Box:
    w: float
    h: float
    seats: list = field(default_factory=list)


def trim_box(box: Box, gap: float = 0.0) -> Box:
    """座席の外接矩形に合わせて余白を除く (背景画像を使わない描画用)。"""
    if not box.seats:
        return box
    x0 = min(p.x for p in box.seats)
    y0 = min(p.y for p in box.seats)
    x1 = max(p.x + p.w for p in box.seats)
    y1 = max(p.y + p.h for p in box.seats)
    return Box(x1 - x0, y1 - y0, [Placed(p.x - x0, p.y - y0, p.w, p.h, p.seat) for p in box.seats])
