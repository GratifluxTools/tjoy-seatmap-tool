"""日本語表示用フォントの探索 (Pillow用)。"""
import glob
import os
import subprocess
import sys


def _candidates():
    bd = getattr(sys, "_MEIPASS", None)
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    dirs = [os.path.join(bd, "tjoy_seatmap", "fonts")] if bd else []
    dirs.append(here)
    for d in dirs:
        yield from sorted(glob.glob(os.path.join(d, "*.[ot]tf")))
        yield from sorted(glob.glob(os.path.join(d, "*.ttc")))
    win = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for name in ("YuGothM.ttc", "YuGothR.ttc", "meiryo.ttc", "msgothic.ttc", "YuGothic.ttf"):
        yield os.path.join(win, name)
    yield "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"
    try:
        out = subprocess.run(["fc-list", ":lang=ja", "file"], capture_output=True, text=True, timeout=5).stdout
        files = [line.split(":")[0].strip() for line in out.splitlines() if line.strip()]
        files.sort(key=lambda f: (any(k in f for k in ("Bold", "Black", "Light", "Thin")), "Serif" in f, f))
        yield from files
    except Exception:
        pass
    for pat in ("/usr/share/fonts/**/NotoSansCJK*Regular*.tt[cf]", "/usr/share/fonts/**/ipag*.ttf"):
        yield from sorted(glob.glob(pat, recursive=True))


def find_cjk_font(user_path=None):
    if user_path:
        return user_path if os.path.exists(user_path) else None
    for p in _candidates():
        if p and os.path.exists(p):
            return p
    return None
