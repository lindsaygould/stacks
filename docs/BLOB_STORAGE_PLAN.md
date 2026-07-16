# Stacks — Vercel Blob storage, PDF import, download & previews (plan)

*Written 2026-07-16. Make Stacks itself hold every paper's PDF — permanently and retrievably — so papers can be uploaded in-app, downloaded one-by-one or in bulk, and previewed, independent of anyone's Google Drive. Source of truth = Stacks DB + Blob.*

---

## The store

- **Vercel Blob**, private. Each PDF → a blob at `papers/<item-id>.pdf`. On the item we store `pdf_url` (the blob), `thumb_url` (page-1 render), and `pdf_sha` (hash, for dedupe).
- One env var: `BLOB_READ_WRITE_TOKEN` (Vercel injects it when you add Blob to the project — one click in the dashboard, same as the Neon DB).
- Durable by definition: uploaded once → stored forever → retrievable anytime. (Rules out ephemeral serverless dirs.)

## Phase 1 — Upload + download (the core)

- **`api/upload.js`** (auth-gated): accepts a PDF → stores to Blob → extracts text (`pdf-parse`) into `fullText` + `read_status='read'` → renders a **page-1 thumbnail** → `thumb_url` → sets `pdf_url` + `pdf_sha` (dedupe by hash so the same paper isn't stored twice).
- **UI — a `Download PDF` button on the card + detail**, with three honest states:
  - **stored** (`pdf_url`) → downloads from Blob.
  - **open-access, nothing uploaded** → links to the free PDF (arXiv/PMC). *Works today.*
  - **paywalled, none yet** → the button becomes **`Upload the PDF →`** (file picker → `api/upload`).
- Card/detail copy makes the link-vs-file distinction explicit: **"Full text ✓ · Download"** vs **"Paywalled — upload the PDF."**

## Phase 2 — Import your existing Drive PDFs (one-time migration)

- Your ~154 Drive PDFs (both folders) → Blob, **matched to items by content** (reuse `drive-sync`'s title/arXiv/DOI matcher — already proven).
- **`api/drive-import.js`** (or a one-off script): for each Drive PDF → download → match to item → upload to Blob (`pdf_url`) → extract text → render thumbnail (`thumb_url`). Batched + resumable, exactly like `drive-sync`. Uses your existing read-only Drive connection — no new permissions.
- **No tidying needed.** The importer reads straight from your **existing** folders (`Literature/Papers` + `Source file dump: Pdfs`) — you do **not** have to duplicate anything into `ENO/Stacks`. (So the manual copy we started earlier stays cancelled.)
- **This is also the real preview fix.** Every imported PDF gets a page-1 thumbnail — so the ~109 paywalled papers you already have PDFs for finally get real previews, stored durably. Previews go up sharply here, not from og:image scraping.

## Phase 3 — Download all (bundle)

- **`api/bundle.js`**: a ZIP of the stored PDFs + a **manifest CSV** (title, authors, provenance, who shared it), with **open-access and paywalled kept in separate folders** inside the zip (the copyright separation you agreed to).
- For 1–2 GB the robust path is a **background job → write the zip to Blob → return a download link** (a live-streamed zip would blow past serverless memory/time). Plus a lightweight **"Download all in this view"** for small, instant zips.

## Previews persist by design

Previews live in **`data/previews.json` (id→url)** + the committed **`thumbs/`** dir + (new) **`thumb_url`** on Blob for uploaded PDFs. **None of these depend on Drive**, so switching PDF storage to Blob cannot break existing previews — and new uploads/imports *generate* previews (page-1 renders) stored durably. Previews only ever increase.

## Multi-user

Blob is **app-owned**, so any signed-in contributor uploads and everyone benefits; provenance (who uploaded / who shared) is stamped per item. Paywalled PDFs are gated in the bulk export.

## Recommended order + the one open question

1. **Phase 1** — upload + per-item download (individual "hold it forever" works first).
2. **Phase 2** — import your Drive backlog → fills text *and* previews for the papers you already have.
3. **Phase 3** — the bundle / "download all."

**Open question:** I recommend **skipping the tidy** — the importer pulls PDFs from your existing Drive folders directly, so duplicating everything into `ENO/Stacks` first buys nothing. The only reason to do the copy first is if you'd prefer a single clean folder for your own peace of mind. **Import-from-where-they-are, or copy-into-one-folder-first?**
