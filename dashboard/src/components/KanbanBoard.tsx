'use client';

import { useState, useMemo } from 'react';
import { useFeed, useTriage, useTasks, useTodos, useInvoices } from '@/hooks/useData';
import { Header } from '@/components/Header';
import { SummaryBar } from '@/components/SummaryBar';
import { MobileTabBar, type TabName } from '@/components/MobileTabBar';
import { Column } from '@/components/Column';
import { EmailCard } from '@/components/cards/EmailCard';
import { TaskCard } from '@/components/cards/TaskCard';
import { TodoCard } from '@/components/cards/TodoCard';
import { InvoiceCard } from '@/components/cards/InvoiceCard';
import { ActivityCard } from '@/components/cards/ActivityCard';
import { ActionButton } from '@/components/ActionButton';
import type {
  TriageRecord,
  TaskRecord,
  TodoRecord,
  InvoiceRecord,
} from '@/lib/types';

function sortByPriority(a: TodoRecord, b: TodoRecord): number {
  const order: Record<string, number> = { high: 0, normal: 1, low: 2 };
  const pa = order[a.priority] ?? 1;
  const pb = order[b.priority] ?? 1;
  if (pa !== pb) return pa - pb;
  // Then by due_date (nulls last)
  if (a.due_date && b.due_date) return a.due_date.localeCompare(b.due_date);
  if (a.due_date) return -1;
  if (b.due_date) return 1;
  return 0;
}

function sortTriageByPriority(records: TriageRecord[]): TriageRecord[] {
  const order: Record<string, number> = {
    urgent: 0,
    'needs-response': 1,
    informational: 2,
    'low-priority': 3,
  };
  return [...records].sort((a, b) => {
    // Starred first
    if (a.starred && !b.starred) return -1;
    if (!a.starred && b.starred) return 1;
    // Then by priority
    const pa = order[a.priority] ?? 2;
    const pb = order[b.priority] ?? 2;
    if (pa !== pb) return pa - pb;
    // Then newest first
    return b.received.localeCompare(a.received);
  });
}

function sortTasksByDate(records: TaskRecord[]): TaskRecord[] {
  return [...records].sort((a, b) => b.ts.localeCompare(a.ts));
}

function sortInvoicesByDueDate(records: InvoiceRecord[]): InvoiceRecord[] {
  return [...records].sort((a, b) => {
    if (a.due_date && b.due_date) return a.due_date.localeCompare(b.due_date);
    if (a.due_date) return -1;
    if (b.due_date) return 1;
    return 0;
  });
}

export function KanbanBoard() {
  const [activeTab, setActiveTab] = useState<TabName>('today');

  const { data: feed = [], error: feedError, isLoading: feedLoading } = useFeed();
  const { data: triage = [], error: triageError, isLoading: triageLoading } = useTriage();
  const { data: tasks = [], error: tasksError, isLoading: tasksLoading } = useTasks();
  const { data: todos = [], error: todosError, isLoading: todosLoading } = useTodos();
  const { data: invoices = [], error: invoicesError, isLoading: invoicesLoading } = useInvoices();

  // Computed data for columns
  const todayTodos = useMemo(
    () => todos.filter((t) => t.status === 'active').sort(sortByPriority),
    [todos]
  );
  const todayTasks = useMemo(
    () =>
      tasks
        .filter((t) => t.status === 'pending' || t.status === 'in-progress')
        .sort((a, b) => b.ts.localeCompare(a.ts)),
    [tasks]
  );
  const sortedTriage = useMemo(() => sortTriageByPriority(triage), [triage]);
  const pendingTasks = useMemo(
    () => sortTasksByDate(tasks.filter((t) => t.status === 'pending' || t.status === 'in-progress')),
    [tasks]
  );
  const activeInvoices = useMemo(
    () =>
      sortInvoicesByDueDate(
        invoices.filter((i) => i.status !== 'paid' && i.status !== 'written-off')
      ),
    [invoices]
  );
  const recentFeed = useMemo(() => feed.slice(0, 20), [feed]);

  // Last updated from most recent feed entry
  const lastUpdated = feed.length > 0 ? feed[0].ts : null;

  // Tab counts for badge display
  const tabCounts: Record<TabName, number> = {
    today: todayTodos.length + todayTasks.length,
    emails: triage.length,
    tasks: pendingTasks.length,
    invoices: activeInvoices.length,
    activity: recentFeed.length,
  };

  // Loading state check
  const isAnyLoading = feedLoading || triageLoading || tasksLoading || todosLoading || invoicesLoading;

  // Render cards for a specific column/tab
  function renderTodayCards() {
    if (todosLoading || tasksLoading) return <LoadingMessage />;
    if (todosError && tasksError) return <ErrorMessage />;
    const items = todayTodos.length + todayTasks.length;
    if (items === 0) return <EmptyMessage text="All clear for today!" />;
    return (
      <>
        {todayTodos.length > 0 && (
          <>
            <h3 className="text-[length:var(--text-sm)] font-semibold uppercase tracking-wide text-text-secondary">
              Your To-Dos
            </h3>
            {todayTodos.map((todo) => (
              <TodoCard key={todo.id} record={todo} />
            ))}
          </>
        )}
        {todayTasks.length > 0 && (
          <>
            <h3 className="mt-2 text-[length:var(--text-sm)] font-semibold uppercase tracking-wide text-text-secondary">
              Claude Tasks
            </h3>
            {todayTasks.map((task) => (
              <TaskCard key={task.id} record={task} />
            ))}
          </>
        )}
      </>
    );
  }

  function renderEmailCards() {
    if (triageLoading) return <LoadingMessage />;
    if (triageError) return <ErrorMessage />;
    if (triage.length === 0) return <EmptyMessage text="No emails to show. Inbox zero!" />;
    return (
      <>
        <div className="mb-2">
          <ActionButton
            action="trigger-triage"
            targetId="inbox"
            label="Trigger Triage"
            icon={'\u{1F4E5}'}
            variant="ghost"
          />
        </div>
        {sortedTriage.map((record) => (
          <EmailCard key={record.message_id} record={record} />
        ))}
      </>
    );
  }

  function renderTaskCards() {
    if (tasksLoading) return <LoadingMessage />;
    if (tasksError) return <ErrorMessage />;
    if (pendingTasks.length === 0) return <EmptyMessage text="No pending tasks." />;
    return pendingTasks.map((task) => (
      <TaskCard key={task.id} record={task} />
    ));
  }

  function renderInvoiceCards() {
    if (invoicesLoading) return <LoadingMessage />;
    if (invoicesError) return <ErrorMessage />;
    if (activeInvoices.length === 0) return <EmptyMessage text="All invoices settled." />;
    return activeInvoices.map((inv) => (
      <InvoiceCard key={inv.id} record={inv} />
    ));
  }

  function renderActivityCards() {
    if (feedLoading) return <LoadingMessage />;
    if (feedError) return <ErrorMessage />;
    if (recentFeed.length === 0)
      return <EmptyMessage text="No activity recorded yet. Run /triage-inbox to get started." />;
    return recentFeed.map((entry, i) => (
      <ActivityCard key={`${entry.ts}-${i}`} record={entry} />
    ));
  }

  // Active tab content for mobile
  const TAB_RENDERERS: Record<TabName, () => React.ReactNode> = {
    today: renderTodayCards,
    emails: renderEmailCards,
    tasks: renderTaskCards,
    invoices: renderInvoiceCards,
    activity: renderActivityCards,
  };

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <Header lastUpdated={lastUpdated} />
      <SummaryBar
        triage={triage}
        tasks={tasks}
        todos={todos}
        invoices={invoices}
      />
      <MobileTabBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        counts={tabCounts}
      />

      {/* Mobile: single column for active tab */}
      <div className="flex flex-col gap-2 p-4 md:hidden" role="tabpanel" id={`panel-${activeTab}`}>
        {isAnyLoading && activeTab === 'today' ? <LoadingMessage /> : TAB_RENDERERS[activeTab]()}
      </div>

      {/* Desktop: 5-column Kanban grid */}
      <div className="mx-auto hidden w-full max-w-[1400px] gap-4 p-4 md:grid md:grid-cols-5 md:px-8">
        <Column title="Today" count={todayTodos.length + todayTasks.length} emptyMessage="All clear for today!">
          {renderTodayCards()}
        </Column>
        <Column title="Emails" count={triage.length} emptyMessage="No emails to show. Inbox zero!">
          {renderEmailCards()}
        </Column>
        <Column title="Tasks" count={pendingTasks.length} emptyMessage="No pending tasks.">
          {renderTaskCards()}
        </Column>
        <Column title="Invoices" count={activeInvoices.length} emptyMessage="All invoices settled.">
          {renderInvoiceCards()}
        </Column>
        <Column title="Activity" count={recentFeed.length} emptyMessage="No activity recorded yet. Run /triage-inbox to get started.">
          {renderActivityCards()}
        </Column>
      </div>
    </div>
  );
}

function LoadingMessage() {
  return (
    <p className="py-4 text-center text-[length:var(--text-body)] text-text-secondary">
      Loading...
    </p>
  );
}

function ErrorMessage() {
  return (
    <p className="py-4 text-center text-[length:var(--text-body)] text-destructive">
      {"Couldn't load data. Try refreshing."}
    </p>
  );
}

function EmptyMessage({ text }: { text: string }) {
  return (
    <p className="py-8 text-center text-[length:var(--text-body)] text-text-secondary">
      {text}
    </p>
  );
}
