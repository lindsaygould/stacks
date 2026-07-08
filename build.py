#!/usr/bin/env python3
"""
Inversal build pipeline.

Reads the source CSVs in data/source/, normalizes + dedupes them into a single
tagged dataset (data/dataset.json), and injects that dataset into the app shell
(app.template.html) to produce a fully self-contained index.html.

No third-party dependencies (stdlib only). Run:  python3 build.py
"""
import csv, json, re, os, datetime

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

PROVIDER_MAP = [
    ("github.com", "GitHub"), ("github.io", "GitHub"), ("huggingface.co", "Hugging Face"),
    ("arxiv.org", "arXiv"), ("biorxiv.org", "bioRxiv"), ("medrxiv.org", "medRxiv"),
    ("nature.com", "Nature"), ("sciencedirect.com", "ScienceDirect"), ("cell.com", "Cell Press"),
    ("pmc.ncbi.nlm.nih.gov", "PubMed / PMC"), ("ncbi.nlm.nih.gov", "PubMed / PMC"),
    ("jamanetwork.com", "JAMA"), ("doi.org", "DOI"), ("linkedin.com", "LinkedIn"),
    ("lnkd.in", "LinkedIn"), ("youtube.com", "YouTube"), ("youtu.be", "YouTube"),
    ("openreview.net", "OpenReview"), ("neurips.cc", "NeurIPS"), ("pnas.org", "PNAS"),
    ("frontiersin.org", "Frontiers"), ("biomedcentral.com", "BMC"), ("springer.com", "Springer"),
    ("link.springer.com", "Springer"), ("onlinelibrary.wiley.com", "Wiley"), ("wiley.com", "Wiley"),
    ("academic.oup.com", "Oxford"), ("oup.com", "Oxford"), ("mdpi.com", "MDPI"),
    ("ssrn.com", "SSRN"), ("papers.ssrn.com", "SSRN"), ("kickstarter.com", "Kickstarter"),
    ("pieeg.com", "PiEEG"), ("brainflow.org", "BrainFlow"), ("mne.tools", "MNE"),
    ("sophont.med", "Web"), ("cell.com", "Cell Press"),
]
def provider_of(host):
    for k, v in PROVIDER_MAP:
        if host.endswith(k) or host == k or ("." + k) in ("." + host):
            return v
    for k, v in PROVIDER_MAP:
        if k in host:
            return v
    return "Web" if host else "Web"

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
                  "dry electrode", "dry-electrode", "openbci", "consumer", "pieeg", "zeto"],
    "psychedelics": ["psychedelic", "psilocybin", "dmt", "lsd", "mdma", "ibogaine", "5-meo", "5meo",
                     "critical period"],
    "neurofeedback": ["neurofeedback", "closed-loop", "closed loop", "downregulat", "biofeedback"],
    "bci": ["bci", "brain-computer", "brain computer", "motor imagery", "p300", "brain2qwerty",
            "brain-to-text", "brain to text"],
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

# well-known identifiers -> friendly titles (high confidence only)
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

# ----------------------------------------------------------------------------- build items

def build_papers():
    items = []
    for r in read_csv("papers.csv"):
        url = (r.get("primary_url") or "").strip()
        if not url:
            continue
        ident = (r.get("title_or_identifier") or "").strip()
        host = host_of(url)
        provider = provider_of(host)
        notes = (r.get("notes") or "").strip()
        ctx = (r.get("context_preview") or "").strip()
        link_type = (r.get("link_type") or "").strip()
        origins = [o.strip() for o in (r.get("source_origin") or "").split("|") if o.strip()]
        srcfiles = [s.strip() for s in (r.get("source_files") or "").split("|") if s.strip()]
        all_urls = [u.strip() for u in (r.get("all_urls") or url).split() if u.strip()][:6]

        # friendly title
        title = ident
        arx = re.match(r"arxiv:(\d+\.\d+)", ident.lower())
        if arx and arx.group(1) in ARXIV_TITLES:
            title = ARXIV_TITLES[arx.group(1)]
        elif arx:
            title = "arXiv " + arx.group(1)
        elif ident.lower().startswith("doi:"):
            title = ident
        kind = "paper"
        if "huggingface.co/datasets" in url:
            kind = "dataset"

        blob = " ".join([ident, title, notes, ctx, link_type, url])
        topics = detect_topics(blob)
        domains = detect_domains(blob, topics, kind)
        items.append({
            "id": "p" + str(r.get("row_id")),
            "kind": kind,
            "title": title,
            "ident": ident,
            "url": url,
            "all_urls": all_urls,
            "host": host,
            "provider": provider,
            "origins": origins or ["Manual search"],
            "domains": domains,
            "focus": [k for k in FOCUS_KEYS if k in topics],
            "topics": [k for k in EXTRA_TOPIC_KEYS if k in topics],
            "category": link_type,
            "license": "",
            "weights": None,
            "notes": notes,
            "context": ctx,
            "source_files": srcfiles,
        })
    return items

LICENSE_PATTERNS = [
    (r"cc[\s-]*by[\s-]*nc", "CC BY-NC (non-commercial)"),
    (r"apache[\s-]*2", "Apache-2.0"),
    (r"\bmit\b", "MIT"),
    (r"\bbsd\b", "BSD"),
    (r"\bgpl\b", "GPL"),
    (r"non[\s-]*commercial", "Non-commercial"),
    (r"all[\s-]*rights[\s-]*reserved", "All rights reserved"),
]
def detect_license(text):
    t = text.lower()
    for pat, label in LICENSE_PATTERNS:
        if re.search(pat, t):
            return label
    return ""

def repo_kind(provider, category, root, name, url, blob):
    n = (name or "").lower()
    rk = clean_repo_key(root)
    cat = (category or "").lower()
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
        notes = (r.get("notes") or "").strip()
        ctx = (r.get("context_preview") or "").strip()
        origins = [o.strip() for o in (r.get("source_origin") or "").split("|") if o.strip()]
        srcfiles = [s.strip() for s in (r.get("source_files") or "").split("|") if s.strip()]
        all_urls = [u.strip() for u in (r.get("all_urls") or url).split() if u.strip().startswith("http")][:8]

        if key not in merged:
            merged[key] = {
                "name": name, "provider": provider, "url": url, "owner": (r.get("owner") or "").strip(),
                "category": category, "notes": notes, "context": ctx,
                "origins": set(origins), "source_files": set(srcfiles), "all_urls": set(all_urls),
            }
        else:
            m = merged[key]
            m["origins"].update(origins)
            m["source_files"].update(srcfiles)
            m["all_urls"].update(all_urls)
            if len(name) > len(m["name"]) and "*" not in name:
                m["name"] = name
            if not m["category"] and category:
                m["category"] = category
            if len(notes) > len(m["notes"]):
                m["notes"] = notes
            if len(ctx) > len(m["context"]):
                m["context"] = ctx

    items = []
    for i, (key, m) in enumerate(merged.items(), 1):
        url = m["url"]
        host = host_of(url)
        provider = m["provider"] or provider_of(host)
        blob = " ".join([m["name"], m["category"], m["notes"], m["context"], url, key])
        kind = repo_kind(provider, m["category"], key, m["name"], url, blob)
        topics = detect_topics(blob)
        # repos/models are inherently AI unless clearly hardware/plotting-only
        domains = detect_domains(blob, topics, kind)
        if kind in ("model", "benchmark", "toolkit") and "ai" not in domains:
            domains = ["ai"] + domains
        lic = detect_license(m["notes"] + " " + m["context"] + " " + m["category"])
        weights = None
        wl = (m["notes"] + " " + m["context"]).lower()
        if provider == "Hugging Face" or "pretrained" in wl or "weights" in wl or "checkpoint" in wl:
            weights = True
        items.append({
            "id": "r" + str(i),
            "kind": kind,
            "title": m["name"],
            "ident": m["name"],
            "url": url,
            "all_urls": sorted(m["all_urls"]) or [url],
            "host": host,
            "provider": provider,
            "origins": sorted(m["origins"]) or ["Manual search"],
            "domains": domains,
            "focus": [k for k in FOCUS_KEYS if k in topics],
            "topics": [k for k in EXTRA_TOPIC_KEYS if k in topics],
            "category": m["category"],
            "license": lic,
            "weights": weights,
            "notes": m["notes"],
            "context": m["context"],
            "source_files": sorted(m["source_files"]),
        })
    return items

def main():
    papers = build_papers()
    repos = build_repos()
    items = papers + repos

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
            "repos_models": sum(1 for it in items if it["kind"] != "paper"),
            "by_kind": tally("kind"),
            "by_origin": tally("origins"),
            "by_domain": tally("domains"),
            "by_focus": tally("focus"),
            "by_topic": tally("topics"),
        },
        "items": items,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=1)

    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    payload = json.dumps(dataset, ensure_ascii=True).replace("</", "<\\/")
    index = template.replace("__INVERSAL_DATA__", payload)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(index)

    print("Built", len(items), "items ->", OUT_JSON, "and index.html")
    print(json.dumps(dataset["counts"], indent=2))

if __name__ == "__main__":
    main()
