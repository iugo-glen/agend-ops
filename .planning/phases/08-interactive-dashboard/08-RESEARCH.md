# Phase 8: Interactive Dashboard (Next.js on Coolify) - Research

**Researched:** 2026-03-24
**Domain:** Next.js deployment, authentication, server-side file I/O, Coolify PaaS
**Confidence:** HIGH

## Summary

This phase replaces the static GitHub Pages dashboard with an interactive Next.js app deployed on Coolify. The core technical challenges are: (1) deploying Next.js from a subdirectory of an existing git repo on Coolify, (2) mounting the host filesystem so the app can read NDJSON data files directly, (3) Google OAuth login restricted to a single user, and (4) an action queue pattern where the dashboard writes requests that Claude processes asynchronously.

The stack is straightforward: Next.js 16 with App Router, Auth.js v5 (beta but production-stable) with Google provider, Tailwind CSS v4 for styling, and SWR for client-side data polling. The data files are tiny (under 30 lines total across all JSONL files) so streaming/pagination is unnecessary -- read-all-at-once with `fs.readFileSync` in API routes is the correct approach. Coolify's "Base Directory" feature handles the subdirectory deployment, and a bind mount maps the host's `data/` directory into the container.

**Primary recommendation:** Use Dockerfile build pack (not Nixpacks) for full control over the subdirectory build context and bind mount configuration. Keep the Kanban layout custom-built with CSS Grid -- no drag-and-drop library needed since cards are not reorderable.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Four dashboard actions: mark invoice paid, complete todo, view/approve Gmail draft, trigger triage
- **D-02:** Mutation strategy: queue for Claude -- dashboard writes action requests to a queue file, Claude picks them up on next triage run or manual check. Claude remains the single writer to data files.
- **D-03:** View/approve draft links directly to Gmail (already built) -- no server-side email sending
- **D-04:** Same repo -- Next.js app in /dashboard directory alongside data files
- **D-05:** Direct file read -- Next.js reads data/*.jsonl from disk (home server has direct access). No compilation step needed for the app.
- **D-06:** Coolify deploys from the /dashboard directory of the same repo
- **D-07:** API routes in Next.js handle action queuing and data reads
- **D-08:** Single user only -- Google OAuth locked to glen@iugo.com.au via NextAuth
- **D-09:** Custom subdomain on a domain Glen owns (e.g., ops.agendsystems.com or ops.iugo.com.au)
- **D-10:** No manager access for now -- single-user tool
- **D-11:** Evolve the Notion aesthetic for interactivity -- keep warm tones and clean typography but redesign for action-focused experience. Linear meets Notion.
- **D-12:** Kanban board style -- columns by domain (Today, Emails, Tasks, Invoices, Activity). Cards within each column have action buttons.
- **D-13:** Better mobile UX -- touch targets for action buttons. On mobile, columns become swipeable tabs (same as current dashboard pattern).
- **D-14:** Same data domains but cards gain action buttons (mark paid, complete, view draft, trigger triage)

### Claude's Discretion
- Next.js project structure (App Router vs Pages Router)
- NextAuth configuration details (providers, callbacks, session strategy)
- Action queue file format and location (data/queue/actions.jsonl or similar)
- How Claude discovers and processes queued actions (scheduled task, triage hook, or new command)
- Coolify deployment configuration (Dockerfile, build settings, env vars)
- CSS framework choice (Tailwind recommended for rapid development, or keep hand-rolled CSS)
- Whether to use a UI component library (shadcn/ui, Radix) or stay minimal
- Server-side data parsing strategy (stream NDJSON or read-all-at-once)
- Real-time refresh approach (polling interval, SWR, or manual refresh button)

### Deferred Ideas (OUT OF SCOPE)
- Real-time WebSocket updates -- polling is fine for v1 of the interactive dashboard
- Manager read-only access -- single user for now
- PWA / installable app -- just a responsive web app for now

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Next.js app deployed on Coolify with Google OAuth login (only Glen can access) | Coolify Base Directory + Dockerfile build pack; Auth.js v5 with signIn callback email check |
| DASH-02 | Dashboard reads live NDJSON data directly from git repo on home server | Bind mount host data/ dir into container; Node.js fs.readFileSync in API routes |
| DASH-03 | Action buttons: mark invoice paid, complete todo, approve/view Gmail draft, trigger triage | Action queue pattern: append to data/queue/actions.jsonl via API route; Claude processes queue |
| DASH-04 | Clickable Gmail links on email and invoice cards (carries over from current dashboard) | Same thread_id/draft_id URL patterns already proven in static dashboard |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Ecosystem**: Must work within Claude Code ecosystem (MCP servers, Claude Dispatch/Schedule)
- **Data ownership**: Local git repo as source of truth -- Glen must own and control all data
- **No SPA frameworks**: CLAUDE.md says "Any JavaScript SPA framework (React, Vue, Svelte) for dashboard" is in the "What NOT to Use" table. **However**, the CONTEXT.md locked decision D-04 explicitly specifies Next.js, which supersedes the general guideline. Next.js is server-rendered, not a client-side SPA, and this is a deliberate evolution from the static dashboard. The "What NOT to Use" entry targets unnecessary client-side framework overhead for a read-only page -- Phase 8 adds interactivity that justifies the upgrade.
- **NDJSON files committed to git**: Data format stays the same
- **Privacy**: Email content and business data must not leak to third-party services
- **hardened-google-workspace-mcp**: Claude can READ emails but not SEND them (by design)

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.2.1 | App framework (App Router, API routes, server components) | Latest stable. App Router is the standard for new Next.js projects. Server components read files directly. |
| next-auth | 5.0.0-beta.30 | Authentication (Google OAuth, session management) | v5 is the actively maintained version. Beta label but production-stable -- used widely. The `auth()` function works everywhere (server components, middleware, API routes). |
| Tailwind CSS | 4.2.2 | Utility-first CSS framework | Rapid development. Design tokens from UI-SPEC.md map directly to Tailwind's config (colors, spacing, typography). No need to hand-roll CSS for a second time. |
| SWR | 2.4.1 | Client-side data fetching with polling | Vercel's own data fetching library. `refreshInterval` option provides polling without WebSockets. Stale-while-revalidate gives instant UI with background refresh. |
| TypeScript | 5.x (bundled with Next.js) | Type safety | Next.js 16 ships with TypeScript support. Schemas define the types already. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @auth/core | 0.34.3 | Auth.js core (peer dep of next-auth v5) | Installed automatically with next-auth@beta |
| clsx | latest | Conditional class names | Cleaner than string concatenation for Tailwind classes |
| date-fns | latest | Date formatting (relative time, ISO parsing) | Replace the hand-rolled relative time function from the static dashboard |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tailwind CSS | Hand-rolled CSS (port from index.html) | More control but slower to iterate. Tailwind with design tokens is faster for an experienced dev. |
| SWR | React Query (TanStack Query) | Heavier, more features than needed. SWR is lighter and Vercel-native. |
| next-auth v5 beta | next-auth v4 stable | v4 does not have the unified `auth()` function for App Router. v5 beta is the right choice. |
| Custom Kanban CSS | @hello-pangea/dnd or dnd-kit | Drag-and-drop libraries add complexity. Cards are NOT reorderable per the design -- they're sorted by data. Action buttons, not DnD, are the interaction model. |
| shadcn/ui | Radix primitives only / fully custom | shadcn/ui would accelerate button/card components but adds a registry dependency. For ~5 component types (card, button, badge, tab, header), custom components are fine. |

**Installation:**
```bash
cd dashboard
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --no-turbopack --import-alias "@/*"
npm install next-auth@beta swr clsx date-fns
```

## Architecture Patterns

### Recommended Project Structure

```
dashboard/
├── Dockerfile                    # Multi-stage build for Coolify
├── next.config.ts                # standalone output, env vars
├── tailwind.config.ts            # Design tokens from UI-SPEC.md
├── src/
│   ├── app/
│   │   ├── layout.tsx            # Root layout with auth session provider
│   │   ├── page.tsx              # Main dashboard (server component)
│   │   ├── login/
│   │   │   └── page.tsx          # Login page with Google sign-in button
│   │   └── api/
│   │       ├── auth/
│   │       │   └── [...nextauth]/
│   │       │       └── route.ts  # Auth.js route handler
│   │       ├── data/
│   │       │   └── [type]/
│   │       │       └── route.ts  # GET /api/data/feed, /api/data/triage, etc.
│   │       └── actions/
│   │           └── route.ts      # POST /api/actions (queue action for Claude)
│   ├── auth.ts                   # Auth.js config (Google provider, signIn callback)
│   ├── middleware.ts             # Protect all routes except /login and /api/auth
│   ├── lib/
│   │   ├── data.ts              # NDJSON file readers (fs.readFileSync + parse)
│   │   ├── queue.ts             # Action queue writer (append to queue file)
│   │   └── types.ts             # TypeScript interfaces from JSON schemas
│   └── components/
│       ├── KanbanBoard.tsx       # Main board layout (columns)
│       ├── Column.tsx            # Single column with header + card list
│       ├── cards/
│       │   ├── EmailCard.tsx     # Email card with Gmail links
│       │   ├── TaskCard.tsx      # Task card with complete button
│       │   ├── TodoCard.tsx      # Todo card with complete button
│       │   ├── InvoiceCard.tsx   # Invoice card with mark-paid button
│       │   └── ActivityCard.tsx  # Activity feed card (read-only)
│       ├── ActionButton.tsx      # Reusable action button with "queued" state
│       ├── Header.tsx            # App header with title + last updated
│       ├── SummaryBar.tsx        # Stats pills row
│       └── MobileTabBar.tsx      # Tab navigation for mobile
├── public/                       # Static assets (if any)
└── package.json
```

### Pattern 1: Server-Side NDJSON Reading

**What:** API routes read NDJSON files directly from the host filesystem via bind mount.
**When to use:** Every data fetch.

```typescript
// src/lib/data.ts
import { readFileSync, existsSync } from 'fs';
import path from 'path';

const DATA_ROOT = process.env.DATA_DIR || '/data';

export function readNDJSON<T>(filePath: string): T[] {
  const fullPath = path.join(DATA_ROOT, filePath);
  if (!existsSync(fullPath)) return [];
  const content = readFileSync(fullPath, 'utf-8').trim();
  if (!content) return [];
  return content.split('\n').map(line => JSON.parse(line) as T);
}

// Example: read feed entries
export function getFeedEntries(limit = 50) {
  return readNDJSON<FeedEntry>('feed.jsonl').slice(-limit).reverse();
}

// Example: read latest triage
export function getLatestTriage() {
  // Find most recent triage file
  const triageDir = path.join(DATA_ROOT, 'triage');
  // ... list files, sort by name (ISO timestamp), read latest
}
```

**Why readFileSync, not streaming:** The data files are tiny (9 feed entries, 19 tasks, 0 invoices as of today). Even at 10x growth, these are sub-millisecond reads. Streaming adds complexity with zero benefit at this scale.

### Pattern 2: Action Queue (Write Path)

**What:** Dashboard writes action requests to a queue file. Claude processes them asynchronously.
**When to use:** All mutation actions (mark paid, complete todo, trigger triage).

```typescript
// src/lib/queue.ts
import { appendFileSync, mkdirSync } from 'fs';
import path from 'path';

const QUEUE_DIR = process.env.DATA_DIR || '/data';
const QUEUE_FILE = path.join(QUEUE_DIR, 'queue', 'actions.jsonl');

interface QueuedAction {
  id: string;           // action-YYYY-MM-DDTHH:mm:ss
  ts: string;           // ISO 8601
  action: 'mark-paid' | 'complete-todo' | 'complete-task' | 'trigger-triage';
  target_id: string;    // inv-2026-03-23-001, todo-2026-03-23-001, etc.
  status: 'queued';     // Always queued when written by dashboard
  requested_by: string; // glen@iugo.com.au
}

export function queueAction(action: Omit<QueuedAction, 'id' | 'ts' | 'status'>) {
  mkdirSync(path.dirname(QUEUE_FILE), { recursive: true });
  const entry: QueuedAction = {
    id: `action-${new Date().toISOString()}`,
    ts: new Date().toISOString(),
    status: 'queued',
    ...action,
  };
  appendFileSync(QUEUE_FILE, JSON.stringify(entry) + '\n', 'utf-8');
  return entry;
}
```

**Claude processes the queue via:**
1. A new `/process-queue` command that reads `data/queue/actions.jsonl`
2. Hooked into the existing `/triage-inbox` flow (check queue before/after triage)
3. Or triggered manually: "check and process action queue"

After processing, Claude updates the relevant data file (e.g., marks invoice as paid in `data/invoices/active.jsonl`) and moves the queue entry to `data/queue/processed.jsonl`.

### Pattern 3: Auth.js v5 Single-User Lock

**What:** Google OAuth restricted to glen@iugo.com.au only.
**When to use:** Auth configuration.

```typescript
// src/auth.ts
import NextAuth from 'next-auth';
import Google from 'next-auth/providers/google';

const ALLOWED_EMAIL = 'glen@iugo.com.au';

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    signIn({ profile }) {
      return profile?.email === ALLOWED_EMAIL;
    },
  },
  pages: {
    signIn: '/login',
  },
});
```

```typescript
// src/middleware.ts
export { auth as middleware } from './auth';

export const config = {
  matcher: ['/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)'],
};
```

### Pattern 4: SWR Polling for Data Freshness

**What:** Client components poll API routes at a configurable interval.
**When to use:** KanbanBoard component.

```typescript
// In a client component
'use client';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useData<T>(type: string) {
  return useSWR<T[]>(`/api/data/${type}`, fetcher, {
    refreshInterval: 30_000, // 30 seconds
    revalidateOnFocus: true,
  });
}
```

### Anti-Patterns to Avoid

- **Reading data files in server components directly:** Use API routes instead. Server components re-render on navigation, but API routes + SWR give you polling and caching for free. Server components are fine for the initial page shell.
- **Writing to data files from the dashboard:** The dashboard MUST NOT write to feed.jsonl, tasks/active.jsonl, etc. Only Claude writes to these. The dashboard writes ONLY to the action queue file.
- **Using NextAuth v4 with App Router:** v4's `getServerSession()` pattern is clunky with App Router. v5's `auth()` is the correct approach.
- **Complex state management (Redux, Zustand):** SWR handles server state. Local UI state (which tab is active, action button loading) is simple `useState`. No state library needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Authentication | Custom JWT/session system | next-auth v5 with Google provider | OAuth flow, CSRF protection, session management, cookie handling are all handled |
| CSS utility classes | Custom CSS class system | Tailwind CSS | Design tokens map directly; responsive prefixes; dark mode built in |
| Data polling | setInterval + fetch | SWR with refreshInterval | Handles cache, dedup, focus revalidation, error retry automatically |
| Relative time display | Custom date math | date-fns `formatDistanceToNow` | Edge cases (timezones, DST, "just now" vs "1m ago") already solved |
| Dockerfile | Nixpacks auto-detection | Official Next.js Dockerfile (standalone) | Nixpacks can fail on monorepo subdirectory builds; Dockerfile gives full control |

## Common Pitfalls

### Pitfall 1: Bind Mount Path Mismatch
**What goes wrong:** Container reads `/data` but the host path isn't mounted, or the mount points to the wrong directory.
**Why it happens:** Coolify's persistent storage UI creates Docker volumes by default, not host bind mounts. The repo's `data/` directory is at a specific path on the Mac host.
**How to avoid:** Configure a bind mount (not a volume) in Coolify's persistent storage settings. Source: the absolute path to the repo's data directory on the host (e.g., `/Users/glenr/work/todo-list/data`). Destination: `/data` inside the container. Set `DATA_DIR=/data` as an environment variable.
**Warning signs:** API routes return empty arrays when data files exist on the host.

### Pitfall 2: Google OAuth Redirect URI Mismatch
**What goes wrong:** "redirect_uri_mismatch" error during login.
**Why it happens:** The existing Google OAuth credentials have redirect URIs for the MCP server, not the Next.js app. The new callback URL (`https://ops.agendsystems.com/api/auth/callback/google`) must be added to the Google Cloud Console.
**How to avoid:** Add the production callback URI to the existing OAuth client's "Authorized redirect URIs" in Google Cloud Console. Also add `http://localhost:3000/api/auth/callback/google` for local development. Same client ID works -- just add more redirect URIs.
**Warning signs:** Login button redirects to Google but returns with an error.

### Pitfall 3: Internal OAuth User Type Restriction
**What goes wrong:** Non-Workspace users cannot log in (not relevant here since Glen IS the Workspace admin), BUT the OAuth consent screen may require the redirect domain to be an "Authorized domain" in the GCP project.
**Why it happens:** Google's OAuth consent screen for Internal apps may enforce that redirect URIs belong to verified domains.
**How to avoid:** Add the custom subdomain's parent domain (e.g., `agendsystems.com` or `iugo.com.au`) to the OAuth consent screen's "Authorized domains" list. Since Glen is the Workspace admin, no verification is needed for Internal apps.
**Warning signs:** "Access blocked" error during sign-in.

### Pitfall 4: Next.js Standalone Output in Subdirectory
**What goes wrong:** Build fails or `server.js` can't find static assets because the build context is wrong.
**Why it happens:** When `output: 'standalone'` is used with a subdirectory deployment, the standalone output path may be nested differently than expected.
**How to avoid:** The Dockerfile's `WORKDIR` and `COPY` commands must reference the `/dashboard` directory correctly. Set Coolify's "Base Directory" to `/dashboard` so it uses that as the build context. The Dockerfile lives inside `/dashboard`, not at repo root.
**Warning signs:** 404 errors on static assets, or `server.js` crashes on startup.

### Pitfall 5: File Write Permissions in Container
**What goes wrong:** Action queue writes fail because the container's Node process can't write to the bind-mounted directory.
**Why it happens:** The Dockerfile runs as `node` user (UID 1000) but the host directory may be owned by a different user.
**How to avoid:** Either: (a) ensure the `data/queue/` directory is writable by UID 1000 on the host, or (b) run the container with `--user` matching the host file owner. Coolify's "Custom Docker Run Options" field can set this.
**Warning signs:** "EACCES: permission denied" errors when clicking action buttons.

### Pitfall 6: AUTH_SECRET Not Set
**What goes wrong:** next-auth crashes on startup with "Missing AUTH_SECRET" error.
**Why it happens:** Forgot to add the secret to Coolify's environment variables.
**How to avoid:** Generate a secret with `openssl rand -base64 32` and add it as `AUTH_SECRET` in Coolify's environment variables for the application. Also set `NEXTAUTH_URL` to the production URL.
**Warning signs:** 500 error on any auth-related route.

## Code Examples

### Dockerfile for Subdirectory Deployment

```dockerfile
# dashboard/Dockerfile
# Based on official Next.js with-docker example
# Adapted for subdirectory deployment on Coolify

FROM node:22-slim AS dependencies
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

FROM node:22-slim AS builder
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder --chown=node:node /app/public ./public
RUN mkdir .next && chown node:node .next
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000
CMD ["node", "server.js"]
```

### next.config.ts

```typescript
// dashboard/next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  // No basePath needed -- app is at root of its subdomain
};

export default nextConfig;
```

### API Route: Data Reader

```typescript
// src/app/api/data/[type]/route.ts
import { NextResponse } from 'next/server';
import { auth } from '@/auth';
import { readNDJSON } from '@/lib/data';

const DATA_MAP: Record<string, string> = {
  feed: 'feed.jsonl',
  tasks: 'tasks/active.jsonl',
  triage: 'triage', // special: find latest file in directory
  todos: 'todos/active.jsonl',
  invoices: 'invoices/active.jsonl',
};

export async function GET(
  request: Request,
  { params }: { params: { type: string } }
) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const file = DATA_MAP[params.type];
  if (!file) return NextResponse.json({ error: 'Unknown type' }, { status: 400 });

  const data = params.type === 'triage'
    ? getLatestTriage()
    : readNDJSON(file);

  return NextResponse.json(data);
}
```

### API Route: Action Queue Writer

```typescript
// src/app/api/actions/route.ts
import { NextResponse } from 'next/server';
import { auth } from '@/auth';
import { queueAction } from '@/lib/queue';

export async function POST(request: Request) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const body = await request.json();
  const { action, target_id } = body;

  const validActions = ['mark-paid', 'complete-todo', 'complete-task', 'trigger-triage'];
  if (!validActions.includes(action)) {
    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  }

  const entry = queueAction({
    action,
    target_id: target_id || '',
    requested_by: session.user?.email || 'unknown',
  });

  return NextResponse.json({ queued: true, id: entry.id });
}
```

### Action Queue Schema

```json
{
  "id": "action-2026-03-24T10:30:00.000Z",
  "ts": "2026-03-24T10:30:00.000Z",
  "action": "mark-paid",
  "target_id": "inv-2026-03-23-001",
  "status": "queued",
  "requested_by": "glen@iugo.com.au"
}
```

After Claude processes:
```json
{
  "id": "action-2026-03-24T10:30:00.000Z",
  "ts": "2026-03-24T10:30:00.000Z",
  "action": "mark-paid",
  "target_id": "inv-2026-03-23-001",
  "status": "completed",
  "requested_by": "glen@iugo.com.au",
  "processed_at": "2026-03-24T10:45:00+10:30",
  "result": "Invoice inv-2026-03-23-001 marked as paid"
}
```

## Coolify Deployment Configuration

### Setup Steps

1. **Create Application** in Coolify: source = Git repo, branch = master
2. **Base Directory:** Set to `/dashboard` (Coolify clones the full repo but uses this as build context)
3. **Build Pack:** Dockerfile (auto-detects `dashboard/Dockerfile`)
4. **Port:** 3000
5. **Watch Paths:** `dashboard/**` (only redeploy on dashboard changes, not data changes)
6. **Persistent Storage (Bind Mount):**
   - Source: `/Users/glenr/work/todo-list/data` (absolute path on host)
   - Destination: `/data`
   - This gives the container read access to all NDJSON files AND write access to `data/queue/`
7. **Environment Variables:**
   - `AUTH_SECRET` = (generated secret)
   - `GOOGLE_CLIENT_ID` = (from existing GCP credentials)
   - `GOOGLE_CLIENT_SECRET` = (from existing GCP credentials)
   - `NEXTAUTH_URL` = `https://ops.agendsystems.com` (or chosen subdomain)
   - `DATA_DIR` = `/data`
8. **Domain:** Configure custom domain in Coolify (proxies to port 3000)

### Google OAuth Credential Reuse

Glen's existing Google Workspace OAuth credentials (used for hardened-workspace-mcp) CAN be reused. The same Client ID supports multiple redirect URIs. Steps:
1. Go to Google Cloud Console > APIs & Services > Credentials
2. Edit the existing OAuth 2.0 Client ID
3. Add to "Authorized redirect URIs":
   - `https://ops.agendsystems.com/api/auth/callback/google` (production)
   - `http://localhost:3000/api/auth/callback/google` (development)
4. Add to "Authorized JavaScript origins":
   - `https://ops.agendsystems.com`
   - `http://localhost:3000`
5. Save (may take 5 minutes to propagate)

**Alternatively**, create a separate OAuth client for the dashboard. This is cleaner (different scopes -- dashboard needs only `openid email profile`, not Gmail/Drive scopes) and prevents coupling. Recommended: create a new OAuth client for the dashboard.

### Coolify MCP Server

The `@masonator/coolify-mcp` package (v2.7.3) provides 38 tools for managing Coolify via Claude. Glen can use it to automate deployment setup, but it's NOT in the current Claude Desktop config. To use it:

```bash
claude mcp add coolify \
  -e COOLIFY_BASE_URL="http://localhost:8000" \
  -e COOLIFY_ACCESS_TOKEN="your-coolify-api-token" \
  -- npx @masonator/coolify-mcp@latest
```

However, the Coolify MCP is a convenience for automation, not a requirement. Manual Coolify UI setup is straightforward for a single application and may be faster for initial deployment.

## Design Token Migration

The existing UI-SPEC.md design tokens map to Tailwind configuration:

```typescript
// dashboard/tailwind.config.ts (relevant excerpt)
import type { Config } from 'tailwindcss';

export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: 'var(--surface)',
        'surface-secondary': 'var(--surface-secondary)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        border: 'var(--border)',
        accent: 'var(--accent)',
        destructive: 'var(--destructive)',
        priority: {
          urgent: '#EB5757',
          'needs-response': '#F2994A',
          informational: 'var(--accent)',
          low: '#9B9A97',
        },
        status: {
          pending: '#F2994A',
          completed: '#6FCF97',
          'in-progress': 'var(--accent)',
        },
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        '2xl': '48px',
      },
      fontSize: {
        sm: '13px',
        body: '15px',
        heading: '18px',
        display: '28px',
      },
    },
  },
} satisfies Config;
```

CSS custom properties for light/dark mode stay in `globals.css` (same values as current `index.html`). Tailwind's `dark:` variant maps to `prefers-color-scheme: dark`.

## Kanban Board: Custom Build, No Library

The dashboard Kanban is NOT a traditional drag-and-drop board. Cards are:
- Sorted by data (timestamps, priority) -- not user-reorderable
- Grouped into fixed columns by domain (Today, Emails, Tasks, Invoices, Activity)
- Interactive via action buttons, not drag handles

This means **no DnD library is needed**. The layout is a CSS Grid on desktop and tabs on mobile -- the same pattern as the current static dashboard, just with React components instead of vanilla JS.

```tsx
// Simplified KanbanBoard structure
<div className="hidden md:grid md:grid-cols-5 md:gap-lg">
  <Column title="Today" cards={todayCards} />
  <Column title="Emails" cards={emailCards} />
  <Column title="Tasks" cards={taskCards} />
  <Column title="Invoices" cards={invoiceCards} />
  <Column title="Activity" cards={activityCards} />
</div>
<div className="md:hidden">
  <MobileTabBar tabs={['Today','Emails','Tasks','Invoices','Activity']} />
  {/* Show active tab's cards */}
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| next-auth v4 (`getServerSession`) | Auth.js v5 (`auth()` universal function) | 2024+ | Single function works in server components, middleware, API routes, server actions |
| Pages Router data fetching | App Router server components + API routes | Next.js 13+ | Server components can use Node.js APIs directly; API routes for client polling |
| `next export` for static | `output: 'standalone'` for server | Next.js 12+ | Standalone creates minimal server.js -- ideal for Docker deployment |
| react-beautiful-dnd | @hello-pangea/dnd (community fork) or dnd-kit | 2024 | react-beautiful-dnd unmaintained. But NOT NEEDED here -- no drag-and-drop required |
| Tailwind v3 config file | Tailwind v4 CSS-first config | 2025 | v4 uses CSS `@theme` directive instead of JS config. Both approaches work. |

## Open Questions

1. **Exact host path for bind mount**
   - What we know: The repo is at `/Users/glenr/work/todo-list`, so data is at `/Users/glenr/work/todo-list/data`
   - What's unclear: Is Coolify running on the same Mac, or in a Docker context where paths differ?
   - Recommendation: Verify with `docker info` on the Coolify host. If Coolify runs in Docker-in-Docker, the host path may need to be an absolute path visible to the Docker daemon.

2. **Queue processing trigger**
   - What we know: Claude checks queue during triage or manual `/status` check
   - What's unclear: Should there be a dedicated `/process-queue` command, or should it be integrated into existing commands?
   - Recommendation: Add queue processing to both `/triage-inbox` (automatic) and create a new `/process-queue` command (manual). Also check queue in `/status` and display pending count.

3. **Subdomain DNS**
   - What we know: Glen wants ops.agendsystems.com or ops.iugo.com.au
   - What's unclear: Which domain, and whether DNS is managed via Cloudflare or another provider
   - Recommendation: Create an A record or CNAME pointing to the home server's IP. If behind Cloudflare, set DNS-only (grey cloud) to let Coolify handle TLS with Let's Encrypt.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Next.js build + runtime | Yes | 22.22.1 | -- |
| npm | Package installation | Yes | 10.9.4 | -- |
| Docker | Coolify deployment | Yes | 28.5.2 | -- |
| Coolify | Deployment platform | Yes (home server) | Unknown | Manual Docker deployment |
| Google OAuth credentials | Authentication | Yes (existing) | -- | Create new client |
| jq | Data build script (backward compat) | Yes | Unknown | -- |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Sources

### Primary (HIGH confidence)
- [Next.js Official Docs - Deploying](https://nextjs.org/docs/app/getting-started/deploying) - standalone output, Docker
- [Coolify Docs - Next.js](https://coolify.io/docs/applications/nextjs) - deployment configuration
- [Coolify Docs - Persistent Storage](https://coolify.io/docs/knowledge-base/persistent-storage) - bind mount configuration
- [Coolify Docs - Build Packs](https://coolify.io/docs/applications/build-packs/overview) - Dockerfile vs Nixpacks
- [Auth.js - Restricting User Access](https://authjs.dev/guides/restricting-user-access) - signIn callback pattern
- [Auth.js - Migration to v5](https://authjs.dev/getting-started/migrating-to-v5) - universal auth() function
- [Next.js Official Dockerfile](https://github.com/vercel/next.js/blob/canary/examples/with-docker/Dockerfile) - multi-stage build
- [SWR - Automatic Revalidation](https://swr.vercel.app/docs/revalidation) - refreshInterval polling
- npm registry - verified package versions (2026-03-24)

### Secondary (MEDIUM confidence)
- [StuMason/coolify-mcp](https://github.com/StuMason/coolify-mcp) - Coolify MCP server capabilities
- [Google OAuth Docs](https://developers.google.com/identity/protocols/oauth2/web-server) - redirect URI multi-app reuse
- [Coolify monorepo discussion](https://github.com/coollabsio/coolify/discussions/1898) - Base Directory feature
- [Coolify Dockerfile build pack](https://coolify.io/docs/applications/build-packs/dockerfile) - custom Dockerfile support

### Tertiary (LOW confidence)
- Auth.js v5 stable release timeline - still in beta, no GA date announced. Beta is production-stable per community consensus.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages verified against npm registry, Next.js + Auth.js v5 + Tailwind is a well-established combination
- Architecture: HIGH - Server-side file reading in Next.js is well-documented; Coolify bind mounts are a standard Docker feature
- Coolify subdirectory deployment: MEDIUM - Base Directory feature confirmed in docs and discussions, but specific interaction with Dockerfile build pack in a non-monorepo-tool repo needs validation during implementation
- Pitfalls: HIGH - Each pitfall is derived from official docs or common issues in GitHub discussions
- Action queue pattern: MEDIUM - Custom design (no library), but the pattern is simple append-only NDJSON consistent with the project's existing data conventions

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (30 days - stable domain, no rapid-moving dependencies)
