#!/usr/bin/env python3
"""
Stacks build pipeline.

Reads the source CSVs + the DOCX-extracted URLs in data/source/, normalizes + dedupes
them into a single tagged dataset (data/dataset.json), and injects that dataset into the
app shell (app.template.html) to produce a fully self-contained index.html.

Resource types: paper, model, repo, dataset, toolkit, benchmark, video, article,
company, event, grant, other. Every item carries provenance (Manual search / Claude /
Claude Science), topic tags, and a preview (real YouTube thumbnails where available,
typed covers otherwise).

No third-party dependencies (stdlib only). Run:  python3 build.py
"""
import csv, json, re, os, datetime, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "source")
OUT_JSON = os.path.join(HERE, "data", "dataset.json")
TEMPLATE = os.path.join(HERE, "app.template.html")
INDEX = os.path.join(HERE, "index.html")

# ----------------------------------------------------------------------------- helpers

def read_csv(name):
    with open(os.path.join(SRC, name), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    h = m.group(1).lower() if m else ""
    return h[4:] if h.startswith("www.") else h

def normkey(u):
    return re.sub(r"^https?://(www\.)?", "", (u or "").lower()).rstrip("/")

PROVIDER_MAP = [
    ("github.com", "GitHub"), ("github.io", "GitHub"), ("huggingface.co", "Hugging Face"),
    ("arxiv.org", "arXiv"), ("biorxiv.org", "bioRxiv"), ("medrxiv.org", "medRxiv"),
    ("nature.com", "Nature"), ("sciencedirect.com", "ScienceDirect"), ("cell.com", "Cell Press"),
    ("pmc.ncbi.nlm.nih.gov", "PubMed / PMC"), ("ncbi.nlm.nih.gov", "PubMed / PMC"),
    ("jamanetwork.com", "JAMA"), ("doi.org", "DOI"), ("linkedin.com", "LinkedIn"),
    ("lnkd.in", "LinkedIn"), ("youtube.com", "YouTube"), ("youtu.be", "YouTube"),
    ("vimeo.com", "Vimeo"), ("open.spotify.com", "Spotify"), ("spotify.com", "Spotify"),
    ("openreview.net", "OpenReview"), ("neurips.cc", "NeurIPS"), ("iclr.cc", "ICLR"),
    ("pnas.org", "PNAS"), ("frontiersin.org", "Frontiers"), ("biomedcentral.com", "BMC"),
    ("link.springer.com", "Springer"), ("springer.com", "Springer"), ("onlinelibrary.wiley.com", "Wiley"),
    ("wiley.com", "Wiley"), ("academic.oup.com", "Oxford"), ("oup.com", "Oxford"), ("mdpi.com", "MDPI"),
    ("ssrn.com", "SSRN"), ("papers.ssrn.com", "SSRN"), ("kickstarter.com", "Kickstarter"),
    ("pieeg.com", "PiEEG"), ("brainflow.org", "BrainFlow"), ("mne.tools", "MNE"),
    ("medium.com", "Medium"), ("substack.com", "Substack"), ("wired.com", "WIRED"),
    ("psypost.org", "PsyPost"), ("businesswire.com", "BusinessWire"), ("paulgraham.com", "Paul Graham"),
    ("x.com", "X"), ("twitter.com", "X"), ("drive.google.com", "Google Drive"),
    ("ai.meta.com", "Meta AI"), ("osf.io", "OSF"), ("direct.mit.edu", "MIT Press"),
    ("journals.sagepub.com", "SAGE"), ("techcrunch.com", "TechCrunch"), ("theverge.com", "The Verge"),
    ("quantamagazine.org", "Quanta"),
]
def provider_of(host):
    for k, v in PROVIDER_MAP:
        if host == k or host.endswith("." + k) or host.endswith(k):
            return v
    for k, v in PROVIDER_MAP:
        if k in host:
            return v
    return "Web"

ACADEMIC_HOSTS = ["arxiv.org", "biorxiv.org", "medrxiv.org", "nature.com", "sciencedirect.com",
    "cell.com", "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "pnas.org", "academic.oup.com",
    "oup.com", "frontiersin.org", "journals.sagepub.com", "direct.mit.edu", "osf.io",
    "jamanetwork.com", "springer.com", "wiley.com", "mdpi.com", "ssrn.com", "jmoodanxdisorders.org",
    "biomedcentral.com", "elifesciences.org", "plos.org", "jneurosci.org", "cebp.aacrjournals.org"]
VIDEO_HOSTS = ["youtube.com", "youtu.be", "vimeo.com"]
PODCAST_HOSTS = ["open.spotify.com", "spotify.com", "podcasts.apple.com", "pod.link", "overcast.fm"]
ARTICLE_HOSTS = ["medium.com", "substack.com", "wired.com", "psypost.org", "businesswire.com",
    "paulgraham.com", "techcrunch.com", "theverge.com", "quantamagazine.org", "psychologytoday.com"]

def youtube_thumb(url):
    m = re.search(r"(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([A-Za-z0-9_-]{11})", url)
    return "https://img.youtube.com/vi/%s/hqdefault.jpg" % m.group(1) if m else ""

def pretty_from_url(u):
    path = re.sub(r"^https?://[^/]+", "", u)
    segs = [s for s in path.split("/") if s]
    seg = segs[-1] if segs else ""
    seg = re.sub(r"\.(html?|pdf|php|aspx?)$", "", seg)
    seg = re.sub(r"[-_]+", " ", seg).strip()
    if len(seg) < 3 or seg.isdigit() or re.match(r"^[0-9a-f]{8,}$", seg):
        return ""
    return seg[:90].strip().capitalize()

def first_sentence(ctx, n=100):
    ctx = re.sub(r"\s+", " ", ctx or "").strip()
    if not ctx:
        return ""
    s = re.split(r"(?<=[.!?])\s", ctx)[0]
    return s[:n].strip()

# ----------------------------------------------------------------------------- tagging

TOPIC_RULES = {
    "eeg": ["eeg", "electroenceph", "eegnet", "labram", "cbramod", "eegpt", "biot ", "biot,", "bendr",
            "braindecode", "moabb", "brainflow", "neurogpt", "neuro-gpt", "neurolm", "tueg", "microstate",
            "qeeg", "quantitative eeg", "seeg", "ieeg", "erp", "eeg-fm", "reve", "neurorvq", "brant"],
    "tms": ["tms", "rtms", "itbs", "transcranial", "neuromodulation", " saint", "magnus", "dlpfc",
            "theta burst", "stimulation"],
    "ketamine": ["ketamine", "esketamine", "spravato"],
    "wearables": ["wearable", "wearables", " muse", "interaxon", "oura", "whoop", "apple watch",
                  "in-ear", "in ear", "idun", "emotiv", "neurable", "neurosity", "headset",
                  "dry electrode", "dry-electrode", "openbci", "consumer", "pieeg", "zeto", "neeuro"],
    "psychedelics": ["psychedelic", "psilocybin", "dmt", "lsd", "mdma", "ibogaine", "5-meo", "5meo",
                     "critical period"],
    "neurofeedback": ["neurofeedback", "closed-loop", "closed loop", "downregulat", "biofeedback"],
    "bci": ["bci", "brain-computer", "brain computer", "motor imagery", "p300", "brain2qwerty",
            "brain-to-text", "brain to text", "neural interface", "neuralink", "synchron"],
    "sleep": ["sleep", "vigilance", "sleepfm", "hypnogram", "polysomn"],
    "biomarker": ["biomarker", "prognostic", "predictive marker", "response prediction", "predict response",
                  "treatment response", "treatment-response", "aperiodic", "1/f", "theta", "gamma",
                  "complexity", "lempel"],
    "connectome": ["connectome", "connectivity", "fmri", "flywire", "efp", "amygdala", "default mode",
                   "dmn", "limbic", "neuroimaging"],
    "foundation-model": ["foundation model", "foundation-model", "pretrained", "self-supervised",
                         "self supervised", "ssl", "masked", "transformer", "labram", "eegpt", "cbramod",
                         "biot", "bendr", "neurolm", "brant", "reve", "neurorvq", "cortexmae", "sleeplm",
                         "large brain model"],
    "depression": ["depression", "depressive", "mdd", "antidepressant", "anhedonia", "trd",
                   "treatment-resistant", "treatment resistant"],
}
MH_KEYWORDS = ["depression", "depressive", "mdd", "antidepressant", "anhedonia", "anxiety", "ptsd",
               "psychiatr", "mental health", "mood", "suicid", "bipolar", "trd", "wellbeing",
               "well-being", "ketamine", "esketamine", "tms", "rtms", "neurofeedback", "psychedelic"]
AI_KEYWORDS = ["model", "foundation", "transformer", "llm", "gpt", "machine learning", "deep learning",
               "neural network", "self-supervised", "self supervised", "decoder", "decoding",
               "benchmark", "embedding", "artificial intelligence", " ai ", "ai-", "agent",
               "fine-tune", "fine tune", "pretrained", "tokeniz", "diffusion", "autoregressive"]

FOCUS_KEYS = ["tms", "ketamine", "eeg", "wearables"]
EXTRA_TOPIC_KEYS = ["foundation-model", "psychedelics", "neurofeedback", "bci", "sleep", "biomarker",
                    "connectome", "depression"]

def detect_topics(text):
    t = text.lower()
    found = set()
    for topic, words in TOPIC_RULES.items():
        for w in words:
            if w in t:
                found.add(topic)
                break
    return found

def detect_domains(text, topics, kind):
    t = text.lower()
    domains = []
    ai = any(k in t for k in AI_KEYWORDS) or "foundation-model" in topics or kind in ("model", "benchmark")
    if ai:
        domains.append("ai")
    mh = any(k in t for k in MH_KEYWORDS) or bool(topics & {"depression", "ketamine", "tms",
                                                             "neurofeedback", "psychedelics"})
    if mh:
        domains.append("mental-health")
    return domains

ARXIV_TITLES = {
    "1706.03762": "Attention Is All You Need (Transformer)",
    "2405.18765": "LaBraM — Large Brain Model",
    "2409.00101": "NeuroLM — EEG + language multitask model",
    "2412.07236": "CBraMod — criss-cross brain foundation model",
    "2101.12037": "BENDR — self-supervised EEG pretraining",
    "2311.03764": "Neuro-GPT — generative EEG foundation model",
    "2508.17742": "EEG-FM-Bench — cross-dataset EEG FM benchmark",
    "2510.21585": "REVE — large-scale EEG pretraining (~60k hrs)",
    "2510.13768": "CortexMAE / Brainmarks (MedARC)",
    "2607.02134": "Coding agents can replicate scientific ML papers",
    "2309.02427": "Cognitive Architectures for Language Agents (CoALA)",
}
TOOLKIT_ROOTS = {"braindecode", "mne-python", "moabb", "torcheeg", "brainflow"}
MODEL_NAMES = {"labram", "eegpt", "cbramod", "biot", "bendr", "neurogpt", "neuro-gpt", "neurolm",
               "brant", "reve", "reve-base", "neurorvq", "cortexmae", "sleeplm", "osf-base",
               "osf-open-sleep-fm", "arl-eegmodels", "eegnet", "eeg-atcnet", "eeg-conformer",
               "eeg-inception", "tsception", "atcnet", "tribev2"}

def clean_repo_key(root):
    return re.sub(r"\*+$", "", (root or "").strip()).rstrip("/").lower()

# ----------------------------------------------------------------------------- item builders

def build_papers():
    items = []
    for r in read_csv("papers.csv"):
        url = (r.get("primary_url") or "").strip()
        if not url:
            continue
        ident = (r.get("title_or_identifier") or "").strip()
        host = host_of(url)
        notes = (r.get("notes") or "").strip()
        ctx = (r.get("context_preview") or "").strip()
        link_type = (r.get("link_type") or "").strip()
        origins = [o.strip() for o in (r.get("source_origin") or "").split("|") if o.strip()]
        srcfiles = [s.strip() for s in (r.get("source_files") or "").split("|") if s.strip()]
        all_urls = [u.strip() for u in (r.get("all_urls") or url).split() if u.strip()][:6]
        title = ident
        arx = re.match(r"arxiv:(\d+\.\d+)", ident.lower())
        if arx and arx.group(1) in ARXIV_TITLES:
            title = ARXIV_TITLES[arx.group(1)]
        elif arx:
            title = "arXiv " + arx.group(1)
        kind = "dataset" if "huggingface.co/datasets" in url else "paper"
        blob = " ".join([ident, title, notes, ctx, link_type, url])
        topics = detect_topics(blob)
        items.append(_item("p" + str(r.get("row_id")), kind, title, ident, url, all_urls, host,
                           provider_of(host), origins or ["Manual search"], topics, blob, link_type,
                           "", None, notes, ctx, srcfiles, "", False))
    return items

LICENSE_PATTERNS = [(r"cc[\s-]*by[\s-]*nc", "CC BY-NC (non-commercial)"), (r"apache[\s-]*2", "Apache-2.0"),
    (r"\bmit\b", "MIT"), (r"\bbsd\b", "BSD"), (r"\bgpl\b", "GPL"),
    (r"non[\s-]*commercial", "Non-commercial"), (r"all[\s-]*rights[\s-]*reserved", "All rights reserved")]
def detect_license(text):
    t = text.lower()
    for pat, label in LICENSE_PATTERNS:
        if re.search(pat, t):
            return label
    return ""

def repo_kind(provider, category, root, name, url):
    n = (name or "").lower(); rk = clean_repo_key(root); cat = (category or "").lower()
    if provider == "Hugging Face":
        return "dataset" if "/datasets/" in url else "model"
    if any(tk in rk for tk in TOOLKIT_ROOTS) or "library" in cat or "toolkit" in cat or "preprocess" in cat:
        return "toolkit"
    if "benchmark" in cat or "benchmark" in n:
        return "benchmark"
    if "foundation" in cat or "supervised" in cat or any(m == n or m in rk for m in MODEL_NAMES):
        return "model"
    return "repo"

def build_repos():
    rows = read_csv("repos.csv")
    merged = {}
    for r in rows:
        root = (r.get("normalized_root") or r.get("all_urls") or "").strip()
        key = clean_repo_key(root)
        if not key:
            continue
        name = re.sub(r"\*+$", "", (r.get("model_or_repo") or r.get("repo_or_model") or "").strip())
        provider = (r.get("provider") or "").strip() or provider_of(host_of(root))
        url = re.sub(r"\*+$", "", root)
        category = (r.get("category_or_type") or "").strip()
        notes = (r.get("notes") or "").strip(); ctx = (r.get("context_preview") or "").strip()
        origins = [o.strip() for o in (r.get("source_origin") or "").split("|") if o.strip()]
        srcfiles = [s.strip() for s in (r.get("source_files") or "").split("|") if s.strip()]
        all_urls = [u.strip() for u in (r.get("all_urls") or url).split() if u.strip().startswith("http")][:8]
        if key not in merged:
            merged[key] = {"name": name, "provider": provider, "url": url, "category": category,
                           "notes": notes, "context": ctx, "origins": set(origins),
                           "source_files": set(srcfiles), "all_urls": set(all_urls)}
        else:
            m = merged[key]; m["origins"].update(origins); m["source_files"].update(srcfiles)
            m["all_urls"].update(all_urls)
            if len(name) > len(m["name"]) and "*" not in name: m["name"] = name
            if not m["category"] and category: m["category"] = category
            if len(notes) > len(m["notes"]): m["notes"] = notes
            if len(ctx) > len(m["context"]): m["context"] = ctx
    items = []
    for i, (key, m) in enumerate(merged.items(), 1):
        url = m["url"]; host = host_of(url); provider = m["provider"] or provider_of(host)
        blob = " ".join([m["name"], m["category"], m["notes"], m["context"], url, key])
        kind = repo_kind(provider, m["category"], key, m["name"], url)
        topics = detect_topics(blob)
        lic = detect_license(m["notes"] + " " + m["context"] + " " + m["category"])
        wl = (m["notes"] + " " + m["context"]).lower()
        weights = True if (provider == "Hugging Face" or "pretrained" in wl or "weights" in wl or "checkpoint" in wl) else None
        it = _item("r" + str(i), kind, m["name"], m["name"], url, sorted(m["all_urls"]) or [url], host,
                   provider, sorted(m["origins"]) or ["Manual search"], topics, blob, m["category"],
                   lic, weights, m["notes"], m["context"], sorted(m["source_files"]), "", False)
        if kind in ("model", "benchmark", "toolkit") and "ai" not in it["domains"]:
            it["domains"] = ["ai"] + it["domains"]
        items.append(it)
    return items

def classify_other(url, host, ctx):
    ql = (url + " " + ctx).lower(); h = host
    if "huggingface.co" in h:
        return "dataset" if "/datasets/" in url else "model"
    if "github.com" in h or "github.io" in h:
        return "repo"
    if any(s in h for s in PODCAST_HOSTS) or "/episode/" in url or re.search(r"\bpodcast\b", ql):
        return "podcast"
    if any(s in h for s in VIDEO_HOSTS):
        return "video"
    if any(a in h for a in ACADEMIC_HOSTS):
        return "paper"
    if re.search(r"\b(fellowship|fellow|grant|sbir|residency|accelerator|apply now|applications open|deadline|funding call)\b", ql):
        return "grant"
    if any(s in h for s in ["neurips.cc", "iclr.cc"]) or re.search(r"\b(conference|symposium|summit|workshop|register|meetup|hackathon)\b", ql):
        return "event"
    if any(s in h for s in ARTICLE_HOSTS):
        return "article"
    if "drive.google.com" in h:
        return "other"
    return "company"

def build_docx(existing_keys):
    path = os.path.join(SRC, "docx_urls.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        recs = json.load(f)
    items = []; seen = set()
    for i, r in enumerate(recs, 1):
        url = r["url"]; key = normkey(url)
        if key in existing_keys or key in seen:
            continue
        seen.add(key)
        host = r.get("host") or host_of(url)
        ctx = r.get("context", "")
        kind = classify_other(url, host, ctx)
        provider = provider_of(host)
        if provider == "Web":
            provider = host
        # title
        if kind == "video":
            title = first_sentence(ctx, 90) or ("Video · " + host)
        else:
            title = pretty_from_url(url) or first_sentence(ctx, 80) or host
        preview = youtube_thumb(url) if kind == "video" else ""
        blob = " ".join([title, ctx, url])
        topics = detect_topics(blob)
        it = _item("d" + str(i), kind, title, "", url, [url], host, provider, ["Manual search"],
                   topics, blob, "", "", None, "", ctx, ["Source file dump (7/4/26)"], preview,
                   bool(r.get("from_linkedin")))
        if kind in ("model", "benchmark", "toolkit") and "ai" not in it["domains"]:
            it["domains"] = ["ai"] + it["domains"]
        items.append(it)
    return items

def _item(id, kind, title, ident, url, all_urls, host, provider, origins, topics, blob,
          category, license, weights, notes, context, source_files, preview_url, via_linkedin):
    return {
        "id": id, "kind": kind, "title": title, "ident": ident, "url": url, "all_urls": all_urls,
        "host": host, "provider": provider, "origins": origins,
        "domains": detect_domains(blob, topics, kind),
        "focus": [k for k in FOCUS_KEYS if k in topics],
        "topics": [k for k in EXTRA_TOPIC_KEYS if k in topics],
        "category": category, "license": license, "weights": weights,
        "notes": notes, "context": context, "source_files": source_files,
        "preview_url": preview_url, "via_linkedin": via_linkedin,
        "date": "", "drive_url": "", "sender": "",
    }

def derive_date(text):
    t = text or ""
    m = re.search(r"/(20\d{2})\.(\d{2})\.\d{2}", t)          # biorxiv/medrxiv YYYY.MM.DD
    if m and 1 <= int(m.group(2)) <= 12:
        return m.group(1) + "-" + m.group(2)
    m = re.search(r"/(20\d{2})/(\d{2})/", t)                 # blog /YYYY/MM/
    if m and 1 <= int(m.group(2)) <= 12:
        return m.group(1) + "-" + m.group(2)
    m = re.search(r"\b([0-2]\d)(\d{2})\.\d{4,5}\b", t)       # arXiv YYMM.xxxxx
    if m and 1 <= int(m.group(2)) <= 12:
        yy = int(m.group(1))
        return ("20" if yy < 80 else "19") + m.group(1) + "-" + m.group(2)
    return ""

# ----------------------------------------------------------------------------- main

def main():
    papers = build_papers()
    repos = build_repos()
    existing = set()
    for it in papers + repos:
        existing.add(normkey(it["url"]))
        for u in it["all_urls"]:
            existing.add(normkey(u))
    docx = build_docx(existing)
    items = papers + repos + docx

    # merge captured previews (og:image URLs + rendered PDF page-1 thumbnails)
    pv_path = os.path.join(HERE, "data", "previews.json")
    if os.path.exists(pv_path):
        with open(pv_path, encoding="utf-8") as f:
            pv = json.load(f)
        for it in items:
            if pv.get(it["id"]):
                it["preview_url"] = pv[it["id"]]
        print("merged", sum(1 for it in items if it["preview_url"]), "previews")

    # dates + Drive-copy links (match your existing Drive PDFs by id/DOI token)
    drive = {}
    dp = os.path.join(SRC, "drive_pdfs.json")
    if os.path.exists(dp):
        with open(dp, encoding="utf-8") as f:
            drive = json.load(f)
    for it in items:
        it["date"] = derive_date(it["url"] + " " + it.get("ident", "") + " " + it.get("context", ""))
        if it["kind"] in ("paper", "dataset") and drive:
            hay = (it["url"] + " " + it.get("ident", "")).lower()
            for tok, fid in drive.items():
                if tok.lower() in hay:
                    it["drive_url"] = "https://drive.google.com/file/d/" + fid + "/view"
                    break
    print("dated", sum(1 for it in items if it["date"]), "| drive-linked", sum(1 for it in items if it["drive_url"]))

    # arXiv abstracts — real titles + content so the Librarian can answer about papers
    ab = {}
    abp = os.path.join(HERE, "data", "abstracts.json")
    if os.path.exists(abp):
        with open(abp, encoding="utf-8") as f:
            ab = json.load(f)
    for it in items:
        it["abstract"] = ""
        if it["kind"] in ("paper", "dataset"):
            hay = (it["url"] + " " + it.get("ident", "")).lower()
            if "arxiv" in hay:
                m = re.search(r"(\d{4}\.\d{4,5})", hay)
                if m and m.group(1) in ab:
                    a = ab[m.group(1)]
                    it["abstract"] = a.get("abstract", "")
                    tl = it["title"].strip().lower()
                    if a.get("title") and (it["title"].startswith("arXiv ") or it["title"] == it.get("ident", "")
                                           or re.match(r"^(arxiv|doi)?[:\s]*\d{4}\.\d{4,5}(v\d+)?$", tl)):
                        it["title"] = a["title"]
    print("abstracts", sum(1 for it in items if it["abstract"]))

    # resolved metadata: real titles + abstracts recovered by scripts/enrich_oa.py
    # (only placeholder id-titles get a resolved title; abstracts fill papers that had none)
    rp = os.path.join(HERE, "data", "resolved_meta.json")
    resolved = json.load(open(rp)) if os.path.exists(rp) else {}
    rt = ra = 0
    for it in items:
        r = resolved.get(it["id"])
        if not r:
            continue
        if r.get("title"):
            it["title"] = r["title"]; rt += 1
        if r.get("abstract") and not it["abstract"]:
            it["abstract"] = r["abstract"]; ra += 1
    print("resolved-meta: titles", rt, "| abstracts", ra)

    # full text (content/<item-id>.txt) + reading status
    content_ids = set(os.path.splitext(os.path.basename(p))[0]
                      for p in glob.glob(os.path.join(HERE, "content", "*.txt")))
    # true open-access hosts only — PubMed (ncbi .../<PMID>) is abstract-only, so require PMC
    OA_HOSTS = ["arxiv.org", "biorxiv.org", "medrxiv.org", "ncbi.nlm.nih.gov/pmc", "osf.io",
                "pnas.org", "plos.org", "elifesciences.org", "frontiersin.org"]
    for it in items:
        it["content"] = ""
        it["read_status"] = ""
        if it["id"] in content_ids:
            it["content"] = "content/" + it["id"] + ".txt"
            it["read_status"] = "read"
        elif it["kind"] in ("paper", "dataset"):
            hay = (it["url"] + " " + it.get("ident", "")).lower()
            it["read_status"] = "fetchable" if any(h in hay for h in OA_HOSTS) else "needs_pdf"
    print("full-text", sum(1 for it in items if it["content"]),
          "| needs-pdf", sum(1 for it in items if it["read_status"] == "needs_pdf"),
          "| fetchable", sum(1 for it in items if it["read_status"] == "fetchable"))

    def tally(field):
        c = {}
        for it in items:
            vals = it[field] if isinstance(it[field], list) else [it[field]]
            for v in vals:
                if v:
                    c[v] = c.get(v, 0) + 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))

    dataset = {
        "generated": datetime.date.today().isoformat(),
        "counts": {
            "total": len(items),
            "papers": sum(1 for it in items if it["kind"] == "paper"),
            "repos_models": sum(1 for it in items if it["kind"] in ("model", "repo", "toolkit", "benchmark", "dataset")),
            "other": sum(1 for it in items if it["kind"] in ("video", "podcast", "article", "company", "event", "grant", "other")),
            "from_docx": len(docx),
            "by_kind": tally("kind"), "by_origin": tally("origins"),
            "by_domain": tally("domains"), "by_focus": tally("focus"), "by_topic": tally("topics"),
            "by_read": tally("read_status"),
        },
        "items": items,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=1)
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    payload = json.dumps(dataset, ensure_ascii=True).replace("</", "<\\/")
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(template.replace("__INVERSAL_DATA__", payload))
    print("Built", len(items), "items (", len(papers), "papers,", len(repos), "repos,", len(docx), "from DOCX )")
    print(json.dumps(dataset["counts"]["by_kind"], indent=2))

if __name__ == "__main__":
    main()
