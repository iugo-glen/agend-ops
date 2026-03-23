'use client';

import clsx from 'clsx';

export type TabName = 'today' | 'emails' | 'tasks' | 'invoices' | 'activity';

interface MobileTabBarProps {
  activeTab: TabName;
  onTabChange: (tab: TabName) => void;
  counts: Record<TabName, number>;
}

const TABS: { id: TabName; label: string }[] = [
  { id: 'today', label: 'Today' },
  { id: 'emails', label: 'Emails' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'invoices', label: 'Invoices' },
  { id: 'activity', label: 'Activity' },
];

export function MobileTabBar({ activeTab, onTabChange, counts }: MobileTabBarProps) {
  return (
    <nav
      className="sticky top-[48px] z-10 flex overflow-x-auto bg-surface md:hidden"
      role="tablist"
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={`panel-${tab.id}`}
          onClick={() => onTabChange(tab.id)}
          className={clsx(
            'flex shrink-0 items-center gap-1 px-4 py-2 text-[length:var(--text-sm)] font-semibold transition-colors cursor-pointer',
            activeTab === tab.id
              ? 'border-b-2 border-accent text-text-primary'
              : 'border-b-2 border-transparent text-text-secondary'
          )}
          style={{ minHeight: '44px' }}
        >
          <span>{tab.label}</span>
          {counts[tab.id] > 0 && (
            <span className="rounded bg-accent px-1.5 py-0.5 text-[11px] font-semibold leading-none text-white">
              {counts[tab.id]}
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}
