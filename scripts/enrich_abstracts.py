#!/usr/bin/env python3
"""
Fetch real titles + abstracts for arXiv papers from the free arXiv API so the
Librarian can answer questions about paper *content*, not just a preview.
Writes data/abstracts.json = { "<arxiv_id>": {"title": ..., "abstract": ...} }.
Resumable. Run: python3 scripts/enrich_abstracts.py
"""
import json, os, re, subprocess, time, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "dataset.json")
OUT = os.path.join(HERE, "data", "abstracts.json")
ATOM = "{http://www.w3.org/2005/Atom}"

def arxiv_id(it):
    hay = (it.get("url", "") + " " + it.get("ident", "")).lower()
    if "arxiv.org" not in hay and not it.get("ident", "").lower().startswith("arxiv:"):
        return None
    m = re.search(r"(\d{4}\.\d{4,5})", hay)
    return m.group(1) if m else None

def main():
    items = json.load(open(DATA))["items"]
    out = {}
    if os.path.exists(OUT):
        try: out = json.load(open(OUT))
        except Exception: out = {}
    ids = []
    for it in items:
        if it["kind"] not in ("paper", "dataset"):
            continue
        aid = arxiv_id(it)
        if aid and aid not in out and aid not in ids:
            ids.append(aid)
    print("fetching", len(ids), "arXiv abstracts")
    for i in range(0, len(ids), 40):
        batch = ids[i:i+40]
        url = "https://export.arxiv.org/api/query?id_list=" + ",".join(batch) + "&max_results=40"
        try:
            xml = subprocess.run(["curl", "-s", "--max-time", "30", url], capture_output=True, text=True, timeout=40).stdout
            root = ET.fromstring(xml)
            for e in root.findall(ATOM + "entry"):
                eid = e.findtext(ATOM + "id", "")
                m = re.search(r"(\d{4}\.\d{4,5})", eid)
                if not m: continue
                title = re.sub(r"\s+", " ", (e.findtext(ATOM + "title", "") or "")).strip()
                summ = re.sub(r"\s+", " ", (e.findtext(ATOM + "summary", "") or "")).strip()
                if title:
                    out[m.group(1)] = {"title": title, "abstract": summ}
        except Exception as ex:
            print("batch", i, "failed:", ex)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
        print("...", len(out), "abstracts")
        time.sleep(3)  # be polite to arXiv
    print("DONE:", len(out), "abstracts ->", OUT)

if __name__ == "__main__":
    main()
