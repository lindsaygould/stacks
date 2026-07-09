#!/usr/bin/env python3
"""
Map the extracted full-text files content/<driveFileId>.txt to Stacks item ids,
producing content/<item-id>.txt so build.py can attach full text + read_status.

Matching, in order of confidence:
  1. Exact: item.drive_url contains the fileId  -> that item.
  2. Identifier token: arXiv id / Nature-Springer / PII shared between the PDF
     title and the item url+ident.
  3. Fuzzy: normalized-title word overlap (Jaccard) for descriptive filenames.

Supplementary / brochure PDFs with no matching item are skipped (reported).
Run: python3 scripts/rekey_content.py
"""
import json, os, re, glob, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(HERE, "content")
DATA = os.path.join(HERE, "data", "dataset.json")
# workflow output holds the fileId -> title manifest
OUT = "/private/tmp/claude-501/-Users-lindsaygould-Library-Mobile-Documents-com-apple-CloudDocs-Claude-Outputs/331797ca-af66-472d-be14-9705214e93fd/tasks/wz7y0hapf.output"

def collapse(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def sigs(s):
    s = (s or "").lower()
    out = set(re.findall(r"\d{4}\.\d{4,5}", s))      # arXiv id
    out |= set(re.findall(r"s\d{7,}", collapse(s)))  # nature/springer + PII
    return out

STOP = set("the a an of for and or in on with to from using via based by is are as at we our "
           "this that these those between within their its it new paper main pdf full".split())
def words(s):
    return set(w for w in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(w) > 3 and w not in STOP)

def main():
    items = json.load(open(DATA))["items"]
    res = json.load(open(OUT))["result"]
    if isinstance(res, str): res = json.loads(res)
    manifest = {m["id"]: m["title"] for m in res.get("manifest", [])}
    files = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(os.path.join(CONTENT, "*.txt"))}
    # ignore anything we've already rekeyed (item ids don't look like drive fileIds)
    files = {fid: p for fid, p in files.items() if fid in manifest}
    print(f"{len(files)} extracted files, {len(items)} items")

    # index items
    by_fileid = {}
    for it in items:
        du = it.get("drive_url", "")
        m = re.search(r"/d/([A-Za-z0-9_-]+)", du)
        if m: by_fileid[m.group(1)] = it
    papers = [it for it in items if it["kind"] in ("paper", "dataset")]
    item_sigs = [(it, sigs(it.get("url", "") + " " + it.get("ident", ""))) for it in papers]
    title_words = {it["id"]: words(it.get("title", "")) for it in papers}

    assigned = {}   # item_id -> (fileId, chars, how)
    unmatched = []
    for fid, path in files.items():
        title = manifest.get(fid, "")
        chars = os.path.getsize(path)
        it = None; how = ""
        # 1. exact fileId from an item's drive_url
        if fid in by_fileid:
            it, how = by_fileid[fid], "fileId"
        # 2. the paper's title appears in the extracted text (papers print their title up top)
        if it is None:
            try: head = open(path, encoding="utf-8", errors="ignore").read(4000).lower()
            except Exception: head = ""
            headw = set(re.split(r"[^a-z0-9]+", head))
            best, bcov = None, 0.0
            for cand in papers:
                tw = title_words[cand["id"]]
                if len(tw) < 4: continue
                cov = len(tw & headw) / len(tw)
                if cov > bcov: best, bcov = cand, cov
            if bcov >= 0.6: it, how = best, f"title({bcov:.2f})"
        # 3. shared identifier token (arXiv / Nature-Springer / PII) between filename and item url
        if it is None:
            fs = sigs(title)
            if fs:
                for cand, cs in item_sigs:
                    if fs & cs: it, how = cand, "ident"; break
        if it is None:
            unmatched.append((title, chars)); continue
        prev = assigned.get(it["id"])
        if prev and prev[1] >= chars:   # keep the larger file (main over supplement)
            continue
        assigned[it["id"]] = (fid, chars, how)

    # write content/<itemid>.txt
    written = 0
    for iid, (fid, chars, how) in assigned.items():
        shutil.copyfile(files[fid], os.path.join(CONTENT, iid + ".txt"))
        written += 1
    print(f"matched {len(assigned)} items -> wrote {written} content/<itemid>.txt")
    print("  by fileId:", sum(1 for v in assigned.values() if v[2] == "fileId"),
          "| by title-in-text:", sum(1 for v in assigned.values() if v[2].startswith("title")),
          "| by ident:", sum(1 for v in assigned.values() if v[2] == "ident"))
    if unmatched:
        print(f"\n{len(unmatched)} unmatched PDFs (likely supplements/brochures, no item):")
        for t, c in sorted(unmatched, key=lambda x: -x[1]):
            print(f"  {c:>7} {t}")

if __name__ == "__main__":
    main()
