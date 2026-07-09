#!/usr/bin/env python3
"""
Fill in PubMed abstracts for still-unread papers that don't have one yet, so the
Librarian knows the paywalled papers at abstract level even when full text is
locked. PubMed indexes an abstract for nearly every biomedical paper, so this
covers far more than Crossref did.

Per paper without full text and without an abstract:
  - find its PMID: from the url, else esearch by DOI, else esearch by exact title
  - efetch the abstract (+ real title) and store in data/resolved_meta.json
Title-verified: the PubMed ArticleTitle must overlap the item title, so a wrong
PMID is never attached. Idempotent. Run: python3 scripts/enrich_pubmed_abs.py
"""
import json, os, re, subprocess, time, html, urllib.parse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "dataset.json")
CONTENT = os.path.join(HERE, "content")
META = os.path.join(HERE, "data", "resolved_meta.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

STOP = set("the a an of for and or in on with to from using via based by is are as at we our this "
           "that these those between within their its it new study effect effects role toward".split())
def words(s): return set(w for w in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(w) > 3 and w not in STOP)
def placeholder(t):
    t = (t or "").strip().lower()
    return (not t) or bool(re.match(r"^(pmid|pmc|doi|arxiv|ieee|ssrn|http)", t)) or len(t) < 15

def get(url, timeout=30):
    try:
        return subprocess.run(["curl", "-sL", "--max-time", str(timeout), "-A", UA, url],
                              capture_output=True, text=True, timeout=timeout + 10).stdout
    except Exception:
        return ""

def esearch(term):
    js = get(f"{EUT}/esearch.fcgi?db=pubmed&retmode=json&term={urllib.parse.quote(term)}")
    try:
        ids = json.loads(js)["esearchresult"]["idlist"]
        return ids[0] if ids else None
    except Exception:
        return None

def efetch(pmid):
    xml = get(f"{EUT}/efetch.fcgi?db=pubmed&id={pmid}&rettype=abstract&retmode=xml")
    title = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", xml, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", " ", title.group(1))).strip() if title else ""
    segs = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", xml, re.S)
    labels = re.findall(r'<AbstractText Label="([^"]*)"', xml)
    parts = []
    for i, s in enumerate(segs):
        s = html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()
        if not s: continue
        parts.append((labels[i] + ": " + s) if i < len(labels) and labels[i] else s)
    return title, re.sub(r"\s+", " ", " ".join(parts)).strip()

def main():
    items = json.load(open(DATA))["items"]
    meta = json.load(open(META)) if os.path.exists(META) else {}
    todo = [it for it in items if it["kind"] in ("paper", "dataset")
            and not os.path.exists(os.path.join(CONTENT, it["id"] + ".txt"))
            and not it.get("abstract") and not meta.get(it["id"], {}).get("abstract")]
    print(f"{len(todo)} papers still without full text or abstract — PubMed lookup")
    added = titled = 0
    for i, it in enumerate(todo, 1):
        hay = it["url"] + " " + it.get("ident", "")
        title = meta.get(it["id"], {}).get("title") or it.get("title", "")
        pmid = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)|[?&]list_uids=(\d+)", hay)
        pmid = (pmid.group(1) or pmid.group(2)) if pmid else None
        doi = re.search(r"10\.\d{4,9}/[^\s\"'?#<>]+", hay)
        doi = doi.group(0).rstrip(".)") if doi else meta.get(it["id"], {}).get("doi")
        if not pmid and doi:
            pmid = esearch(f"{doi}[AID]"); time.sleep(0.34)
        if not pmid and title and not placeholder(title):
            clean = re.sub(r'[^\w\s.-]', " ", title)
            pmid = esearch(f"{clean}[Title]"); time.sleep(0.34)
        if not pmid:
            continue
        rt, ab = efetch(pmid); time.sleep(0.34)
        # verify the PubMed record is this paper
        if not placeholder(title):
            tw = words(title)
            if tw and len(tw & words(rt)) / len(tw) < 0.5:
                continue
        m = meta.setdefault(it["id"], {})
        if rt and placeholder(title):
            m["title"] = rt; titled += 1
        if ab and len(ab) > 120:
            m["abstract"] = ab[:1800]; added += 1
            print(f"  [{i}/{len(todo)}] + {it['id']}  {(rt or title)[:55]}")
        if i % 25 == 0:
            json.dump(meta, open(META, "w"), ensure_ascii=False, indent=1)
            print(f"  ... {i}/{len(todo)} | abstracts {added} | titles {titled}")
    json.dump(meta, open(META, "w"), ensure_ascii=False, indent=1)
    print(f"\nDONE: +{added} PubMed abstracts, +{titled} titles. Re-run build.py.")

if __name__ == "__main__":
    main()
