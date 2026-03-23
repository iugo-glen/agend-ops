---
phase: 05-scheduled-automation
plan: 02
subsystem: automation, scheduling
tags: [github-actions, claude-desktop, cron, mcp, scheduled-tasks, acst-timezone]

# Dependency graph
requires:
  - phase: 05-scheduled-automation/05-01
    provides: /daily-briefing command, extended feed schema with briefing type
  - phase: 04-dashboard
    provides: build-dashboard-data.sh pipeline, docs/ JSON output
  - phase: 02-email-triage
    provides: /triage-inbox command, email-scanner subagent
provides:
  - GitHub Actions scheduled triage workflow (.github/workflows/daily-triage.yml) as documented fallback
  - Claude Desktop scheduled task as primary scheduling mechanism (zero API cost)
  - Key finding: MCP servers in Desktop config need full binary paths (e.g., /Users/glenr/.local/bin/uv, not just uv)
affects: [05-03-PLAN (dashboard briefing section relies on triage running on schedule)]

# Tech tracking
tech-stack:
  added: [claude-code-action@v1, actions/checkout@v4]
  patterns:
    - "Desktop scheduled tasks ARE viable for MCP workflows when binary paths are fully qualified"
    - "GitHub Actions cron with ACST-to-UTC mapping: early ACST hours use previous UTC day-of-week"
    - "PAT_TOKEN workaround for OIDC bug #814 on cron-triggered workflows"

key-files:
  created:
    - ".github/workflows/daily-triage.yml"
  modified: []

key-decisions:
  - "Claude Desktop scheduling is PRIMARY approach (no API cost, MCP works with full binary paths) -- GitHub Actions is documented fallback"
  - "Desktop bug #36327 was NOT the issue -- the real problem was uv needing full path in MCP server config"
  - "GitHub Actions workflow kept as fallback for when laptop is off or Desktop unavailable"

patterns-established:
  - "MCP full-path pattern: Desktop scheduled tasks require full binary paths in server config (e.g., /Users/glenr/.local/bin/uv)"
  - "Dual scheduling strategy: Desktop primary (free, local), GitHub Actions fallback (API cost, remote)"

requirements-completed: [SCHED-01]

# Metrics
duration: 5min
completed: 2026-03-23
---

# Phase 5 Plan 2: Scheduled Triage Automation Summary

**GitHub Actions workflow created as fallback, Claude Desktop scheduled tasks confirmed working as primary approach after discovering MCP servers need full binary paths (not bug #36327)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-23T10:15:19Z
- **Completed:** 2026-03-23T10:20:19Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- GitHub Actions scheduled triage workflow created with 6 cron expressions covering ACST business hours (7am-5pm, every 2 hours, weekdays)
- Claude Desktop scheduled task smoke test PASSED -- MCP access works when uv uses full path (/Users/glenr/.local/bin/uv)
- User created a working "Email Triage" scheduled task in Claude Desktop that runs the full triage pipeline
- Identified root cause: Desktop scheduled tasks DO support MCP (bug #36327 was not the blocker), the issue was uv needing fully qualified path in Desktop MCP config
- Dual scheduling strategy established: Desktop primary (zero API cost), GitHub Actions fallback (for when laptop is off)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create GitHub Actions scheduled triage workflow** - `476a80a` (feat)
2. **Task 2: Desktop task smoke test and verification** - completed by user, no separate code commit (verification checkpoint)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `.github/workflows/daily-triage.yml` - Scheduled triage workflow with 6 ACST-to-UTC cron expressions, PAT auth, MCP config injection, conditional daily briefing, error logging

## Decisions Made
- **Desktop scheduling is PRIMARY:** Claude Desktop scheduled tasks work with MCP servers when the config uses full binary paths. This is zero-cost (no Anthropic API charges for Desktop usage) versus GitHub Actions which requires ANTHROPIC_API_KEY and consumes API credits.
- **Bug #36327 was not the issue:** The widely reported bug about MCP tools being unavailable in Desktop scheduled tasks did not affect this project. The actual problem was that the Desktop config specified `uv` (bare command name) which could not be resolved in the scheduled task's PATH. Using `/Users/glenr/.local/bin/uv` resolved it.
- **GitHub Actions kept as fallback:** The workflow remains committed and documented for scenarios where Glen's laptop is off, Desktop is unavailable, or a remote/headless execution is needed. Secrets setup documented but not yet configured (deferred until needed).
- **PAT_TOKEN for GitHub Actions auth:** Workaround for OIDC bug #814 in claude-code-action. If the fallback is ever activated, a fine-grained PAT with Contents: Read & Write permission is required.

## Deviations from Plan

### Deviation 1: Desktop scheduling works (plan assumed it would fail)

- **Plan assumption:** Desktop scheduled tasks would fail due to bug #36327, confirming GitHub Actions as the only approach
- **Actual outcome:** Desktop scheduled tasks work perfectly when MCP server config uses full binary paths
- **Impact:** Desktop becomes the PRIMARY scheduling mechanism (better than planned -- zero API cost)
- **Adjustment:** Summary reflects dual strategy with Desktop primary, GitHub Actions fallback (reverse of plan's expected outcome)

This is a positive deviation -- the outcome is better than the plan anticipated. No scope creep.

## Issues Encountered
- The MCP server config in Claude Desktop needed `/Users/glenr/.local/bin/uv` instead of just `uv`. The scheduled task environment does not inherit the same PATH as an interactive terminal, so bare command names fail silently. This was resolved by the user updating the Desktop MCP config with the full path.

## User Setup Required

**For Desktop scheduling (primary -- already configured):**
- Claude Desktop "Email Triage" scheduled task is active and working
- MCP config uses full binary path for uv

**For GitHub Actions fallback (deferred -- configure when needed):**

| Secret Name | Where to get it |
|------------|-----------------|
| `ANTHROPIC_API_KEY` | console.anthropic.com -> API Keys |
| `PAT_TOKEN` | GitHub -> Settings -> Developer settings -> Fine-grained tokens -> Create with `Contents: Read & Write` on this repo |
| `GOOGLE_CLIENT_ID` | Google Cloud Console -> APIs & Credentials |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console -> APIs & Credentials |
| `GOOGLE_REFRESH_TOKEN` | Run: `cat ~/.google_workspace_mcp/credentials/*.json` or check `GOOGLE_MCP_CREDENTIALS_DIR` |

## Next Phase Readiness
- Scheduled triage is operational via Desktop scheduled task
- GitHub Actions workflow ready as fallback (needs secrets configuration when activated)
- Plan 03 (dashboard briefing summary banner) can proceed -- briefing data will be generated by scheduled runs
- First automated triage already executed successfully (commit 3cb532c)

## Self-Check: PASSED

- .github/workflows/daily-triage.yml verified on disk
- Commit 476a80a verified in git log
- 05-02-SUMMARY.md created successfully

---
*Phase: 05-scheduled-automation*
*Completed: 2026-03-23*
