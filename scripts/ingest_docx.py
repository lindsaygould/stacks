#!/usr/bin/env python3
"""
Extract non-paper/repo source material from the source-dump DOCX — YouTube videos,
company/product pages, articles, events, plus any direct paper/repo links — and the
surrounding LinkedIn-post text as context.

LinkedIn / lnkd.in URLs are NOT emitted as primary sources (per PRD); instead, when a
direct link is preceded by LinkedIn post text, that text is preserved as the item's
context and the item is flagged `from_linkedin: true`.

Output: data/source/docx_urls.json  (a list the main build.py consumes)
Run:    python3 scripts/ingest_docx.py "<path to docx>"
"""
import zipfile, re, json, os, sys, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "source", "docx_urls.json")
DOCX = sys.argv[1] if len(sys.argv) > 1 else "/Users/lindsaygould/Downloads/Source file dump 7_4_26 (2).docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def plain_text(docx):
    z = zipfile.ZipFile(docx)
    doc = ET.fromstring(z.read("word/document.xml"))
    out = []
    for p in doc.iter(W + "p"):
        runs = [(t.text or "") for t in p.iter(W + "t")]
        line = "".join(runs).strip()
        if line:
            out.append(line)
    return "\n".join(out)

URL_RE = re.compile(r"https?://[^\s)>\]\"'|]+")
def norm(u):
    u = u.rstrip(".,);]")
    u = re.sub(r"[#?].*$", "", u) if "arxiv.org" in u else u
    return u.rstrip("/")
def host(u):
    m = re.match(r"https?://([^/]+)", u)
    return (m.group(1).lower().replace("www.", "") if m else "")
def is_linkedin(u):
    h = host(u); return "linkedin.com" in h or "lnkd.in" in h

def main():
    text = plain_text(DOCX)
    # ordered scan: walk URLs in document order, capture preceding text block as context
    records = {}
    last_end = 0
    pending_linkedin = False
    for m in URL_RE.finditer(text):
        raw = m.group(0)
        ctx = text[last_end:m.start()].strip()
        last_end = m.end()
        if is_linkedin(raw):
            pending_linkedin = True
            continue
        u = norm(raw)
        h = host(u)
        if not h:
            continue
        # context: last ~500 chars of the preceding block (often the LinkedIn post body)
        ctx = re.sub(r"\s+", " ", ctx)[-600:].strip()
        from_li = pending_linkedin or ("linkedin" in ctx.lower())
        pending_linkedin = False
        key = u.lower()
        if key not in records:
            records[key] = {"url": u, "host": h, "context": ctx, "from_linkedin": from_li,
                            "all_urls": [u], "count": 1}
        else:
            r = records[key]; r["count"] += 1
            if len(ctx) > len(r["context"]):
                r["context"] = ctx
            r["from_linkedin"] = r["from_linkedin"] or from_li

    out = list(records.values())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    from collections import Counter
    hist = Counter(r["host"] for r in out)
    print("Extracted", len(out), "unique direct (non-LinkedIn) URLs ->", OUT)
    print("from-LinkedIn-context:", sum(1 for r in out if r["from_linkedin"]))
    print("top domains:", dict(hist.most_common(20)))

if __name__ == "__main__":
    main()
