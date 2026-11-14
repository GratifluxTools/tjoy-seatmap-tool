"""劇場トップ（上映スケジュール）のHTMLから上映回一覧を作る。"""
import re
import unicodedata
from bs4 import BeautifulSoup

from .theaters import theater_info


def _ancestor(li):
    for p in li.parents:
        if getattr(p, "name", None) is None:
            continue
        cls = p.get("class") or []
        pid = p.get("id") or ""
        if p.name == "div" and "film-content" in cls and pid.startswith("film-"):
            return "film", p
        if p.name == "section" and pid.startswith("event-"):
            return "event", p
    return None, None


def parse_schedule(html, slug=None):
    soup = BeautifulSoup(html, "html.parser")
    t = soup.find("title")
    info = theater_info(slug)
    show_date = None
    inp = soup.find("input", id="showDate")
    if inp:
        show_date = inp.get("value")
    rows, seen = [], set()
    for li in soup.select("li.theater-item"):
        kind, anc = _ancestor(li)
        if anc is None:
            continue
        if kind == "film":
            h5 = anc.find_previous("h5", class_="js-title-film")
            tp = anc.find_previous("p", class_="time-film")
            rc = anc.find_previous("span", class_=re.compile("coup-rate"))
        else:
            h5 = anc.find("h5")
            tp = anc.find("p", class_="time-film")
            rc = anc.find("span", class_=re.compile("coup-rate"))
        a = li.select_one(".theater-name a")
        label = a.get_text(strip=True) if a else ""
        nums = re.findall(r"\d+", _norm(label))
        body = li.select_one(".schedule-box-body")
        st = li.select_one(".schedule-status")
        onclick = (body.get("onclick") if body else "") or (st.get("onclick") if st else "") or ""
        m = re.search(r"/([^/']+)/reservation/index/(\d+)/([A-Za-z0-9]+)/(\d+)/(\d{4}-\d{2}-\d{2})\?type=(\w+)", onclick)
        time_el = li.select_one(".schedule-time")
        status = st.find("span").get_text(strip=True) if st and st.find("span") else None
        key = (anc.get("id"), label, time_el.get_text(" ", strip=True) if time_el else None,
               m.group(5) if m else show_date)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "kind": kind,
            "title": h5.get_text(strip=True) if h5 else None,
            "runtime": tp.get_text(" ", strip=True) if tp else None,
            "rating": rc.get_text(strip=True) if rc else None,
            "screen_label": label,
            "screen_no": int(nums[0]) if nums else None,
            "times": time_el.get_text(" ", strip=True) if time_el else None,
            "status": status,
            "date": m.group(5) if m else show_date,
            "performance_id": m.group(2) if m else None,
            "film_code": m.group(3) if m else None,
            "bookable": bool(m) and status not in ("満席", "販売終了", "終了"),
        })
    return {"theater_name": info["name"] if slug in ("shinjuku_wald9", "t-joy_emiterrace_tokorozawa", "t-joy_umeda", "t-joy_kyoto") else (t.text.strip() if t else slug),
            "slug": slug, "show_date": show_date, "showings": rows}


def _norm(s):
    return unicodedata.normalize("NFKC", s or "")
