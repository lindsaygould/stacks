# Stacks — landing page (PRD)

*Written 2026-07-16. A calm welcome screen shown when you click the "Stacks" wordmark (top-left). Not a route — an in-app overlay, same pattern as Settings.*

---

## Problem
Clicking the logo today just silently resets filters. There's no "front door" that says what Stacks is, shows how much is in it, or points a first-time visitor (or future you) at the three things you actually do here: browse, ask, add. The reference library has a clear identity; Stacks should too.

## What ships
A full-screen overlay (`#landing`, like `#settings`) that appears when the **Stacks** wordmark is clicked. It has:

- **Hero** — the stacked-plates mark + "Stacks" wordmark, one-line tagline ("The durable home for everything behind the research"), and a one-sentence description of what it is.
- **Live stat tiles** — pulled from the real library at open time: total sources · papers · repos & models · added by you · read · needs review. Numbers, not prose.
- **Three doors** (primary actions):
  1. **Enter the library** → closes the overlay to the full grid.
  2. **Ask the Librarian** → closes the overlay and opens the chat.
  3. **Add material** → closes the overlay and opens the Add flow.
- **A quiet footer line** — "built {date} · syncs across your devices when signed in".

## Behavior
- Opens on brand click; closes on **Enter the library**, the **×**, `Esc`, or clicking the scrim.
- Reachable anytime; never blocks (it's a welcome, not a gate — the auth gate is separate).
- Blue hero gradient consistent with the app; theme-aware (light/dark).
- No new backend, no route, no data change. Stats are read from `ALL` at open time.

## Non-goals
- Not a marketing site, not a login wall, not a tour. One screen, three doors.
- Does not replace "Clear all" (filters reset stays on the Clear all control).
