# Phase 4: Dashboard - Research

**Researched:** 2026-03-23
**Domain:** Static HTML/CSS/JS dashboard, GitHub Pages deployment, NDJSON data compilation
**Confidence:** HIGH

## Summary

Phase 4 builds a single-file HTML dashboard (inline CSS + JS) served from the `docs/` directory via GitHub Pages. The dashboard displays four data columns (Starred, Urgent, Pending Tasks, Recent Activity) using data compiled from NDJSON files to JSON by a build script. All visual specifications are locked in the UI-SPEC, including exact color tokens, spacing scale, typography, component dimensions, and accessibility requirements.

The primary technical challenge is modest: compile triage data into `docs/triage.json` (the build script currently handles `feed.json` and `tasks.json` but not triage), build the HTML/CSS/JS dashboard as a single file, implement ARIA-compliant tab navigation for mobile, and wire the build script into existing slash commands for auto-rebuild.

**Primary recommendation:** Build `docs/index.html` as a single self-contained file with inline CSS (design tokens via custom properties, `prefers-color-scheme` media query for dark mode) and inline JS (parallel fetch of three JSON files, DOM population, relative time computation). Enhance `scripts/build-dashboard-data.sh` to also compile `docs/triage.json` from the latest triage run.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Status board layout -- Kanban-style columns: Starred | Urgent | Pending Tasks | Recent Activity. Data-dense, everything visible at once.
- **D-02:** Medium item density -- subject, sender, first line of summary, priority badge. No tap needed for most items.
- **D-03:** Mobile-first responsive design -- columns stack vertically on phone, expand horizontally on desktop.
- **D-04:** System auto dark/light mode -- follows phone's prefers-color-scheme setting
- **D-05:** Notion-style aesthetics -- content-focused, warm, readable. Less tool-like, more document-like. Clean typography, subtle borders, rounded corners.
- **D-06:** Plain HTML/CSS/JS -- no framework, no build step. Claude generates directly.
- **D-07:** Auto-rebuild after triage/task commands -- /triage-inbox and /task automatically run build-dashboard-data.sh and commit
- **D-08:** Manual rebuild also available (scripts/build-dashboard-data.sh)
- **D-09:** Prominent "Last updated" timestamp at the top of the dashboard
- **D-10:** Private GitHub repo -- use GitHub Pro/Team for private repo with GitHub Pages. Full data visible (client names, email subjects) since access is restricted.

### Claude's Discretion
- Exact HTML structure and CSS styling within Notion-style guidelines
- Column widths and breakpoints for responsive layout
- Color palette for dark/light modes
- How summary cards display numbers (badges, counts, etc.)
- Animation/transition choices (if any -- keep minimal)
- Favicon and page title

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VIS-01 | Activity feed logged as NDJSON (data/feed.jsonl) with timestamp, trigger, action, inputs, outputs, and outcome | Already implemented in Phases 1-3. feed.jsonl exists with 5 entries. Build script compiles to docs/feed.json. |
| VIS-02 | GitHub Pages dashboard auto-deployed from repo | docs/ directory exists. GitHub Pages configured to deploy from docs/ on main branch. Build script produces JSON files in docs/. |
| VIS-03 | Dashboard displays: unread email count, starred queue, recent activity feed, pending task suggestions | Requires: (1) docs/index.html with four columns, (2) docs/triage.json (NEW -- build script enhancement), (3) summary bar stats computed from feed.json + triage.json + tasks.json |
| VIS-04 | Dashboard is mobile-first and responsive -- glanceable from phone | UI-SPEC defines two breakpoints (< 768px mobile tabs, >= 768px desktop Kanban), sticky header, 44px touch targets, system font stack |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **MCP Security:** Use ONLY `hardened-workspace` MCP for Gmail/Drive. No `claude.ai Gmail` connectors.
- **Data Conventions:** All timestamps ISO 8601 with timezone offset. NDJSON for data storage.
- **Dashboard data:** Run `scripts/build-dashboard-data.sh` to compile NDJSON into docs/ JSON files.
- **Commands:** Custom slash commands in `.claude/commands/` -- triage-inbox and task are relevant for auto-rebuild hooks.
- **GSD Workflow:** All work through GSD commands. Do not make direct repo edits outside GSD workflow.

## Standard Stack

### Core
| Technology | Version | Purpose | Why Standard |
|------------|---------|---------|--------------|
| Plain HTML5 | N/A | Dashboard page structure | D-06: no framework. Semantic HTML for accessibility. |
| CSS3 Custom Properties | N/A | Design token system (colors, spacing, typography) | CSS variables enable dark/light mode switching via single media query override |
| Vanilla JavaScript (ES2020+) | N/A | Data fetching, DOM population, relative time | D-06: no framework. fetch() + Promise.all for parallel JSON loading |
| jq | 1.7.1 (installed) | NDJSON to JSON compilation in build script | Already used by build-dashboard-data.sh. Verified installed. |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `Intl.RelativeTimeFormat` | Browser built-in (ES2020+) | Relative time display ("2h ago") | For "Last updated" timestamp. Supported in all modern browsers. |
| GitHub Pages | N/A | Static site hosting from docs/ directory | Already configured pattern in this project. Deploy from main branch /docs folder. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline CSS/JS | Separate files | Single file simplifies deployment. No HTTP request overhead on GitHub Pages. Dashboard is small enough that separation adds no value. |
| `Intl.RelativeTimeFormat` | Custom relative time function | UI-SPEC defines specific format rules (e.g., "{N}m ago", "{N}h ago") that don't match Intl output. Custom function preferred -- see Code Examples. |
| CSS Grid for Kanban | Flexbox | CSS Grid is cleaner for 4-column layout with equal sizing. Use Grid for desktop columns, Flexbox for mobile tab content. |

## Architecture Patterns

### Recommended File Structure
```
docs/
  index.html          # Single-page dashboard (HTML + inline CSS + inline JS)
  feed.json            # Activity feed data (compiled by build script)
  tasks.json           # Task queue data (compiled by build script)
  triage.json          # Triage email data (NEW -- compiled by build script)
  .gitkeep             # Already exists

scripts/
  build-dashboard-data.sh   # Enhanced to also compile triage.json
```

### Pattern 1: CSS Custom Properties for Theming
**What:** Define all design tokens as CSS custom properties on `:root`, override in `@media (prefers-color-scheme: dark)`.
**When to use:** Always -- this is the standard approach for system-auto dark/light mode without JavaScript.
**Example:**
```css
:root {
  --surface: #FFFFFF;
  --surface-secondary: #F7F6F3;
  --text-primary: #37352F;
  --text-secondary: #787774;
  --border: #E3E2DE;
  --accent: #2383E2;
  color-scheme: light dark;
}

@media (prefers-color-scheme: dark) {
  :root {
    --surface: #191919;
    --surface-secondary: #252525;
    --text-primary: #FFFFFFCF;
    --text-secondary: #FFFFFF52;
    --border: #FFFFFF14;
    --accent: #529CCA;
  }
}
```

### Pattern 2: Parallel JSON Fetch with Graceful Degradation
**What:** Fetch all three JSON files simultaneously. Render available data even if one fetch fails.
**When to use:** Page load sequence -- UI-SPEC mandates this pattern (fetch in parallel, error state per column).
**Example:**
```javascript
const [feedResult, tasksResult, triageResult] = await Promise.allSettled([
  fetch('./feed.json').then(r => r.ok ? r.json() : Promise.reject(r.status)),
  fetch('./tasks.json').then(r => r.ok ? r.json() : Promise.reject(r.status)),
  fetch('./triage.json').then(r => r.ok ? r.json() : Promise.reject(r.status))
]);

const feed = feedResult.status === 'fulfilled' ? feedResult.value : null;
const tasks = tasksResult.status === 'fulfilled' ? tasksResult.value : null;
const triage = triageResult.status === 'fulfilled' ? triageResult.value : null;
```

### Pattern 3: ARIA Tablist for Mobile Navigation
**What:** Implement WAI-ARIA tab pattern with `role="tablist"`, `role="tab"`, `role="tabpanel"`, keyboard navigation.
**When to use:** Mobile tab bar (< 768px). Required by UI-SPEC accessibility contract.
**Example:**
```html
<nav role="tablist" aria-label="Dashboard columns" class="tab-bar">
  <button role="tab" aria-selected="true" aria-controls="panel-starred" id="tab-starred">Starred</button>
  <button role="tab" aria-selected="false" aria-controls="panel-urgent" id="tab-urgent" tabindex="-1">Urgent</button>
  <!-- ... -->
</nav>
<section role="tabpanel" id="panel-starred" aria-labelledby="tab-starred">
  <!-- cards -->
</section>
```
**Keyboard interaction:** Arrow Left/Right to navigate tabs, Enter/Space to activate. Active tab gets `tabindex="0"`, inactive tabs get `tabindex="-1"`.

### Pattern 4: Build Script Enhancement for Triage Data
**What:** Add triage.json compilation to build-dashboard-data.sh. Find the latest triage JSONL file and compile it to docs/triage.json.
**When to use:** Every build script run.
**Example:**
```bash
# Compile latest triage run -> docs/triage.json
LATEST_TRIAGE=$(ls -t "$REPO_ROOT/data/triage/"*.jsonl 2>/dev/null | head -1)
if [ -n "$LATEST_TRIAGE" ] && [ -s "$LATEST_TRIAGE" ]; then
  jq -s '.' "$LATEST_TRIAGE" > "$REPO_ROOT/docs/triage.json"
  echo "Built docs/triage.json ($(jq length "$REPO_ROOT/docs/triage.json") entries from $(basename "$LATEST_TRIAGE"))"
else
  echo "[]" > "$REPO_ROOT/docs/triage.json"
  echo "Built docs/triage.json (empty -- no triage data yet)"
fi
```

### Anti-Patterns to Avoid
- **JavaScript theme toggle:** D-04 locks system-auto mode. No manual toggle. Use `prefers-color-scheme` media query only.
- **Framework or bundler:** D-06 locks plain HTML/CSS/JS. No React, no Vite, no npm packages.
- **External CSS/JS files:** UI-SPEC file output contract specifies single-file architecture. All CSS and JS inline in index.html.
- **Fetch without error handling:** UI-SPEC requires per-column error states. Never assume all fetches succeed.
- **innerHTML for user-supplied data:** Triage data contains email subjects/snippets from untrusted senders. Use `textContent` for all user data to prevent XSS.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NDJSON to JSON compilation | Custom Node.js script | `jq -s '.'` in bash | jq is already installed (1.7.1), already used by existing build script. One-liner. |
| Dark mode detection | JavaScript theme detection | CSS `@media (prefers-color-scheme: dark)` | Zero JS needed. Automatic. Respects system setting. |
| Responsive layout | Manual media query juggling | CSS Grid + single 768px breakpoint | Two layouts only per UI-SPEC. Grid handles desktop, Flexbox handles mobile. |
| Accessible tabs | Custom keyboard handling from scratch | Follow WAI-ARIA APG Tabs Pattern exactly | W3C's reference pattern covers all edge cases (focus management, keyboard nav, screen reader announcements) |

**Key insight:** This is a read-only dashboard with no user input, no forms, no mutations. The entire JS surface is: fetch 3 JSON files, populate DOM, compute one relative timestamp. Keep it simple.

## Common Pitfalls

### Pitfall 1: GitHub Pages Privacy Misconception
**What goes wrong:** Assuming a private repo means the GitHub Pages site is private.
**Why it happens:** GitHub Pages sites published from private repos are still publicly accessible on the internet for GitHub Pro users. True private access control (restricting to repo members) requires GitHub Enterprise Cloud.
**How to avoid:** Accept that the Pages site will be publicly accessible via URL. Privacy comes from obscurity (the URL is not indexed, not linked anywhere). If true access control is needed, upgrade to Enterprise Cloud or use a different hosting approach.
**Warning signs:** Client names and email subjects visible in triage.json. Ensure the user understands the privacy model. D-10 says "Private GitHub repo" -- this makes the source code private, but the Pages site is public unless Enterprise Cloud.

### Pitfall 2: XSS via Email Content
**What goes wrong:** Email subjects, sender names, and snippets are untrusted input from external senders. Using innerHTML to render them opens XSS vectors.
**Why it happens:** Triage data contains real email content. A malicious sender could craft a subject line like `<img src=x onerror=alert(1)>`.
**How to avoid:** Always use `element.textContent = value` for rendering triage/task/feed data. Never use `innerHTML` with data from JSON files. For any structured HTML (like priority badges), build elements programmatically with `document.createElement`.
**Warning signs:** Any use of `innerHTML` or template literals inserted via innerHTML with data values.

### Pitfall 3: Stale Build Script Output
**What goes wrong:** Dashboard shows old data because build script was not re-run after triage/task commands.
**Why it happens:** D-07 requires auto-rebuild after triage/task commands, but the current slash commands do not call `build-dashboard-data.sh`.
**How to avoid:** Add `bash scripts/build-dashboard-data.sh` calls to the end of `/triage-inbox` and `/task` command files. Also commit the updated docs/*.json files.
**Warning signs:** "Last updated" timestamp showing hours/days old data when triage was run recently.

### Pitfall 4: Empty State Handling
**What goes wrong:** Dashboard shows blank/broken UI when data files are empty (`[]`) or fetches fail.
**Why it happens:** First-time setup or fresh clone has no data. Build script writes `[]` for empty sources.
**How to avoid:** UI-SPEC defines specific empty state copy for each column. Implement these as the default state, replaced when data loads. Also implement error states per the copywriting contract.
**Warning signs:** Blank columns, missing headers, JavaScript errors in console.

### Pitfall 5: Relative Time Timezone Confusion
**What goes wrong:** "Last updated" shows incorrect relative time because timestamp parsing ignores timezone offset.
**Why it happens:** feed.jsonl timestamps include timezone offset (e.g., `+10:30` for Adelaide). If parsed naively, the relative time calculation is off by the UTC offset.
**How to avoid:** Use `new Date(isoString)` which correctly parses ISO 8601 with timezone offset. Then compare with `Date.now()` for the difference. JavaScript's Date constructor handles this correctly.
**Warning signs:** "Last updated" showing very large or negative relative times.

### Pitfall 6: Missing Triage Fields
**What goes wrong:** Dashboard code assumes all triage record fields are present, but some are optional in the schema.
**Why it happens:** `client_name`, `client_domain`, `draft_id`, `from_name` are not in the `required` array of triage-record.json. Some records may lack these fields.
**How to avoid:** Use optional chaining and defaults: `record.from_name || record.from`, `record.client_name || ''`. Check actual data -- verified that the latest triage file (58 records) has `from_name` on all records but `client_name`/`client_domain` only on some.
**Warning signs:** "undefined" appearing in card text, or cards with missing sender names.

## Code Examples

### Relative Time Formatting (Custom per UI-SPEC)
```javascript
// UI-SPEC defines specific format rules that differ from Intl.RelativeTimeFormat
function relativeTime(isoString) {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  const date = new Date(isoString);
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}`;
}
```

### Safe DOM Card Rendering (XSS-safe)
```javascript
function createEmailCard(record) {
  const card = document.createElement('article');
  card.className = 'email-card';

  const line1 = document.createElement('div');
  line1.className = 'card-line1';

  const sender = document.createElement('span');
  sender.className = 'sender';
  if (record.starred) {
    sender.textContent = '\u2605 ' + (record.from_name || record.from);
  } else {
    sender.textContent = record.from_name || record.from;
  }
  line1.appendChild(sender);

  if (record.priority && record.priority !== 'informational') {
    const badge = document.createElement('span');
    badge.className = 'priority-badge priority-' + record.priority;
    badge.textContent = priorityLabels[record.priority] || record.priority;
    line1.appendChild(badge);
  }
  card.appendChild(line1);

  const subject = document.createElement('div');
  subject.className = 'card-subject';
  subject.textContent = record.subject;
  card.appendChild(subject);

  // ... snippet, timestamp lines follow same pattern
  return card;
}
```

### Accessible Tab Switching (ARIA pattern)
```javascript
function initTabs() {
  const tabs = document.querySelectorAll('[role="tab"]');
  const panels = document.querySelectorAll('[role="tabpanel"]');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab, tabs, panels));
    tab.addEventListener('keydown', (e) => {
      const tabArray = Array.from(tabs);
      const index = tabArray.indexOf(tab);
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        const next = tabArray[(index + 1) % tabArray.length];
        next.focus();
        switchTab(next, tabs, panels);
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        const prev = tabArray[(index - 1 + tabArray.length) % tabArray.length];
        prev.focus();
        switchTab(prev, tabs, panels);
      }
    });
  });
}

function switchTab(activeTab, allTabs, allPanels) {
  allTabs.forEach(t => {
    t.setAttribute('aria-selected', 'false');
    t.setAttribute('tabindex', '-1');
  });
  allPanels.forEach(p => p.hidden = true);

  activeTab.setAttribute('aria-selected', 'true');
  activeTab.setAttribute('tabindex', '0');
  const panel = document.getElementById(activeTab.getAttribute('aria-controls'));
  if (panel) panel.hidden = false;
}
```

### HTML Color Scheme Meta Tag
```html
<!-- Place in <head> before any CSS to prevent flash of wrong theme -->
<meta name="color-scheme" content="light dark">
```

### Desktop Column Scroll Pattern
```css
.column {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  /* Smooth scrolling for content overflow */
  -webkit-overflow-scrolling: touch;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| moment.js for relative time | `Intl.RelativeTimeFormat` or custom function | 2020+ | No dependency needed. UI-SPEC specifies custom format anyway. |
| JavaScript theme detection | CSS `prefers-color-scheme` media query | 2019+ | Zero JS, automatic, respects system. Supported in all modern browsers. |
| AJAX / XMLHttpRequest | `fetch()` + `Promise.allSettled()` | 2020+ | Cleaner API, built-in. allSettled for graceful degradation. |
| Float-based layouts | CSS Grid + Flexbox | 2018+ | Grid for 4-column desktop Kanban, Flexbox for mobile stacking. |

## Open Questions

1. **GitHub Pages Privacy Model**
   - What we know: D-10 specifies "Private GitHub repo". GitHub Pro allows publishing Pages from private repos, but the Pages site itself is still publicly accessible via URL. True access control (restrict to repo members) requires GitHub Enterprise Cloud.
   - What's unclear: Whether Glen has GitHub Enterprise Cloud or just GitHub Pro/Team.
   - Recommendation: Document the privacy model in the dashboard itself (or commit notes). The URL is not indexed or linked, so practical obscurity provides baseline privacy. If true access control is needed, investigate Enterprise Cloud or alternative deployment (e.g., Cloudflare Access).

2. **Triage Data Freshness**
   - What we know: Build script will compile the latest triage file only. If the last triage was days ago, the dashboard shows stale email data.
   - What's unclear: How often Glen runs `/triage-inbox`.
   - Recommendation: The "Last updated" timestamp (D-09) handles this. Show the triage run timestamp prominently so staleness is obvious.

3. **Data Volume Limits**
   - What we know: Latest triage file has 58 records. Feed has 5 entries. Active tasks has 16 records. These are small.
   - What's unclear: Whether data will grow significantly over time.
   - Recommendation: Build script already limits feed to last 100 entries. Triage compiles only the latest run file. Tasks file will grow but slowly. No pagination needed for v1 -- revisit if column card counts exceed ~50.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| jq | Build script (NDJSON to JSON) | Yes | 1.7.1-apple | -- |
| bash | Build script execution | Yes | (macOS default) | -- |
| git | Commit dashboard data after build | Yes | (project is a git repo) | -- |
| GitHub Pages | Dashboard hosting | Yes (docs/ directory exists) | -- | Needs manual setup in repo Settings > Pages |

**Missing dependencies with no fallback:**
- None. All tools are available.

**Missing dependencies with fallback:**
- GitHub Pages configuration: docs/ directory exists with .gitkeep. Needs manual one-time setup in GitHub repo settings (Settings > Pages > Deploy from branch > main > /docs). This is a manual step, not automatable by the plan.

## Data Contract Summary

### Existing Data (verified)

| File | Path | Records | Status |
|------|------|---------|--------|
| feed.jsonl | data/feed.jsonl | 5 entries | Compiled to docs/feed.json (currently empty `[]` -- build script not yet re-run after data creation) |
| active.jsonl | data/tasks/active.jsonl | 16 records (2 completed, 14 pending) | Compiled to docs/tasks.json (currently empty `[]`) |
| Triage (latest) | data/triage/2026-03-23T021003.jsonl | 58 records (1 starred, 13 urgent, 7 needs-response, 28 info, 10 low) | NOT YET compiled -- needs build script enhancement |

### Required Build Script Output

| File | Source | Content |
|------|--------|---------|
| docs/feed.json | data/feed.jsonl (last 100) | Array of feed entry objects |
| docs/tasks.json | data/tasks/active.jsonl (all) | Array of task record objects |
| docs/triage.json | data/triage/{latest}.jsonl (all from latest run) | Array of triage record objects |

### Column-to-Data Mapping (from UI-SPEC)

| Column | Source | Filter | Sort |
|--------|--------|--------|------|
| Starred | triage.json | `starred === true` | `received` desc |
| Urgent | triage.json | `priority === "urgent" && !starred` | `received` desc |
| Pending Tasks | tasks.json | `status === "pending" OR status === "in-progress"` | `ts` desc |
| Recent Activity | feed.json | All entries | `ts` desc |

## Sources

### Primary (HIGH confidence)
- `schemas/feed-entry.json` -- Activity feed schema (verified against actual data)
- `schemas/triage-record.json` -- Triage record schema (verified against 58 actual records)
- `schemas/task-record.json` -- Task record schema (verified against 16 actual records)
- `scripts/build-dashboard-data.sh` -- Existing build script (verified: compiles feed + tasks, needs triage addition)
- `.planning/phases/04-dashboard/04-UI-SPEC.md` -- Complete visual specification with component inventory, data binding, interaction contract
- `.planning/phases/04-dashboard/04-CONTEXT.md` -- User decisions D-01 through D-10
- [W3C WAI-ARIA Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) -- Authoritative ARIA tab pattern
- [MDN prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme) -- CSS dark mode media query
- [MDN Intl.RelativeTimeFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/RelativeTimeFormat) -- Browser built-in relative time formatting

### Secondary (MEDIUM confidence)
- [GitHub Pages docs directory configuration](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) -- Deploy from docs/ folder on main branch
- [GitHub Pages private repo visibility](https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site) -- Access control requires Enterprise Cloud; Pro/Team allows private repo but public Pages site
- [web.dev dark mode tutorial](https://web.dev/articles/prefers-color-scheme) -- Best practices for color-scheme meta tag and CSS

### Tertiary (LOW confidence)
- None -- all findings verified against primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Plain HTML/CSS/JS is trivial to verify. jq confirmed installed. All patterns are browser-standard.
- Architecture: HIGH -- Single-file dashboard pattern is well-established. Data contract fully specified in schemas + UI-SPEC.
- Pitfalls: HIGH -- XSS via email content is a verified concern (triage data contains untrusted sender input). Privacy model verified against GitHub docs.

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no fast-moving dependencies)
