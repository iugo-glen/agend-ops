---
phase: 06-daily-task-management
verified: 2026-03-23T12:00:00+10:00
status: human_needed
score: 10/10 must-haves verified
re_verification: false
human_verification:
  - test: "Open docs/index.html in a browser and confirm Today tab is the default selected tab"
    expected: "Today tab is pre-selected; YOUR TO-DOS and CLAUDE TASKS section labels appear when data is present; empty state 'Nothing on your plate today. Nice!' appears when no data"
    why_human: "Visual tab rendering and default-selected state cannot be confirmed via static analysis alone"
  - test: "Resize browser to desktop width (>768px) and count dashboard columns"
    expected: "5 columns visible: Today, Starred, Urgent, Tasks, Activity"
    why_human: "CSS grid layout requires visual inspection"
  - test: "Toggle system dark mode and reload docs/index.html"
    expected: "Priority pills, due-badge colours (red for overdue, amber for due-today), and category tags render legibly in dark mode"
    why_human: "Colour contrast for todo-specific CSS classes requires visual verification"
  - test: "Run /todo buy groceries by tomorrow !high #personal in Claude Code, then run /todo"
    expected: "To-do appears numbered with !!! badge, due date, and #personal tag; dashboard rebuild runs and docs/todos.json is updated"
    why_human: "End-to-end command execution requires a live Claude Code session"
---

# Phase 6: Daily Task Management Verification Report

**Phase Goal:** Glen tracks personal to-dos alongside Claude tasks, visible in briefing and dashboard
**Verified:** 2026-03-23T12:00:00+10:00
**Status:** human_needed — all automated checks passed; 4 items require visual/interactive verification
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Glen can add a to-do with priority, due date, category, and recurring flag via /todo | VERIFIED | Mode 5 in `.claude/commands/todo.md` (lines 163-288) parses `!high/!low/!normal`, `#business/#personal/#marketing`, `by/due/before {date}`, `every day/daily/every weekday/weekly`; builds 11-field record; appends to `data/todos/active.jsonl` |
| 2  | Glen can complete a to-do by text match or number via /todo done | VERIFIED | Mode 3 (lines 96-135) supports numeric position and case-insensitive substring match; updates status and completed_at; logs feed entry |
| 3  | Glen can list to-dos filtered by status/priority/category via /todo list | VERIFIED | Mode 2 (lines 57-93) supports `completed`, `all`, `#category`, `!priority` filters using jq; table format output |
| 4  | Glen can reprioritize a to-do via /todo prioritize | VERIFIED | Mode 4 (lines 138-159) supports `/todo pri N !high/!normal/!low`; rewrites active.jsonl in-place via tmp file |
| 5  | To-do items persist in data/todos/active.jsonl as NDJSON | VERIFIED | `data/todos/.gitkeep` exists; all write paths in todo.md append/modify `data/todos/active.jsonl`; `docs/todos.json` is `[]` (empty initial state, correct) |
| 6  | build-dashboard-data.sh compiles todos.json for dashboard consumption | VERIFIED | Lines 55-62 of build-dashboard-data.sh: produces `docs/todos.json` from `data/todos/active.jsonl` or emits `[]` when empty |
| 7  | Daily briefing includes a Your To-Dos section showing active to-dos with priority and due dates | VERIFIED | Step 4e added to `daily-briefing.md` (line 65); queries `data/todos/active.jsonl`; sorts by priority then due_date; flags overdue and due-today items |
| 8  | Briefing to-do section is separate from Pending Tasks section per D-07 | VERIFIED | In briefing template: "## Pending Tasks" block (step 4b) is distinct from "## Your To-Dos" block (step 4e); placed between Pending Tasks and Key Deadlines per D-07 |
| 9  | Dashboard shows a Today tab combining to-dos and pending tasks | VERIFIED | `docs/index.html` line 669: `tab-today` with `aria-selected="true"` (default); line 677: `col-today` section; lines 1262-1280: YOUR TO-DOS and CLAUDE TASKS sections with `section-label` dividers |
| 10 | Dashboard grid becomes 5-column on desktop to include the Today column | VERIFIED | `docs/index.html` line 608: `grid-template-columns: repeat(5, 1fr)` inside `@media (min-width: 768px)` |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `schemas/todo-record.json` | JSON Schema draft-07 for to-do records | VERIFIED | 11 fields (id, ts, status, text, priority, trigger, due_date, category, recurring, completed_at, linked_task_id); `additionalProperties: false`; correct `$id: "todo-record"` |
| `schemas/feed-entry.json` | type enum includes "todo" | VERIFIED | Line 16: `"enum": ["triage", "task", "draft", "system", "command", "briefing", "todo"]` |
| `.claude/commands/todo.md` | /todo command with 5 modes, min 100 lines | VERIFIED | 301 lines; YAML frontmatter with description and allowed-tools; all 5 modes present (Mode Detection section explicit) |
| `scripts/build-dashboard-data.sh` | todos.json compilation block | VERIFIED | Lines 55-62: compiles `data/todos/active.jsonl` -> `docs/todos.json` |
| `scripts/validate-data.sh` | Validation for todos/active.jsonl | VERIFIED | Line 42: `validate_jsonl "$REPO_ROOT/data/todos/active.jsonl" "Active todos"` |
| `.claude/commands/daily-briefing.md` | Briefing with to-do section | VERIFIED | Step 4e "Your To-Dos" present; queries active.jsonl; briefing template includes "## Your To-Dos" section; feed entry includes `active_todos` count |
| `docs/index.html` | Dashboard with Today tab (col-today) | VERIFIED | `col-today`, `tab-today`, `createTodoCard`, `stat-todos`, `todos.json` fetch, `repeat(5, 1fr)` all present |
| `data/todos/.gitkeep` | Directory placeholder | VERIFIED | File exists; `docs/todos.json` is `[]` (correct empty initial state) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `.claude/commands/todo.md` | `data/todos/active.jsonl` | jq append and query | WIRED | Modes 1-5 all read/write `data/todos/active.jsonl` explicitly; jq used for both query and mutation |
| `.claude/commands/todo.md` | `data/feed.jsonl` | feed entry on add/complete | WIRED | Mode 3 (complete) and Mode 5 (add) both append JSON feed entries with `"type": "todo"` to `data/feed.jsonl` |
| `scripts/build-dashboard-data.sh` | `docs/todos.json` | jq -s compilation | WIRED | `jq -s '.' "$REPO_ROOT/data/todos/active.jsonl" > "$REPO_ROOT/docs/todos.json"` |
| `.claude/commands/daily-briefing.md` | `data/todos/active.jsonl` | jq query for active todos | WIRED | Step 4e: `jq -r 'select(.status=="active")' data/todos/active.jsonl` |
| `docs/index.html` | `docs/todos.json` | fetch at page load | WIRED | Line 1140: `fetch('./todos.json')` in `Promise.allSettled` array; `todosResult` extracted at index `results[4]` |
| `docs/index.html` | `summary-bar` | todos count in stat-todos pill | WIRED | Line 1201: `document.getElementById('stat-todos').textContent = activeTodos` where `activeTodos` is filtered from `todosResult` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `docs/index.html` (Today column) | `activeTodoItems` | `fetch('./todos.json')` -> `todosResult` | Yes — `todos.json` is compiled from `data/todos/active.jsonl` by build script; filter `r.status === 'active'` applied | FLOWING |
| `docs/index.html` (summary bar) | `activeTodos` | `todosResult.filter(...)` | Yes — same source as above; graceful null fallback to 0 | FLOWING |
| `docs/index.html` (createTodoCard) | `record.text`, `record.priority`, `record.due_date`, `record.category` | todo record from `todosResult` array | Yes — all fields are part of `todo-record.json` schema; XSS-safe textContent-only rendering | FLOWING |
| `.claude/commands/daily-briefing.md` | to-do list | `jq` query on `data/todos/active.jsonl` | Yes — direct NDJSON read; graceful empty handling when file absent | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Schema is valid JSON | `jq '.' schemas/todo-record.json > /dev/null` | Valid (read confirms parseable JSON with 11 properties) | PASS |
| Feed schema includes "todo" type | Grep for `"todo"` in `schemas/feed-entry.json` line 16 | Found: `"enum": [..., "todo"]` | PASS |
| todo.md has YAML frontmatter | head -3 of file | `---`, `description:`, `allowed-tools:` present | PASS |
| Build script produces todos.json | Verified pattern in build-dashboard-data.sh lines 55-62 | Outputs `docs/todos.json` | PASS |
| Validate script checks todos | Grep for `validate_jsonl` in validate-data.sh line 42 | Present | PASS |
| Dashboard fetches todos.json | Grep `todos.json` in docs/index.html line 1140 | `fetch('./todos.json')` in Promise.allSettled | PASS |
| All 4 phase commits present in git | `git log --oneline 3e5bdbb fb29a6f 9974979 7b51890` | All 4 commits verified | PASS |
| XSS safety: no innerHTML in todo rendering | Grep `innerHTML` in docs/index.html | Comment `/* textContent only -- no innerHTML */` at line 786; createTodoCard uses textContent exclusively | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TODO-01 | 06-01-PLAN.md | /todo command supports add, complete, list, and prioritize operations | SATISFIED | `.claude/commands/todo.md` implements all 4 operations as Modes 2-5; Mode 1 is a free show-today bonus |
| TODO-02 | 06-01-PLAN.md | To-do items stored in NDJSON (data/todos/active.jsonl) with schema | SATISFIED | `schemas/todo-record.json` (11 fields, draft-07, additionalProperties:false); `data/todos/.gitkeep`; all write paths append to `active.jsonl` |
| TODO-03 | 06-02-PLAN.md | Daily briefing integrates to-do items alongside email and task status | SATISFIED | Step 4e in `daily-briefing.md`: "Your To-Dos" section with jq queries, priority sorting, due-date flagging; separate from Claude tasks per D-07 |
| TODO-04 | 06-02-PLAN.md | Dashboard "Today" tab shows daily to-dos with completion status | SATISFIED | `col-today`/`tab-today` in `docs/index.html`; `createTodoCard` renders checkbox, priority pill, due badge, category tag; shows `completed` status visually |

All 4 phase requirements accounted for across the 2 plans. No orphaned requirements.

---

### Anti-Patterns Found

No blockers or warnings found.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.claude/commands/todo.md` | 119, 152 | `TODO_ID="{matched id}"` | Info | These are bash variable assignment instructions (template placeholders for Claude to fill at runtime), not code TODOs. The command is a prompt file, not executed code. No impact. |

---

### Human Verification Required

#### 1. Today Tab Default Selection

**Test:** Open `docs/index.html` in a browser (or visit GitHub Pages URL).
**Expected:** Today tab is the default selected tab on mobile view. YOUR TO-DOS and CLAUDE TASKS section labels appear when `docs/todos.json` has data; "Nothing on your plate today. Nice!" empty state appears when `docs/todos.json` is empty.
**Why human:** `aria-selected="true"` on `tab-today` is confirmed via grep, but actual browser tab rendering and JavaScript-driven show/hide requires visual confirmation.

#### 2. Desktop 5-Column Layout

**Test:** Resize browser window to greater than 768px width.
**Expected:** 5 columns appear side-by-side: Today, Starred, Urgent, Tasks, Activity.
**Why human:** CSS `grid-template-columns: repeat(5, 1fr)` is confirmed in the file but actual rendering requires visual inspection to confirm no overflow or layout breakage.

#### 3. Dark Mode Colour Rendering for Todo Cards

**Test:** Toggle system dark mode preference and reload `docs/index.html`.
**Expected:** Priority pills (`.priority-pill--high` red, `.priority-pill--normal` surface-secondary), overdue due badges (`.due-badge--overdue` red), and category tags render legibly against the dark background.
**Why human:** CSS custom property resolution in dark mode requires visual inspection.

#### 4. End-to-End /todo Command Execution

**Test:** In a Claude Code session, run `/todo buy groceries by tomorrow !high #personal`, then run `/todo`.
**Expected:** (1) Record appended to `data/todos/active.jsonl`; (2) Feed entry appended to `data/feed.jsonl`; (3) Build script runs; (4) `/todo` shows the item numbered with `!!!` badge, due date, and `#personal` tag.
**Why human:** The /todo command is a prompt-based instruction file executed by Claude — it cannot be run without a live Claude Code session.

---

### Gaps Summary

No gaps found. All 10 observable truths are verified. All 4 requirements (TODO-01 through TODO-04) are satisfied by artifacts that exist, are substantive, and are wired to their data sources.

The phase goal — "Glen tracks personal to-dos alongside Claude tasks, visible in briefing and dashboard" — is achieved at the code level. The 4 human verification items are visual/interactive confirmations, not functional gaps.

---

_Verified: 2026-03-23T12:00:00+10:00_
_Verifier: Claude (gsd-verifier)_
