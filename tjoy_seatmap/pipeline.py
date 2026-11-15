"""HAR群 -> 座席表(SeatMap) -> 画像ファイル、までの処理。CLI/GUI共通。"""
from __future__ import annotations

import dataclasses
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field

from . import assets, hario, theaters
from .official import build_official
from .render_png import FontSet, make_fontset, render_png
from .render_svg import render_svg
from .scene import Options, build_scene
from .schedule import ScheduleIndex, theater_code_of_slug
from .seatpage import Box, Placed, parse_seat_page
from .styles import style_of

PLAIN_K = 0.4  # 座席の画素座標 -> plainスタイルの描画単位(参考画像の座席の大きさに合わせて大きめ)


@dataclass
class SeatMap:
    stem: str
    site_cd: str  # 劇場コード
    screen_cd: str  # 画面番号(2桁)
    screen_no: str | None
    box: Box  # 座席の画素座標(背景画像の座標系)
    source: str
    params: dict
    stated: tuple | None  # (席数, 車いす席数) ページ表記
    facility: str
    schedule_info: dict | None
    warnings: list = field(default_factory=list)
    theater_override: str | None = None
    schedule_theater: str | None = None
    fetch_missing: bool = False
    sheet: object = None  # 互換用(未使用)
    bg: object = None  # 背景画像 (PIL.Image) / None
    resources: dict = field(default_factory=dict)

    @property
    def counts(self) -> Counter:
        c = Counter()
        for p in self.box.seats:
            c[style_of(p.seat.kind)[0]] += 1
        return c

    @property
    def n_seats(self) -> int:
        return len(self.box.seats)

    @property
    def n_wheelchair(self) -> int:
        return self.stated[1] if self.stated else 0

    def theater_name(self, lang: str = "ja") -> str:
        return theaters.name_for(self.site_cd, lang, self.theater_override, self.schedule_theater)

    @property
    def theater_known(self) -> bool:
        return (
            bool(self.theater_override and self.theater_override.strip())
            or theaters.is_known(self.site_cd)
            or bool(self.schedule_theater)
        )

    def screen_label(self, lang: str = "ja") -> str:
        if self.schedule_info and self.schedule_info.get("name"):
            return self.schedule_info["name"]
        if self.screen_no:
            return f"シアター{self.screen_no}" if lang == "ja" else f"Theater {self.screen_no}"
        return "シアター(不明)" if lang == "ja" else "Theater (unknown)"

    def title(self, lang: str = "ja") -> str:
        return f"{self.theater_name(lang)} {self.screen_label(lang)}"

    def subtitle(self, lang: str = "ja") -> str:
        if lang == "ja":
            parts = [self.facility] if self.facility else []
            parts += ["全席空席表示", f"{self.n_seats}席 + 車いす席 {self.n_wheelchair}席"]
        else:
            parts = [self.facility] if self.facility else []
            parts += ["All seats shown as available", f"{self.n_seats} seats + {self.n_wheelchair} wheelchair"]
        return "  /  ".join(parts)


def build_seatmaps(paths, schedule_paths=(), log=print, fetch_missing=False) -> list:
    """入力(.har/.zip/フォルダ)から SeatMap のリストを作る。"""
    sched = ScheduleIndex()
    aux_inputs = set()  # 座席ページ以外に、劇場・施設の情報を含む入力
    blobs = [(n, d, False) for n, d in hario.iter_har_blobs(list(paths))]
    blobs += [(n, d, True) for n, d in hario.iter_har_blobs(list(schedule_paths))]
    if not blobs:
        log("入力に .har ファイルが見つかりません。")
    hars, shared = [], {}
    for name, data, is_sched in blobs:
        try:
            har = hario.parse_har(data)
        except ValueError as e:
            log(f"[skip] {name}: HARとして読めません ({e})")
            continue
        hars.append((name, har, is_sched))
        # 背景画像は HAR の Fiddler 上限(約60KB超)で本体が欠けることがある。全HARの分を共有する。
        shared.update(hario.find_background_resources(har))
    for name, har, _s in hars:
        for e in har.get("log", {}).get("entries", []):
            url = e.get("request", {}).get("url", "")
            m = re.match(r"^https?://tjoy\.jp/([^/?#]+?)(?:/facilities)?/?$", url)
            code = theater_code_of_slug(m.group(1)) if m else None
            if not code:
                continue
            text = hario.entry_text(e)
            if "data-target=\"#screen" in text:
                sched.add_theater_page(text, code)
            if sched.add_facility_page(text, code):  # 施設案内ページ(/facilities)の「シアター情報」表
                aux_inputs.add(name)
            elif "data-target=\"#screen" in text:
                aux_inputs.add(name)

    pages, order = {}, []
    for name, har, is_sched in hars:
        found = hario.find_seat_pages(har, name)
        if not found and not is_sched and name not in aux_inputs:
            log(f"[skip] {name}: 座席ページ(choice_seat)が見つかりません。座席選択画面を開いた状態で保存したHARか確認してください。")
            continue
        for pg in found:
            pg.resources = shared
            parsed = parse_seat_page(pg.html)
            slug_code = theater_code_of_slug(pg.slug)
            code = parsed.theater_code or slug_code or ""
            key = (code, parsed.screen_no or "")
            if key in pages:
                continue
            pages[key] = (pg, parsed)
            order.append(key)

    per_source = Counter(pages[k][0].source for k in order)
    maps = []
    for key in order:
        pg, parsed = pages[key]
        if not parsed.seats:
            log(f"[skip] {pg.source}: 座席が見つかりません")
            continue
        code, screen_no = key
        bg = None
        data = assets.background(code, screen_no or "0", pg.resources, parsed.bg_url, fetch=fetch_missing)
        if data:
            bg = assets.to_image(data)
        note = ""
        if bg is None:
            note = (f"{pg.source}: この画面の背景画像がHARに無いため、座席の位置から描画しました"
                    "(公式の座席図にするには --fetch-missing か、HARを取り直してください)。")
        if bg is not None:
            box = Box(w=float(bg.size[0]), h=float(bg.size[1]), seats=parsed.seats)
        else:
            mw = max((p.x + p.w for p in parsed.seats), default=0)
            mh = max((p.y + p.h for p in parsed.seats), default=0)
            box = Box(w=mw + 10, h=mh + 10, seats=parsed.seats)
        stem = os.path.splitext(pg.source)[0]
        if per_source[pg.source] > 1:
            stem += f"_{screen_no}"
        fac = sched.facility(code, screen_no) if screen_no else ""
        sm = SeatMap(
            stem=stem,
            site_cd=code,
            screen_cd=screen_no or "",
            screen_no=screen_no,
            box=box,
            source=pg.source,
            params={},
            stated=parsed.stated,
            facility=fac,
            schedule_info=sched.lookup(code, screen_no) if screen_no else None,
            schedule_theater=sched.theater_name(code),
            bg=bg,
            resources=pg.resources,
            fetch_missing=fetch_missing,
        )
        if note:
            sm.warnings.append(note)
        if not sched.has_facility_info(code):
            sm.warnings.append(
                "施設案内ページのHARが無いため、特別設備は表示していません(このHARを追加すると表示されます)。"
            )
        if sm.stated and sm.stated[0] != sm.n_seats:
            sm.warnings.append(
                f"ページ表記({sm.stated[0]}席)と解析結果({sm.n_seats}席)が一致しません。座席表に実在する席のみ描画しています。"
            )
        maps.append(sm)
    return maps


def _plain_box(box: Box, k: float) -> Box:
    seats = [Placed(p.x * k, p.y * k, p.w * k, p.h * k, p.seat) for p in box.seats]
    return Box(w=box.w * k, h=box.h * k, seats=seats)


def make_scene(sm: SeatMap, opts: Options):
    if opts.style == "official" and sm.bg is not None:
        return build_official(sm, opts)
    tb = _plain_box(sm.box, PLAIN_K)
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
        "seats": sm.n_seats,
        "wheelchair": sm.n_wheelchair,
        "counts": dict(sm.counts),
        "seat_list": [
            {
                "id": p.seat.seat_id,
                "row": p.seat.row,
                "number": p.seat.num,
                "kind": p.seat.kind,
                "type_code": p.seat.state,
                "x": p.x,
                "y": p.y,
                "w": p.w,
                "h": p.h,
            }
            for p in sm.box.seats
        ],
    }


def save_webp(img, path: str) -> None:
    """PNGを変換しただけの見た目になるよう、ロスレス(劣化なし)でWebPに保存する。"""
    img.save(path, "WEBP", lossless=True, quality=100, method=6)


def output_name(stem: str, kind: str, opts: Options) -> str:
    """出力ファイル名。PNG/WebP: <入力名>_plane.png / _official.png。SVG: _hasObject / _noObject。JSON: <入力名>.json"""
    if kind == "json":
        return f"{stem}.json"
    style = "official" if opts.style == "official" else "plane"
    if kind == "svg":
        return f"{stem}_{style}_{'hasObject' if opts.svg_objects else 'noObject'}.svg"
    return f"{stem}_{style}.{kind}"


def write_outputs(sm: SeatMap, outdir: str, formats, opts: Options, scale: float, fonts: FontSet, with_json=False, progress=None) -> list:
    """1画面分のファイルを書き出す。progress(path, finished) で進捗通知。例外を投げると中断する。"""
    os.makedirs(outdir, exist_ok=True)
    if opts.style == "official" and sm.bg is None:  # 背景が無い画面は自動描画(plain)になるので名前もそろえる
        opts = dataclasses.replace(opts, style="plain")
    written = []
    plan = [kind for kind in ("png", "webp", "svg") if kind in formats]
    if with_json:
        plan.append("json")
    img = None  # PNGとWebPは同じ画像から作る(1回だけ描画)
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
