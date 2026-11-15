"""座席1席の情報(席番号・席種)。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Seat:
    seat_id: str
    row: str
    num: int
    kind: str  # normal / executive / trio / reclining / counter / type<N>
    blocked: bool  # T・ジョイの全席空席表示では常に False
    state: str  # 元の席種コード
