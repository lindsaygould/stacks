# Stacks — a calm way to begin (PRD)

*Written 2026-07-16. A simple, unoverwhelming entry point the user starts from — with the full, dense library exactly as it is today one click away. Progressive disclosure at the level of the whole app.*

---

## The problem — what a first-time user sees today

Open Stacks right now and, before doing anything, you're hit with roughly everything at once, top to bottom:

- a top bar (logo, search, **+ Add material**, Export, theme, avatar),
- a 2–3 line **mission paragraph**,
- a **Quick views** row (8 chips),
- a **left rail** packed with Filters/Clear all, a *When* histogram + presets + two date inputs, and **7 facet groups** (Type, Domain, Mental-health focus, From, Source, Topics, Reading status) — dozens of chips — plus rail stats,
- the **main grid**: "Showing 628 of 628", a Cards/Rows toggle, saved-views, sort, then a wall of **628 cards** grouped by month,
- and a floating Librarian orb.

That's 40+ interactive elements before a single decision. It's *great* for a returning power user mid-project — and genuinely overwhelming for a first encounter, or for anyone who just wants to find or ask **one** thing.

## Goal

Give the user a **calm place to begin** — one clear primary action and a few gentle doorways — while keeping **100% of today's functionality unchanged**, always one interaction away. Nothing is removed; the dense library is *revealed on demand* instead of *imposed on arrival*.

This is the app-level version of the "calm by default, depth on demand" principle already applied to individual cards.

## What ships — the "Start" screen

On open, the user lands on **Start** (an evolution of the existing landing overlay), which contains **only**:

1. **Identity** — the Stacks mark + one line of what it is. (No mission wall.)
2. **One primary input** — a single large field: **"Search the library, or ask the Librarian…"**
   - Typing + Enter on a short/keyword query → opens the full library with that **search applied**.
   - A question (ends in `?`, or natural-language) → opens the **Librarian** with the question asked.
   - This unifies the two things people actually come to do: *find* and *ask*.
3. **A few calm doorways** (4–6 large tiles, not a filter wall):
   - **Papers**, **Repos & models**, **Recently added**, **Needs review (N)** → each opens the full library **pre-scoped** to that view.
   - **Ask the Librarian** → opens the chat.
   - **Open the full library →** → the current interface, unfiltered.
4. **A quiet stat line** — total · papers · repos · added · needs review (the live numbers already on the landing).

Nothing else. No rail, no facet chips, no 628-card wall, no sort/tool row.

## Behavior

- **The full app is unchanged.** Any doorway or a search/ask **transitions into the exact current interface** (rail, facets, histogram, grid, saved views, sort) — pre-scoped if a tile was chosen. This is a presentation layer in front of the app, not a rebuild of it.
- **Don't nag power users.** Remember the choice: once someone clicks **Open the full library** (or flips a "skip the start screen" preference in Settings), later opens go **straight to the full library**. First-timers and casual visitors get calm; daily users aren't slowed by an extra click. Stored per-user (synced) with a local fallback.
- **The mark always returns to Start.** Clicking the **Stacks** wordmark opens Start from anywhere (it already opens the landing today — this becomes that home).
- **Esc / "Open the full library" / any doorway** leaves Start. It never blocks — it's a beginning, not a gate (the auth gate is separate).
- Theme-aware, mobile-first, same blue system.

## Why this over the alternatives

- *Just collapse the rail by default* — helps a little, but the grid wall + tool row are still a lot, and it doesn't give a clear "begin here."
- *A guided tour / onboarding modal* — interrupts and is dismissed once; it doesn't create a durable calm home to return to.
- **Start screen** — one obvious first action, gentle doorways, full power on demand, and a home the mark always returns to. Highest calm-to-effort ratio, and it reuses the landing that already exists.

## Non-goals

- No change to search, filtering, the Librarian, the card/detail views, Add, or Export — Start only changes **how you enter**.
- Not a marketing page and not a login wall.
- No new backend (the "skip the start screen" preference rides the existing per-user sync).

## Build note

~80% of this already exists as the landing overlay (mark, tagline, live stats, three doors). The delta: add the **unified search/ask input**, add the **pre-scoped doorways** (Papers / Repos / Recently added / Needs review), make Start the **default first screen** (not only a click target), and add **remember-and-skip**.
