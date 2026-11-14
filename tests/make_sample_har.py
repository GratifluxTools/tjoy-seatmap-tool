"""tests/fixtures の座席ページから、テスト用の小さなHAR(tests/sample/sample.har)を作る。

使い方: python tests/make_sample_har.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def make_har(html: str, slug: str, screen: int, performance_id: str = "65924",
             film_code: str = "C5011100", date: str = "2026-11-12") -> dict:
    entries = [
        {"request": {"method": "GET", "url": f"https://tjoy.jp/{slug}/reservation/index/{performance_id}/{film_code}/{screen}/{date}?type=film"},
         "response": {"status": 302, "content": {"mimeType": "text/html", "size": 0, "text": ""}}},
        {"request": {"method": "GET", "url": f"https://tjoy.jp/{slug}/reservation/choice_seat"},
         "response": {"status": 200, "content": {"mimeType": "text/html; charset=UTF-8", "size": len(html.encode("utf-8")), "text": html}}},
    ]
    return {"log": {"version": "1.2", "creator": {"name": "tjoy-seatmap sample", "version": "1"}, "entries": entries}}


def main(out_path=None):
    src = os.path.join(HERE, "fixtures", "seat_tokorozawa_4.html")
    with open(src, encoding="utf-8") as f:
        html = f.read()
    out_path = out_path or os.path.join(HERE, "sample", "sample.har")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(make_har(html, "t-joy_emiterrace_tokorozawa", 4), f, ensure_ascii=False)
    return out_path


if __name__ == "__main__":
    print(main())
