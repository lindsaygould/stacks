#!/usr/bin/env python3
"""
Open-access auto-fetch for Stacks. For every paper/dataset item that has no full
text yet, try to get a legal PDF automatically and extract its text to
content/<item-id>.txt — no manual download.

Sources, in priority order:
  1. arXiv        -> https://arxiv.org/pdf/<id>.pdf
  2. PubMed Central (PMC) -> .../pmc/articles/PMC<id>/pdf/
  3. bioRxiv / medRxiv    -> <url>.full.pdf
  4. Unpaywall (any DOI)  -> best legal OA PDF, if one exists
  5. the item url itself, if it already points at a .pdf

Whatever it can't fetch (real paywall, no OA copy) is left untouched, so build.py
keeps it as "needs your PDF" in the app's to-do list. Idempotent: skips items that
already have content/<id>.txt. Run: python3 scripts/ingest.py
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "dataset.json")
CONTENT = os.path.join(HERE, "content")
TMP = "/private/tmp/stacks_ingest.pdf"
EMAIL = "lindsayagould@gmail.com"      # Unpaywall requires a contact email
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
PDFTOTEXT = "/opt/homebrew/bin/pdftotext"
MAX_CHARS = 120000

def curl(url, out):
    try:
        subprocess.run(["curl", "-sL", "--max-time", "50", "-A", UA, "-o", out, url],
                       capture_output=True, timeout=60)
        return os.path.exists(out) and os.path.getsize(out) > 1000
    except Exception:
        return False

def curl_text(url):
    try:
        return subprocess.run(["curl", "-sL", "--max-time", "30", "-A", UA, url],
                              capture_output=True, text=True, timeout=40).stdout
    except Exception:
        return ""

def is_pdf(path):
    try:
        with open(path, "rb") as f:
            return f.read(5).startswith(b"%PDF")
    except Exception:
        return False

def to_text(path):
    if not is_pdf(path):
        return ""
    txt = path + ".txt"
    try:
        subprocess.run([PDFTOTEXT, "-q", path, txt], capture_output=True, timeout=90)
        t = open(txt, encoding="utf-8", errors="ignore").read()
        os.remove(txt)
        return t
    except Exception:
        return ""

def candidates(it):
    """Yield PDF URLs to try, best first."""
    hay = (it.get("url", "") + " " + it.get("ident", ""))
    low = hay.lower()
    # arXiv
    m = re.search(r"(\d{4}\.\d{4,5})", low) if "arxiv" in low else None
    if m:
        yield "https://arxiv.org/pdf/" + m.group(1) + ".pdf"
    # PMC
    m = re.search(r"pmc(\d{5,})", low)
    if m:
        yield "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC" + m.group(1) + "/pdf/"
    # bioRxiv / medRxiv
    if "biorxiv.org" in low or "medrxiv.org" in low:
        base = it["url"].split("?")[0].rstrip("/")
        yield (base if base.endswith(".full.pdf") else base + ".full.pdf")
    # the url is already a PDF
    if it.get("url", "").lower().split("?")[0].endswith(".pdf"):
        yield it["url"]
    # Unpaywall via DOI
    m = re.search(r"10\.\d{4,9}/[^\s\"'?#<>]+", hay)
    if m:
        doi = m.group(0).rstrip(".)")
        js = curl_text(f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}")
        try:
            loc = (json.loads(js) or {}).get("best_oa_location") or {}
            pdf = loc.get("url_for_pdf") or loc.get("url")
            if pdf:
                yield pdf
        except Exception:
            pass

def main():
    only = set(sys.argv[1:])   # optional: pass specific item ids
    items = json.load(open(DATA))["items"]
    todo = [it for it in items if it["kind"] in ("paper", "dataset")
            and not os.path.exists(os.path.join(CONTENT, it["id"] + ".txt"))
            and (not only or it["id"] in only)]
    print(f"{len(todo)} papers without full text — trying open-access fetch")
    got = fail = 0
    for i, it in enumerate(todo, 1):
        text = ""
        for url in candidates(it):
            if curl(url, TMP):
                text = to_text(TMP)
                if len(text.strip()) > 2000:
                    break
                text = ""
            time.sleep(0.5)
        if text:
            open(os.path.join(CONTENT, it["id"] + ".txt"), "w", encoding="utf-8").write(text[:MAX_CHARS])
            got += 1
            print(f"  [{i}/{len(todo)}] ✓ {it['id']}  {it['title'][:60]}")
        else:
            fail += 1
        if i % 20 == 0:
            print(f"  ... {i}/{len(todo)} | fetched {got}")
    try: os.remove(TMP)
    except Exception: pass
    print(f"\nDONE: fetched {got}, could not fetch {fail}. Re-run build.py to update status.")

if __name__ == "__main__":
    main()
