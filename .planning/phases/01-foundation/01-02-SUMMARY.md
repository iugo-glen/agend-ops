---
phase: 01-foundation
plan: 02
subsystem: infra
tags: [google-oauth, mcp, gmail, google-drive, security, hardened-mcp]

# Dependency graph
requires:
  - phase: 01-foundation-01
    provides: "Directory structure and data schema"
provides:
  - "Google OAuth 2.0 in Internal mode (no 7-day token expiry)"
  - "Hardened Google Workspace MCP server (c0webster fork) installed at ~/hardened-google-workspace-mcp"
  - "MCP server registered at user scope in Claude Code (hardened-workspace)"
  - "Verified Gmail read access via MCP tools"
  - "Verified Google Drive access via MCP tools"
  - "Security-confirmed: no send, share, or filter-creation tools in MCP server"
affects: [01-03, 02-email-triage, 03-task-execution]

# Tech tracking
tech-stack:
  added: [hardened-google-workspace-mcp, google-oauth-2.0, uv]
  patterns: [user-scope-mcp, internal-oauth-consent, read-only-mcp]

key-files:
  created:
    - ~/hardened-google-workspace-mcp (external - cloned hardened MCP server)
    - ~/.claude.json (modified - MCP server registration at user scope)
    - ~/.zshrc (modified - GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET env vars)
  modified: []

key-decisions:
  - "Registered MCP server at user scope (not project scope) to avoid secrets in repo"
  - "Used Internal OAuth consent type to eliminate 7-day token expiry for Workspace accounts"
  - "Verified hardened fork has no send/share/filter/delete tools before registration"

patterns-established:
  - "User-scope MCP: MCP servers with credentials registered at user scope, never project scope"
  - "Internal OAuth: Google Workspace accounts use Internal consent type for persistent tokens"
  - "Security-first MCP: verify tool surface of MCP server before trusting it"

requirements-completed: [FOUND-01, FOUND-02]

# Metrics
duration: 15min
completed: 2026-03-23
---

# Phase 01 Plan 02: Google OAuth and Hardened MCP Server Summary

**Google OAuth 2.0 (Internal mode) with hardened-google-workspace-mcp providing read-only Gmail and Drive access via Claude Code MCP**

## Performance

- **Duration:** ~15 min (across checkpoint interactions)
- **Started:** 2026-03-22T23:10:00Z
- **Completed:** 2026-03-22T23:40:50Z
- **Tasks:** 3
- **Files modified:** 0 in-repo (all changes external: Google Cloud Console, ~/hardened-google-workspace-mcp, ~/.claude.json, ~/.zshrc)

## Accomplishments
- Google OAuth 2.0 configured in Internal mode on Agend Systems Workspace (eliminates 7-day token expiry)
- Gmail API and Google Drive API enabled in Google Cloud project "Agend Ops MCP"
- Hardened MCP server (c0webster fork) cloned, dependencies installed via uv, security verified
- MCP server registered at user scope with Claude Code -- no secrets stored in repo
- Gmail read access verified end-to-end via MCP tools (inbox listing works)
- Google Drive access verified end-to-end via MCP tools (file listing works)
- Security confirmed: no send_gmail_message, share_drive_file, or create_gmail_filter tools present

## Task Commits

This plan involved no in-repo file changes. All work was external:

1. **Task 1: Google OAuth setup in Google Cloud Console** - No commit (user action in Google Cloud Console + ~/.zshrc env vars)
2. **Task 2: Install hardened MCP server and register with Claude Code** - No commit (~/hardened-google-workspace-mcp clone + ~/.claude.json registration)
3. **Task 3: Verify Gmail and Drive access via MCP** - No commit (verification only, no file changes)

**Plan metadata:** See final commit below.

## Files Created/Modified

No files created or modified inside the repository. All changes were external:

- **Google Cloud Console** - OAuth consent screen (Internal), Gmail API enabled, Drive API enabled, OAuth 2.0 Client ID created
- **~/.zshrc** - GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables added
- **~/hardened-google-workspace-mcp/** - Cloned hardened MCP server, dependencies installed via `uv sync`
- **~/.claude.json** - MCP server `hardened-workspace` registered at user scope

## Decisions Made
- Registered MCP server at user scope (not project scope) to keep OAuth secrets out of the repository
- Used Internal OAuth consent type on Workspace account to get persistent tokens without 7-day expiry
- Verified the hardened fork's tool surface before registration (confirmed no send/share/filter/delete capabilities)
- Used Desktop app type for OAuth client ID (correct for CLI-based MCP server)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

This plan WAS the user setup. Glen completed OAuth configuration in Google Cloud Console (Task 1) and approved the browser-based OAuth consent flow during verification (Task 3).

## Known Stubs

None - this plan established external connectivity, not in-repo code.

## Next Phase Readiness
- Gmail and Drive access are live and verified -- Phase 2 (Email Triage) can read inbox immediately
- MCP server is registered at user scope -- works across all projects without reconfiguration
- OAuth tokens persist indefinitely (Internal consent type) -- no silent 7-day expiry to debug later
- Plan 01-03 (CLAUDE.md and custom commands) can reference hardened-workspace MCP tools in slash commands

## Self-Check: PASSED

- SUMMARY.md file exists at .planning/phases/01-foundation/01-02-SUMMARY.md
- No in-repo task commits expected (all work was external: Google Cloud Console, ~/hardened-google-workspace-mcp, ~/.claude.json, ~/.zshrc)
- STATE.md advanced to plan 3 of 3
- ROADMAP.md updated: Phase 1 shows 2/3 plans complete
- REQUIREMENTS.md updated: FOUND-01 and FOUND-02 marked complete

---
*Phase: 01-foundation*
*Completed: 2026-03-23*
