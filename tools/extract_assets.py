"""T・ジョイのHARから、座席表画像(公式)と席種アイコンを取り出して、同梱用のフォルダに保存する。

使い方:
  python tools/extract_assets.py <HAR / ZIP / フォルダ ...> [--out tjoy_seatmap/assets/screens]

注意: 開発者ツールの「キャッシュを無効化」にチェックを入れて取得したHARには画像の本体が入ります。
取り出した座席表画像は T・ジョイの著作物です(リポジトリは非公開にしてください)。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tjoy_seatmap import hario  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="+")
    p.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                                  "tjoy_seatmap", "assets", "screens"))
    args = p.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    saved = 0
    for name, data in hario.iter_har_blobs(args.inputs):
        har = hario.parse_har(data)
        for key, blob in hario.find_resources(har).items():
            if not key.startswith("map:"):
                continue
            _, code, nn = key.split(":")
            path = os.path.join(args.out, f"{code}_{nn}.png")
            with open(path, "wb") as f:
                f.write(blob)
            print(f"saved {path} (from {name})")
            saved += 1
    print(f"{saved} 件保存しました")
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(main())
