#!/usr/bin/env python3
"""Parse the 7/4 LinkedIn source dump -> attach sharer + post commentary to Stacks items.

Match key = the real article URL (safety/go decoded + lnkd.in resolved) -> item url/all_urls,
with arXiv-id and DOI normalization. Commentary = the post body (text after the timestamp).
Writes scripts/li_context_patch.json = {id: {sender, li_context}}. Modifies nothing else.
"""
import json, re, urllib.parse, html

DUMP = "/Users/lindsaygould/.claude/projects/-Users-lindsaygould-Library-Mobile-Documents-com-apple-CloudDocs-Claude-Outputs/331797ca-af66-472d-be14-9705214e93fd/tool-results/mcp-4d6b084c-ab72-466c-944a-08cd94661fd9-read_file_content-1784216239586.txt"
t = json.load(open(DUMP))["fileContent"]
items = json.load(open("data/dataset.json"))["items"]

# resolved lnkd.in -> real url
LNKD = {}
for line in open("scripts/lnkd_resolved.tsv"):
    p = line.rstrip("\n").split("\t")
    if len(p) == 2 and p[1]: LNKD[p[0]] = p[1]

def norm(u):
    if not u: return ""
    u = html.unescape(u).strip().replace("\\", "")
    u = re.sub(r'^https?://', '', u, flags=re.I)
    u = re.sub(r'^www\.', '', u, flags=re.I)
    u = u.split('#')[0].split('?')[0].rstrip('/').lower()
    m = re.search(r'arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})', u)
    if m: return 'arxiv:' + m.group(1)
    m = re.search(r'(10\.\d{4,9}/[^\s/]+)', u)
    if m: return 'doi:' + m.group(1).rstrip('.')
    return u

idx = {}
for it in items:
    for u in (list(it.get("all_urls") or []) + ([it["url"]] if it.get("url") else [])):
        k = norm(u)
        if k and k not in idx: idx[k] = it["id"]

# split into posts on the header pattern: [Name](profile) \n\n [• degree]
hdr = re.compile(r'\[([^\]]{1,80})\]\((https://www\.linkedin\.com/(?:in|company)/[^)]+)\)\s*\n\s*\n\[•\s', re.I)
starts = [(m.start(), m.group(1).strip()) for m in hdr.finditer(t)]
posts = [(starts[i][1], t[starts[i][0]:(starts[i+1][0] if i+1 < len(starts) else len(t))]) for i in range(len(starts))]

TS = re.compile(r'\n\s*\d+\s*(?:mo|d|w|h|yr|s)\s*•')   # "2d •", "2w •", "3mo •"
DROP = re.compile(r'^\s*(follow(ing)?$|activate to view|like\b|comment\b|repost\b|send\b|\d+\s*(likes?|comments?|reposts?|impressions?)|•\s*edited|edited\s*•|see more|view my|\[•)', re.I)
def commentary(block):
    m = TS.search(block)
    body = block[m.end():] if m else block
    out = []
    for ln in body.split('\n'):
        s = ln.strip()
        if not s or DROP.match(s): continue
        if 'linkedin.com/safety/go' in s or re.match(r'^\[?https?://', s): continue
        if s.startswith('[') and '](http' in s and s.endswith(')'): continue
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)              # markdown link -> text
        s = s.replace('\\>', '>').replace('\\_', '_').replace('\\&', '&').replace('\\-', '-')
        out.append(s)
    txt = ' '.join(out)
    txt = txt.replace('\\!', '!').replace('\\?', '?').replace('\\.', '.').replace('\\,', ',').replace('\\:', ':')
    txt = txt.encode('ascii', 'ignore').decode('ascii')   # drop mojibake/emoji artifacts (ð, â, etc.)
    return re.sub(r'\s+', ' ', txt).strip(' •-–—:').strip()

def real_urls(block):
    out = []
    for m in re.finditer(r'linkedin\.com/safety/go/\?url=([^&)\s]+)', block):
        out.append(urllib.parse.unquote(m.group(1).replace('%2E', '.')))
    for m in re.finditer(r'https://lnkd\.in/[A-Za-z0-9_-]+', block):
        if m.group(0) in LNKD: out.append(LNKD[m.group(0)])
    for m in re.finditer(r'\((https?://(?!www\.linkedin\.com|lnkd\.in)[^)\s]+)\)', block):
        out.append(m.group(1))
    return out

patch, matched, unmatched = {}, 0, []
for name, block in posts:
    urls = real_urls(block)
    hit = next((idx[norm(u)] for u in urls if norm(u) in idx), None)
    if not hit:
        unmatched.append((name, block))   # keep the whole raw block for a verbatim dump
        continue
    matched += 1
    ctx = commentary(block)
    if hit not in patch or len(ctx) > len(patch[hit]["li_context"]):
        patch[hit] = {"sender": name, "li_context": ctx}

by = {it["id"]: it for it in items}
for iid in patch:                       # url = stable fallback key for the build merge
    patch[iid]["url"] = by[iid].get("url", "")
print(f"posts parsed: {len(posts)} | matched->item: {matched} | unique items: {len(patch)}")
print(f"  set sender (was empty): {sum(1 for i in patch if not by[i].get('sender'))}")
print(f"  add context (was empty): {sum(1 for i,v in patch.items() if v['li_context'] and not by[i].get('context'))}")
print(f"  already had context: {sum(1 for i,v in patch.items() if by[i].get('context'))}")
print("\n--- 8 samples ---")
for iid, v in list(patch.items())[:8]:
    print(f"[{by[iid]['kind']}] {by[iid]['title'][:58]}\n   via {v['sender']} :: {v['li_context'][:150]}")
json.dump(patch, open("data/li_context.json","w"), indent=0, ensure_ascii=False)
print(f"\nwrote data/li_context.json ({len(patch)} items) — merged into the library by build.py")

# ---- write the unmatched list VERBATIM (so each entry is Ctrl-F-able in the original doc) ----
def all_links(block):
    out = []
    for m in re.finditer(r'linkedin\.com/safety/go/\?url=([^&)\s]+)', block):
        out.append(urllib.parse.unquote(m.group(1).replace('%2E', '.')))
    for m in re.finditer(r'https://lnkd\.in/[A-Za-z0-9_-]+', block):
        out.append(LNKD.get(m.group(0), m.group(0)))          # resolved dest if known, else the shortener itself
    for m in re.finditer(r'https?://[^\s)\]<>"]+', block):     # any other URL (bare, angle-bracket, or markdown)
        u = m.group(0).rstrip('.,);')
        if 'linkedin.com' in u or 'lnkd.in' in u or 'licdn' in u:
            continue
        out.append(u)
    seen, ded = set(), []
    for u in out:
        if u not in seen: seen.add(u); ded.append(u)
    return ded

def verbatim_body(block):
    lines = block.split('\n'); start = 0
    for i, ln in enumerate(lines):                            # skip the profile/degree/bio/timestamp header
        s = ln.strip()
        if re.match(r'^\d+\s*(?:mo|d|w|h|yr|s)\s*•', s) or s == 'Follow':
            start = i + 1
    return '\n'.join(lines[start:]).strip() or block.strip()

nolink = sum(1 for _, b in unmatched if not all_links(b))
L = ["# Unmatched LinkedIn posts from the 7/4 source dump — VERBATIM",
     "",
     f"{len(unmatched)} of {len(posts)} posts didn't map to a Stacks item "
     f"({matched} matched). Each entry below is the post's text **exactly as it appears in the source "
     f"dump**, so you can Ctrl-F any line to find the original. Links it carried are listed first "
     f"(resolved destination where the lnkd.in shortener could be followed, otherwise the shortener itself). "
     f"{len(unmatched)-nolink} carry a link; {nolink} have no link (use the verbatim text to locate them).",
     "", "---", ""]
for i, (name, block) in enumerate(unmatched, 1):
    links = all_links(block)
    L.append(f"## {i}. {name}")
    L.append("**Links:** " + (" · ".join(links) if links else "_(none in the post — Ctrl-F the text below)_"))
    L.append("")
    L.append(verbatim_body(block))
    L.append("")
    L.append("---")
    L.append("")
open("docs/unmatched_linkedin_sources.md", "w", encoding="utf-8").write("\n".join(L))
print(f"wrote docs/unmatched_linkedin_sources.md — {len(unmatched)} posts verbatim ({len(unmatched)-nolink} with a link, {nolink} without)")

# structured JSON for the .docx builder — body cleaned of markdown link syntax (anchor text kept),
# escapes unwrapped, one paragraph per line, but otherwise verbatim so it stays Ctrl-F-able.
def clean_lines(block):
    out = []
    for ln in verbatim_body(block).split('\n'):
        s = ln.strip()
        if not s: continue
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
        for a, b in [('\\>', '>'), ('\\_', '_'), ('\\!', '!'), ('\\&', '&'), ('\\.', '.'),
                     ('\\,', ','), ('\\-', '-'), ('\\#', '#'), ('\\(', '('), ('\\)', ')'), ('\\[', '['), ('\\]', ']')]:
            s = s.replace(a, b)
        out.append(s)
    return out
entries = [{"n": i, "name": name, "links": all_links(block), "body": clean_lines(block)}
           for i, (name, block) in enumerate(unmatched, 1)]
json.dump(entries, open("docs/unmatched_linkedin.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"wrote docs/unmatched_linkedin.json ({len(entries)} entries) for the .docx builder")
