"""座席の配置(画素座標)のデータ型。描画側(scene)が参照する。"""
from __future__ import annotations

from dataclasses import dataclass, field

from .seatmodel import Seat


@dataclass
class Placed:
    x: float
    y: float
    w: float
    h: float
    seat: Seat


@dataclass
class Box:
    w: float
    h: float
    seats: list = field(default_factory=list)
