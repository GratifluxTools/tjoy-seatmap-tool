"""劇場コード(site_cd) -> 劇場名。組み込み + 利用者が登録した名前(設定ファイル)。

site_cd は座席表画像の劇場コード(新宿=140、所沢=200)。コードが分からない劇場は、
URLのスラッグ(umeda / kyoto)を使う。
"""
from __future__ import annotations

import json
import os

BUILTIN_JA = {
    "140": "新宿バルト9",
    "200": "T・ジョイ エミテラス所沢",
    "umeda": "T・ジョイ梅田",
    "kyoto": "T・ジョイ京都",
}
BUILTIN_EN = {
    "140": "Shinjuku Balt 9",
    "200": "T-JOY Emiterrace Tokorozawa",
    "umeda": "T-JOY Umeda",
    "kyoto": "T-JOY Kyoto",
}

_USER: dict | None = None


def config_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "tjoy-seatmap", "theaters.json")


def user_names() -> dict:
    """利用者が登録した {site_cd: 劇場名}。"""
    global _USER
    if _USER is None:
        try:
            with open(config_path(), encoding="utf-8") as f:
                data = json.load(f)
            _USER = {str(k): str(v) for k, v in data.items() if str(v).strip()}
        except (OSError, ValueError, AttributeError):
            _USER = {}
    return _USER


def save_user_name(site_cd: str, name: str) -> bool:
    """劇場名を設定ファイルに記憶する(空文字なら削除)。成功したら True。"""
    d = dict(user_names())
    if name.strip():
        d[str(site_cd)] = name.strip()
    else:
        d.pop(str(site_cd), None)
    try:
        os.makedirs(os.path.dirname(config_path()), exist_ok=True)
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except OSError:
        return False
    global _USER
    _USER = d
    return True


def is_known(site_cd: str) -> bool:
    return site_cd in BUILTIN_JA or site_cd in user_names()


def name_for(site_cd: str, lang: str = "ja", override: str | None = None, schedule_name: str | None = None) -> str:
    """優先順位: 手動指定 > 利用者登録 > 組み込み > 「T・ジョイ (site コード)」。(schedule_name は互換のため受け取るだけ)"""
    if override and override.strip():
        return override.strip()
    if site_cd in user_names():
        return user_names()[site_cd]
    table = BUILTIN_JA if lang == "ja" else BUILTIN_EN
    if site_cd in table:
        return table[site_cd]
    return f"T・ジョイ (site {site_cd})" if lang == "ja" else f"T-JOY (site {site_cd})"
