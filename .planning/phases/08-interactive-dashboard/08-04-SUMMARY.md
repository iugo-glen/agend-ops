---
phase: 08-interactive-dashboard
plan: 04
subsystem: infra
tags: [coolify, docker, deployment, oauth, reverse-proxy, bind-mount, production]

# Dependency graph
requires:
  - phase: 08-interactive-dashboard
    plan: 01
    provides: "Next.js app scaffold with Dockerfile, auth config, and data layer"
  - phase: 08-interactive-dashboard
    plan: 02
    provides: "Dashboard UI: Kanban board, card components, action buttons, mobile tabs"
  - phase: 08-interactive-dashboard
    plan: 03
    provides: "Action queue schema, /process-queue command, triage/status integration"
provides:
  - "Live production dashboard at ops.agend.info via Coolify"
  - "Google OAuth login protecting dashboard (glen@iugo.com.au only)"
  - "Bind-mount data pipeline: host /opt/agend-ops/data -> container /data"
  - "Action queue writes from dashboard to host filesystem"
  - "Dockerfile build-time ARGs for auth environment variables"
affects: []

# Tech tracking
tech-stack:
  added: [coolify]
  patterns: [coolify-docker-deployment, bind-mount-data-access, build-time-auth-args, reverse-proxy-trust-host]

key-files:
  created: []
  modified:
    - dashboard/Dockerfile

key-decisions:
  - "Coolify runs on remote server 103.249.238.17, not local Mac -- repo cloned to /opt/agend-ops on server"
  - "Bind mount /opt/agend-ops/data -> /data in container for live NDJSON data access"
  - "AUTH_TRUST_HOST=true required for Coolify reverse proxy (Caddy) to pass auth correctly"
  - "middleware.ts renamed from proxy.ts (Next.js 16 deprecation warning but still functional)"
  - "Data sync via git push from Mac + git pull on server (manual for now)"
  - "Domain: ops.agend.info (not ops.agendsystems.com as originally planned)"
  - "Build-time ARGs added to Dockerfile for NextAuth v5 middleware compilation"

patterns-established:
  - "Coolify deployment: Dockerfile with build-time ARGs for auth, bind mount for data, reverse proxy with AUTH_TRUST_HOST"
  - "Data sync workflow: local git push -> server git pull for NDJSON updates"

requirements-completed: [DASH-01]

# Metrics
duration: 2min
completed: 2026-03-25
---

# Phase 8 Plan 4: Coolify Deployment Summary

**Next.js dashboard deployed to Coolify at ops.agend.info with Google OAuth, bind-mounted NDJSON data, and working action queue**

## Performance

- **Duration:** 2 min (documentation; actual deployment done by user across sessions)
- **Started:** 2026-03-25T12:35:39Z
- **Completed:** 2026-03-25T12:36:28Z
- **Tasks:** 2 (both checkpoint tasks completed by user)
- **Files modified:** 1

## Accomplishments
- Dashboard live at ops.agend.info with HTTPS via Coolify's Caddy reverse proxy
- Google OAuth login functional -- only glen@iugo.com.au can access
- Bind mount from /opt/agend-ops/data to /data gives the container read/write access to all NDJSON files
- Action queue writes succeed from dashboard to host filesystem via bind mount
- Dockerfile updated with build-time ARGs so NextAuth v5 compiles correctly in Docker

## Task Commits

Both tasks were checkpoint tasks (human-action and human-verify) completed by the user:

1. **Task 1: Configure Coolify deployment and Google OAuth** - `06cc310` (fix) - Dockerfile build-time ARGs for auth
2. **Task 2: Verify full production dashboard end-to-end** - No code commit (visual verification only)

Also relevant: `a0eca61` (fix) - Renamed proxy.ts to middleware.ts for auth protection

## Files Created/Modified
- `dashboard/Dockerfile` - Added build-time ARGs for AUTH_SECRET, AUTH_TRUST_HOST, NEXTAUTH_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

## Decisions Made

1. **Remote server deployment** - Coolify runs on 103.249.238.17, not Glen's Mac. Repo cloned to /opt/agend-ops on server for data access via bind mount.
2. **Domain change** - Using ops.agend.info instead of ops.agendsystems.com as originally planned in the plan.
3. **AUTH_TRUST_HOST=true** - Required for reverse proxy setup so NextAuth correctly trusts the forwarded host header from Coolify's Caddy.
4. **middleware.ts over proxy.ts** - Next.js 16 emits deprecation warning for proxy.ts convention but middleware.ts works. Renamed for forward compatibility.
5. **Manual data sync** - Git push from Mac, git pull on server. Automated sync (webhook or cron) deferred to future improvement.
6. **Build-time ARGs** - NextAuth v5 requires auth config at build time for middleware compilation, not just runtime. Added ARG/ENV pairs to Dockerfile builder stage.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dockerfile missing build-time auth ARGs**
- **Found during:** Task 1 (Coolify deployment)
- **Issue:** NextAuth v5 middleware compilation fails without AUTH_SECRET and OAuth credentials available at build time
- **Fix:** Added ARG/ENV pairs for AUTH_SECRET, AUTH_TRUST_HOST, NEXTAUTH_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET to the builder stage
- **Files modified:** dashboard/Dockerfile
- **Verification:** Coolify build succeeds and auth works in production
- **Committed in:** 06cc310

**2. [Rule 3 - Blocking] proxy.ts renamed to middleware.ts**
- **Found during:** Task 1 (Coolify deployment)
- **Issue:** Next.js 16 deprecation warning for proxy.ts convention; middleware.ts is the supported name
- **Fix:** Renamed dashboard/src/proxy.ts to dashboard/src/middleware.ts
- **Files modified:** dashboard/src/middleware.ts (renamed from proxy.ts)
- **Verification:** Auth protection works correctly at ops.agend.info
- **Committed in:** a0eca61

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required for production deployment to work. No scope creep.

## Issues Encountered
- Next.js 16 still emits a deprecation warning about middleware.ts convention but it functions correctly
- Data sync between Mac and server is manual (git push + git pull) -- not automated yet

## Known Stubs
None -- all data sources are wired to live NDJSON files via bind mount.

## Next Phase Readiness
- Phase 8 complete -- all 4 DASH requirements verified in production
- Dashboard fully operational at ops.agend.info
- Future improvements: automated data sync (webhook/cron on server), CI/CD pipeline for dashboard changes
- Ready for Phase 9 (Telegram Mobile Commands) if/when pursued

## Self-Check: PASSED

- dashboard/Dockerfile: FOUND
- dashboard/src/middleware.ts: FOUND
- 08-04-SUMMARY.md: FOUND
- Commit 06cc310: FOUND
- Commit a0eca61: FOUND

---
*Phase: 08-interactive-dashboard*
*Completed: 2026-03-25*
