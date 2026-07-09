# Stacks

A searchable, filterable knowledge base for the papers, repositories, and models behind the research — a calmer, smarter home for everything that would otherwise get lost in a folder or a source dump.

**Live site (Vercel, primary):** https://stacks-lindsayagould-6658s-projects.vercel.app
**Backup (GitHub Pages):** https://lindsaygould.github.io/stacks/

## What it does

- **628 sources** to start — 300 papers + 68 repos/models, plus videos, companies, articles and more — each tagged by **type**, **domain** (AI / mental health), **focus** (TMS · ketamine · EEG · wearables), extra **topics** (foundation models, biomarkers, connectome/fMRI, depression, psychedelics, BCI, sleep, neurofeedback), and **source provenance** (Manual search · Claude · Claude Science).
- **Filter + search** everything from the left rail; facet counts update as you narrow, like booking a flight.
- **Typed previews** — every card gets a provider-colored cover (arXiv, GitHub, Hugging Face, Nature, LinkedIn, …) so the wall is scannable at a glance, with no broken images.
- **Add anything** you find online with one click (**+ Add**): paste a URL, the type + provider are guessed, tag it, save. Additions live in your browser and can be exported to make them permanent (**Data → Export**).
- **Ask Stacks** — a bottom-right assistant that searches only this library (no web, no API key): *“show me all the repos”*, *“papers about ketamine”*, *“EEG foundation models”*, *“what’s from Claude Science?”* It answers with counts and clickable source cards, and can push its results into the grid as filters.

## How it’s built

Fully static, zero backend, zero dependencies at runtime — a single self-contained `index.html` (data inlined) that works on GitHub Pages or by double-click.

```
data/source/         the three source CSVs (papers, repos, combined) — provenance
build.py             parses + dedupes the CSVs, tags every item, injects data into the shell
app.template.html    the app shell (CSS + JS) with a __INVERSAL_DATA__ placeholder
data/dataset.json    the generated, tagged dataset (also committed for reference)
index.html           the built, deployable app  ← what GitHub Pages serves
```

### Rebuild after changing data or the UI

```bash
python3 build.py
```

That regenerates `data/dataset.json` and `index.html`. Commit and push — Pages redeploys automatically.

### Making browser-added items permanent

Items added via **+ Add** are saved in `localStorage` (per browser). To bake them into the shared library: **Data → Export JSON**, drop the items into `data/dataset.json` (or add rows to a source CSV and re-run `build.py`), then commit.

## Provenance

Every item records where it came from, mirroring the ENO research folder taxonomy:
**Manual search** (collected by hand), **Claude Science** (from the Claude Science model/biomarker work), and **Claude** (from the Claude master-sources compilation). Items you add are tagged **Added by you**.

## Roadmap ideas

- Live rich previews (og:image, paper abstracts) via a small serverless fetch function.
- Optional LLM mode for the assistant (paste an API key) for free-form Q&A over the corpus.
- A commit-back button so **+ Add** writes straight to the repo.
