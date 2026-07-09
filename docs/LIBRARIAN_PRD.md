# Stacks — the Librarian: list + answer (PRD)

*Written 2026-07-09. Turns the Librarian from a lister into something that can also **answer questions about the content** of your sources, with citations. Covers the UX decision (toggle vs. filter vs. auto-route) and the architecture.*

---

## 1. The two jobs, and the UX decision you asked about

The Librarian does two fundamentally different things:

| | **List / filter** | **Answer** |
|---|---|---|
| Example | "show me all the repos", "grants to apply for", "only the YouTube videos" | "what does the EMBARC paper find about rACC theta?", "which paper argues EEG microstates need 20+ electrodes and why?" |
| It's really a… | **filter** — a set of items | a **question** — a synthesized answer grounded in sources |
| Needs | nothing (instant, local, free) | an LLM reading the content + your API key |
| Output | a list of cards + "apply as filter" | prose answer + citations that jump to the source cards |

**You floated three options** — a toggle inside the Librarian, a filter on the main page, or an "AI insight filter." Here's the recommendation, and why:

**Do all three roles, but resolve them by *auto-routing a single box* — not a manual toggle.**

1. **One Librarian input, no mode switch.** You type anything; it decides. If the text is a list command ("show me…", "only the…", a type/topic with no question), it **lists** instantly (free, no key). If it's a question, it **answers** (LLM + citations). A tiny label on each reply says which it did ("Listed 53 repos" vs "Answered from 6 sources"), so it's never a mystery. A manual toggle makes you pre-classify your own question every time; auto-routing is the thing you liked — "you can kind of pick your own."
2. **The common lists are *also* one-tap chips on the main page.** Because a list is a filter, "Papers / Repos & models / Videos / Podcasts / Companies / Grants" live as quick chips right above the grid. Faster than typing when you just want to browse a shelf. This is the "filter on the main page" instinct — kept, because it's genuinely better for lists.
3. **The deep Q&A stays in the Librarian only** — it's a conversation, not a filter.

Net: lists are available two ways (type it, or tap a chip); answers are one way (ask the Librarian). No toggle to think about.

---

## 2. What "it knows every paper" actually means

For the Librarian to answer "what does this paper find?", it must have the paper's **content**, not a preview. Three tiers, cheapest first:

- **Tier 0 — metadata** (today): title, provider, tags, and the LinkedIn/annotation context. Enough to *find* things, not to explain findings.
- **Tier 1 — abstracts + rich context** (this build): we fetch **real arXiv abstracts** (free, no key) for every arXiv paper and fold in the context we already have. Now the Librarian can answer "what does paper X argue?" from the abstract, and retrieval searches inside abstracts, not just titles. Honest limit: abstract-depth, not full-text-depth.
- **Tier 2 — full text** (later): extract full PDF text (from the Drive copies / open-access PDFs), chunk + embed, retrieve passages, and cite exact sentences. Deeper answers, quote-level citations. Needs the offline PDF pipeline already scoped in `STACKS_BUILD_PLAN.md`.

This build ships **Tier 1** — a real jump ("it read the abstracts of all 240 papers") without waiting on the full-text pipeline.

---

## 3. Architecture — how the answer gets made

**Retrieval-augmented, client-side, bring-your-own-key** (matches how your testers use Kairos — everyone brings their own Anthropic key):

1. **Retrieve** — score every item against the question over `title + abstract + context + notes`, take the top ~8.
2. **Prompt** — hand those 8 to Claude as numbered sources with a strict system prompt: *answer only from these sources, cite as [n], and say so if they don't cover it.*
3. **Call** — the browser calls the Anthropic Messages API directly (`anthropic-dangerous-direct-browser-access: true`), using a key you paste once (stored only in your browser's localStorage, never in the repo). Model: `claude-opus-4-8`.
4. **Render** — show the answer; turn each `[n]` into a clickable chip that opens the cited source card (the cite-and-flash pattern).

**Why client-side + your key (for now):** it works today on the static/Vercel site with zero backend, no shared secret, and no dead-API-key blocker (the exact thing that stalled The Stacks). Each person who uses it brings their own key, so there's no shared bill.

**Why it moves to serverless later:** for a shared team instance you'd want the key server-side (one place, not pasted per device) and Tier-2 full-text retrieval. That's the Vercel-function upgrade — same project, incremental, no migration.

### Honesty guardrails (non-negotiable)
- The Librarian answers **only** from retrieved sources and **cites every claim**; if the sources don't cover it, it says so rather than guessing.
- It never implies it read a full PDF when it only has the abstract — answers are grounded in what's actually indexed.
- Refusals / bad-key / network errors surface as clear messages, not silent failures.

---

## 4. Scope

**This build:** auto-routing Librarian (list ↔ answer), arXiv-abstract enrichment, client-side RAG with citations + your key, main-page quick-list chips.

**Next:** Tier-2 full-text (chunk/embed the Drive PDFs), serverless key + shared history for the team, per-source "ask about just this paper" from the detail view.
