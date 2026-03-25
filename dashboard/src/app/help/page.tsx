import { auth } from '@/auth';
import { redirect } from 'next/navigation';

const commands = [
  {
    name: '/triage-inbox',
    description: 'Scan Gmail inbox and categorize emails',
    details: 'Scans last 24 hours, categorizes into urgent/needs-response/informational/low-priority. Drafts replies for urgent + client emails. Detects action items (contracts, invoices, meetings, deadlines). Auto-queues tasks and invoice reminders.',
    examples: ['/triage-inbox'],
  },
  {
    name: '/task',
    description: 'Delegate work to Claude',
    details: 'Natural language task kickoff. Claude retrieves documents from Gmail/Drive, analyzes them, produces executive summaries, and creates Gmail drafts.',
    examples: [
      '/task — show pending queue',
      '/task review the contract Sarah sent',
      '/task run task-2026-03-23-001',
      '/task list — show all tasks',
    ],
  },
  {
    name: '/todo',
    description: 'Personal to-do management',
    details: 'Track personal action items with priorities, due dates, categories, and recurring support. Separate from Claude tasks — these are things YOU need to do.',
    examples: [
      '/todo — show active to-dos',
      '/todo book flight to Sydney by Friday !high #business',
      '/todo done 3 — complete by number',
      '/todo done book flight — complete by text match',
      '/todo priority 2 high — change priority',
      '/todo #marketing — filter by category',
    ],
  },
  {
    name: '/invoice',
    description: 'Invoice tracking and management',
    details: 'Track invoices through their lifecycle (draft → sent → paid). Syncs with Xero. Triage auto-detects invoice emails and creates reminders. Overdue invoices highlighted automatically.',
    examples: [
      '/invoice — show outstanding',
      '/invoice create Acme Corp March retainer $5000 PROP-0324',
      '/invoice overdue — show overdue only',
      '/invoice mark-paid INV-001',
      '/invoice sync — pull from Xero',
      '/invoice list — show all',
    ],
  },
  {
    name: '/daily-briefing',
    description: 'Morning summary of everything',
    details: 'Generates a briefing with four sections: email summary (counts by bucket), pending tasks, your to-dos, key deadlines (next 48 hours), and yesterday recap. Auto-generated on first triage of the day.',
    examples: ['/daily-briefing'],
  },
  {
    name: '/status',
    description: 'Quick overview',
    details: 'Shows recent activity count, triage runs, pending tasks, dashboard queue status, and top pending items at a glance.',
    examples: ['/status'],
  },
  {
    name: '/feed',
    description: 'Activity log',
    details: 'Shows recent activity feed entries — what Claude did, when, and why.',
    examples: ['/feed', '/feed 20 — show last 20 entries'],
  },
  {
    name: '/process-queue',
    description: 'Execute dashboard actions',
    details: 'Processes pending actions queued from this dashboard (mark-paid, complete-todo, complete-task, trigger-triage). Run after tapping action buttons here.',
    examples: ['/process-queue'],
  },
];

const workflows = [
  {
    title: 'Morning Routine',
    steps: [
      'Check ops.agend.info on your phone for the overnight briefing',
      'Review starred emails and urgent items',
      'Tap action buttons on any items that need attention',
      'Run /process-queue in Claude Code to execute queued actions',
    ],
  },
  {
    title: 'During the Day',
    steps: [
      'Claude Desktop runs /triage-inbox every 2 hours automatically',
      'Check dashboard for new items between triage runs',
      'Use /task for ad-hoc work (review contracts, prep meetings)',
      'Use /todo to track personal action items',
    ],
  },
  {
    title: 'Invoicing',
    steps: [
      'Triage auto-detects invoice emails and creates reminders',
      'Run /invoice sync to pull latest from Xero',
      'Check dashboard Invoices tab for overdue items',
      'Use /invoice mark-paid after payment received',
    ],
  },
];

export default async function HelpPage() {
  const session = await auth();
  if (!session) redirect('/login');

  return (
    <main className="min-h-screen bg-surface px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <header className="mb-8">
          <a
            href="/"
            className="mb-4 inline-block text-sm text-text-secondary hover:text-accent"
          >
            ← Back to Dashboard
          </a>
          <h1 className="text-display font-semibold text-text-primary">
            Agend Ops Guide
          </h1>
          <p className="mt-2 text-body text-text-secondary">
            Quick reference for all commands and workflows.
          </p>
        </header>

        {/* Daily Workflows */}
        <section className="mb-10">
          <h2 className="mb-4 border-b border-border-default pb-2 text-heading font-semibold text-text-primary">
            Daily Workflows
          </h2>
          <div className="space-y-4">
            {workflows.map((wf) => (
              <div
                key={wf.title}
                className="rounded-lg border border-border-default bg-surface-secondary p-4"
              >
                <h3 className="mb-3 font-semibold text-text-primary">
                  {wf.title}
                </h3>
                <ol className="list-inside list-decimal space-y-1.5 text-sm text-text-secondary">
                  {wf.steps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </section>

        {/* Commands Reference */}
        <section className="mb-10">
          <h2 className="mb-4 border-b border-border-default pb-2 text-heading font-semibold text-text-primary">
            Commands Reference
          </h2>
          <p className="mb-4 text-sm text-text-secondary">
            All commands run in Claude Code (terminal).
          </p>
          <div className="space-y-4">
            {commands.map((cmd) => (
              <div
                key={cmd.name}
                className="rounded-lg border border-border-default bg-surface-secondary p-4"
              >
                <div className="mb-1 flex items-baseline gap-3">
                  <code className="font-mono text-sm font-semibold text-accent">
                    {cmd.name}
                  </code>
                  <span className="text-sm text-text-secondary">
                    {cmd.description}
                  </span>
                </div>
                <p className="mb-3 text-sm text-text-secondary">
                  {cmd.details}
                </p>
                <div className="space-y-1">
                  {cmd.examples.map((ex, i) => (
                    <code
                      key={i}
                      className="block rounded bg-surface px-2 py-1 font-mono text-xs text-text-primary"
                    >
                      {ex}
                    </code>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Dashboard Actions */}
        <section className="mb-10">
          <h2 className="mb-4 border-b border-border-default pb-2 text-heading font-semibold text-text-primary">
            Dashboard Actions
          </h2>
          <p className="mb-4 text-sm text-text-secondary">
            Actions you can take directly from this dashboard:
          </p>
          <div className="rounded-lg border border-border-default bg-surface-secondary p-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-default text-left text-text-secondary">
                  <th className="pb-2 pr-4">Action</th>
                  <th className="pb-2 pr-4">Card Type</th>
                  <th className="pb-2">What Happens</th>
                </tr>
              </thead>
              <tbody className="text-text-primary">
                <tr className="border-b border-border-default">
                  <td className="py-2 pr-4 font-medium">Mark Paid</td>
                  <td className="py-2 pr-4">Invoice</td>
                  <td className="py-2">
                    Queued → run /process-queue to update status
                  </td>
                </tr>
                <tr className="border-b border-border-default">
                  <td className="py-2 pr-4 font-medium">Complete</td>
                  <td className="py-2 pr-4">Todo</td>
                  <td className="py-2">
                    Queued → run /process-queue to mark done
                  </td>
                </tr>
                <tr className="border-b border-border-default">
                  <td className="py-2 pr-4 font-medium">Complete</td>
                  <td className="py-2 pr-4">Task</td>
                  <td className="py-2">
                    Queued → run /process-queue to mark done
                  </td>
                </tr>
                <tr className="border-b border-border-default">
                  <td className="py-2 pr-4 font-medium">View Draft</td>
                  <td className="py-2 pr-4">Email</td>
                  <td className="py-2">Opens Gmail draft directly</td>
                </tr>
                <tr className="border-b border-border-default">
                  <td className="py-2 pr-4 font-medium">Open Email</td>
                  <td className="py-2 pr-4">Email / Invoice</td>
                  <td className="py-2">Opens email thread in Gmail</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-medium">Trigger Triage</td>
                  <td className="py-2 pr-4">Global</td>
                  <td className="py-2">
                    Queued → run /process-queue to start triage
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Architecture */}
        <section className="mb-10">
          <h2 className="mb-4 border-b border-border-default pb-2 text-heading font-semibold text-text-primary">
            How It Works
          </h2>
          <div className="space-y-3 text-sm text-text-secondary">
            <p>
              <strong className="text-text-primary">Data:</strong> All data
              lives as NDJSON files in a git repo. Git history is the audit
              trail. Claude is the primary writer.
            </p>
            <p>
              <strong className="text-text-primary">Dashboard:</strong> This
              Next.js app reads data files directly from disk (bind-mounted).
              Polls every 30 seconds for updates.
            </p>
            <p>
              <strong className="text-text-primary">Actions:</strong> When you
              tap an action button, it writes to a queue file. Claude processes
              the queue via /process-queue — keeping Claude as the single writer
              to data files.
            </p>
            <p>
              <strong className="text-text-primary">Scheduling:</strong> Claude
              Desktop runs /triage-inbox every 2 hours on weekdays (ACST).
              Morning runs also generate a daily briefing.
            </p>
            <p>
              <strong className="text-text-primary">Security:</strong> Gmail
              access uses a hardened MCP server that cannot send emails — only
              read and create drafts. You review and send from Gmail.
            </p>
          </div>
        </section>

        <footer className="border-t border-border-default pt-4 text-center text-xs text-text-secondary">
          Agend Ops v2.0 — Built with Claude
        </footer>
      </div>
    </main>
  );
}
