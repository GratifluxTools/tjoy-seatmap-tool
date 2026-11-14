"""劇場スラッグ → 表示名・短い識別子。"""
THEATERS = {
    "shinjuku_wald9": {"name": "新宿バルト9", "short": "新宿バルト9", "key": "shinjuku", "code": "140"},
    "t-joy_emiterrace_tokorozawa": {"name": "T・ジョイ エミテラス所沢", "short": "エミテラス所沢", "key": "tokorozawa", "code": "200"},
    "t-joy_umeda": {"name": "T・ジョイ梅田", "short": "梅田", "key": "umeda", "code": None},
    "t-joy_kyoto": {"name": "T・ジョイ京都", "short": "京都", "key": "kyoto", "code": None},
}


def theater_info(slug, name=None):
    """スラッグ、無ければ劇場名から劇場情報を引く。"""
    if slug in THEATERS:
        return THEATERS[slug]
    if name:
        for info in THEATERS.values():
            if info["name"] == name:
                return info
    return {"name": name or slug or "不明", "short": (name or slug or "不明").replace("T・ジョイ", ""), "key": slug or "unknown", "code": None}
