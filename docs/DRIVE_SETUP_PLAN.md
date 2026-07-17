# Stacks × Google Drive — the setup (plan)

*Written 2026-07-16. Make Stacks "just work" with Google Drive as the file store — no Vercel Blob. One folder, one clear rule for what goes there, and a one-time tidy to get you there.*

---

## The model, in one sentence

**Stacks' database is the brain** (every source's metadata, provenance, your notes, and the searchable full text). **Google Drive is the filing cabinet** for the actual PDF files. Stacks reads exactly **one** Drive folder.

## What lives in Google Drive — and what doesn't

This is the important part. The dividing line is simple: **a file you want to keep and read → Drive. A live web link → it just stays a link in Stacks.**

| When you add… | The file lives in… | Stacks stores… |
|---|---|---|
| A **paywalled paper** (you have the PDF) | **Google Drive** → `Stacks Papers` | link + metadata + extracted text + a Download button |
| An **open-access paper** (arXiv / bioRxiv / PMC) | Drive **optional** — Stacks reads it free | link + metadata + text. Drop the PDF too *only if* you want a guaranteed personal copy + a page-1 preview |
| A **web article / blog post** (no PDF) | **Nothing** — it's a link | link + metadata + your note |
| A **YouTube video / podcast** | **Nothing** — it's a link | link + metadata (+ transcript later) |
| A **GitHub repo / model / dataset** | **Nothing** — it's a link | link + metadata |
| A **company / event / grant** | **Nothing** — it's a link | link + metadata |

**Rule of thumb:** if it's a **PDF you want to keep and read offline**, it goes in Drive. Everything that's a live web link stays a link inside Stacks — nothing to upload.

## The one folder

`ENO / Stacks / Stacks Papers` — the single home for every paper/article PDF. Stacks syncs **only** this folder. *(I already created it — it's empty.)* Repo/model catalogs go in `Stacks Repos & Models` next to it, for your reference (Stacks doesn't ingest those — they're already in the database).

## One-time tidy (the "go back and do it" task)

Your ~154 existing PDFs are split across two folders (`Literature/Papers` ≈ 44 and `Source file dump: Pdfs` ≈ 110), which is why Stacks only sees 44 today. To fix it once:

1. **Copy** all ~154 PDFs into `Stacks Papers` — **duplicates; your originals are never touched.**
2. **Pin the sync** to read only `Stacks Papers` (remove the old fallback).
3. **Sync** → Stacks pulls text for all of them, clearing most of the "Needs your PDF" queue, and I render page-1 **previews** from them.

## By hand vs. me — my recommendation: **let me do it**

- Copying through the Drive API (`copy_file`) is **non-destructive by design** — it makes a copy in `Stacks Papers` and leaves every original exactly where it is. I have the exact file IDs, so nothing gets missed.
- Doing it **by hand is riskier**: in Drive, drag-and-drop **moves** files (it doesn't copy), so a slip could pull your originals out of their folders — across 154 files, that's a real chance of disorganizing your archive. To truly duplicate by hand you'd have to copy-then-move each one, which is slow and error-prone.
- Cost either way: ~1–2 GB of duplicate storage in your Drive (you've said that's fine).

So: **I run the copy** (safe, precise, ~154 non-destructive operations), you keep your originals untouched, and you get one clean folder.

## Making the PDFs accessible from inside Stacks

- Any paper with a Drive copy gets a **Download / Open PDF** button (opens your Drive file).
- Page-1 thumbnails rendered from those PDFs fill in the ~200 missing previews. Previews live in the app's own build (a data file + committed thumbnails), so they're permanent regardless.

## Going forward (dead simple)

- **Paper/article you want the file for** → save the PDF → drop it in **`Stacks Papers`**, add the link in Stacks. It stores, reads, previews, and is downloadable.
- **Video / repo / web article / company** → just add the link in Stacks. Nothing goes to Drive.

## What I'd change in the app so this is obvious

- The **Add** flow labels each add: a paper says *"drop the PDF in your Stacks Papers folder to store + read it"*; a link says *"saved as a link."*
- Cards/detail show **Download PDF** when a Drive copy exists, and a clear *"Needs your PDF → add it to Stacks Papers"* when it doesn't.

## Green light?

Say go and I'll: (1) copy your ~154 PDFs into `Stacks Papers` (non-destructive), (2) pin the sync, (3) add the Download button + fill previews.
