# Stacks — build plan for the hard parts (Drive archive · full-text Librarian · real previews)

*Written 2026-07-08. Companion to the shipped app. Covers the three capabilities that a static page can't do honestly, with a recommended architecture and the decisions you need to make. Your own `inversal_prd.md` is the north star; this is the "how to actually build it" layer.*

---

## 0. Where we are

**Shipped and live** (https://lindsaygould.github.io/stacks/, repo `lindsaygould/stacks`):
- 628 sources = 300 papers + 68 repos/models + 260 other (183 companies, 36 videos, 28 articles, events, grants), each with **provenance** (Manual search / Claude / Claude Science).
- Filters by type, domain, MH focus, source, topic; search; **Ask the Librarian** (metadata retrieval, no key); **Add material**; **row + card views**; **saved views**; exports (all / view / papers / repos); LinkedIn-post context preserved and flagged; **real YouTube thumbnails**, typed covers otherwise.

**Not yet real — and honestly can't be on a static page:**
1. **The Librarian reading full paper text** (answering "what did this paper find?" from content, not a preview).
2. **Every paper archived in a Drive folder** with redundancy links.
3. **A real captured preview** (og:image / first-page render) for each source.

All three need a step that *fetches and processes external content* — impossible from a browser (CORS, paywalls, no filesystem, no Drive write). They need an **offline pipeline** and, for true Q&A, a **small backend**. That's the decision this doc frames.

---

## 1. The one architectural decision everything hangs on

Today Stacks is a **static single file on GitHub Pages**. Two of the three asks (full-text answers; persistent add-to-repo) want a server. Three viable paths:

| Path | What it unlocks | Cost / effort | Verdict |
|---|---|---|---|
| **A. Stay static + offline pipeline** | Papers downloaded to Drive, text extracted, previews captured, a richer `dataset.json` + a **full-text keyword index** shipped with the app. Librarian can *search inside* papers and quote snippets. No live LLM Q&A. | Low. A Python pipeline I run (or a GitHub Action). $0 hosting. | **Recommended first step.** Delivers ~80% of the value with no backend, no keys, no new bill. |
| **B. Move to Vercel + serverless Librarian** | Everything in A **plus** true conversational Q&A over full text (RAG: retrieve chunks → LLM answers with citations), and an "Add material" button that commits straight to the repo. | Medium. A Vercel project, an Anthropic key (server-side), an embeddings index. Small monthly cost + per-question API cost. | **Recommended once A proves the corpus.** This is the "it actually read the paper" experience. |
| **C. Full research OS** (Zotero sync, dead-link cron, browser extension, evidence matrices) | Everything in your PRD §19 Phases 4–5. | High, ongoing. | Later. Don't build until A+B are used daily. |

**Recommendation: build A now, B next, C never-until-needed.** A is cheap and reversible; B is the real Librarian; C is scope you can grow into.

---

## 2. Paper archive to Google Drive (the "download every paper" ask)

### 2.1 Reality check — you already have ~90 of them
The ENO Drive folder `Research / Source files from personal research / Source file dump: Pdfs` already holds ~90 downloaded PDFs. So this is **reconcile + fill the gaps**, not download-everything-from-scratch.

### 2.2 What's downloadable vs not
Of the 300 paper records: **open-access is fetchable** (arXiv, bioRxiv, medRxiv, PMC, OSF, many Nature/Frontiers OA, PLOS). **Paywalled is not** (many Nature/Cell/ScienceDirect/JAMA/Wiley/Oxford full texts). Honest target: **archive the open-access set (~55–65% of papers) automatically; flag the rest as `link-only, paywalled`** so you can grab them manually from institutional access.

### 2.3 Recommended flow (a script I run, `scripts/archive_papers.py`)
1. For each `paper`, resolve a **direct PDF URL** (arXiv `/pdf/…`, PMC PDF, DOI→Unpaywall API for a free PDF if one exists).
2. **Match against existing Drive PDFs first** (by arXiv id / DOI / title) so we never re-download the ~90 you have.
3. Download the missing open-access PDFs; upload to one canonical Drive folder — **`ENO / Stacks Library / Papers`** — via the Drive API. Record the **Drive file id + shareable link**.
4. Write back to each record: `pdf_status` (downloaded / paywalled / not-found), `drive_file_id`, `drive_url`, `local_pdf_name`.
5. Redundancy, exactly as you intuited: the card keeps the **public URL** *and* a **"📄 Your Drive copy"** button. The public link is the human-readable source; the Drive link is the durable copy that survives link rot.

### 2.4 Data-model additions (aligns with your PRD §9/§11)
`pdf_status · drive_file_id · drive_url · doi · arxiv_id · full_text_extracted · full_text_path`. These become new columns; the app shows an **asset-status badge** (Drive ✓ / paywalled / link-only) and a Drive filter.

**Decision needed:** authorize Drive **write** to that folder (one-time), and confirm the folder name. Copyright note (your PRD §16): keep the Drive folder **private** — never expose downloaded PDFs on the public site.

---

## 3. The Librarian that has actually read everything

This is the heart of your ask: *"if I ask a specific question about a paper, it would know it, not just from a little preview."* That is **retrieval-augmented generation (RAG)** over full text. Two tiers:

### Tier 1 — Full-text *search* (static, no key) — ship with Path A
- Pipeline extracts text from every archived PDF (`PyMuPDF`) and from open article pages (`trafilatura`); stores a compact **per-source text blob** (title + abstract + section headers + first ~2–3k words) and builds a client-side **BM25/inverted index** shipped as a compressed file.
- The Librarian then searches **inside** papers, not just titles — "which papers discuss aperiodic slope flattening?" returns papers whose *body* mentions it, with the matching **snippet** quoted.
- Honest limit: it *finds and quotes*, it doesn't *reason/synthesize*. No API cost. Big jump over today.

### Tier 2 — Full-text *Q&A* (serverless + key) — Path B
- Chunk each full text (~800 tokens), **embed** (one-time), store vectors (a static JSON for a few hundred papers is fine, or a lightweight vector store).
- A Vercel function: embed the question → retrieve top chunks → **Claude (`claude-opus-4-8`)** answers with **inline citations** that deep-link to the source card (exactly The Stacks' cite-and-flash pattern). Cost is per-question, small.
- This is the "it read the paper and can explain it" experience, grounded and cited.

**Recommendation:** Tier 1 in Path A (immediate, free, honest), Tier 2 when you want conversational depth. Never let the Librarian imply it read a PDF it hasn't — asset status gates the claim (your PRD §5/§15, "trust over cleverness").

---

## 4. Real previews for every source

You asked: capture the preview from the link and store it. Best-per-type:

| Source type | Best real preview | How |
|---|---|---|
| **Video (YouTube)** | ✅ already live | thumbnail from video id (no fetch) |
| **Paper (PDF archived)** | **First-page render → PNG** | `PyMuPDF` renders page 1 of the Drive PDF; store the PNG. This is the single highest-value preview — a real thumbnail of the actual paper. |
| **GitHub / Hugging Face** | Social preview image | GitHub `opengraph.githubassets.com` / HF card via API at build time |
| **Company / article / blog** | **og:image** | fetch the page's `og:image` at build time; store the image |
| **Paywalled paper / LinkedIn** | No reliable image | typed cover + the preserved context text (LinkedIn can't be scraped logged-out) |

Mechanism: a build-time `scripts/capture_previews.py` fetches og:images and renders PDF first pages into `public/thumbs/`, writes `preview_path` per record. For the stubborn ~10–15% (paywalls, JS-only pages) an optional headless-screenshot service (Browserless/ScreenshotOne) fills gaps — a small metered cost. Typed covers remain the guaranteed fallback so coverage stays 100%.

---

## 5. Also worth folding in (cheap wins, from your PRD)

- **Related-resource clustering** (your PRD §9 `related_resources`): NeuroRVQ's paper + repo + HF model + project page are one *thing*. The pipeline can group by shared name/authors and show "3 related" on a card. High value, low cost.
- **Evidence grade** on papers (Established / Emerging / Contested) — we already produced this grading in the eno research; import it as a field + filter.
- **Edit for any card** (today only user-added items are editable) — needed so you can fix a weak auto-title or re-tag a "company" that's really a grant. Add in Path A.
- **De-dup across types** — the pipeline should merge a paper that appears both in the CSV and the DOCX (already done by URL; extend to DOI/arXiv id).

---

## 6. Phased plan

**Phase A1 — Enrichment pipeline (static, no key, ~1 build session)**
`scripts/` gains: `archive_papers.py` (Drive), `extract_fulltext.py` (PyMuPDF/trafilatura), `capture_previews.py` (og:image + PDF page 1), `build_index.py` (BM25). App gains: asset-status badges + Drive filter + full-text search in the Librarian + PDF/og previews + card editing + related-resources. Still GitHub Pages, still $0.

**Phase A2 — Drive reconcile**
Map the ~90 existing PDFs, download the open-access gaps, write Drive links back. One-time Drive-write authorization.

**Phase B — Serverless Librarian (Vercel + key)**
Move hosting to Vercel (or keep Pages + a Vercel function endpoint), add embeddings + RAG Q&A with citations, and commit-back for Add material.

**Phase C — Automation** (later): GitHub issue/bookmarklet capture, dead-link cron, Zotero/BibTeX export, evidence matrices.

---

## 7. Decisions for you

1. **Hosting:** stay on **GitHub Pages** for Phase A (recommended), or jump to **Vercel** now so Phase B's real-Q&A Librarian and commit-back are on the table sooner?
2. **Private or public?** Your PRD §16 defaults **private**. Full-text snippets + LinkedIn context + Drive-linked PDFs are borderline to host publicly. Recommendation: **make it private** before Phase A ships full text (private Pages needs GitHub Pro; Vercel does private free — a point for Path B).
3. **Drive write:** OK to authorize me to create an `ENO / Stacks Library / Papers` folder and archive the open-access PDFs into it, reconciling your existing ~90?
4. **Librarian depth:** Tier 1 full-text *search* (free) enough for now, or go straight to Tier 2 *Q&A* (needs an Anthropic key)?
5. **Preview spend:** free previews only (YouTube + og:image + PDF page-1), or add a metered screenshot service for the paywalled/JS-only ~15%?

**My recommendation in one line:** do **Phase A1 + A2 on a private repo/host now** (full-text *search*, PDF + og previews, Drive archive of the open-access papers with redundancy links) — it makes the Librarian genuinely knowledgeable and every paper durable, at ~$0 — then add the **Tier-2 RAG Q&A on Vercel** once you're living in it daily.
