"""座席モデル。T・ジョイの座席ページ(画像マップ <area>)の属性から席種を決める。

席種の対応 (所沢・新宿の実データで確認: docs/ANALYSIS.md)::

    type-seat 1 / 5   通常席 (5 は肘掛け付きの幅の広い席)
    type-seat 2       エグゼクティブ (追加料金 +1,000円)
    type-seat 3       プレミア (+500円)
    type-seat 11      リクライニング (+200円、最前列)
    type-seat 14      カウンター (+200円、最後列)
    type-seat 1 + seat-group が2件/3件 ... ペア / トリオ (料金なし)
"""
from __future__ import annotations

from dataclasses import dataclass

# type-seat -> kind
TYPE_KINDS = {
    "1": "normal",
    "5": "normal",
    "2": "executive",
    "3": "premier",
    "11": "reclining",
    "14": "counter",
}


@dataclass(frozen=True)
class Seat:
    seat_id: str
    row: str
    num: int
    kind: str  # normal / pair / trio / premier / executive / reclining / counter
    blocked: bool  # T・ジョイでは選択不可席は無いので常に False (TOHO版との互換のため残す)
    state: str  # 元ページの状態 ("1"=空席 / "sold-out"=予約済み)
    fee: int = 0  # 追加料金 (円)
    type_code: str = "1"  # 元の席種コード (JSON出力用)
