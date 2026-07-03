# Handoff: Challenge Detail — Leaderboard Redesign (Tom's Gym)

## Overview
Redesign of the challenge detail page (e.g. "Summer plank challenge"). The current page shows entrants as a flat chronological feed with the key metric (hold time) buried in a tiny chip. This redesign reframes the page as what it actually is — a **leaderboard** — with a podium for the top 3 and a ranked table for everyone else. Mobile is the primary surface.

## About the Design Files
`Challenge Redesign.dc.html` is a **design reference created in HTML** — a prototype showing intended look and behavior, not production code to copy directly. Recreate these designs in the target codebase using its existing framework, component library, and patterns (React/Vue/SwiftUI/etc.). If no environment exists yet, choose the most appropriate framework and implement there. Do not ship the HTML as-is.

The file contains four mockups arranged as anchored option cards. The **approved direction is the podium layout**:
- **`#1b`** — desktop podium + ranked table
- **`#2b`** — mobile podium (PRIMARY — build this first)

`#1a` / `#2a` are an alternate "ranked list" direction, kept for reference only.

## Fidelity
**High-fidelity.** Colors, typography, spacing, and layout are final. Recreate pixel-accurately using the codebase's existing libraries. Video thumbnails and avatars are placeholders (gradient blocks / initials) — wire them to real media.

---

## Screens / Views

### 1. Mobile — Challenge Detail w/ Podium (`#2b`, PRIMARY)
- **Purpose:** View a challenge, see the ranked leaderboard, watch entrants' clips, upload your own attempt.
- **Frame:** 390px wide (iPhone-class). Vertical scroll, sticky bottom CTA.
- **Layout (top → bottom):**
  1. **Status bar** (system).
  2. **App bar** — brand lockup left (logo tile + "Tom's Gym"), search icon + hamburger right. Bottom border `rgba(255,255,255,.07)`.
  3. **Hero block** — padding `16px 18px`, background radial glow `radial-gradient(120% 60% at 50% 0%, rgba(47,123,246,.18), transparent 55%)`. Contains: Back link, status pill ("Ongoing · 23d left"), H1 title.
  4. **Podium** — 3 columns, bottom-aligned, `gap:8px`. Order left→right = 2nd, 1st, 3rd. Each column: avatar (with blue play badge bottom-right), name, score, and a pedestal bar. Pedestal heights: 1st=96px, 2nd=70px, 3rd=56px. Champion (1st) has a gold trophy icon above the avatar.
  5. **"Everyone else" list** — bordered rounded container (`border-radius:12px`, `1px solid rgba(255,255,255,.07)`), rows separated by `1px solid rgba(255,255,255,.06)`. Each row: rank number, **video thumbnail (44×44, rounded 8px, play glyph)**, name + date, score right-aligned.
  6. **"You" row** — highlighted `rgba(47,123,246,.1)` background, blue "YOU" avatar, "Not logged yet" + "Upload →".
  7. **Sticky bottom CTA** — full-width blue "Upload your plank" button, fades in over a bottom gradient.
- **Placement of clips (important, recently added):** top-3 clips are reached by tapping the **play badge on each podium avatar**; ranks 4+ show a **thumbnail on the left of each list row**.

### 2. Desktop — Challenge Detail w/ Podium (`#1b`)
- **Frame:** 1160px content width.
- **Layout:** Top nav (brand + links + search). Hero band with radial blue glow: back link, status pill + date range, large H1 (42px), description, primary "Upload your plank" button (top-right). Podium (same 2-1-3 arrangement, larger). Below: "Everyone else" as a 4-column table — `Rank | Athlete | Hold | Clip` — header row uppercase muted labels; each body row has rank, avatar+name, score, and a 30×30 clip button. Final highlighted "You" row prompts upload.

---

## Design Tokens

**Colors**
- Background (app): `#0a0a0b`
- Surface / card fill: `#141416`
- Subtle fill: `rgba(255,255,255,.03)`
- Border: `rgba(255,255,255,.07)` (dividers `.06`)
- Text primary: `#fafafa`
- Text muted: `rgba(255,255,255,.6)` / `.45` / `.42` / `.4`
- Primary / brand blue: `#2f7bf6`; light blue text `#7fb0ff`
- Primary button shadow: `0 8px 22px -6px rgba(47,123,246,.7)`
- Success (Ongoing pill): text `#4ade80` on `rgba(52,199,89,.14)`
- Tag purple (Men/Women): text `#b39dff` on `rgba(147,112,255,.14)`
- Rank / medal: gold `#f5c542`, silver `#cbd5e1`, bronze `#cd7f52`
- Highlight ("You") row: `rgba(47,123,246,.1)` fill, `rgba(47,123,246,.3)` border

**Typography**
- Display / numbers / titles: **Space Grotesk** (600–700), tight tracking (`-.02em` to `-.025em`). Used for H1, scores, rank numbers, stat values.
- Body / UI: **Inter** (400–600).
- Mobile H1 ≈ 27px; desktop H1 = 42px. Scores: podium champion 23px (mobile) / 32px (desktop); list rows 16–17px. Score unit ("s") is ~55–60% of the number size, muted.

**Radius**
- Cards/containers: 11–14px · thumbnails: 8px · avatars: 50% · pills: 999px · buttons: 13px · pedestal tops: `10px 10px 0 0`.

**Spacing**
- Mobile page padding: `16px 18px` (bottom `96px` to clear sticky CTA). Row padding `9–11px 14px`. Grid/flex `gap` 8–12px.

## Interactions & Behavior
- **Sort:** leaderboard sorted by hold time descending. Rank = position. Ties → earlier timestamp wins (confirm rule).
- **Podium avatar tap / list clip tap:** open the entrant's video clip (modal or full-screen player).
- **Upload CTA:** opens upload flow; sticky on mobile, top-right on desktop.
- **"You" row:** if the viewer hasn't logged an attempt, show the highlighted prompt row; once logged, replace with their ranked row.
- **Status pill:** derive "Ongoing / Ended" and the countdown ("23 days left") from challenge start/end dates.
- **Empty states:** <3 entrants → collapse/adapt podium (e.g. only fill filled places); 0 entrants → show upload prompt only.

## State / Data
- Challenge: id, title, description, startDate, endDate, status, tags, participantCount.
- Entries: [{ athlete (name, avatar), score (seconds), date, clipUrl, thumbnailUrl }], sorted desc.
- Viewer: hasEntry (bool), own entry if present.

## Assets
- **Avatars:** placeholders are colored circles with initials — replace with user photos.
- **Clip thumbnails:** placeholders are gradient blocks with a play glyph — replace with real video poster frames.
- **Icons:** inline SVG (search, menu, back chevron, upload arrow, play triangle, trophy). Swap for the codebase's icon set.
- **Fonts:** Space Grotesk + Inter (Google Fonts) — or map to the codebase's equivalent display/body pairing.

## Files
- `Challenge Redesign.dc.html` — all four mockups. Build `#2b` (mobile) first, then `#1b` (desktop). Ignore `#1a`/`#2a`.
