"""席種ごとの見た目(plainスタイル用)と凡例名。

凡例の並び順 LEGEND_ORDER。色は参考の座席表(日比谷)に合わせて、一般席=白、特別席=色付き。
ペア/トリオは料金が無いので一般席と同じ白。
"""
from __future__ import annotations

# kind -> (凡例グループキー, 塗り, 枠線, 文字色)
KIND_STYLE = {
    "normal": ("normal", "#FFFFFF", "#6B7785", "#33404D"),
    "pair": ("pair", "#FFFFFF", "#6B7785", "#33404D"),
    "trio": ("trio", "#FFFFFF", "#6B7785", "#33404D"),
    "premier": ("premier", "#F2994A", "#B8651B", "#4A2300"),
    "executive": ("executive", "#F5C542", "#A97C00", "#4A3600"),
    "reclining": ("reclining", "#E58FB8", "#A93F77", "#4A1230"),
    "counter": ("counter", "#6FCF97", "#2E8B57", "#0F3B22"),
}
BLOCKED_STYLE = ("blocked", "#E3E6EA", "#9AA3AE", "#7B8591")
LEGEND_ORDER = ["normal", "pair", "trio", "premier", "executive", "reclining", "counter"]
_FALLBACK_PALETTE = [
    ("#C7A6E8", "#7B4FB0", "#2A1745"),
    ("#8ADBD3", "#2B8C84", "#0D3A36"),
]

KIND_LABELS_JA = {
    "normal": "一般席",
    "pair": "ペアシート",
    "trio": "トリオシート",
    "premier": "プレミアシート",
    "executive": "エグゼクティブシート",
    "reclining": "リクライニングシート",
    "counter": "カウンターシート",
    "blocked": "選択不可席",
}
KIND_LABELS_EN = {
    "normal": "Standard",
    "pair": "Pair Seat",
    "trio": "Trio Seat",
    "premier": "Premier Seat",
    "executive": "Executive Seat",
    "reclining": "Reclining Seat",
    "counter": "Counter Seat",
    "blocked": "Not selectable",
}


def style_of(kind: str, blocked: bool = False):
    """(group, fill, stroke, text) を返す。未知の席種は種別名で色を決める。"""
    if blocked:
        return BLOCKED_STYLE
    if kind in KIND_STYLE:
        return KIND_STYLE[kind]
    fill, stroke, text = _FALLBACK_PALETTE[sum(map(ord, kind)) % len(_FALLBACK_PALETTE)]
    return (kind, fill, stroke, text)


def label_of(group: str, lang: str = "ja") -> str:
    table = KIND_LABELS_JA if lang == "ja" else KIND_LABELS_EN
    if group in table:
        return table[group]
    return f"特別席({group})" if lang == "ja" else f"Special ({group})"
