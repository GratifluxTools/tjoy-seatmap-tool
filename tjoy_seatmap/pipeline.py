"""読み込み・出力の処理（CLI と GUI の共通部分）。画面(tkinter)には依存しない。"""
import os
import re
from dataclasses import dataclass, field

from .har import find_schedule_pages, find_seat_pages, iter_captures
from .render import render_official_png, render_official_svg, render_plain_png, render_plain_svg, to_webp_bytes
from .schedule import parse_schedule
from .seatpage import parse_seat_page

STYLES = ("official", "plain")


@dataclass
class ScreenItem:
    key: str
    screen: object                  # SeatScreen
    official: bytes | None = None   # 公式の座席表画像（PNG/JPEG のバイト列）
    selected: bool = True

    @property
    def label(self):
        s = self.screen
        extra = f"  {s.film_title}" if s.film_title else ""
        return f"{s.theater_name} {s.screen_label}{extra}"

    @property
    def stem(self):
        """出力ファイル名の基になる名前。TOHO版と同じく、入力ファイル名（拡張子なし）を使う。
        例: tjoy_tokorozawa_4.har（zipの中のファイルなら、その名前） → tjoy_tokorozawa_4"""
        src = self.screen.source or "seatmap"
        if "!" in src:
            src = src.split("!")[-1]
        return os.path.splitext(os.path.basename(src))[0]


@dataclass
class LoadResult:
    items: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    schedule_count: int = 0


def _schedule_titles(paths):
    titles, count = {}, 0
    for pg in find_schedule_pages(iter_captures(paths)):
        r = parse_schedule(pg["html"], slug=pg["slug"])
        for sh in r["showings"]:
            count += 1
            if sh.get("performance_id") and sh.get("title"):
                titles[sh["performance_id"]] = sh["title"]
    return titles, count


def load_screens(paths, schedule_paths=None):
    """座席HAR/ZIP/フォルダを読み込み、画面一覧を返す。"""
    res = LoadResult()
    titles, res.schedule_count = _schedule_titles(schedule_paths or [])
    seen = set()
    for pg in find_seat_pages(iter_captures(paths)):
        try:
            scr = parse_seat_page(pg["html"], source=pg["source"], slug=pg["slug"], reservation=pg["reservation"])
        except ValueError as e:
            res.warnings.append(f"{pg['source']}: {e}")
            continue
        if not scr.film_title and pg["reservation"]:
            scr.film_title = titles.get(pg["reservation"]["performance_id"])
        ident = (scr.theater_key, scr.screen_no, scr.show_date, scr.show_time)
        if ident in seen:
            res.warnings.append(f"重複を除外: {pg['source']}")
            continue
        seen.add(ident)
        for w in scr.warnings:
            res.warnings.append(f"{pg['source']}: {w}")
        res.items.append(ScreenItem(key="", screen=scr))
    res.items.sort(key=lambda it: (it.screen.theater_key, it.screen.screen_no))
    for i, it in enumerate(res.items):
        it.key = str(i)
    return res


def match_official(folder, item):
    """フォルダ内から、画面に対応する公式画像のパスを探す。

    対応する名前:
      - tjoy_<劇場キー>_screen<NN>.(png|jpg)   （リネーム済み）
      - <劇場コード3桁>_<NN>_*.png              （サイトの画像ファイル名。例 200_04_20240700.png）
    """
    from .theaters import theater_info
    s = item.screen
    code = theater_info(s.slug, s.theater_name).get("code")
    want = f"tjoy_{s.theater_key}_screen{s.screen_no:02d}".lower()
    cdn = re.compile(r"^(\d{3})_(\d{2})_")
    for root, _, names in os.walk(folder):
        for n in sorted(names):
            low = n.lower()
            if not low.endswith((".png", ".jpg", ".jpeg")):
                continue
            if low.startswith(want):
                return os.path.join(root, n)
            m = cdn.match(low)
            if m and code and m.group(1) == code and int(m.group(2)) == s.screen_no:
                return os.path.join(root, n)
    return None


def attach_official(items, folder):
    """フォルダから公式画像を探して各画面に付ける。見つからなかった画面のリストを返す。"""
    missing = []
    for it in items:
        p = match_official(folder, it)
        if p:
            with open(p, "rb") as fh:
                it.official = fh.read()
        else:
            missing.append(it.label)
    return missing


STYLE_LABEL = {"official": "official", "plain": "plane"}


def write_outputs(items, out_dir, formats=("png", "svg"), styles=("official", "plain"), svg_objects=(True, False),
                  scale=2.0, show_title=True, show_legend=True, progress=None, cancelled=None):
    """選択された画面を書き出す。戻り値は (書き出したファイル, 飛ばした説明)。

    ファイル名（参考の日比谷スクリーン1と同じ形）:
      <入力名>_official.png / <入力名>_plane.png
      <入力名>_plane_hasObject.svg / <入力名>_plane_noObject.svg（公式風も同じ形）
    """
    for st in styles:
        if st not in STYLES:
            raise ValueError(f"未知の表示形式: {st}")
    os.makedirs(out_dir, exist_ok=True)
    fmts = {f.lower() for f in formats}
    targets = [it for it in items if it.selected]
    written, skipped = [], []
    for i, it in enumerate(targets):
        if cancelled and cancelled():
            break
        if progress:
            progress(it.label, i, len(targets))
        for style in styles:
            if style == "official" and it.official is None:
                skipped.append(f"{it.label}: 公式画像がありません（公式風は作りません）")
                continue
            base = os.path.join(out_dir, f"{it.stem}_{STYLE_LABEL[style]}")
            if style == "official":
                if fmts & {"png", "webp"}:
                    img = render_official_png(it.screen, it.official, scale=1.0,
                                              show_title=show_title, show_legend=show_legend)
                    if "png" in fmts:
                        img.save(base + ".png", "PNG")
                        written.append(base + ".png")
                    if "webp" in fmts:
                        with open(base + ".webp", "wb") as fh:
                            fh.write(to_webp_bytes(img))
                        written.append(base + ".webp")
                if "svg" in fmts:
                    for obj in svg_objects:
                        p = f"{base}_{'hasObject' if obj else 'noObject'}.svg"
                        with open(p, "w", encoding="utf-8") as fh:
                            fh.write(render_official_svg(it.screen, it.official, objects=obj,
                                                         show_title=show_title, show_legend=show_legend))
                        written.append(p)
            else:
                if fmts & {"png", "webp"}:
                    img = render_plain_png(it.screen, scale=scale, show_title=show_title, show_legend=show_legend)
                    if "png" in fmts:
                        img.save(base + ".png", "PNG")
                        written.append(base + ".png")
                    if "webp" in fmts:
                        with open(base + ".webp", "wb") as fh:
                            fh.write(to_webp_bytes(img))
                        written.append(base + ".webp")
                if "svg" in fmts:
                    for obj in svg_objects:
                        p = f"{base}_{'hasObject' if obj else 'noObject'}.svg"
                        with open(p, "w", encoding="utf-8") as fh:
                            fh.write(render_plain_svg(it.screen, show_title=show_title,
                                                      show_legend=show_legend, objects=obj))
                        written.append(p)
    if progress:
        progress("完了", len(targets), len(targets))
    return written, skipped


def self_check():
    """配布物の検査: 日本語フォントの有無と、PNG/SVG の描画が動くかを確認する。"""
    from .fonts import find_cjk_font
    from .render import render_plain_svg
    from .seatpage import Seat, SeatScreen
    seat = Seat(id="A-1", row="A", number=1, x1=0, y1=0, x2=40, y2=40, type_code="1", fee=0,
                group=None, kind="normal")
    scr = SeatScreen(source="self-check", slug=None, theater_name="self-check", theater_key="check",
                     screen_no=1, screen_label="シアター1", film_title=None, show_date=None,
                     show_time=None, seats=[seat])
    try:
        img = render_plain_png(scr, scale=1.0)
        svg = render_plain_svg(scr)
        render = "ok" if img.size[0] > 0 and "<svg" in svg else "ng"
    except Exception as e:
        render = f"ng ({e})"
    return {"render": render, "cjk_font": find_cjk_font() or "none"}
