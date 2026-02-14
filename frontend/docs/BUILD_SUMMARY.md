# BreachWatch Frontend — Build Summary

## Status: Phase 1–6 Complete ✓

Build verified: `next build` passes with 0 TypeScript errors.

```
Route (app)
├ ƒ /              (dynamic — SSR, fetches from Supabase)
├ ○ /_not-found    (static)
├ ○ /about         (static)
├ ƒ /breach/[id]   (dynamic — SSR, dynamic metadata)
└ ƒ /search        (dynamic — SSR, URL-driven filters)
```

---

## Getting Started

```bash
cd frontend
cp .env.local.example .env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
npm install
npm run dev
```

---

## File Structure & Purpose

### `app/` — Pages (Next.js App Router)

| File | Type | Purpose |
|------|------|---------|
| `layout.tsx` | Server | Root layout — wraps all pages in ThemeProvider, TooltipProvider, Header, and Footer |
| `page.tsx` | Server | Homepage — hero section, search bar, 3 stat cards, 12-card breach grid |
| `loading.tsx` | Server | Global loading skeleton shown while any page segment is fetching |
| `not-found.tsx` | Server | Styled 404 page with icon and home link |
| `error.tsx` | Client | Error boundary with retry button, wraps all route segments |
| `globals.css` | CSS | Tailwind v4 import + shadcn/ui CSS variable definitions for light/dark themes |
| `breach/[id]/page.tsx` | Server | Breach detail page — fetches full breach data in parallel, generates dynamic `<title>` |
| `breach/[id]/loading.tsx` | Server | Skeleton matching the two-column detail layout |
| `search/page.tsx` | Server | Search & filter results — reads all filter state from `searchParams`, paginates |
| `about/page.tsx` | Server | Static about page — platform mission, 4-step explainer, 8 data sources, AI disclaimer |

---

### `components/layout/` — Site Shell

| File | Purpose |
|------|---------|
| `header.tsx` | Sticky header with backdrop blur. Left: logo + nav links. Right: compact search bar, theme toggle, mobile hamburger. |
| `footer.tsx` | Minimal footer with AI disclosure disclaimer and About link. |
| `mobile-nav.tsx` | Sheet (slide-in drawer) for mobile. Contains nav links and search bar. Opens via hamburger icon in header. |

---

### `components/breach/` — Breach Display

| File | Purpose |
|------|---------|
| `breach-card.tsx` | Card used on homepage and search results. Shows company name, severity badge, relative date, industry/country, truncated summary, records affected, update count badge. Links to detail page. |
| `breach-detail.tsx` | Orchestrates the full detail page layout. Two-column on desktop (main content + sidebar), single column on mobile. Renders all sections in order. |
| `breach-timeline.tsx` | Vertical timeline for `breach_updates`. Each entry has a date, typed icon (Gavel for fines, Scale for class actions, Shield for remediation, etc.), and description text. |
| `breach-facts.tsx` | Sidebar card with icon + label + value rows: company, industry, location, discovery date, disclosure date, records affected, attack vector, threat actor, status. Null fields are hidden. |
| `breach-tags.tsx` | Sidebar card grouping all `breach_tags` by type (Industry, Attack Vector, CVE, MITRE, Threat Actor). Each tag is a clickable badge linking to `/search`. |
| `related-breaches.tsx` | Small grid (up to 3) of breach cards for similar incidents, powered by the `get_related_breaches()` Supabase RPC. Hidden if no results. |
| `source-list.tsx` | Ordered list of source articles for a breach. Each item shows title, publication date, and opens the original URL in a new tab. |

---

### `components/search/` — Search & Filtering

| File | Purpose |
|------|---------|
| `search-bar.tsx` | Client component. Text input with search icon. On submit, navigates to `/search?q=...`. Used in the header (compact, fixed width) and on the search page (full width). |
| `filter-sidebar.tsx` | Client component. Collapsible filter sections (Industry, Country, Attack Vector) with checkbox selection. Each option shows breach count. Clicking a checkbox updates URL `searchParams` and resets to page 1. |
| `filter-bar.tsx` | Client component. Displays active filters as removable badge chips above results. Includes "Clear all" button. Hides itself when no filters are active. |
| `sort-select.tsx` | Client component. Dropdown with 4 sort options — Most Recent, Recently Updated, Severity (High→Low), Records Affected. Updates URL `sort` param. |

---

### `components/ui/` — Custom UI Primitives

| File | Purpose |
|------|---------|
| `severity-badge.tsx` | Color-coded badge — `critical`=red, `high`=orange, `medium`=yellow, `low`=green. Uses shadcn `badge`. |
| `status-badge.tsx` | Status pill — `investigating`=blue, `confirmed`=amber, `resolved`=green. |
| `tag-badge.tsx` | Clickable `<Badge>` that links to `/search?{tagType}={tagValue}`. Can be set non-clickable for display-only use. |
| `stat-card.tsx` | Simple bordered card with a large number and a label. Used on the homepage for total breaches, weekly count, and source count. |
| `empty-state.tsx` | Centered icon + heading + subtitle for empty search results or missing data. |
| `theme-toggle.tsx` | Dropdown with Light / Dark / System options. Uses `useTheme()` from next-themes. |

### `components/theme-provider.tsx`
Client wrapper around `NextThemesProvider`. Required because `ThemeProvider` needs `"use client"` but `layout.tsx` is a Server Component.

---

### `lib/supabase/` — Database Clients

| File | Purpose |
|------|---------|
| `server.ts` | Creates a Supabase client using `createClient()`. Used exclusively in Server Components and Route Handlers. Throws at startup if env vars are missing. |
| `client.ts` | Singleton browser-side Supabase client. Currently a stub — will be used when auth (watchlists, saved searches) is added. |

---

### `lib/queries/` — Data Access Layer

| File | Function | What It Does |
|------|----------|-------------|
| `breaches.ts` | `getRecentBreaches(limit)` | Fetches latest breaches from `breach_summary` view, ordered by `last_update_date` |
| | `getBreachById(id)` | Fetches full breach + updates + tags + sources in 4 parallel queries |
| | `searchBreaches(query)` | Calls `search_breaches()` RPC (full-text, weighted by company > summary > method) |
| | `getRelatedBreaches(id, n)` | Calls `get_related_breaches()` RPC (finds breaches with shared tags) |
| | `getBreachCount()` | Returns total breach count for homepage stat |
| | `getRecentBreachCount(days)` | Returns count of breaches created in the last N days |
| | `getFilteredBreaches(filters)` | Full filter + sort + paginate — routes to search RPC or view query based on whether a text query is present |
| `tags.ts` | `getTagCounts(tagType)` | Fetches tag frequencies from `tag_counts` view for one tag type (e.g. "industry") |
| | `getAllTagCounts()` | Fetches all tag frequencies and groups them by type |

---

### `lib/utils/` — Utilities

| File | Exports | Purpose |
|------|---------|---------|
| `constants.ts` | `SEVERITY_COLORS`, `STATUS_COLORS`, `STATUS_LABELS`, `ATTACK_VECTOR_LABELS`, `UPDATE_TYPE_LABELS`, `TAG_TYPE_LABELS`, `RSS_SOURCES` | Maps enum values to display labels and Tailwind color classes |
| `formatting.ts` | `formatDate`, `formatRelativeDate`, `formatNumber`, `formatRecordsAffected`, `truncate` | Date formatting (e.g. "Jan 15, 2026"), relative dates ("3 days ago"), number shortening ("1.5M records"), text truncation with ellipsis |

---

### `types/database.ts` — TypeScript Types

Mirrors `database/current_db.sql` exactly. Key types:

| Type | Description |
|------|-------------|
| `Breach` | Core breach record matching the `breaches` table |
| `BreachSummary` | Extends `Breach` with `update_count`, `source_count`, `last_update_date` from the `breach_summary` view |
| `BreachDetail` | Extends `Breach` with `updates[]`, `tags[]`, `sources[]` for the detail page |
| `BreachUpdate` | One entry in the `breach_updates` timeline table |
| `BreachTag` | One tag from `breach_tags` |
| `Source` | One source article from `sources` |
| `TagCount` | One row from the `tag_counts` view |
| `Severity`, `Status`, `AttackVector`, `UpdateType`, `TagType` | String union types matching all CHECK constraints in the schema |

---

### `middleware.ts`

Auth-ready pass-through stub. Currently allows all requests through. Contains commented-out pattern showing exactly where to add session checking and redirect logic when auth is implemented.

---

## Key Architectural Decisions

**URL-driven filter state** — All search/filter/sort/page state lives in the URL's `searchParams`. This makes pages shareable, back-button friendly, and avoids complex client-side state management.

**Server Components for data fetching** — All Supabase queries run on the server. Pages receive pre-fetched data, making them fast on first load with full HTML in the source for SEO.

**`force-dynamic` on data pages** — The homepage, search, and detail pages use `export const dynamic = "force-dynamic"` to prevent Next.js from trying to pre-render them at build time (which would fail without Supabase credentials).

**Graceful null handling** — Every field that can be null in the database (discovery_date, records_affected, attack_vector, etc.) is handled in components — sections are hidden if empty, numbers show "Not disclosed", dates show "Unknown".

**Parallel data fetching** — Detail page fetches breach, updates, tags, sources, and related breaches in a single `Promise.all()`. Homepage fetches breach list, total count, and weekly count in parallel.

---

## Environment Variables

```bash
# Required — get from your Supabase project dashboard
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```
