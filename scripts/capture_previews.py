#!/usr/bin/env python3
"""
Capture a real preview for every source:
  - YouTube            -> video thumbnail (derived from id, no fetch)
  - PDF / arXiv        -> rendered page-1 thumbnail (curl + qlmanage) saved to thumbs/<id>.png
  - everything else    -> og:image / twitter:image URL scraped from the page
Writes data/previews.json ({id: preview_url}). Resumable: already-recorded ids are skipped.
Run:  python3 scripts/capture_previews.py
"""
import json, os, re, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "dataset.json")
OUT = os.path.join(HERE, "data", "previews.json")
THUMBS = os.path.join(HERE, "thumbs")
os.makedirs(THUMBS, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

previews = {}
if os.path.exists(OUT):
    try:
        previews = json.load(open(OUT))
    except Exception:
        previews = {}
lock = Lock()

def save():
    with lock:
        json.dump(previews, open(OUT, "w"), indent=1)

def og_image(url):
    try:
        html = subprocess.run(["curl", "-sL", "--max-time", "14", "-A", UA, url],
                              capture_output=True, text=True, timeout=22).stdout
    except Exception:
        return ""
    for prop in ("og:image:secure_url", "og:image:url", "og:image", "twitter:image", "twitter:image:src"):
        m = (re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\'][^>]*content=["\']([^"\']+)', html, re.I)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']' + re.escape(prop), html, re.I))
        if m:
            img = m.group(1).strip().replace("&amp;", "&")
            if img.startswith("//"):
                img = "https:" + img
            if img.startswith("http"):
                return img
    return ""

def pdf_thumb(url, iid):
    out_png = os.path.join(THUMBS, iid + ".png")
    if os.path.exists(out_png):
        return "thumbs/" + iid + ".png"
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "f.pdf")
        try:
            subprocess.run(["curl", "-sL", "--max-time", "30", "--max-filesize", "31457280", "-A", UA, url, "-o", pdf], timeout=40)
        except Exception:
            return ""
        if not os.path.exists(pdf) or os.path.getsize(pdf) < 1000:
            return ""
        with open(pdf, "rb") as f:
            if f.read(5) != b"%PDF-":
                return ""
        try:
            subprocess.run(["qlmanage", "-t", "-s", "700", "-o", td, pdf], capture_output=True, timeout=45)
        except Exception:
            return ""
        cand = os.path.join(td, "f.pdf.png")
        if os.path.exists(cand):
            os.replace(cand, out_png)
            return "thumbs/" + iid + ".png"
    return ""

def yt(url):
    m = re.search(r"(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})", url)
    return "https://img.youtube.com/vi/%s/hqdefault.jpg" % m.group(1) if m else ""

def is_pdf(url):
    u = url.lower()
    return u.endswith(".pdf") or "/pdf/" in u or "arxiv.org/pdf" in u

def process(it):
    iid = it["id"]
    url = it["url"]; host = it.get("host", "")
    if "youtube.com" in host or "youtu.be" in host:
        pv = yt(url)
    elif is_pdf(url):
        pv = pdf_thumb(url, iid)
    else:
        pv = og_image(url)
    with lock:
        previews[iid] = pv

def main():
    items = json.load(open(DATA))["items"]
    todo = [it for it in items if it["id"] not in previews]
    print("processing", len(todo), "of", len(items), "sources")
    done = 0
    with ThreadPoolExecutor(max_workers=int(os.environ.get("STACKS_WORKERS", "8"))) as ex:
        futs = [ex.submit(process, it) for it in todo]
        for f in futs:
            try:
                f.result()
            except Exception:
                pass
            done += 1
            if done % 25 == 0:
                save()
                print("...", done, "processed;", sum(1 for v in previews.values() if v), "with preview")
    save()
    print("DONE. previews:", sum(1 for v in previews.values() if v), "/", len(previews))

if __name__ == "__main__":
    main()
