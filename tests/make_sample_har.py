"""tests/fixtures の座席ページから、テスト用の小さなHAR(tests/sample/sample.har)を作る。

使い方: python tests/make_sample_har.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def make(src_html, out_path):
    with open(src_html, encoding="utf-8") as f:
        html = f.read()
    entries = [
        {"request": {"method": "GET", "url": "https://tjoy.jp/t-joy_emiterrace_tokorozawa/reservation/index/65924/C5011100/4/2026-11-12?type=film"},
         "response": {"status": 302, "content": {"mimeType": "text/html", "size": 0, "text": ""}}},
        {"request": {"method": "GET", "url": "https://tjoy.jp/t-joy_emiterrace_tokorozawa/reservation/choice_seat"},
         "response": {"status": 200, "content": {"mimeType": "text/html; charset=UTF-8", "size": len(html.encode("utf-8")), "text": html}}},
    ]
    har = {"log": {"version": "1.2", "creator": {"name": "tjoy-seatmap sample", "version": "1"}, "entries": entries}}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(har, f, ensure_ascii=False)
    return out_path


if __name__ == "__main__":
    print(make(os.path.join(HERE, "fixtures", "seat_tokorozawa_4.html"),
               os.path.join(HERE, "sample", "sample.har")))
