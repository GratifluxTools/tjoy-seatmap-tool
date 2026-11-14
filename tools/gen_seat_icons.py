"""席種アイコン(icn_*.png)を tjoy_seatmap/seat_icons.py に埋め込むためのスクリプト。

使い方: python tools/gen_seat_icons.py <icn_*.png があるフォルダ>
  例: HARから抽出したフォルダ(out/icons 等)を指定する。
"""
import base64
import os
import sys

NAMES = ["icn_type1.png", "icn_type2.png", "icn_type6.png", "icn_type4-blue.png",
         "icn_type4-gold.png", "icn_type7.png", "icn_seat_dis.png"]


def main(src: str) -> int:
    lines = ['"""席種アイコン(T・ジョイ公式サイトの凡例画像)を埋め込んだもの。tools/gen_seat_icons.py で生成。"""',
             "ICONS = {"]
    for n in NAMES:
        with open(os.path.join(src, n), "rb") as f:
            lines.append(f'    "{n}": "{base64.b64encode(f.read()).decode("ascii")}",')
    lines.append("}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tjoy_seatmap", "seat_icons.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("written", os.path.normpath(out), len(NAMES), "icons")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
