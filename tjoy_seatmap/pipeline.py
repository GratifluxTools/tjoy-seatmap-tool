"""HAR群 -> 座席表(SeatMap) -> 画像ファイル、までの処理。CLI/GUI共通。"""
from __future__ import annotations

import dataclasses
import json
import os
from collections import Counter
from dataclasses import dataclass, field

from . import assets, hario, theaters
from .layout import Box, trim_box
from .official import build_official
from .render_png import FontSet, make_fontset, render_png  # noqa: F401 (make_fontset は CLI/GUI から使う)
from .render_svg import render_svg
from .scene import Options, build_scene
from .seatparse import SeatPageError, parse_seat_html
from .styles import style_of


@dataclass
class SeatMap:
    stem: str
    site_cd: str
    screen_cd: str
    screen_no: str
    box: Box
    source: str
    params: dict
    stated: tuple | None  # (席数, 車いす席数) ページ表記
    facility: str  # 特別設備 (例: IMAXⓇ Dolby AtmosⓇ)
    show_date: str = ""
    show_time: str = ""
    warnings: list = field(default_factory=list)
    theater_override: str | None = None  # 手動指定の劇場名
    fetch_missing: bool = False
    bg: object = None  # 公式の座席表画像 (PIL.Image, RGB) / None
    resources: dict = field(default_factory=dict)

    @property
    def counts(self) -> Counter:
        c = Counter()
        for p in self.box.seats:
            c[style_of(p.seat.kind, p.seat.blocked)[0]] += 1
        return c

    @property
    def n_seats(self) -> int:
        return len(self.box.seats)

    @property
    def n_wheelchair(self) -> int:
        return self.stated[1] if self.stated else 0

    def theater_name(self, lang: str = "ja") -> str:
        return theaters.name_for(self.site_cd, lang, self.theater_override)

    @property
    def theater_known(self) -> bool:
        return bool(self.theater_override and self.theater_override.strip()) or theaters.is_known(self.site_cd)

    def screen_label(self, lang: str = "ja") -> str:
        if lang == "ja":
            return f"シアター{self.screen_no}"
        return f"Theater {self.screen_no}"

    def title(self, lang: str = "ja") -> str:
        """劇場名 + シアター番号 (タイトル帯・plainスタイルの見出し)。"""
        return f"{self.theater_name(lang)} {self.screen_label(lang)}"

    def subtitle(self, lang: str = "ja") -> str:
        if lang == "ja":
            s = f"全席空席表示  /  {self.n_seats}席 + 車いす席 {self.n_wheelchair}席"
        else:
            s = f"All seats shown as available  /  {self.n_seats} seats + {self.n_wheelchair} wheelchair"
        if self.facility:
            s += f"  /  {self.facility}"
        return s


def build_seatmaps(paths, log=print, fetch_missing=False) -> list:
    """入力(.har/.txt/.zip/フォルダ)から SeatMap のリストを作る。"""
    blobs = list(hario.iter_har_blobs(list(paths)))
    if not blobs:
        log("入力に .har / .txt ファイルが見つかりません。")
    pages, order = {}, []
    hars = []
    for name, data in blobs:
        try:
            har = hario.parse_har(data)
        except ValueError as e:
            log(f"[skip] {name}: HARとして読めません ({e})")
            continue
        hars.append((name, har))
    # 公式画像・アイコンは、どのHARに記録されていても使えるように全HARで共有する
    shared = {}
    for _name, har in hars:
        shared.update(hario.find_resources(har))
    for name, har in hars:
        found = hario.find_seat_pages(har, name)
        if not found:
            log(f"[skip] {name}: 座席ページ(choice_seat)が見つかりません。座席選択画面を開いた状態で保存したHARか確認してください。")
            continue
        for pg in found:
            pg.resources = shared
            key = (pg.site_cd, pg.params.get("screen_no_map") or pg.params.get("screen_no"), pg.params.get("performance_id"))
            if key in pages:
                continue
            pages[key] = pg
            order.append(key)

    per_source = Counter(pages[k].source for k in order)
    maps = []
    for key in order:
        pg = pages[key]
        try:
            parsed = parse_seat_html(pg.html)
        except SeatPageError as e:
            log(f"[skip] {pg.source}: {e}")
            continue
        screen_no = parsed["screen_no"]
        site_cd = pg.site_cd if pg.site_cd.isdigit() else (pg.site_cd or "unknown")
        if parsed["box"].seats == []:
            log(f"[skip] {pg.source}: 座席が見つかりません")
            continue
        stem = os.path.splitext(pg.source)[0]
        if per_source[pg.source] > 1:
            stem += f"_{screen_no}"
        notes = list(parsed["warnings"])
        raw = assets.map_image_bytes(site_cd, screen_no, pg.resources, fetch_missing, parsed["map_url"])
        bg = assets.to_image(raw).convert("RGB") if raw and assets.to_image(raw) is not None else None
        if bg is None:
            notes.append(f"{pg.source}: この画面の公式の座席表画像がありません。公式風は作れません"
                         "(『キャッシュを無効化』でHARを取り直すか、--fetch-missing で取得してください)。プレーンは作れます。")
        sm = SeatMap(
            stem=stem, site_cd=site_cd, screen_cd=str(screen_no), screen_no=str(screen_no),
            box=parsed["box"], source=pg.source, params=pg.params, stated=parsed["stated"],
            facility=parsed["facility"], show_date=parsed["show_date"], show_time=parsed["show_time"],
            warnings=notes, fetch_missing=fetch_missing, bg=bg, resources=pg.resources,
        )
        maps.append(sm)
    return maps


def make_scene(sm: SeatMap, opts: Options):
    if opts.style == "official" and sm.bg is not None:
        return build_official(sm, opts)
    tb = trim_box(sm.box)
    return build_scene(tb, sm.title(opts.lang), sm.subtitle(opts.lang), opts)


def render_image(sm: SeatMap, opts: Options, scale: float, fonts: FontSet):
    """PNG用のPIL画像。日本語フォントが無ければ自動で英語表記にする。"""
    o = dataclasses.replace(opts, lang="ja" if fonts.has_cjk else "en", svg_objects=False)
    return render_png(make_scene(sm, o), scale, fonts)


def render_svg_text(sm: SeatMap, opts: Options, scale: float) -> str:
    return render_svg(make_scene(sm, dataclasses.replace(opts, lang="ja")), scale)


def to_json(sm: SeatMap) -> dict:
    return {
        "source": sm.source,
        "site_cd": sm.site_cd,
        "screen_no": sm.screen_no,
        "title": sm.title("ja"),
        "subtitle": sm.subtitle("ja"),
        "date": sm.show_date,
        "time": sm.show_time,
        "seats": sm.n_seats,
        "wheelchair": sm.n_wheelchair,
        "facility": sm.facility,
        "counts": dict(sm.counts),
        "seat_list": [
            {"id": p.seat.seat_id, "row": p.seat.row, "number": p.seat.num, "kind": p.seat.kind,
             "fee": p.seat.fee, "x": p.x, "y": p.y, "w": p.w, "h": p.h}
            for p in sm.box.seats
        ],
    }


def save_webp(img, path: str) -> None:
    """PNGを変換しただけの見た目になるよう、ロスレス(劣化なし)でWebPに保存する。"""
    img.save(path, "WEBP", lossless=True, quality=100, method=6)


def output_name(stem: str, kind: str, opts: Options) -> str:
    """出力ファイル名。
    PNG/WebP: <入力名>_plane.png / <入力名>_official.png
    SVG:      <入力名>_plane_hasObject.svg / <入力名>_plane_noObject.svg (公式風は official_*)
    JSON:     <入力名>.json
    """
    if kind == "json":
        return f"{stem}.json"
    style = "official" if opts.style == "official" else "plane"
    if kind == "svg":
        return f"{stem}_{style}_{'hasObject' if opts.svg_objects else 'noObject'}.svg"
    return f"{stem}_{style}.{kind}"


def write_outputs(sm: SeatMap, outdir: str, formats, opts: Options, scale: float, fonts: FontSet,
                  with_json=False, progress=None) -> list:
    """1画面分のファイルを書き出す。progress(path, finished) を呼び、例外で中断できる(GUIの中止)。"""
    os.makedirs(outdir, exist_ok=True)
    if opts.style == "official" and sm.bg is None:
        opts = dataclasses.replace(opts, style="plain")  # 公式の座席表画像が無い画面は、プレーンとして出力する
    written = []
    plan = [kind for kind in ("png", "webp", "svg") if kind in formats]
    if with_json:
        plan.append("json")
    img = None
    for kind in plan:
        path = os.path.join(outdir, output_name(sm.stem, kind, opts))
        if progress is not None:
            progress(path, False)
        if kind in ("png", "webp"):
            if img is None:
                img = render_image(sm, opts, scale, fonts)
            if kind == "png":
                img.save(path)
            else:
                save_webp(img, path)
        elif kind == "svg":
            with open(path, "w", encoding="utf-8") as f:
                f.write(render_svg_text(sm, opts, scale))
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(to_json(sm), f, ensure_ascii=False, indent=1)
        written.append(path)
        if progress is not None:
            progress(path, True)
    return written
