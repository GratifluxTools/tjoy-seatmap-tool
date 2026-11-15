"""劇場コード -> 劇場名。組み込み + 利用者が登録した名前(設定ファイル)。

劇場コードは座席表の背景画像のファイル名(例: cdn.tjoy.jp/images/_up/theater/200_01_...png の 200)由来。
"""
from __future__ import annotations

import json
import os

BUILTIN_JA = {
    "140": "新宿バルト9",
    "200": "T・ジョイ エミテラス所沢",
    "320": "T・ジョイ梅田",
    "360": "T・ジョイ京都",
}
BUILTIN_EN = {
    "140": "Shinjuku Baruto 9",
    "200": "T-Joy Emiterrace Tokorozawa",
    "320": "T-Joy Umeda",
    "360": "T-Joy Kyoto",
}
# 劇場トップのURLスラッグ -> 劇場コード
CODE_OF_SLUG = {
    "shinjuku_wald9": "140",
    "t-joy_emiterrace_tokorozawa": "200",
    "t-joy_umeda": "320",
    "t-joy_kyoto": "360",
}

_USER: dict | None = None


def config_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "tjoy-seatmap", "theaters.json")


def user_names() -> dict:
    """利用者が登録した {劇場コード: 劇場名}。"""
    global _USER
    if _USER is None:
        try:
            with open(config_path(), encoding="utf-8") as f:
                data = json.load(f)
            _USER = {str(k): str(v) for k, v in data.items() if str(v).strip()}
        except (OSError, ValueError, AttributeError):
            _USER = {}
    return _USER


def save_user_name(code: str, name: str) -> bool:
    """劇場名を設定ファイルに記憶する(空文字なら削除)。成功したら True。"""
    d = dict(user_names())
    if name.strip():
        d[str(code)] = name.strip()
    else:
        d.pop(str(code), None)
    try:
        os.makedirs(os.path.dirname(config_path()), exist_ok=True)
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except OSError:
        return False
    global _USER
    _USER = d
    return True


def is_known(code: str) -> bool:
    return code in BUILTIN_JA or code in user_names()


def name_for(code: str, lang: str = "ja", override: str | None = None, schedule_name: str | None = None) -> str:
    """優先順位: 手動指定 > 利用者登録 > 組み込み > スケジュールHAR由来 > 「T・ジョイ (コード)」。"""
    if override and override.strip():
        return override.strip()
    if code in user_names():
        return user_names()[code]
    table = BUILTIN_JA if lang == "ja" else BUILTIN_EN
    if code in table:
        return table[code]
    if lang == "ja" and schedule_name and schedule_name.strip():
        return schedule_name.strip()
    return f"T・ジョイ (code {code})" if lang != "ja" else f"T・ジョイ (コード {code})"
