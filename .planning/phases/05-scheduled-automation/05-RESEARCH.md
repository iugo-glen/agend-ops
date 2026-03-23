# Phase 5: Scheduled Automation - Research

**Researched:** 2026-03-23
**Domain:** Claude Code scheduled automation (GitHub Actions, Desktop tasks, cron tools) + daily briefing generation from NDJSON data
**Confidence:** HIGH (official docs verified, bugs confirmed via GitHub issues, architecture from existing v1 codebase)

## Summary

Phase 5 automates existing manual operations: email triage runs on a schedule, dashboard rebuilds after each run, and a daily morning briefing is generated. The user wants to try Claude Desktop scheduled tasks first, with GitHub Actions as fallback. Research reveals this order should be **reversed**: Desktop scheduled tasks have a confirmed open bug (#36327) preventing MCP access, and GitHub Actions cron schedules have a separate authentication bug (#814) that requires a workaround (custom GitHub App token instead of the default Claude GitHub App OIDC flow).

The most reliable path is GitHub Actions with a custom GitHub App or PAT for authentication, bypassing the OIDC bug. The hardened-google-workspace-mcp server needs to be installed on the runner with OAuth credentials (client ID, client secret, refresh token) injected from GitHub Secrets. ACST timezone mapping to UTC creates a non-obvious pitfall: early morning ACST times (7am, 9am) fall on the previous UTC day, complicating weekday-only cron expressions.

The daily briefing is a new command (`.claude/commands/daily-briefing.md`) that reads existing NDJSON data (feed, triage, tasks) and produces a markdown file in `data/briefings/YYYY-MM-DD.md`, a feed entry, and a dashboard summary section. No new APIs or MCP servers needed -- it is purely a data compilation task.

**Primary recommendation:** Use GitHub Actions with a custom GitHub App for authentication, skip Desktop scheduled tasks entirely (bug #36327 + #814 double risk), and implement the daily briefing as a separate command that the 7am scheduled triage run also triggers.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Triage runs every 2 hours during business hours on weekdays (approximately 7am, 9am, 11am, 1pm, 3pm, 5pm ACST)
- **D-02:** Timezone: ACST (UTC+9:30) -- Adelaide, South Australia
- **D-03:** Weekdays only (Monday-Friday). No weekend runs.
- **D-04:** Try Claude Desktop recurring tasks first. If MCP access fails (bug #36327), document GitHub Actions as the fallback approach.
- **D-05:** Morning briefing contains four sections: email summary (counts by bucket, key starred items), pending tasks (auto-queued + approvals), key deadlines (next 48 hours from action detection), yesterday recap (tasks completed, drafts created, triage stats)
- **D-06:** Briefing available in three places: separate daily file (data/briefings/YYYY-MM-DD.md), summary on dashboard, and feed entry
- **D-07:** Briefing generated as the first run of the day (7am triage also generates briefing)
- **D-08:** Dashboard staleness indicator (already exists from Phase 4) -- if "Last updated" shows >4 hours on a weekday, something's wrong
- **D-09:** Failed scheduled runs log an error-level feed entry visible in /feed and dashboard activity
- **D-10:** No external alerting infrastructure -- monitoring via dashboard + feed is sufficient for single-user system

### Claude's Discretion
- Claude Desktop /schedule configuration syntax and options
- Briefing markdown formatting and section structure
- How to detect "first run of the day" for briefing generation vs regular triage
- Dashboard summary card design for briefing content
- Error feed entry format for failed runs
- GitHub Actions fallback workflow file design (if needed)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHED-01 | Claude Desktop recurring task runs /triage-inbox on a configurable schedule (test MCP access, document fallback to GitHub Actions) | Desktop tasks have confirmed MCP bug #36327 (open, no fix). GitHub Actions is the reliable fallback. Detailed workflow YAML patterns documented. OIDC auth bug #814 requires custom GitHub App workaround. |
| SCHED-02 | Dashboard data auto-rebuilds after each scheduled triage run | Existing `scripts/build-dashboard-data.sh` already called by `/triage-inbox`. On GitHub Actions runner, the script runs after triage and results are committed+pushed, triggering Pages redeploy. |
| SCHED-03 | Daily briefing generated each morning -- email status, pending tasks, today's to-dos, key deadlines | Briefing is a data compilation command reading from feed.jsonl, triage/*.jsonl, and tasks/active.jsonl. New command, new data directory, new feed entry type. Architecture pattern documented. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **MCP server restriction:** Use ONLY `hardened-workspace` MCP server for Gmail and Drive access. DO NOT use `claude.ai Gmail` or `claude.ai Google Calendar` connectors.
- **Security model:** Claude can READ emails and CREATE drafts, but CANNOT send emails, share files, create filters, or delete anything.
- **Data conventions:** All timestamps in ISO 8601 with timezone offset. NDJSON append-only. Feed entries require: ts, type, summary, level, trigger.
- **Feed entry types:** Currently `["triage", "task", "draft", "system", "command"]`. Phase 5 will add `"briefing"` and `"error"`.
- **Dashboard data rebuild:** Run `scripts/build-dashboard-data.sh` after data changes.
- **GSD workflow:** Use GSD commands for all work.

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| claude-code-action | @v1 | Run Claude Code on GitHub Actions runners | Official Anthropic action. Supports MCP config passthrough, prompt parameter, scheduled workflows. |
| GitHub Actions | N/A | Durable cron-based scheduling | Only reliable unattended automation option. Desktop tasks have MCP bug, CLI /loop dies on exit. |
| actions/checkout | @v4 | Repo checkout on runner | Standard. Required before claude-code-action can read repo. |
| actions/create-github-app-token | @v2 | Generate GitHub App token for auth | Workaround for OIDC bug #814 in cron-triggered workflows. |
| jq | >=1.7 | JSON processing in briefing script | Already in use. Compiles NDJSON to briefing sections. |

### Supporting

| Library/Tool | Version | Purpose | When to Use |
|-------------|---------|---------|-------------|
| hardened-google-workspace-mcp | latest | Gmail read access on runner | Required for scheduled triage. Installed via `uv` on runner. |
| github/github-mcp-server | remote HTTP | GitHub operations on runner | If Claude needs to create issues/PRs during scheduled runs. Optional for Phase 5. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GitHub Actions | Claude Desktop /schedule | Desktop has MCP bug #36327 (open, unresolved). Would only work for non-MCP tasks. |
| GitHub Actions | Claude Code CLI /loop | Session-scoped, dies on exit, 3-day expiry. Not viable for unattended operation. |
| GitHub Actions | OS-level cron + `claude -p` | Requires Glen's Mac to be on. Less robust than cloud runner. |
| Custom GitHub App | Default Claude GitHub App | Default app has OIDC bug #814 on cron triggers. Custom app + PAT is the workaround. |

## Architecture Patterns

### Recommended Project Structure (new files for Phase 5)

```
.github/
  workflows/
    daily-triage.yml          # Scheduled triage + briefing workflow
  mcp-config.json             # MCP server config for GitHub Actions runner
data/
  briefings/
    YYYY-MM-DD.md             # Daily briefing files
.claude/
  commands/
    daily-briefing.md         # New: daily briefing generation command
schemas/
  feed-entry.json             # Modified: add "briefing" and "error" types
scripts/
  build-dashboard-data.sh     # Modified: add briefing.json compilation
docs/
  index.html                  # Modified: add briefing summary section
  briefing.json               # New: compiled briefing data for dashboard
```

### Pattern 1: GitHub Actions Scheduled Workflow with MCP

**What:** A cron-triggered workflow that runs Claude Code with full MCP access on a GitHub Actions runner.

**When to use:** Any operation that must run unattended and needs MCP server access.

**Key implementation detail:** Use a custom GitHub App (not the default Claude app) to generate tokens, avoiding the OIDC bug #814.

**Example:**
```yaml
# Source: Claude Code GitHub Actions docs + claude-code-action configuration docs
name: Scheduled Triage
on:
  schedule:
    # ACST (UTC+9:30) weekday schedule mapped to UTC
    # 7am ACST = 21:30 UTC previous day (Sun-Thu for Mon-Fri ACST)
    - cron: '30 21 * * 0-4'   # 7am ACST
    - cron: '30 23 * * 0-4'   # 9am ACST
    - cron: '30 1 * * 1-5'    # 11am ACST
    - cron: '30 3 * * 1-5'    # 1pm ACST
    - cron: '30 5 * * 1-5'    # 3pm ACST
    - cron: '30 7 * * 1-5'    # 5pm ACST
  workflow_dispatch: {}        # Manual trigger for testing

permissions:
  contents: write
  id-token: write

jobs:
  triage:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Generate GitHub App token
        id: app-token
        uses: actions/create-github-app-token@v2
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - name: Create MCP config
        run: |
          cat > /tmp/mcp-config.json << 'MCPEOF'
          {
            "mcpServers": {
              "hardened-workspace": {
                "command": "uv",
                "args": ["--directory", "./hardened-google-workspace-mcp", "run", "main.py"],
                "env": {
                  "GOOGLE_OAUTH_CLIENT_ID": "${{ secrets.GOOGLE_CLIENT_ID }}",
                  "GOOGLE_OAUTH_CLIENT_SECRET": "${{ secrets.GOOGLE_CLIENT_SECRET }}",
                  "GOOGLE_REFRESH_TOKEN": "${{ secrets.GOOGLE_REFRESH_TOKEN }}"
                }
              }
            }
          }
          MCPEOF

      - name: Install hardened-workspace MCP
        run: |
          git clone https://github.com/c0webster/hardened-google-workspace-mcp.git
          cd hardened-google-workspace-mcp
          uv sync

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          github_token: ${{ steps.app-token.outputs.token }}
          prompt: |
            Run /triage-inbox to scan and categorize emails.
            If this is the first triage run of the day (check data/briefings/ for today's file),
            also run /daily-briefing to generate the morning briefing.
            After all operations, commit and push any changed data files.
          claude_args: |
            --mcp-config /tmp/mcp-config.json
            --model claude-sonnet-4-6
            --max-turns 25
```

### Pattern 2: Daily Briefing as Data Compilation Command

**What:** A command that reads existing NDJSON data and produces a formatted daily briefing. No API calls needed.

**When to use:** First run of each day (7am), invoked by the scheduled workflow or manually.

**"First run of the day" detection:**
```bash
# Check if today's briefing already exists
TODAY=$(date +%Y-%m-%d)
if [ -f "data/briefings/${TODAY}.md" ]; then
  echo "Briefing already generated for today"
else
  echo "First run of the day -- generate briefing"
fi
```

### Pattern 3: Error Logging to Feed

**What:** When a scheduled run fails, log an error-level feed entry so it appears in the dashboard and /feed.

**Example feed entry:**
```json
{
  "ts": "2026-03-24T07:00:00+10:30",
  "type": "system",
  "summary": "Scheduled triage failed: MCP server connection timeout",
  "level": "critical",
  "trigger": "scheduled",
  "details": {
    "error": "hardened-workspace MCP server failed to connect",
    "workflow_run_id": "12345678"
  }
}
```

### Anti-Patterns to Avoid

- **Using Desktop scheduled tasks for MCP-dependent work:** Bug #36327 is open, no timeline for fix. Don't build on a broken foundation.
- **Using the default Claude GitHub App for cron triggers:** OIDC bug #814 causes "User does not have write access" errors. Use a custom GitHub App with `actions/create-github-app-token@v2`.
- **Hardcoding UTC times without ACST mapping:** 7am ACST is 9:30pm UTC the previous day. Getting the day-of-week wrong means triage runs on weekends.
- **Running briefing as a separate scheduled workflow:** Wasteful. The 7am triage run should also generate the briefing in the same workflow execution, reducing API costs and runner minutes.
- **Storing raw email content in briefing files:** Briefings should contain summaries and counts, not full email bodies. Privacy and token cost concerns.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron scheduling | Custom scheduler daemon | GitHub Actions `schedule` trigger | Built-in, free tier sufficient (~300 min/month), survives restarts |
| MCP config for runners | Manual env var setup | `--mcp-config` flag with JSON file | claude-code-action merges MCP configs automatically |
| GitHub auth on cron | Raw GITHUB_TOKEN | `actions/create-github-app-token@v2` | OIDC bug #814 breaks default auth on cron triggers |
| Timezone math | Manual UTC offset calculation | Pre-computed cron expressions (documented below) | ACST is UTC+9:30 -- the 30-minute offset makes mental math error-prone |
| Dashboard staleness check | Custom monitoring system | Existing "Last updated" display in dashboard | D-08: if >4 hours stale on a weekday, something's wrong |

**Key insight:** The scheduled triage is wrapping an existing command (`/triage-inbox`) in automation infrastructure. The triage logic itself is unchanged. The complexity is in auth, MCP config, timezone mapping, and error handling -- all infrastructure concerns.

## Common Pitfalls

### Pitfall 1: ACST-to-UTC Day Boundary for Weekday Cron

**What goes wrong:** You set up cron for weekdays (Mon-Fri) in UTC day-of-week notation, but 7am and 9am ACST fall on the **previous** UTC day. Monday 7am ACST = Sunday 9:30pm UTC. So `30 21 * * 1-5` (Mon-Fri UTC) actually fires Mon-Fri UTC = Tue-Sat ACST. Wrong!

**Why it happens:** ACST is UTC+9:30. The 9.5 hour offset means early ACST hours cross the UTC day boundary backward.

**How to avoid:** Use this pre-computed mapping:

| ACST Time | UTC Time | Cron Expression | UTC Day-of-Week (for Mon-Fri ACST) |
|-----------|----------|-----------------|--------------------------------------|
| 7:00 | 21:30 prev day | `30 21 * * 0-4` | Sun-Thu (= Mon-Fri ACST) |
| 9:00 | 23:30 prev day | `30 23 * * 0-4` | Sun-Thu (= Mon-Fri ACST) |
| 11:00 | 01:30 | `30 1 * * 1-5` | Mon-Fri (= Mon-Fri ACST) |
| 13:00 | 03:30 | `30 3 * * 1-5` | Mon-Fri (= Mon-Fri ACST) |
| 15:00 | 05:30 | `30 5 * * 1-5` | Mon-Fri (= Mon-Fri ACST) |
| 17:00 | 07:30 | `30 7 * * 1-5` | Mon-Fri (= Mon-Fri ACST) |

**Warning signs:** Triage runs appearing on Saturday morning (ACST) or missing on Monday morning (ACST).

### Pitfall 2: OIDC Authentication Bug on Cron Triggers (Issue #814)

**What goes wrong:** The scheduled workflow fires but fails immediately with "User does not have write access on this repository" during OIDC token exchange. The same workflow works perfectly via `workflow_dispatch`.

**Why it happens:** Bug in how the Claude GitHub App handles OIDC token exchange for scheduled (non-interactive) triggers. Issue #814, labeled P1 (Showstopper), still open.

**How to avoid:** Use a **custom GitHub App** instead of the default Claude GitHub App:
1. Create a custom GitHub App with Contents: Read & Write, Issues: Read & Write, Pull requests: Read & Write permissions
2. Install it on the repo
3. Store App ID and Private Key as GitHub Secrets
4. Use `actions/create-github-app-token@v2` to generate tokens in the workflow
5. Pass the token via `github_token: ${{ steps.app-token.outputs.token }}`

**Alternative:** Use a PAT (Personal Access Token) with `repo` scope. Simpler but less secure (broader permissions, no expiry unless configured).

**Warning signs:** Workflow logs show "401 Unauthorized" on "Exchanging OIDC token for app token."

### Pitfall 3: Hardened MCP Server OAuth on Headless Runner

**What goes wrong:** The hardened-workspace MCP server needs OAuth credentials. On Glen's machine, these were set up interactively (browser flow). On a headless GitHub Actions runner, there is no browser.

**Why it happens:** The standard OAuth flow requires a user to authenticate in a browser window. GitHub Actions runners are headless.

**How to avoid:**
1. On Glen's machine, export the existing refresh token from `~/.google_workspace_mcp/credentials/` (or `GOOGLE_MCP_CREDENTIALS_DIR`)
2. Store three values as GitHub Secrets: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
3. Pass them as environment variables in the MCP config JSON (via the `env` field in mcpServers config)
4. The MCP server reads credentials from env vars instead of the file-based credential store

**Warning signs:** MCP server starts but immediately fails with OAuth errors. Or refresh token expires (if still in Google Cloud "Testing" mode -- 7-day expiry).

**Pre-requisite check:** Verify Google Cloud OAuth consent screen is in "Production" mode (not "Testing"). Testing mode tokens expire after 7 days.

### Pitfall 4: Git Merge Conflicts from Concurrent Writes

**What goes wrong:** A scheduled triage run on the GitHub Actions runner commits and pushes while Glen is also interacting locally. Git push fails with conflict.

**Why it happens:** Two writers (local Glen + remote runner) modifying the same files (feed.jsonl, tasks/active.jsonl).

**How to avoid:**
1. The runner should `git pull --rebase` before committing
2. NDJSON append-only format helps -- appends rarely conflict
3. The workflow should handle push failures gracefully: retry once after pull, or log an error feed entry
4. During business hours when triage runs every 2 hours, Glen should pull before starting manual work

**Warning signs:** Workflow fails at `git push` step with "rejected" error.

### Pitfall 5: GitHub Actions Schedule Drift and Delays

**What goes wrong:** Scheduled workflows don't fire at the exact cron time. They can be delayed by 5-30 minutes during peak periods.

**Why it happens:** GitHub Actions schedule triggers are best-effort. During periods of high load, scheduled workflows may be delayed. GitHub documentation explicitly states this.

**How to avoid:** Accept approximate timing. The 2-hour cadence is forgiving -- a 15-minute delay is fine. Don't rely on exact fire times for logic (e.g., don't use "it's exactly 7am" to determine it's the first run).

**Warning signs:** Dashboard "Last updated" shows times that don't match the expected schedule.

### Pitfall 6: Desktop Scheduled Tasks MCP Bug (#36327)

**What goes wrong:** You configure Claude Desktop to run `/triage-inbox` on a schedule. The task fires on time, but Claude cannot access the hardened-workspace MCP server. The triage scan fails silently or with a generic "tools not available" error.

**Why it happens:** Open bug #36327 (and duplicates #35899, #35002, #33773). Desktop scheduled tasks don't inherit or load MCP connectors. No Anthropic staff response, no timeline for fix. Latest activity: March 19, 2026.

**How to avoid:** Don't use Desktop scheduled tasks for any MCP-dependent operation. Use GitHub Actions instead.

**For SCHED-01 compliance (test Desktop first):** Build a quick test -- schedule a simple non-MCP task in Desktop (e.g., "tell me the current time"). If that works, try with MCP. Document the failure, then switch to GitHub Actions. This satisfies D-04's "try first, document fallback" requirement without wasting implementation effort.

## Code Examples

### Daily Briefing Command Structure

```markdown
# .claude/commands/daily-briefing.md
---
description: Generate daily morning briefing from existing data
allowed-tools: Read, Bash(jq *), Bash(date *), Bash(wc *), Bash(ls *), Bash(tail *), Write, Edit, Bash(git *)
---

Compile the daily morning briefing from existing Agend Ops data.

## Execution

1. **Check if briefing already exists for today:**
   ```bash
   TODAY=$(date +%Y-%m-%d)
   if [ -f "data/briefings/${TODAY}.md" ]; then
     echo "BRIEFING_EXISTS"
   fi
   ```
   If it exists, display it and exit. Do not regenerate.

2. **Ensure briefings directory exists:**
   ```bash
   mkdir -p data/briefings
   ```

3. **Compile briefing sections:**

   a. **Email Summary** -- Read the most recent triage file:
      ```bash
      LATEST_TRIAGE=$(ls -t data/triage/*.jsonl 2>/dev/null | head -1)
      ```
      Extract: total emails scanned, counts by priority bucket, starred items.

   b. **Pending Tasks** -- Read active tasks:
      ```bash
      jq -r 'select(.status=="pending")' data/tasks/active.jsonl
      ```
      List pending tasks grouped by trigger (triage-suggested vs manual).

   c. **Key Deadlines** -- Scan recent triage records for action items with deadlines:
      Extract action_items where action_type includes "deadline" or "contract" or "meeting"
      from triage files within the last 48 hours.

   d. **Yesterday Recap** -- Read yesterday's feed entries:
      ```bash
      YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
      jq -r "select(.ts | startswith(\"${YESTERDAY}\"))" data/feed.jsonl
      ```
      Summarize: tasks completed, drafts created, triage runs, any errors.

4. **Write briefing file:**
   Write to `data/briefings/${TODAY}.md` in this format:

   ```markdown
   # Daily Briefing: {date}

   ## Email Summary
   - {N} emails scanned in latest triage
   - Urgent: {N} | Needs Response: {N} | Informational: {N} | Low: {N}
   - Starred: {list starred sender + subject}

   ## Pending Tasks
   - {N} pending ({N} from triage, {N} manual)
   - [task-id] description (type)
   ...

   ## Key Deadlines (Next 48 Hours)
   - {deadline description} -- from {sender}
   ...

   ## Yesterday Recap
   - {N} triage runs, {N} emails scanned
   - {N} tasks completed
   - {N} drafts created
   ```

5. **Log to feed:**
   Append a briefing entry to data/feed.jsonl.

6. **Rebuild dashboard data and commit.**
```

### Feed Entry Schema Extension

```json
{
  "type": {
    "type": "string",
    "enum": ["triage", "task", "draft", "system", "command", "briefing"],
    "description": "Category of activity"
  },
  "trigger": {
    "type": "string",
    "enum": ["manual", "scheduled", "hook"],
    "description": "What initiated this action"
  }
}
```

Note: The `"briefing"` type is added for daily briefing entries. The `"system"` type with `"level": "critical"` is used for error logging of failed scheduled runs (no need for a separate "error" type -- use the existing system type with critical level).

### Briefing Feed Entry Example

```json
{
  "ts": "2026-03-24T07:00:00+10:30",
  "type": "briefing",
  "summary": "Daily briefing: 38 emails (4 urgent), 6 pending tasks, 2 deadlines in next 48h",
  "level": "info",
  "trigger": "scheduled",
  "details": {
    "briefing_file": "data/briefings/2026-03-24.md",
    "emails_scanned": 38,
    "urgent": 4,
    "pending_tasks": 6,
    "deadlines_48h": 2
  }
}
```

### GitHub Secrets Required

| Secret Name | Value | Where From |
|------------|-------|------------|
| `ANTHROPIC_API_KEY` | Anthropic API key | console.anthropic.com |
| `APP_ID` | Custom GitHub App ID | GitHub App settings page |
| `APP_PRIVATE_KEY` | Custom GitHub App private key (.pem contents) | Generated during App creation |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | Google Cloud Console |
| `GOOGLE_REFRESH_TOKEN` | Google OAuth Refresh Token | Exported from Glen's local credentials |

### ACST-to-UTC Cron Reference (Complete)

For copy-paste into the workflow file:

```yaml
on:
  schedule:
    # All times are ACST (UTC+9:30) mapped to UTC for weekdays (Mon-Fri ACST)
    - cron: '30 21 * * 0-4'   # 7:00 ACST (Mon-Fri) = 21:30 UTC (Sun-Thu)
    - cron: '30 23 * * 0-4'   # 9:00 ACST (Mon-Fri) = 23:30 UTC (Sun-Thu)
    - cron: '30 1 * * 1-5'    # 11:00 ACST (Mon-Fri) = 01:30 UTC (Mon-Fri)
    - cron: '30 3 * * 1-5'    # 13:00 ACST (Mon-Fri) = 03:30 UTC (Mon-Fri)
    - cron: '30 5 * * 1-5'    # 15:00 ACST (Mon-Fri) = 05:30 UTC (Mon-Fri)
    - cron: '30 7 * * 1-5'    # 17:00 ACST (Mon-Fri) = 07:30 UTC (Mon-Fri)
  workflow_dispatch: {}         # Manual trigger for testing
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude Desktop /schedule for durable tasks | GitHub Actions with claude-code-action@v1 | Bug #36327 confirmed March 2026 | Desktop tasks cannot use MCP -- use Actions |
| Default Claude GitHub App for cron | Custom GitHub App + create-github-app-token@v2 | Bug #814 reported Jan 2026 | OIDC fails on cron triggers -- use custom app |
| claude-code-action@beta | claude-code-action@v1 (GA) | v1.0 released 2026 | Breaking changes: mode auto-detected, prompt replaces direct_prompt |
| CLI /loop for recurring tasks | GitHub Actions schedule trigger | Documented limitation (3-day expiry) | /loop is session-scoped, not for production |

**Deprecated/outdated:**
- `claude-code-action@beta`: Replaced by `@v1` with breaking changes (mode removed, prompt replaces direct_prompt, claude_args replaces individual params)
- `@modelcontextprotocol/server-github` (npm): Deprecated April 2025. Use `github/github-mcp-server` remote HTTP.

## Open Questions

1. **Hardened MCP server credential injection on runners**
   - What we know: The server accepts `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` as env vars. Refresh token path is less documented.
   - What's unclear: Does the hardened fork specifically support reading the refresh token from an env var (`GOOGLE_REFRESH_TOKEN`), or does it require a credential file at `GOOGLE_MCP_CREDENTIALS_DIR`?
   - Recommendation: During implementation, test env var injection first. If it fails, write the credentials to a temp file on the runner and set `GOOGLE_MCP_CREDENTIALS_DIR=/tmp/gcp-creds/`. The workaround is straightforward.

2. **Custom GitHub App setup complexity**
   - What we know: Creating a custom app requires: App creation, private key generation, installing on the repo, adding secrets.
   - What's unclear: Whether a simpler PAT-based approach would suffice for this single-user, single-repo setup.
   - Recommendation: Try PAT first (simpler setup: just one secret). If it causes issues with attribution or permissions, upgrade to custom GitHub App.

3. **GitHub Actions free tier sufficiency**
   - What we know: Free tier = 2,000 min/month for private repos. Estimated usage: 6 runs/day * 5 days * 10 min max = 300 min/month.
   - What's unclear: Whether the repo is private (free tier) or public (unlimited minutes but data visible).
   - Recommendation: If repo is private, 300 min/month is well within limits. If public, minutes aren't a concern but dashboard data exposure is (Phase 4 concern, not Phase 5).

4. **Desktop task test scope for D-04 compliance**
   - What we know: User decision D-04 says "try Desktop first." Bug #36327 strongly suggests it will fail for MCP tasks.
   - What's unclear: How much effort to invest in "trying" before switching to GitHub Actions.
   - Recommendation: Quick smoke test only. Schedule a simple task (no MCP) to verify Desktop scheduling works at all. Then try with MCP, document the failure, switch to Actions. Budget 15 minutes for this, not a plan wave.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| jq | Briefing data compilation, build script | Yes | 1.7.1 | -- |
| git | Data commits, push to remote | Yes | 2.53.0 | -- |
| gh | GitHub CLI (may need for app setup) | Yes | 2.86.0 | -- |
| uv | Hardened MCP server on runner | Yes (local) | 0.8.4 | pip install on runner |
| python3 | Hardened MCP server on runner | Yes (local) | 3.14.3 | Runner has Python pre-installed |
| GitHub Actions runner | Scheduled execution | N/A (cloud) | ubuntu-latest | -- |
| Claude Desktop | Desktop scheduled tasks (D-04 test) | Yes (Mac) | -- | GitHub Actions (primary approach) |

**Missing dependencies with no fallback:**
- None. All required tools are available locally. Runner tools (uv, python3) are installable in the workflow.

**Missing dependencies with fallback:**
- `.github/` directory does not exist yet -- must be created.
- No existing GitHub App configured -- must create one (or use PAT as simpler alternative).
- Google OAuth refresh token not yet exported for CI use -- must extract from local credential store.

## Sources

### Primary (HIGH confidence)
- [Claude Code Scheduled Tasks (official docs)](https://code.claude.com/docs/en/scheduled-tasks) -- /loop syntax, CronCreate/CronList/CronDelete tools, 3-day expiry, session-scoped limitations
- [Claude Code GitHub Actions (official docs)](https://code.claude.com/docs/en/github-actions) -- claude-code-action@v1 setup, MCP config passthrough via `--mcp-config`, scheduled workflow examples
- [claude-code-action configuration docs](https://github.com/anthropics/claude-code-action/blob/main/docs/configuration.md) -- MCP config inline JSON vs file, settings parameter, environment variable injection
- [MCP Scheduled Task Bug #36327](https://github.com/anthropics/claude-code/issues/36327) -- Desktop tasks cannot access MCP, OPEN, March 19 2026, duplicates #35899, #35002, #33773
- [claude-code-action Cron Bug #814](https://github.com/anthropics/claude-code-action/issues/814) -- OIDC auth fails on cron triggers, OPEN, P1 Showstopper, Jan 13 2026
- [Claude Desktop Cowork Scheduled Tasks (support docs)](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-cowork) -- /schedule syntax, persistence (survives restarts), requires app open
- [hardened-google-workspace-mcp (GitHub)](https://github.com/c0webster/hardened-google-workspace-mcp) -- OAuth credential configuration, environment variables

### Secondary (MEDIUM confidence)
- [SmartScope: Claude Code Scheduled Execution Guide](https://smartscope.blog/en/generative-ai/claude/claude-code-scheduled-automation-guide/) -- Practical patterns for scheduled workflows
- [DevelopersIO: /loop vs /schedule comparison](https://dev.classmethod.jp/en/articles/comparing-claude-code-loop-and-claude-cowork-schedule/) -- CLI vs Desktop task comparison

### Tertiary (LOW confidence)
- OIDC bug #814 workaround (custom GitHub App vs PAT) -- mentioned in linked PR but not officially documented by Anthropic. PAT approach needs validation during implementation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Official docs for GitHub Actions, claude-code-action@v1. Both bugs verified via GitHub issues.
- Architecture: HIGH -- Existing v1 codebase well-understood. New components follow established NDJSON patterns.
- Pitfalls: HIGH -- All pitfalls verified against official docs or open GitHub issues with reproduction steps.
- Timezone mapping: HIGH -- Mathematical calculation verified.
- Auth workaround (custom app/PAT): MEDIUM -- Workaround mentioned in community but not officially documented. Needs validation.

**Research date:** 2026-03-23
**Valid until:** 2026-04-07 (14 days -- fast-moving area with open bugs that may be resolved)

---
*Phase 5 Research for: Agend Ops -- Scheduled Automation*
*Researched: 2026-03-23*
