"""席種ごとの見た目(plainスタイル用)と凡例名。

凡例名は T・ジョイの座席案内(seat-variety)の表記に合わせる。
"""
from __future__ import annotations

# kind -> (凡例グループキー, 塗り, 枠線, 文字色)
KIND_STYLE = {
    "normal": ("normal", "#FFFFFF", "#6B7785", "#33404D"),
    "executive": ("executive", "#F5C542", "#A97C00", "#4A3600"),
    "premium": ("premium", "#3B5BDB", "#1F3A9E", "#FFFFFF"),
    "reclining": ("reclining", "#B88BE0", "#7B4FB0", "#2A1745"),
    "pair": ("pair", "#A9E5BC", "#2E8B57", "#0F3B22"),
    "trio": ("trio", "#6FCF97", "#1E6B45", "#0F3B22"),
    "counter": ("counter", "#F1E4D0", "#8D6E4B", "#4A3520"),
}
_FALLBACK_PALETTE = [
    ("#E8D28A", "#9C842B", "#3D3410"),
    ("#F2994A", "#B8651B", "#4A2300"),
    ("#9DB8F5", "#4968B8", "#14264F"),
]

KIND_LABELS_JA = {
    "normal": "一般席",
    "executive": "エグゼクティブシート",
    "premium": "プレミアシート",
    "reclining": "リクライニングシート",
    "pair": "ペアシート",
    "trio": "トリオシート",
    "counter": "カウンターシート",
}
KIND_LABELS_EN = {
    "normal": "Standard",
    "executive": "Executive seat",
    "premium": "Premium seat",
    "reclining": "Reclining seat",
    "pair": "Pair seat",
    "trio": "Trio seat",
    "counter": "Counter seat",
}
WHEELCHAIR_LABEL = {"ja": "車いす席", "en": "Wheelchair"}
LEGEND_ORDER = ["normal", "executive", "premium", "reclining", "pair", "trio", "counter"]


def style_of(kind: str, blocked: bool = False):
    """(group, fill, stroke, text) を返す。未知の席種は席種コードから色を決める。"""
    if kind in KIND_STYLE:
        return KIND_STYLE[kind]
    fill, stroke, text = _FALLBACK_PALETTE[sum(map(ord, kind)) % len(_FALLBACK_PALETTE)]
    return (kind, fill, stroke, text)


def label_of(group: str, lang: str = "ja") -> str:
    table = KIND_LABELS_JA if lang == "ja" else KIND_LABELS_EN
    if group in table:
        return table[group]
    if group.startswith("type"):
        code = group[4:]
        return f"席種コード{code}" if lang == "ja" else f"Seat type {code}"
    return group
