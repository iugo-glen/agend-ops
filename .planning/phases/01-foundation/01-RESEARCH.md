# Phase 1: Foundation - Research

**Researched:** 2026-03-23
**Domain:** Google OAuth 2.0, hardened MCP server, NDJSON data schema, Claude Code custom commands, repo structure
**Confidence:** HIGH

## Summary

Phase 1 establishes the plumbing everything else depends on: Google OAuth with production tokens, a security-hardened MCP server for Gmail/Drive read access, an NDJSON data schema for activity logging, a directory structure for the repo, and custom Claude Code commands.

The critical finding is that Glen's Agend Systems Google Workspace account qualifies for the **Internal** user type on the OAuth consent screen, which means restricted scopes (gmail.readonly, gmail.modify, gmail.compose) do **not** require Google verification. This is the simplest and most reliable path -- no 7-day token expiry, no unverified-app warning, no 100-user cap. Glen already has Claude Code v2.1.81 installed, Python 3.14, and uv 0.8.4 -- all dependencies for the hardened MCP server are available.

A secondary finding: Glen already has Anthropic's official Gmail and Google Calendar MCP connectors registered (`claude.ai Gmail` at `gmail.mcp.claude.com/mcp`). These are Anthropic-hosted servers that **can send emails** and route data through Anthropic infrastructure. They must NOT be used for this project. The hardened fork (c0webster) is required because it (a) removes all send/share/filter capabilities, and (b) keeps data local without third-party intermediaries.

**Primary recommendation:** Use the Google Workspace "Internal" app type for zero-friction OAuth, install c0webster/hardened-google-workspace-mcp at user scope, and define NDJSON schemas with separate files per triage run as decided in CONTEXT.md.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use Agend Systems Google Workspace account (not personal Gmail)
- **D-02:** Glen is Workspace admin -- can set OAuth consent screen to production mode and manage API access directly
- **D-03:** No Google verification needed (under 100 users) -- set to production mode immediately to avoid 7-day token expiry
- **D-04:** Triage results stored as separate files (one JSONL per triage run, e.g., data/triage/2026-03-23.jsonl) -- feed entries link to them
- **D-05:** Activity feed detail level -- Claude's discretion (balance between lean scanning and useful dashboard display)
- **D-06:** Task record structure -- Claude's discretion (choose what works best for the task execution and dashboard requirements)
- **D-07:** Definite commands: /status (quick summary), /task <description> (kick off a task), /feed (show recent activity)
- **D-08:** Triage command design -- Claude's discretion (whether one command does everything or staged steps)
- **D-09:** Claude designs the full command set based on requirements -- user wants these three minimum
- **D-10:** GitHub Pages dashboard lives in docs/ (standard GitHub Pages from /docs on main branch)
- **D-11:** Top-level repo layout -- Claude's discretion (optimize for NDJSON append-only pattern, GitHub Pages, and clean separation of concerns)

### Claude's Discretion
- Activity feed entry detail level (lean vs rich)
- Task record structure (individual files vs JSONL)
- Top-level directory organization
- Triage command design (full vs staged)
- Additional commands beyond /status, /task, /feed
- NDJSON field definitions (informed by dashboard needs)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Google OAuth 2.0 configured in PRODUCTION mode for Gmail and Drive access | Internal user type for Workspace org bypasses verification entirely; restricted scopes (gmail.readonly, gmail.modify) exempt for internal apps; production mode eliminates 7-day token expiry |
| FOUND-02 | Hardened Google Workspace MCP server (c0webster fork) installed and configured with security-stripped capabilities | c0webster fork verified on GitHub; removes send_gmail_message, share_drive_file, create_gmail_filter, delete operations; Python 3.11+ required (Glen has 3.14); uv required (Glen has 0.8.4); registration via `claude mcp add` at user scope |
| FOUND-03 | NDJSON data schema defined for activity feed, email summaries, and task records | NDJSON spec verified; separate JSONL per triage run (D-04); feed.jsonl for activity log; schema definitions documented below with field specifications |
| FOUND-04 | CLAUDE.md project configuration with custom commands for common operations | Claude Code skills/commands system documented; .claude/commands/ or .claude/skills/ supported; frontmatter for tool access, model, and invocation control; /status, /task, /feed as minimum set (D-07) |
| FOUND-05 | Git repo directory structure established (data/, dashboard/, scripts/) | Architecture research provides recommended structure; data/ for NDJSON, docs/ for GitHub Pages (D-10), scripts/ for tooling, .claude/ for commands/config |
</phase_requirements>

## Standard Stack

### Core
| Technology | Version | Purpose | Why Standard |
|------------|---------|---------|--------------|
| Claude Code | 2.1.81 (installed) | AI runtime, command execution | Already installed. v2.1.80+ required for full features. Verified via `claude --version`. |
| hardened-google-workspace-mcp | latest (c0webster fork) | Gmail read, Drive access, draft creation -- NO send/share/filter | Security requirement. Removes all exfiltration vectors. Python-based MCP server using uv. |
| Python | 3.14.3 (installed) | Runtime for hardened MCP server | Server requires 3.11+. Glen has 3.14.3 at /opt/homebrew/bin/python3. |
| uv | 0.8.4 (installed) | Python package manager for MCP server | Used by `uv sync` to install MCP server dependencies. Glen has 0.8.4 at ~/.local/bin/uv. |
| jq | 1.7.1-apple (installed) | JSON/NDJSON processing in scripts | Transform NDJSON to dashboard JSON. Already available at /usr/bin/jq. |
| git | 2.53.0 (installed) | Version control, data store backbone | All structured data committed to git. Already available. |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| NDJSON (.jsonl) | N/A (spec) | Append-only data format for feed, triage, tasks | All structured logging and data storage. One JSON object per line. |
| GitHub Pages | N/A | Static dashboard hosting from docs/ directory | Serves dashboard. Configure in repo settings to serve from docs/ on main branch. |
| .claude/commands/ | N/A | Custom slash commands as markdown files | /status, /task, /feed minimum. Frontmatter controls tools, model, invocation. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hardened-google-workspace-mcp (local) | Anthropic official Gmail connector (gmail.mcp.claude.com) | Official connector CAN send emails and routes data through Anthropic servers. Violates both security hardening requirement and data-ownership constraint. Do NOT use. |
| NDJSON flat files | SQLite | SQLite not git-diffable, adds binary dependency. NDJSON is simpler for append-only logs. |
| .claude/commands/ (legacy) | .claude/skills/ (modern) | Skills support additional features (supporting files, auto-invocation). Either works; skills recommended for new projects. |

**Installation:**
```bash
# Clone hardened MCP server
git clone https://github.com/c0webster/hardened-google-workspace-mcp.git ~/hardened-google-workspace-mcp
cd ~/hardened-google-workspace-mcp && uv sync

# Register with Claude Code at user scope
claude mcp add hardened-workspace \
  --scope user \
  -e GOOGLE_OAUTH_CLIENT_ID="$GOOGLE_OAUTH_CLIENT_ID" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="$GOOGLE_OAUTH_CLIENT_SECRET" \
  -- uv run --directory ~/hardened-google-workspace-mcp python -m main --single-user
```

## Architecture Patterns

### Recommended Project Structure
```
todo-list/                              # Root (git repo = data store)
+-- .claude/
|   +-- commands/                       # Custom slash commands (Phase 1)
|   |   +-- status.md                   # /status -- quick summary
|   |   +-- task.md                     # /task -- kick off a task
|   |   +-- feed.md                     # /feed -- show recent activity
|   |   +-- triage-inbox.md             # /triage-inbox -- email triage (Phase 2)
|   +-- settings.json                   # Hooks, permissions, project config
|   +-- settings.local.json             # Local-only secrets (gitignored)
+-- data/
|   +-- feed.jsonl                      # NDJSON append-only activity log
|   +-- triage/                         # One JSONL per triage run (D-04)
|   |   +-- 2026-03-23T0900.jsonl       # Example triage run file
|   +-- tasks/
|   |   +-- active.jsonl                # Current task records
|   |   +-- completed/                  # Monthly archives
|   +-- config/
|       +-- contacts.json               # Known contacts + context
+-- docs/                               # GitHub Pages source (D-10)
|   +-- index.html                      # Dashboard shell (Phase 4)
|   +-- feed.json                       # Compiled from feed.jsonl
+-- scripts/
|   +-- build-dashboard-data.sh         # Compile NDJSON -> feed.json
|   +-- validate-data.sh               # Validate NDJSON before commit
+-- schemas/
|   +-- feed-entry.json                 # JSON Schema for feed entries
|   +-- triage-record.json              # JSON Schema for triage records
|   +-- task-record.json                # JSON Schema for task records
+-- CLAUDE.md                           # Project instructions (enhanced)
+-- .gitignore                          # Ignore secrets, tokens, etc.
+-- .mcp.json                           # Project-scoped MCP config (optional)
```

### Pattern 1: NDJSON Append-Only Data Flow
**What:** All state changes produce an NDJSON line appended to the relevant .jsonl file. No read-modify-write cycles.
**When to use:** Every data write operation.
**Example:**
```bash
# Append a feed entry
echo '{"ts":"2026-03-23T10:30:00+10:00","type":"triage","summary":"Scanned 12 emails","level":"info"}' >> data/feed.jsonl
```

### Pattern 2: Separate Files Per Triage Run (D-04)
**What:** Each triage run writes to a timestamped file (e.g., `data/triage/2026-03-23T0900.jsonl`), not a shared inbox file. Feed entries link to triage files by filename.
**When to use:** Every email triage operation.
**Why:** Isolates runs, prevents corruption across runs, makes it easy to replay or audit individual scans.

### Pattern 3: Custom Commands as Markdown Skills
**What:** Claude Code commands defined as markdown files with YAML frontmatter. Each file becomes a /command.
**When to use:** All custom operations.
**Example (.claude/commands/status.md):**
```yaml
---
name: status
description: Quick summary of current state -- unread emails, pending tasks, recent activity
allowed-tools: Read, Grep, Glob, Bash(jq *)
disable-model-invocation: true
---

Show a quick status summary:

1. Count lines in data/feed.jsonl for recent activity (last 24h)
2. Count files in data/triage/ for recent triage runs
3. Count entries in data/tasks/active.jsonl for pending tasks
4. Display a formatted summary
```

### Anti-Patterns to Avoid
- **Using Anthropic's official Gmail connector:** It can send emails and routes through Anthropic servers. Use hardened fork instead.
- **Storing OAuth tokens in git:** Use .claude/settings.local.json (gitignored) or environment variables.
- **Monolithic JSON files:** Use NDJSON (append-only, line-isolated) instead of JSON arrays.
- **Registering MCP at project scope with secrets:** Use user scope for the MCP server since OAuth secrets should not be in .mcp.json committed to git.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth 2.0 token management | Custom token refresh logic | hardened-google-workspace-mcp handles it | OAuth token refresh has edge cases (race conditions, revocation, scope changes). The MCP server manages the full lifecycle. |
| Gmail API interaction | Direct API calls via scripts | MCP server tool calls | MCP server handles auth, pagination, rate limiting, error handling. |
| JSON/NDJSON validation | Custom validation scripts | jq for parsing, JSON Schema for structure | jq is battle-tested for NDJSON. JSON Schema provides declarative validation. |
| Slash command framework | Custom CLI parsing | .claude/commands/ or .claude/skills/ | Claude Code has built-in command loading from markdown files. No code needed. |
| Dashboard data compilation | Custom Node.js scripts | `jq -s '.' data/feed.jsonl > docs/feed.json` | One-liner with jq. No build toolchain. |

**Key insight:** Phase 1 is plumbing. Every component here has a standard solution. The value is in correct configuration, not custom code.

## Common Pitfalls

### Pitfall 1: OAuth Testing Mode Token Expiry (CRITICAL)
**What goes wrong:** OAuth consent screen left in "Testing" mode. Refresh tokens expire after 7 days. System silently stops working.
**Why it happens:** Default consent screen status is "Testing". Easy to forget to switch.
**How to avoid:** Set consent screen to "Internal" user type (Google Workspace accounts) OR "In Production" immediately. Internal user type is better for this project because it bypasses all verification requirements for restricted scopes.
**Warning signs:** Gmail MCP tools return `invalid_grant` errors after ~7 days.

### Pitfall 2: Using Wrong Gmail OAuth Scopes
**What goes wrong:** Requesting overly broad scopes (gmail.modify, mail.google.com) when only gmail.readonly is needed for triage. Or requesting gmail.send which the hardened MCP explicitly does not use.
**Why it happens:** Scope selection is confusing. The hardened MCP's OAUTH_SETUP.md lists 21 scopes including gmail.modify and gmail.compose -- more than needed for read-only triage.
**How to avoid:** For Phase 1, verify the MCP server works with the scopes it requests. The hardened fork removes the tools that use dangerous scopes, but still requests the scopes at OAuth time. This is acceptable because the tool-level restriction prevents abuse even if the token has broad scope. Consider scope reduction in future hardening.
**Warning signs:** Google consent screen shows alarming permissions ("Read, compose, and send emails").

### Pitfall 3: Registering MCP at Wrong Scope
**What goes wrong:** MCP server registered at project scope with secrets in .mcp.json. Secrets get committed to git.
**Why it happens:** Project scope is the default if not specified. .mcp.json supports env var expansion but secrets still need to be in the environment.
**How to avoid:** Register at user scope (`--scope user`). OAuth client ID/secret passed via `-e` flags on the `claude mcp add` command, stored in ~/.claude.json (not in repo).
**Warning signs:** .mcp.json contains literal secret values. git diff shows credentials.

### Pitfall 4: Forgetting to Gitignore Sensitive Files
**What goes wrong:** .claude/settings.local.json, token files, or OAuth credentials committed to repo.
**Why it happens:** New repo, no .gitignore yet.
**How to avoid:** Create .gitignore as first task. Include: `.claude/settings.local.json`, `*.token`, `token.json`, `.env`, `.env.local`.
**Warning signs:** `git status` shows sensitive files as untracked.

### Pitfall 5: Anthropic Official Connectors Conflict
**What goes wrong:** Glen has `claude.ai Gmail` and `claude.ai Google Calendar` already registered. These are Anthropic's hosted connectors that CAN send emails. If Claude uses these instead of the hardened fork, the security model is broken.
**Why it happens:** Anthropic's connectors are pre-installed and may be used by default if not explicitly managed.
**How to avoid:** Either (a) remove the Anthropic Gmail connector (`claude mcp remove "claude.ai Gmail"`), or (b) ensure commands explicitly reference the hardened-workspace MCP server tools. Document which MCP server to use in CLAUDE.md.
**Warning signs:** Tool calls showing `mcp__claude.ai Gmail__*` instead of `mcp__hardened-workspace__*`.

## Code Examples

### NDJSON Schema: Activity Feed Entry
```json
{
  "ts": "2026-03-23T10:30:00+10:00",
  "type": "triage|task|draft|system|command",
  "summary": "Human-readable one-liner",
  "level": "critical|info|debug",
  "trigger": "manual|scheduled|hook",
  "details": {
    "emails_scanned": 12,
    "flagged": 3,
    "triage_file": "data/triage/2026-03-23T1030.jsonl"
  },
  "duration_ms": 4500
}
```

### NDJSON Schema: Triage Record (per email, in triage run file)
```json
{
  "message_id": "gmail-message-id",
  "thread_id": "gmail-thread-id",
  "from": "sender@example.com",
  "from_name": "Sarah Jones",
  "subject": "Contract renewal Q3",
  "received": "2026-03-23T09:00:00Z",
  "category": "client|team|sales|admin|noise",
  "priority": "urgent|needs-response|informational|low-priority",
  "starred": true,
  "has_attachments": true,
  "snippet": "First 200 chars of body text...",
  "action_items": ["Review contract terms", "Respond by Friday"],
  "suggested_action": "draft-reply|review-attachment|forward-to-team|archive"
}
```

### NDJSON Schema: Task Record
```json
{
  "id": "task-2026-03-23-001",
  "ts": "2026-03-23T10:45:00+10:00",
  "status": "pending|in-progress|completed|cancelled",
  "description": "Review contract Sarah sent",
  "trigger": "manual|triage-suggestion",
  "source_email": "gmail-message-id",
  "outcome": null,
  "completed_at": null
}
```

### Google OAuth Setup: Internal App (Workspace)
```
1. Google Cloud Console > APIs & Services > OAuth consent screen
2. User type: "Internal" (only available for Workspace accounts)
3. App name: "Agend Ops MCP"
4. Support email: glen@agendsystems.com (or actual domain)
5. Enable APIs: Gmail API, Google Drive API
6. Add scopes: (use the scopes the hardened MCP server requests)
7. Save -- no verification required for Internal apps
8. Create OAuth credentials > Desktop app > "Claude Code MCP"
9. Download client ID and secret
```

### MCP Server Registration
```bash
# Store secrets in environment (add to ~/.zshrc or similar)
export GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"

# Register hardened MCP server at user scope
claude mcp add hardened-workspace \
  --scope user \
  -e GOOGLE_OAUTH_CLIENT_ID="$GOOGLE_OAUTH_CLIENT_ID" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="$GOOGLE_OAUTH_CLIENT_SECRET" \
  -- uv run --directory ~/hardened-google-workspace-mcp python -m main --single-user

# Verify it connects
claude mcp list
# Should show: hardened-workspace: ... - Connected (or Needs authentication)
```

### Custom Command Example: /status
```yaml
---
name: status
description: Quick summary of current Agend Ops state
allowed-tools: Read, Bash(jq *), Bash(wc *), Bash(ls *), Bash(tail *)
disable-model-invocation: true
---

Show a quick status summary for Agend Ops:

1. **Recent Activity**: Read last 5 entries from data/feed.jsonl
2. **Triage Runs**: List files in data/triage/ sorted by date (most recent first)
3. **Pending Tasks**: Count and list entries in data/tasks/active.jsonl
4. **System Health**: Check if hardened-workspace MCP server is connected

Format output as a clean, scannable summary. Use emoji sparingly for visual anchoring only if natural.
```

### Custom Command Example: /feed
```yaml
---
name: feed
description: Show recent activity feed entries
allowed-tools: Read, Bash(jq *), Bash(tail *)
disable-model-invocation: true
---

Display the most recent activity feed entries from data/feed.jsonl.

Default: last 10 entries. If an argument is provided, show that many entries.
Use: `tail -n ${1:-10} data/feed.jsonl | jq -s '.'`

Format each entry showing: timestamp, type icon, summary, and level.
Group by date if spanning multiple days.
```

### Custom Command Example: /task
```yaml
---
name: task
description: Create or manage a task
argument-hint: <description of what to do>
allowed-tools: Read, Write, Edit, Bash(jq *), Bash(date *)
disable-model-invocation: true
---

Create a new task record from the description: $ARGUMENTS

1. Generate a task ID: task-{date}-{sequence}
2. Create a task record JSON object with status "pending"
3. Append to data/tasks/active.jsonl
4. Append a feed entry to data/feed.jsonl noting the task creation
5. Display the created task with its ID

If no arguments provided, list current pending tasks from data/tasks/active.jsonl instead.
```

### .gitignore
```
# Claude Code local settings (contains secrets)
.claude/settings.local.json

# OAuth tokens
token.json
*.token
credentials.json

# Environment files
.env
.env.local
.env.*.local

# OS files
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
.venv/

# Node (in case of future tooling)
node_modules/
```

### CLAUDE.md Enhancement (project instructions to add)
```markdown
## MCP Server Usage

CRITICAL: Use ONLY the `hardened-workspace` MCP server for Gmail and Drive access.
DO NOT use `claude.ai Gmail` or `claude.ai Google Calendar` connectors -- they can
send emails and route data through external servers.

When accessing Gmail or Drive, use tools prefixed with `mcp__hardened-workspace__`.

## Data Conventions

- Activity feed: append to data/feed.jsonl (NDJSON, one object per line)
- Triage results: create new file in data/triage/ named by timestamp
- Task records: append to data/tasks/active.jsonl
- All timestamps in ISO 8601 with timezone offset

## Commands

- /status -- Quick summary of current state
- /task <description> -- Create or manage tasks
- /feed [count] -- Show recent activity (default: 10)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| .claude/commands/ only | .claude/skills/ (superset) | Late 2025 | Skills add auto-invocation, supporting files. Commands still work. |
| MCP via npm packages | Official remote HTTP MCP servers | Early 2026 | github/github-mcp-server via HTTP, no Docker/npm needed. |
| Desktop scheduled tasks for automation | GitHub Actions with claude-code-action@v1 | Ongoing (bug #36327) | Desktop tasks cannot access MCP servers. Use GitHub Actions for durable scheduling. |
| Testing mode OAuth | Production or Internal mode OAuth | Always true | Testing tokens expire in 7 days. Always use production/internal mode for real usage. |

## Open Questions

1. **Hardened MCP scope reduction**
   - What we know: The hardened fork requests 21 OAuth scopes including gmail.modify and gmail.compose. It removes the tools that use dangerous scopes, but the token still has broad access.
   - What's unclear: Whether the fork supports scope reduction at the OAuth level (requesting only gmail.readonly for Gmail).
   - Recommendation: Accept broad scopes for now (tool-level restriction is the primary guard). File an issue or PR on the fork later to support configurable scope sets.

2. **Anthropic official connector management**
   - What we know: Glen has `claude.ai Gmail` and `claude.ai Google Calendar` pre-registered. These conflict with the hardened-fork approach.
   - What's unclear: Whether removing them affects other Claude functionality, or if they are safe to remove entirely.
   - Recommendation: Test removing `claude.ai Gmail` via `claude mcp remove`. If it breaks nothing, remove it. If it cannot be removed, document in CLAUDE.md that hardened-workspace tools should always be preferred.

3. **Google Drive MCP integration testing**
   - What we know: The hardened fork supports Drive read access. FOUND-01 requires Drive access verification.
   - What's unclear: Whether Drive requires separate OAuth configuration or shares the same token as Gmail.
   - Recommendation: Test Drive access after Gmail is working. The same OAuth token should cover both since both scopes are requested together.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Claude Code | Runtime platform | Yes | 2.1.81 | -- |
| Python 3.11+ | hardened-google-workspace-mcp | Yes | 3.14.3 | -- |
| uv | MCP server dependency management | Yes | 0.8.4 | -- |
| jq | NDJSON processing scripts | Yes | 1.7.1-apple | -- |
| git | Version control, data store | Yes | 2.53.0 | -- |
| rclone | Google Drive sync (future) | No | -- | Not needed for Phase 1. Install when needed (v2 feature). |
| Google Cloud Console access | OAuth setup | Requires verification | -- | Glen is Workspace admin (D-02), should have access. |

**Missing dependencies with no fallback:**
- None -- all Phase 1 dependencies are available.

**Missing dependencies with fallback:**
- rclone: Not installed, but not needed for Phase 1 (deferred to v2 automation).

## Project Constraints (from CLAUDE.md)

- GSD workflow enforcement: Start work through GSD commands (/gsd:quick, /gsd:debug, /gsd:execute-phase)
- Do not make direct repo edits outside a GSD workflow unless explicitly asked
- RTK (Rust Token Killer) is installed as a CLI proxy -- it rewrites commands via hooks for token optimization
- zen MCP server is already configured at user scope (unrelated to this project but present in environment)
- playwright MCP server is already configured at user scope (unrelated to this project)

## Sources

### Primary (HIGH confidence)
- [hardened-google-workspace-mcp (GitHub)](https://github.com/c0webster/hardened-google-workspace-mcp) -- installation, tools, OAuth setup, security model
- [hardened-google-workspace-mcp SECURITY.md](https://github.com/c0webster/hardened-google-workspace-mcp/blob/main/SECURITY.md) -- removed tools, attack vectors, residual risks
- [hardened-google-workspace-mcp OAUTH_SETUP.md](https://github.com/c0webster/hardened-google-workspace-mcp/blob/main/OAUTH_SETUP.md) -- OAuth setup steps, scope list
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) -- .mcp.json format, scopes, transport, registration
- [Claude Code skills/commands docs](https://code.claude.com/docs/en/slash-commands) -- SKILL.md format, frontmatter, arguments, invocation control
- [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) -- scope classification (sensitive/restricted)
- [Google OAuth consent screen](https://developers.google.com/workspace/guides/configure-oauth-consent) -- Internal vs External, verification requirements
- [NDJSON specification](https://ndjson.com/definition/) -- format spec, append-only advantages

### Secondary (MEDIUM confidence)
- [Claude official Gmail connector](https://support.claude.com/en/articles/10166901-use-google-workspace-connectors) -- confirms send capability, Anthropic-hosted
- [Google verification exemptions](https://support.google.com/cloud/answer/13464323) -- Internal apps exempt from verification for restricted scopes
- [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) -- scope classification details

### Tertiary (LOW confidence)
- None -- all findings verified against primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools verified installed, versions confirmed via CLI
- Architecture: HIGH -- patterns from project-level architecture research, verified against Claude Code docs
- OAuth setup: HIGH -- Internal user type exemption verified via Google docs, Glen confirmed as Workspace admin
- MCP server: HIGH -- c0webster fork verified on GitHub, installation tested conceptually against available Python/uv
- NDJSON schemas: MEDIUM -- schemas are author-designed based on requirements; no external validation yet
- Pitfalls: HIGH -- all critical pitfalls from project-level pitfall research, Phase 1 items verified

**Research date:** 2026-03-23
**Valid until:** 2026-04-22 (30 days -- stable domain, unlikely to change rapidly)
