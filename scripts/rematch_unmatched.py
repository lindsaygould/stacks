#!/usr/bin/env python3
"""Second-pass matcher: try to connect the 102 unmatched LinkedIn posts to items that ALREADY
exist in the app, using more than exact-URL equality:
  (A) shared core identifier across ANY of the post's links — arXiv id, DOI, or publisher slug
      (nature s-number, ScienceDirect PII, long numeric article id) — catches "same paper, other URL"
  (B) title overlap — the post names/quotes the paper title that's in the library
Reads docs/unmatched_linkedin.json (name, links, body) + data/dataset.json. Writes a report.
Applies NOTHING — just reports candidates + confidence for review.
"""
import json, re, collections

items = json.load(open("data/dataset.json"))["items"]
unm = json.load(open("docs/unmatched_linkedin.json"))

STOP = set("the a an of for and or in on with to from using via based by is are as at we our this that these those between within their its it new study effect effects role toward paper main pdf full into over under about using can how why what when new using our your more most using approach method results using model models data using brain neural human been will using can also may such using both than then them they using into".split())

def core_keys(url):
    u = (url or "").lower()
    ks = set()
    m = re.search(r'arxiv\.org/(?:pdf|abs|html)/(\d{4}\.\d{4,5})', u)
    if m: ks.add('arxiv:' + m.group(1))
    for m in re.finditer(r'(10\.\d{4,9}/[^\s/?&#"\')]+)', u):
        ks.add('doi:' + m.group(1).rstrip('.'))
    for m in re.finditer(r'(s\d{2}-?\d{3,}-\d{3,}-[\dxy]+|s\d{5,}-\d{3,}-[\dxy]+)', u):  # nature/springer style
        ks.add('slug:' + m.group(1))
    for m in re.finditer(r'pii/([a-z0-9]{12,})', u):                                    # sciencedirect / cell / lancet PII
        ks.add('pii:' + m.group(1))
    for m in re.finditer(r's(\d{16,})', u):
        ks.add('pii:s' + m.group(1))
    for m in re.finditer(r'/(?:fullarticle|document|poster|records?|abstract_id=)/?(\d{6,})', u):
        ks.add('num:' + m.group(1))
    return ks

def title_words(t):
    return set(w for w in re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).split() if len(w) > 3 and w not in STOP)

# ---- item index ----
key2item = {}
item_tw = {}
for it in items:
    for u in ([it.get("url")] + list(it.get("all_urls") or []) + [it.get("ident", "")]):
        for k in core_keys(u):
            key2item.setdefault(k, it["id"])
    item_tw[it["id"]] = title_words(it.get("title", ""))
by = {it["id"]: it for it in items}

id_match, title_match, still = [], [], []
for e in unm:
    post_keys = set()
    for lk in e["links"]:
        post_keys |= core_keys(lk)
    hit = next((key2item[k] for k in post_keys if k in key2item), None)
    if hit:
        shared = [k for k in post_keys if k in key2item and key2item[k] == hit]
        id_match.append((e, hit, shared[0] if shared else ""))
        continue
    # title overlap
    ptext = title_words(" ".join(e["body"]))
    best, bestscore = None, 0.0
    for iid, tw in item_tw.items():
        if len(tw) < 4: continue
        ov = len(tw & ptext) / len(tw)
        if ov > bestscore:
            bestscore, best = ov, iid
    if best and bestscore >= 0.65:
        title_match.append((e, best, round(bestscore, 2)))
    else:
        still.append((e, best, round(bestscore, 2)))

print(f"UNMATCHED POSTS: {len(unm)}")
print(f"  → now connect by shared identifier (arXiv/DOI/slug): {len(id_match)}")
print(f"  → now connect by title overlap (>=0.65):            {len(title_match)}")
print(f"  → still unmatched:                                  {len(still)}")

print("\n=== IDENTIFIER MATCHES (high confidence) ===")
for e, iid, k in id_match:
    print(f"  post #{e['n']} ({e['name']})  ->  [{by[iid]['kind']}] {by[iid]['title'][:60]}   via {k}")

print("\n=== TITLE MATCHES (review) ===")
for e, iid, sc in sorted(title_match, key=lambda x: -x[2]):
    print(f"  post #{e['n']} ({e['name']}) [{sc}] -> [{by[iid]['kind']}] {by[iid]['title'][:60]}")

report = {
    "id_match": [{"n": e["n"], "name": e["name"], "item": iid, "title": by[iid]["title"], "kind": by[iid]["kind"], "via": k} for e, iid, k in id_match],
    "title_match": [{"n": e["n"], "name": e["name"], "item": iid, "title": by[iid]["title"], "kind": by[iid]["kind"], "score": sc} for e, iid, sc in title_match],
    "still": [{"n": e["n"], "name": e["name"], "best": iid, "best_title": by[iid]["title"] if iid else "", "score": sc} for e, iid, sc in still],
}
json.dump(report, open("scripts/rematch_report.json", "w"), ensure_ascii=False, indent=1)
print("\nwrote scripts/rematch_report.json")
