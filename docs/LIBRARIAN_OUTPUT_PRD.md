# Stacks — Librarian answer format + sourcing (PRD)

*Written 2026-07-09. Make the answer's citations first-class: a `[3]` is a live link to that one source, not a decoration — it takes you to that exact source (title and all) and opens it on demand.*

---

## The problem
The Librarian writes an answer with inline citations like `[3]`, and lists the cited sources below. But the `[3]` in the prose is dead text — you can't tell *which* of the listed sources it is without counting, and the jump from "the model claims X [3]" to "open source 3 and see it" takes eye-work. Citations should behave like footnotes that actually go somewhere.

## The idea
Three tiers of interaction, from lightest to fullest, so a reader can move from claim → source → the thing itself without losing their place:

1. **Answer text** — every `[n]` in the prose is a **clickable citation**. Clicking it doesn't dump a wall of sources; it **brings you to that one source** in the list below and highlights it (a brief pulse) so you see *its title* — the specific post, not a flood.
2. **Source row** — the highlighted row shows the source's title + kind. It's a button: click it and it **opens** the full detail (the rich preview: cover/thumbnail, provider, abstract or context, links, reading status). "The preview you have going" *is* the payoff here.
3. **The source itself** — from the detail, **Open source ↗** goes to the actual paper/post/repo, and for a bundled object every associated link (the paper *and* the LinkedIn post it came from) is listed and clickable.

So: click a number → land on that one source's title → click to open its preview → click into the real link. Each step is deliberate; nothing floods.

## Behavior

**Clickable `[n]`.** After the answer streams in, each `[n]` in the text is rendered as a `<button class="cite">`. Clicking it scrolls the cited-source row into view inside the chat and pulses it (~1s highlight). The prose stays readable; the number is visually marked as interactive (accent color, subtle underline).

**Cited-source list.** Below the answer, only the sources actually cited appear, numbered to match the `[n]`s (each row carries `data-n`). Each row = number · title · kind. Clicking a row calls `openDetail(id)` → the existing rich modal (unchanged, already good).

**One source, not many.** A citation resolves to exactly one source. We never expand `[3]` into "all sources" — the whole point is to disambiguate to the single post.

**Fallback.** If the model cites nothing parseable, we show the top few retrieved sources (as today) so the answer is never sourceless.

## Notes / non-goals
- Applies to the LLM answer path (citations). The local list path already lists its results as clickable rows; those get the same open-on-click behavior.
- No inline hovercards in v1 (click-to-reveal is enough and calmer); a hover preview is a possible later add.
- Pairs with the result-set feature (see RESULT_VIEW_PRD): "Open these N as a view →" turns the *whole* cited set into a grid you can work; the citation clicks are for reading a *single* claim's source in place.
