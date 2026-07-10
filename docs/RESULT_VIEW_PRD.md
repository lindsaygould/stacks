# Stacks — turn a Librarian result into a working view (PRD)

*Written 2026-07-09. Let any Librarian answer become a filtered main-grid view you can sort, filter further, export, and clear — not just a list trapped in the chat.*

---

## The problem
The Librarian answers in the chat panel: a text answer + a set of cited sources, or a plain list. That set is a dead end — you can read it, but you can't sort it, filter it further, switch it to rows, or export it the way you can the main grid. If you ask *"show me all posts that mention Sam Allman"* and it finds eight, you want those eight **in the main view**, to work with.

## The idea
Every Librarian result gets an **"Open these N as a view →"** button. Clicking it drops the exact result set into the main grid as a **result-set filter** — a removable chip that reflects the prompt. The grid now shows only those sources, and everything the main view can do still works on them: sort, card/row toggle, facet-filter *within* the set, export, open a card.

This is **not** a new page and not the whole library reshuffled — it's the normal grid, scoped to the result, clearly labeled and one click to clear.

## Behavior

**The button.** Appears under any answer that produced sources (both the free/local list answers and the LLM answers with citations). Label: `Open these N as a view →`. Clicking it:
1. Sets `state.resultSet = { label: <your prompt>, ids: <the source ids> }`.
2. Closes the Librarian panel and scrolls to the top of the grid.
3. Re-renders: the grid shows only the result-set items.

**The chip.** While a result set is active, a distinct pill sits with the other active-filter chips: `✦ "show me all posts that mention Sam Allman" · 8 ×`. The `×` clears the result set (back to the full library); other filters stay.

**Interacting with it.**
- **Sort** (relevance/date/title/…) applies within the set.
- **Facets** (kind, domain, reading-status, date…) filter *within* the set — the facet counts recompute against the result set, so you can drill down (e.g. only the papers among the eight).
- **Cards ⇄ Rows**, **saved views**, and **export** all operate on the visible (result-set-scoped) list.
- The result-set chip and the facet chips are independent: clearing facets keeps the result set; clearing the result set keeps facets.

**Data model.** `state.resultSet = null | { label:string, ids:Set<string> }`. `filtered()` gains one line at the top: `if (state.resultSet && !state.resultSet.ids.has(it.id)) return false;` — so it composes with text search, date, and every facet. It's intentionally **not** written to the URL (a result set is an ephemeral product of a query, not a shareable filter); a fresh load starts clean.

## Non-goals
- No separate route/page. It's the same grid.
- No persistence across reloads (the chip is transient).
- Doesn't replace the existing "apply as facet filter" path for pure list queries — that still works; the result-set button is the general path that also handles free-text results a facet can't express (like a person's name).
