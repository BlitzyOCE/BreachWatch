# BreachCase Frontend Development Plan

## Context

BreachCase is an AI-powered data breach intelligence platform. The backend (Python scraper + Supabase database) is operational and collecting breach data from 8 RSS sources. This document covers the phased plan for building the Next.js frontend.

**Design decisions made before implementation:**
- **UI Tone**: Modern / Editorial — card-based, generous whitespace, easy scanning (like a news site)
- **Auth**: Auth-ready structure — no functional auth yet, but structured so it's trivial to add
- **Data Fetching**: Server Components + SSR — data fetched server-side for SEO, no client waterfalls
- **Dark Mode**: Light + Dark toggle with system preference detection from day 1

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16+ (App Router, React Server Components) |
| Language | TypeScript |
| Styling | Tailwind CSS v4 |
| Component Library | shadcn/ui (New York style, slate base) |
| Database Client | @supabase/supabase-js |
| Dark Mode | next-themes |
| Icons | lucide-react |
| Deployment | Vercel |

---

## File Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout — ThemeProvider, TooltipProvider, Header, Footer
│   ├── page.tsx                # Homepage — hero, stats, breach grid
│   ├── loading.tsx             # Global loading skeleton
│   ├── not-found.tsx           # 404 page
│   ├── error.tsx               # Error boundary (client component)
│   ├── globals.css             # Tailwind + shadcn CSS variables
│   ├── breach/[id]/
│   │   ├── page.tsx            # Breach detail page (SSR, dynamic metadata)
│   │   └── loading.tsx         # Detail page skeleton
│   ├── search/
│   │   └── page.tsx            # Search + filter results (URL-driven state)
│   └── about/
│       └── page.tsx            # About page (static)
├── components/
│   ├── layout/
│   │   ├── header.tsx          # Site header — logo, nav, search, theme toggle
│   │   ├── footer.tsx          # Site footer — disclaimer, links
│   │   └── mobile-nav.tsx      # Mobile Sheet drawer with nav
│   ├── breach/
│   │   ├── breach-card.tsx     # Card for listing pages
│   │   ├── breach-detail.tsx   # Full detail layout — orchestrates all sections
│   │   ├── breach-timeline.tsx # Vertical timeline with typed icons
│   │   ├── breach-facts.tsx    # Sidebar key facts (company, dates, records, etc.)
│   │   ├── breach-tags.tsx     # Sidebar tags grouped by type
│   │   ├── related-breaches.tsx# Grid of related breach cards
│   │   └── source-list.tsx     # List of source article links
│   ├── search/
│   │   ├── search-bar.tsx      # Search input — navigates to /search?q=...
│   │   ├── filter-sidebar.tsx  # Collapsible filter sections with counts
│   │   ├── filter-bar.tsx      # Active filter chips with remove/clear
│   │   └── sort-select.tsx     # Sort dropdown (recent, updated, severity, records)
│   ├── ui/                     # Custom UI primitives
│   │   ├── severity-badge.tsx  # Color-coded severity indicator
│   │   ├── status-badge.tsx    # Status pill (investigating/confirmed/resolved)
│   │   ├── tag-badge.tsx       # Clickable tag navigating to /search
│   │   ├── stat-card.tsx       # Numeric stat display for homepage
│   │   ├── empty-state.tsx     # Empty/no results state with icon
│   │   └── theme-toggle.tsx    # Light/Dark/System dropdown switcher
│   └── theme-provider.tsx      # next-themes client wrapper
├── lib/
│   ├── supabase/
│   │   ├── server.ts           # Server-side Supabase client (for RSC)
│   │   └── client.ts           # Browser-side client (for future auth/realtime)
│   ├── queries/
│   │   ├── breaches.ts         # All breach queries — recent, search, detail, related, filtered
│   │   └── tags.ts             # Tag count queries for filter sidebar
│   ├── utils/
│   │   ├── constants.ts        # Severity/status/attack vector/update type labels & colors
│   │   └── formatting.ts       # formatDate, formatRelativeDate, formatNumber, truncate
│   └── utils.ts                # shadcn cn() utility (auto-generated)
├── types/
│   └── database.ts             # TypeScript types mirroring Supabase schema exactly
├── middleware.ts                # Auth-ready pass-through stub
├── .env.local.example          # Environment variable template
├── components.json             # shadcn/ui config
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## Phases

### Phase 1 — Foundation
**Goal**: Runnable app with Supabase connected, types defined, dark mode working.

- Initialize Next.js with TypeScript + Tailwind
- Install and configure shadcn/ui (New York style, slate base)
- Install next-themes, @supabase/supabase-js, lucide-react
- Define all TypeScript types (`types/database.ts`) — mirrors `current_db.sql` exactly
- Create server-side and browser-side Supabase clients
- Build data access layer (`lib/queries/`) using `breach_summary` view and RPC functions
- Create utility constants (enum labels, color maps) and formatting helpers
- Add auth-ready middleware stub

**shadcn/ui components**: `button`, `badge`, `card`, `input`, `separator`, `skeleton`, `sheet`, `dropdown-menu`, `scroll-area`

---

### Phase 2 — Layout & Navigation
**Goal**: Consistent site shell across all pages.

- Root `layout.tsx` wrapping everything in ThemeProvider + TooltipProvider
- `Header` — sticky, backdrop blur, logo, nav links, compact search, theme toggle
- `Footer` — AI disclosure disclaimer
- `MobileNav` — Sheet drawer for mobile
- Global `loading.tsx`, `not-found.tsx`, `error.tsx`

**shadcn/ui components**: `sheet`

---

### Phase 3 — Homepage
**Goal**: Homepage showing recent breaches, stats, and search entry point.

- Server Component fetches 12 recent breaches + total count + weekly count in parallel
- Hero section with full-width search bar
- 3-column stats bar (total breaches, this week, sources)
- Responsive breach card grid (3 cols desktop → 2 tablet → 1 mobile)
- `BreachCard` — company name, severity badge, relative date, records, update count
- `SeverityBadge`, `StatusBadge`, `TagBadge`, `StatCard`, `EmptyState`

---

### Phase 4 — Breach Detail Page
**Goal**: Full breach article page with all sections from the product spec.

- Dynamic SSR page with `generateMetadata` (company name as page title)
- Two-column layout: main content (2/3) + sidebar (1/3), collapses to single column on mobile
- **Main content sections**: Summary, Attack Method, Data Compromised, Incident Timeline, Lessons Learned, CVE References, Sources, Related Breaches
- **Sidebar**: Key Facts card + Tags card
- `BreachTimeline` — vertical timeline with icons per update_type (discovery, fine, class_action, remediation, resolution, investigation)
- `BreachFacts` — icon + label + value rows, gracefully handles null fields
- `BreachTags` — tags grouped by type with clickable badges
- `RelatedBreaches` — calls `get_related_breaches()` RPC function
- Loading skeleton matching detail page structure

**shadcn/ui components**: `tooltip`

---

### Phase 5 — Search & Filtering
**Goal**: Full-text search + tag-based filtering with URL-driven state.

- Server Component reads `searchParams` — `q`, `severity`, `industry`, `country`, `attack_vector`, `sort`, `page`
- Full-text search calls `search_breaches()` RPC; filter-only queries use `breach_summary` view
- `FilterSidebar` — collapsible sections (Industry, Country, Attack Vector) with breach counts from `tag_counts` view
- `FilterBar` — active filter chips with individual remove and "Clear all"
- `SortSelect` — Most Recent, Recently Updated, Severity, Records Affected
- Mobile: filters accessible via Sheet drawer with filter count badge
- URL-driven pagination (prev/next with page numbers)
- All state lives in the URL — shareable, back-button friendly

**shadcn/ui components**: `checkbox`, `collapsible`, `select`

---

### Phase 6 — About Page & Polish
**Goal**: About page, error handling, SEO.

- Static `About` page — platform description, 4-step "how it works" cards, 8 data source links, AI disclosure
- `error.tsx` — client-side error boundary with retry button
- Global `loading.tsx` and route-level skeletons
- Dynamic metadata on all pages
- `force-dynamic` on data-fetching pages to avoid build-time Supabase calls

---

## Database Integration Points

| Query | Source |
|-------|--------|
| Homepage breach list | `breach_summary` view → `getRecentBreaches()` |
| Homepage stats | Direct count query on `breaches` table |
| Breach detail | `breaches` + `breach_updates` + `breach_tags` + `sources` (parallel) |
| Related breaches | `get_related_breaches(uuid, n)` RPC function |
| Full-text search | `search_breaches(query)` RPC function |
| Filter sidebar counts | `tag_counts` view → `getTagCounts(tagType)` |
| Filtered results | `breach_summary` + tag subqueries |

---

## Auth-Ready Patterns

The codebase is structured to make auth easy to bolt on later:

- `middleware.ts` — pass-through stub with commented-out auth check pattern
- `lib/supabase/client.ts` — browser-side singleton client, ready for `supabase.auth` calls
- `components/theme-provider.tsx` — client wrapper pattern can be replicated for `AuthProvider`
- Protected route pattern: add `isProtectedRoute()` check inside `middleware.ts`

---

## Dependency Graph

```
Phase 1 (Foundation)
  └─► Phase 2 (Layout)
       ├─► Phase 3 (Homepage)
       │    ├─► Phase 4 (Detail Page)    ─┐
       │    └─► Phase 5 (Search)         ─┤ can be built in parallel
       │                                  ┘
       └─► Phase 6 (About & Polish) — waits for Phases 3-5
```

---

## shadcn/ui Components (Total: 13)

`button` · `badge` · `card` · `input` · `separator` · `skeleton` · `sheet` · `dropdown-menu` · `scroll-area` · `tooltip` · `checkbox` · `collapsible` · `select`
