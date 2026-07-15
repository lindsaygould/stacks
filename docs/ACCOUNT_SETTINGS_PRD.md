# Stacks — account menu + Settings page (PRD)

*Written 2026-07-10. Move the account from a floating bottom-left chip to a proper top-right avatar with a dropdown, and give Drive + key + export a real Settings page.*

---

## Problem
The signed-in account lives in a small chip pinned bottom-left, and Drive connect/sync hangs off it. That's cramped, easy to miss, and there's no home for settings. Account controls belong top-right (where everyone looks), and Drive/key/export deserve a dedicated surface.

## What ships

**Top-right avatar.** When signed in, a circular avatar (your initial) sits at the far right of the header. Click it → a small **dropdown**: **Settings**, **Sync Drive**, **Sign out**. (The bottom-left chip is removed.)

**Settings page.** "Settings" opens a full-screen in-app **page** with a **← Back** button (returns to the library; the app is a single page, so this is an overlay, not a route). Sections:

- **Account** — signed in as `<email>`, Sign out.
- **Anthropic key** — set/change the key the Librarian uses (encrypted server-side when signed in). Shows whether one is set.
- **Google Drive** — connection status; **Connect** (or **Reconnect**) and **Sync now**; a one-line explainer that paywalled PDFs go in a Drive folder named **Stacks Papers** and are matched by content. This is where the earlier bottom-chip Drive action now lives.
- **Library** — export JSON / CSV, and a quick stat line (total · added · read · needs review).

## Behavior
- Avatar + dropdown + Settings appear only when signed in. Click-away closes the dropdown; Esc / Back closes Settings.
- Drive connect still routes through `/api/drive-start` → Google consent → `/api/drive-callback`; on return, Settings shows Connected and offers Sync.
- Nothing about storage/sync changes — this is presentation + a home for Drive/key/export.

## Non-goals
- No client-side router (Settings is an overlay). No new backend. The Librarian's own ⚙ key entry stays as a shortcut.
