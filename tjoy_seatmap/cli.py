"""コマンドライン: HAR/ZIP/フォルダから T・ジョイ座席表（全席空席）を出力する。"""
import argparse
import json
import os
import sys

from . import __version__
from .pipeline import attach_official, load_screens, self_check, write_outputs


def _log(msg):
    print(msg, file=sys.stderr)


def build_parser():
    p = argparse.ArgumentParser(prog="tjoy-seatmap-cli", description="T・ジョイ座席表（全席空席）を生成")
    p.add_argument("inputs", nargs="*", help="座席HAR / ZIP / フォルダ")
    p.add_argument("-o", "--out", default="seatmaps", help="出力フォルダ（既定: seatmaps）")
    p.add_argument("-s", "--style", default="official,plain",
                   help="表示形式 official(公式風) / plain(プレーン) をカンマ区切り（既定: 両方）")
    p.add_argument("--svg-objects", default="on,off",
                   help="SVGのオブジェクト: on=座席ごとにオブジェクト化 / off=図形のみ（既定: 両方）")
    p.add_argument("-f", "--format", default="png,svg", help="出力形式 png,svg,webp（既定: png,svg）")
    p.add_argument("--official-dir", help="公式の座席表画像のフォルダ（tjoy_<劇場>_screenNN.png または 200_04_*.png）")
    p.add_argument("--official", help="公式の座席表画像1枚（画面が1つのときだけ）")
    p.add_argument("--scale", type=float, default=2.0, help="プレーンのPNG/WebPの倍率（既定 2）")
    p.add_argument("--no-title", action="store_true", help="プレーンの上部の劇場名・作品名を描かない")
    p.add_argument("--no-legend", action="store_true", help="プレーンの下部の凡例を描かない")
    p.add_argument("--schedule", action="append", default=[], help="スケジュールHAR（作品名の補完。複数可）")
    p.add_argument("--json", action="store_true", help="検出した画面の一覧をJSONで表示")
    p.add_argument("--self-check", action="store_true", help="描画と日本語フォントを検査して終了")
    p.add_argument("--version", action="version", version=__version__)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.self_check:
        info = self_check()
        print(f"render={info['render']} cjk_font={info['cjk_font']}")
        return 0 if info["render"] == "ok" else 1
    if not args.inputs:
        _log("入力（HAR/ZIP/フォルダ）を指定してください。")
        return 2
    formats = [f.strip().lower() for f in args.format.split(",") if f.strip()]
    styles = [x.strip().lower() for x in args.style.split(",") if x.strip()]
    if set(styles) - {"official", "plain"}:
        _log("-s は official / plain から指定してください。")
        return 2
    objs = [x.strip().lower() for x in args.svg_objects.split(",") if x.strip()]
    if set(objs) - {"on", "off"}:
        _log("--svg-objects は on / off から指定してください。")
        return 2
    svg_objects = tuple(x == "on" for x in dict.fromkeys(objs))
    unknown = set(formats) - {"png", "svg", "webp"}
    if unknown:
        _log(f"未知の形式: {', '.join(sorted(unknown))}")
        return 2

    res = load_screens(args.inputs, args.schedule)
    for w in res.warnings:
        _log(f"注意: {w}")
    if not res.items:
        _log("座席ページ(choice_seat)が見つかりませんでした。")
        return 1
    if args.json:
        print(json.dumps([{"theater": it.screen.theater_name, "screen": it.screen.screen_no,
                           "film": it.screen.film_title, "seats": len(it.screen.seats)} for it in res.items],
                         ensure_ascii=False, indent=2))

    if args.official:
        if len(res.items) != 1:
            _log("--official は画面が1つのときだけ指定できます（複数は --official-dir）。")
            return 2
        with open(args.official, "rb") as fh:
            res.items[0].official = fh.read()
    if args.official_dir:
        for label in attach_official(res.items, args.official_dir):
            _log(f"公式画像が見つかりません: {label}")
    if "official" in styles and not any(it.official for it in res.items):
        _log("公式風の画像がありません。--official-dir で公式画像を指定すると公式風も作れます。")

    written, skipped = write_outputs(res.items, args.out, formats, styles=styles, svg_objects=svg_objects,
                                     scale=args.scale, show_title=not args.no_title,
                                     show_legend=not args.no_legend)
    for s in skipped:
        _log(f"飛ばしました: {s}")
    _log(f"完了: {len(written)}ファイル → {os.path.abspath(args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
