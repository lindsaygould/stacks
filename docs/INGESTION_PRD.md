# Stacks — bundled sources + full-text ingestion (PRD)

*Written 2026-07-09. Two linked problems: (1) let one "thing" be several links (a LinkedIn post that points to a paper = one object), and (2) get the actual full text of every paper into the Librarian — automatically where possible, with a clearly-outlined manual fallback where not.*

---

## 1. Bundled sources — one object, many links

**The case you described:** you find a LinkedIn post that links to a paper. The LinkedIn URL is a wrapper (auth-gated, unreadable to a model); the paper URL is the real source. You'd have both. Today "Add" takes one URL, so you'd either lose the paper or lose the post context.

**The model:** an item can carry **several URLs**, saved as **one object**:

| Field | Meaning |
|---|---|
| `url` (canonical) | The real source to open/ingest — the **paper**, never the LinkedIn wrapper |
| `all_urls` | Every link in the bundle (paper + LinkedIn post + blog + repo…) |
| `context` | The pasted text — usually the **LinkedIn post body** (why it matters) |
| `via_linkedin` | Flag: this came from a LinkedIn post (already in the UI) |

**Canonical rule** (matches the existing non-goal "never treat LinkedIn as primary"): when a bundle has a LinkedIn/`lnkd.in` URL *and* a direct link, the direct link is canonical and the LinkedIn URL becomes an associated link + context. If the only URL is LinkedIn, it stays as-is (a LinkedIn item).

**Why this matters:** you do the un-wrapping once (you paste the direct paper link you found behind the post), so the model never has to defeat LinkedIn's gating. The object then ingests from the paper link and keeps the post as context.

**Add flow:** the URL field becomes "**paste one or more links**" (one per line). On save: split lines → pick canonical (first non-LinkedIn direct link) → `all_urls` = all → `context` = your notes/post text → type inferred from canonical. One object, many links.

---

## 2. Reading status — what's ingested, what needs you

Every item gets a **`read_status`** so the app is explicit about what the Librarian actually knows:

| Status | Meaning | Action |
|---|---|---|
| ✅ **read** | Full text is ingested (from your Drive PDF, or auto-fetched open-access) | none — the Librarian answers from the paper |
| ⏳ **fetchable** | Open-access (arXiv / PMC / bioRxiv / OSF, or a DOI with a free copy) — text not pulled *yet* | none — the auto-sync gets it |
| 📄 **needs your PDF** | A paper we can't fetch (paywalled) and isn't in your Drive folder | **you** drop the PDF in the Drive folder (monthly is fine) |
| — **n/a** | Non-paper (video, company, repo…) — its context/preview is already indexed | none |

This is the "clearly outlined by the app" part you asked for: a **"Needs your PDF (N)"** quick-view and filter lists *exactly* which papers still need you, each with a one-click link to the Drive folder to drop it into. Everything else is either already read or fetches itself.

---

## 3. The ingestion pipeline — automatic first, manual only as fallback

**Assume open access.** When a paper enters (existing corpus or a new add), try to get its text automatically, in order:

1. **arXiv / bioRxiv / medRxiv / PMC** → fetch the PDF directly, extract text (`pdftotext`), store. No key, no login.
2. **DOI** → check **Unpaywall** for a legal free PDF; if one exists, fetch + extract. (Covers many "paywalled-looking" papers that actually have an OA copy.)
3. **Your Drive PDF folders** → for anything you've already downloaded (incl. paywalled), read the text straight from Drive (the tool returns extracted text, no download). *This is already done for your ~140 existing PDFs.*
4. **Still nothing** → mark **needs your PDF** and surface it in the to-do list.

**Where text lives:** extracted text is stored in the **database** as `content/<item-id>.txt` (small — a paper is ~40–60 KB of text). PDFs stay in Drive; the repo never holds a PDF. The Librarian loads a paper's text on demand when it answers, and cites from it.

**Forward, without you downloading everything:**
- **New open-access add** → auto-fetched and read on the next sync. Zero manual work.
- **New paywalled add** → lands in "Needs your PDF." You drop the file in the Drive folder on your own cadence; the next sync reads it. The app always shows the exact backlog.
- The **sync** is a script now (`ingest.py`), a scheduled job later — it runs the four steps above over anything not yet `read`.

**The ideal (auto-download + organized archive):** for open-access papers the sync can also **save the fetched PDF into one organized Drive folder** (`ENO / Stacks Library / Papers`) so your archive stays complete without you lifting a finger — "read or download it on your behalf and store it organized." This needs Drive **write** access (a one-time auth), so it's the one piece that graduates to the backend; paywalled papers can't be auto-downloaded and stay on the manual list.

---

## 4. What ships now vs. next

**Now (this build):**
- Multi-link **bundled Add** (canonical + associated links + context).
- **Full text** from your existing Drive PDFs wired into the Librarian (answers from paper text, cites it).
- **Open-access auto-fetch** (`ingest.py`: arXiv/PMC/Unpaywall → `pdftotext` → `content/`) so OA papers read themselves — no manual download.
- **Reading-status** everywhere + a clearly-outlined **"Needs your PDF"** to-do (filter + quick view + per-card badge + link to the Drive folder).

**Next:** the sync as a scheduled/serverless job (auto-ingest on every add), and the ideal auto-download-to-Drive for OA (needs Drive write). Both live on the same Vercel project — no migration.
