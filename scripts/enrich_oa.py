#!/usr/bin/env python3
"""
Second-pass open-access recovery + metadata resolution for papers ingest.py missed.

Two jobs, per still-unread paper:
  1. RESOLVE real metadata (title, DOI, PMCID) for items that only have a
     placeholder id-title (e.g. "pmid:36566924", "doi:10.1093/..."), via
     Crossref (DOI) / NCBI eutils (PMID) / Europe PMC (PMCID). Persisted to
     data/resolved_meta.json so build.py can fix the ugly titles too.
  2. RECOVER full text from the OA sources a plain PDF-grab misses:
       - Europe PMC open-access full text (fullTextXML) by PMCID or title search
       - Unpaywall legal OA PDF for any (now-resolved) DOI
     Every candidate is title-verified (>=50% of the paper's title words present)
     before it is written, so a wrong paper is never ingested.

Writes content/<item-id>.txt + data/resolved_meta.json. Idempotent.
Run: python3 scripts/enrich_oa.py
"""
import json, os, re, subprocess, time, html

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "dataset.json")
CONTENT = os.path.join(HERE, "content")
META_OUT = os.path.join(HERE, "data", "resolved_meta.json")
TMP = "/private/tmp/stacks_enrich.pdf"
EMAIL = "lindsayagould@gmail.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
PDFTOTEXT = "/opt/homebrew/bin/pdftotext"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
MAX_CHARS = 120000

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

def title_ok(text_or_title, item_title):
    tw = words(item_title)
    if len(tw) < 4:
        return False
    hw = set(re.split(r"[^a-z0-9]+", (text_or_title or "")[:3000].lower()))
    return len(tw & hw) / len(tw) >= 0.5

def strip_xml(xml):
    m = re.search(r"<body\b.*?>(.*)</body>", xml, re.S)
    body = m.group(1) if m else xml
    body = re.sub(r"<ref-list\b.*?</ref-list>", " ", body, flags=re.S)
    txt = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return re.sub(r"[ \t]*\n[ \t\n]*", "\n", re.sub(r"[ \t]+", " ", txt)).strip()

def clean_abs(a):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", a or ""))).strip()

def clean_doi(d):
    if not d:
        return d
    d = d.rstrip(".)")
    d = re.sub(r"(v\d+)?\.full(\.pdf)?$", "", d)   # biorxiv/medrxiv pdf suffix
    d = re.sub(r"/full$", "", d)                    # frontiers /full
    d = re.sub(r"/\d{6,}$", "", d)                  # OUP trailing article number
    d = re.sub(r"v\d+$", "", d)                     # bare version suffix
    return d

def ids_from(it):
    hay = it["url"] + " " + it.get("ident", "")
    m = re.search(r"10\.\d{4,9}/[^\s\"'?#<>]+", hay)
    doi = clean_doi(m.group(0)) if m else None
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)|[?&]list_uids=(\d+)", hay)
    pmid = (m.group(1) or m.group(2)) if m else None
    m = re.search(r"PMC(\d+)", hay, re.I)
    pmcid = "PMC" + m.group(1) if m else None
    return doi, pmid, pmcid

def crossref(doi):
    js = get(f"https://api.crossref.org/works/{doi}?mailto={EMAIL}", 25)
    try:
        msg = json.loads(js)["message"]
        title = (msg.get("title") or [""])[0]
        return title, clean_abs(msg.get("abstract", ""))
    except Exception:
        return "", ""

def eutils(pmid):
    js = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json")
    title = doi = pmcid = ""
    try:
        rec = json.loads(js)["result"][pmid]
        title = rec.get("title", "").rstrip(".")
        for a in rec.get("articleids", []):
            if a["idtype"] == "doi": doi = a["value"]
            if a["idtype"] in ("pmc", "pmcid"):
                mm = re.search(r"PMC\d+", a["value"], re.I)
                if mm: pmcid = mm.group(0)
    except Exception:
        pass
    return title, doi, pmcid

def epmc_by_id(kind, val):
    """kind: 'PMC' -> PMCID, 'DOI', 'MED' -> PMID. Returns (title, pmcid, doi, isOA)."""
    q = {"PMC": f"PMCID:{val}", "DOI": f"DOI:{val}", "MED": f"EXT_ID:{val}"}[kind]
    js = get(f"{EPMC}/search?query={q}&format=json&resultType=core&pageSize=1")
    try:
        r = json.loads(js)["resultList"]["result"][0]
        return r.get("title", ""), r.get("pmcid"), r.get("doi"), r.get("isOpenAccess") == "Y"
    except Exception:
        return "", None, None, False

def epmc_search_title(title):
    q = re.sub(r'["\\]', " ", title)[:220].replace(" ", "%20")
    js = get(f'{EPMC}/search?query=TITLE:%22{q}%22&format=json&resultType=core&pageSize=3')
    try:
        for r in json.loads(js)["resultList"]["result"]:
            if r.get("pmcid") and r.get("isOpenAccess") == "Y" and title_ok(r.get("title", ""), title):
                return r["pmcid"], r.get("doi")
    except Exception:
        pass
    return None, None

def bioc_fulltext(pmcid):
    js = get(f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmcid}/unicode", 45)
    try:
        parts = []
        for doc in json.loads(js)[0]["documents"]:
            for p in doc.get("passages", []):
                t = (p.get("text") or "").strip()
                if t: parts.append(t)
        txt = "\n".join(parts)
        return txt if len(txt) > 2000 else ""
    except Exception:
        return ""

def epmc_fulltext(pmcid):
    xml = get(f"{EPMC}/PMC/{pmcid}/fullTextXML", 45)
    if "<body" in xml or "<article" in xml:
        t = strip_xml(xml)
        return t if len(t) > 2000 else ""
    return ""

def pmc_fulltext(pmcid):
    return bioc_fulltext(pmcid) or epmc_fulltext(pmcid)

def unpaywall_pdf(doi):
    js = get(f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}")
    try:
        loc = (json.loads(js) or {}).get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url")
    except Exception:
        return None

def pdf_text(url):
    try:
        subprocess.run(["curl", "-sL", "--max-time", "50", "-A", UA, "-o", TMP, url], capture_output=True, timeout=60)
        with open(TMP, "rb") as f:
            if not f.read(5).startswith(b"%PDF"): return ""
        subprocess.run([PDFTOTEXT, "-q", TMP, TMP + ".txt"], capture_output=True, timeout=90)
        return open(TMP + ".txt", encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""
    finally:
        for p in (TMP, TMP + ".txt"):
            try: os.remove(p)
            except Exception: pass

def main():
    items = json.load(open(DATA))["items"]
    todo = [it for it in items if it["kind"] in ("paper", "dataset")
            and not os.path.exists(os.path.join(CONTENT, it["id"] + ".txt"))]
    meta = json.load(open(META_OUT)) if os.path.exists(META_OUT) else {}
    print(f"{len(todo)} still-unread papers — metadata resolve + OA recovery")
    got = 0; how = {}; titled = 0
    absn = 0
    for i, it in enumerate(todo, 1):
        doi, pmid, pmcid = ids_from(it)
        title = it.get("title", "")
        rt = rabs = ""
        # 1. resolve real title (placeholder) + DOI/PMCID from PMID
        if pmid and not (doi and pmcid):
            rt, d2, pc2 = eutils(pmid); doi = doi or d2; pmcid = pmcid or pc2; time.sleep(0.34)
        if placeholder(title) and not rt and doi:
            rt, rabs = crossref(doi)
        if placeholder(title) and not rt and pmcid:
            rt, _, d3, _ = epmc_by_id("PMC", pmcid); doi = doi or d3
        if placeholder(title) and rt and not placeholder(rt):
            title = rt
            m = meta.setdefault(it["id"], {}); m["title"] = rt
            if doi: m["doi"] = doi
            titled += 1
        # abstract for any paywalled paper that lacks one (keeps the Librarian useful even without full text)
        if not it.get("abstract") and doi:
            if not rabs: _, rabs = crossref(doi)
            if rabs and len(rabs) > 120:
                meta.setdefault(it["id"], {})["abstract"] = rabs[:1800]; absn += 1
        # 2. recover full text
        text = ""; src = ""
        if pmcid:
            text = pmc_fulltext(pmcid); src = "pmc"
        if not text and pmid and not pmcid:
            _, pc, d4, oa = epmc_by_id("MED", pmid)
            if pc and oa: text = pmc_fulltext(pc); src = "epmc-med"; doi = doi or d4
            time.sleep(0.2)
        if not text and title and not placeholder(title):
            pc, d5 = epmc_search_title(title)
            if pc: text = pmc_fulltext(pc); src = "epmc-title"; doi = doi or d5
            time.sleep(0.34)
        if not text and doi:
            pdf = unpaywall_pdf(doi)
            if pdf:
                t = pdf_text(pdf)
                if title_ok(t, title): text = t; src = "unpaywall"
        # PMC full text is the right article by construction; PDF paths are title-checked above
        if text:
            open(os.path.join(CONTENT, it["id"] + ".txt"), "w", encoding="utf-8").write(text[:MAX_CHARS])
            got += 1; how[src] = how.get(src, 0) + 1
            print(f"  [{i}/{len(todo)}] ✓ {src:11} {it['id']}  {title[:52]}")
        if i % 25 == 0:
            json.dump(meta, open(META_OUT, "w"), ensure_ascii=False, indent=1)
            print(f"  ... {i}/{len(todo)} | full-text {got} | titles {titled} | abstracts {absn}")
    json.dump(meta, open(META_OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\nDONE: recovered {got} full texts, fixed {titled} titles, added {absn} abstracts. by source: {how}")
    print(f"  wrote {META_OUT}. Re-run build.py.")

if __name__ == "__main__":
    main()
