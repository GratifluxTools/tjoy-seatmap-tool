"""テスト用の合成HARを作る(実際のT・ジョイのページは含まない)。

座席ページ(choice_seat)の <map> <area> 構造と、背景画像・劇場トップのスクリーン一覧を最小限に再現する。
"""
import json
import sys


def _area(sid, typ, x, y):
    return (f'<area id="{sid}" type-seat="{typ}" seat-group="null" add-change="0" '
            f'data-coords="{x},{y},{x + 40},{y + 40}" coords="{x},{y},{x + 40},{y + 40}" shape="rect" class="seat-select">')


def seat_html():
    areas = [_area("A-1", 1, 20, 20), _area("A-2", 1, 70, 20), _area("B-1", 5, 20, 70), _area("G-1", 2, 20, 120),
             _area("A-12", 11, 300, 20)]
    return ('<html><body><div class="seat"><img src="https://cdn.tjoy.jp/images/_up/theater/200_01_20240802.png" '
            'usemap="#image-map" class="map js-map"><map name="image-map">' + "\n".join(areas) + "</map></div>"
            '<div class="modal popupscreen" id="screen01"><h4 class="modal-new__title">シアター1</h4>'
            '<p>5席 +（車椅子1席）</p></div></body></html>')


def theater_html():
    return ('<html><head><title>T・ジョイ エミテラス所沢</title></head><body>'
            '<a data-toggle="modal" data-target="#screen01">シアター１</a></body></html>')


def entry(url, text, mime="text/html; charset=utf-8", status=200, method="GET"):
    return {"request": {"method": method, "url": url, "queryString": []},
            "response": {"status": status, "content": {"mimeType": mime, "size": len(text), "text": text}}}


def make(path_seat="sample_tjoy_200_1.har", path_theater="sample_tjoy_200_theater.har"):
    seat = {"log": {"version": "1.2", "entries": [
        entry("https://tjoy.jp/t-joy_emiterrace_tokorozawa/reservation/choice_seat", seat_html()),
        # 背景画像は本体が省略された状態(Fiddlerの上限)を再現する
        entry("https://cdn.tjoy.jp/images/_up/theater/200_01_20240802.png", "", mime="image/png"),
    ]}}
    theater = {"log": {"version": "1.2", "entries": [
        entry("https://tjoy.jp/t-joy_emiterrace_tokorozawa", theater_html()),
    ]}}
    with open(path_seat, "w", encoding="utf-8") as f:
        json.dump(seat, f, ensure_ascii=False)
    with open(path_theater, "w", encoding="utf-8") as f:
        json.dump(theater, f, ensure_ascii=False)


if __name__ == "__main__":
    import os

    if len(sys.argv) >= 3:
        make(*sys.argv[1:3])
    else:
        os.makedirs("tests/sample", exist_ok=True)
        make("tests/sample/sample_tjoy_200_1.har", "tests/sample/sample_tjoy_200_theater.har")
