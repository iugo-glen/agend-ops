---
phase: 08-interactive-dashboard
plan: 01
subsystem: infra
tags: [nextjs, auth, api, docker, ndjson, tailwind, coolify]

# Dependency graph
requires:
  - phase: 04-dashboard
    provides: "Design tokens (colors, typography, spacing) in UI-SPEC.md"
  - phase: 01-foundation
    provides: "NDJSON schemas (feed, triage, task, todo, invoice)"
provides:
  - "Next.js app with auth-protected API routes for all 5 data types"
  - "Action queue endpoint for dashboard-to-Claude mutations"
  - "TypeScript interfaces derived from JSON schemas"
  - "NDJSON file readers for direct disk access"
  - "Google OAuth locked to glen@iugo.com.au"
  - "Dockerfile for Coolify standalone deployment"
  - "CSS design tokens (light/dark mode) from UI-SPEC"
affects: [08-02, 08-03, 08-04]

# Tech tracking
tech-stack:
  added: [next.js 16.2.1, next-auth 5.0.0-beta.30, tailwind-css 4, swr 2.4.1, clsx, date-fns]
  patterns: [app-router, auth-js-v5-single-user, ndjson-file-readers, action-queue-pattern, proxy-convention]

key-files:
  created:
    - dashboard/src/auth.ts
    - dashboard/src/proxy.ts
    - dashboard/src/lib/types.ts
    - dashboard/src/lib/data.ts
    - dashboard/src/lib/queue.ts
    - dashboard/src/app/api/data/[type]/route.ts
    - dashboard/src/app/api/actions/route.ts
    - dashboard/src/app/layout.tsx
    - dashboard/src/app/globals.css
    - dashboard/src/app/login/page.tsx
    - dashboard/src/app/page.tsx
    - dashboard/Dockerfile
    - dashboard/.env.local.example
  modified: []

key-decisions:
  - "Used proxy.ts instead of deprecated middleware.ts for Next.js 16 compatibility"
  - "Params typed as Promise<{type: string}> per Next.js 16 API route convention"
  - "DATA_ROOT defaults to ../data relative to project root for local dev"
  - "readFileSync for NDJSON reads since files are tiny (sub-millisecond)"

patterns-established:
  - "Proxy convention: src/proxy.ts re-exports auth for route protection"
  - "Data API pattern: GET /api/data/[type] with auth check, dispatching to typed readers"
  - "Action queue pattern: POST /api/actions appends to data/queue/actions.jsonl"
  - "CSS custom properties in globals.css with @theme inline for Tailwind v4 integration"
  - "Auth.js v5 with signIn callback for single-user email lock"

requirements-completed: [DASH-01, DASH-02]

# Metrics
duration: 8min
completed: 2026-03-24
---

# Phase 08 Plan 01: Next.js App Scaffold Summary

**Next.js 16 app with Auth.js v5 Google OAuth (single-user lock), NDJSON data API routes for 5 data types, action queue endpoint, and Coolify-ready Dockerfile**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-23T23:05:19Z
- **Completed:** 2026-03-23T23:13:06Z
- **Tasks:** 2
- **Files modified:** 30

## Accomplishments
- Next.js 16 project with TypeScript, Tailwind CSS v4, App Router fully scaffolded
- Auth.js v5 with Google provider restricting login to glen@iugo.com.au only
- API routes for all 5 NDJSON data types (feed, triage, tasks, todos, invoices)
- Action queue POST endpoint for mark-paid, complete-todo, complete-task, trigger-triage
- Design tokens from UI-SPEC.md ported to CSS custom properties with light/dark mode
- Multi-stage Dockerfile for Coolify standalone deployment

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js project with auth, types, and data layer** - `66cdf9e` (feat)
2. **Task 2: API routes for data reads and action queue, plus Dockerfile** - `620d61e` (feat)

## Files Created/Modified
- `dashboard/src/auth.ts` - Auth.js v5 config with Google provider and single-user lock
- `dashboard/src/proxy.ts` - Route protection proxy (replaces deprecated middleware.ts)
- `dashboard/src/lib/types.ts` - TypeScript interfaces for all 5 NDJSON schemas + QueuedAction
- `dashboard/src/lib/data.ts` - NDJSON file readers (readNDJSON, getFeedEntries, getLatestTriage, getTodos, getInvoices, getTasks)
- `dashboard/src/lib/queue.ts` - Action queue writer (queueAction, getQueuedActions)
- `dashboard/src/app/api/data/[type]/route.ts` - Data API route for all 5 types with auth check
- `dashboard/src/app/api/actions/route.ts` - Action queue POST/GET endpoints with validation
- `dashboard/src/app/layout.tsx` - Root layout with SessionProvider and system font stack
- `dashboard/src/app/globals.css` - Design tokens (light/dark), Tailwind v4 @theme inline
- `dashboard/src/app/login/page.tsx` - Login page with Google sign-in button
- `dashboard/src/app/page.tsx` - Placeholder main page with session info and sign out
- `dashboard/src/app/api/auth/[...nextauth]/route.ts` - Auth.js route handler
- `dashboard/Dockerfile` - Multi-stage build (dependencies, builder, runner) with standalone output
- `dashboard/.dockerignore` - Excludes node_modules, .next, env files from Docker build
- `dashboard/.env.local.example` - Documents required env vars for local dev
- `dashboard/next.config.ts` - Standalone output for Docker deployment
- `dashboard/package.json` - Next.js 16 with next-auth, swr, clsx, date-fns

## Decisions Made
- Used `proxy.ts` with `export const proxy = auth` instead of deprecated `middleware.ts` for Next.js 16 compatibility -- eliminates deprecation warning
- Typed dynamic route params as `Promise<{ type: string }>` per Next.js 16 convention (params are now async)
- Used Tailwind v4 `@theme inline` directive for design token integration instead of JS config file
- DATA_ROOT defaults to `../data` relative to `process.cwd()` for local dev, overridable via `DATA_DIR` env var for production

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used proxy.ts instead of middleware.ts**
- **Found during:** Task 1 (scaffold project)
- **Issue:** Next.js 16 deprecates middleware.ts in favor of proxy.ts convention
- **Fix:** Created src/proxy.ts with `export const proxy = auth` instead of src/middleware.ts
- **Files modified:** dashboard/src/proxy.ts (created instead of middleware.ts)
- **Verification:** Build succeeds with no deprecation warnings
- **Committed in:** 66cdf9e (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed .env.local.example being gitignored**
- **Found during:** Task 1 (scaffold project)
- **Issue:** Default `.gitignore` pattern `.env*` excluded `.env.local.example`
- **Fix:** Added `!.env.local.example` exception to `.gitignore`
- **Files modified:** dashboard/.gitignore
- **Verification:** File tracked by git
- **Committed in:** 66cdf9e (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for correct Next.js 16 convention and proper git tracking. No scope creep.

## Known Stubs

- `dashboard/src/app/page.tsx:13` - "Dashboard loading..." placeholder text. Intentional per plan -- Plan 02 replaces this page with the KanbanBoard component.

## Issues Encountered
- Turbopack NFT file tracing warning during build (data.ts uses dynamic fs paths). This is informational only -- does not affect build output or standalone deployment. In production, DATA_DIR env var eliminates the dynamic path resolution.

## User Setup Required

**External services require manual configuration** before the dashboard can authenticate users:
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from Google Cloud Console
- Add `http://localhost:3000/api/auth/callback/google` to OAuth client redirect URIs
- Generate `AUTH_SECRET` with `openssl rand -base64 32`
- Copy `.env.local.example` to `.env.local` and populate values

## Next Phase Readiness
- All backend infrastructure ready for Plan 02 (UI components with SWR hooks)
- API routes tested via build -- all compile and route correctly
- Design tokens in CSS custom properties ready for Tailwind utility classes
- Auth middleware protecting all routes except /login and /api/auth

## Self-Check: PASSED

All 14 key files verified present. Both task commits (66cdf9e, 620d61e) verified in git log.

---
*Phase: 08-interactive-dashboard*
*Completed: 2026-03-24*
