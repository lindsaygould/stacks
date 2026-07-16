#!/usr/bin/env python3
"""Resolve lnkd.in short links to their real destination by reading the interstitial HTML."""
import re, urllib.request, concurrent.futures as cf

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BAD = re.compile(r'linkedin|lnkd|licdn|w3\.org|schema\.org|/favicon|gstatic|googletag|cookielaw|doubleclick', re.I)
links = [l.strip() for l in open("scripts/lnkd_links.txt") if l.strip()]

def resolve(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            final = r.geturl()
            if "lnkd.in" not in final and "linkedin.com" not in final:
                return u, final                       # server-side redirect worked
            body = r.read(200000).decode("utf-8", "ignore")
        for m in re.finditer(r'https?://[^"\'<> )]+', body):
            d = m.group(0)
            if not BAD.search(d):
                return u, d
    except Exception as e:
        return u, ""
    return u, ""

out = {}
with cf.ThreadPoolExecutor(max_workers=16) as ex:
    for u, dest in ex.map(resolve, links):
        out[u] = dest

with open("scripts/lnkd_resolved.tsv", "w") as f:
    for u in links:
        f.write(f"{u}\t{out.get(u,'')}\n")
got = sum(1 for v in out.values() if v)
print(f"resolved {got}/{len(links)} short links")
for u in links[:6]:
    print(" ", u, "->", out.get(u,'')[:90])
