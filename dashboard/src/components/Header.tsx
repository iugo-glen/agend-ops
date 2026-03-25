'use client';

import { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { signOut } from 'next-auth/react';

interface HeaderProps {
  lastUpdated: string | null;
}

export function Header({ lastUpdated }: HeaderProps) {
  const [queueCount, setQueueCount] = useState(0);
  const relativeTime = lastUpdated
    ? formatDistanceToNow(new Date(lastUpdated), { addSuffix: true })
    : null;

  useEffect(() => {
    // Read initial count from sessionStorage
    const queued = JSON.parse(sessionStorage.getItem('queuedActions') || '[]');
    setQueueCount(queued.length);

    // Listen for new queue events
    const handler = () => {
      const updated = JSON.parse(sessionStorage.getItem('queuedActions') || '[]');
      setQueueCount(updated.length);
    };
    window.addEventListener('action-queued', handler);
    return () => window.removeEventListener('action-queued', handler);
  }, []);

  return (
    <header
      className="sticky top-0 z-10 flex items-center justify-between border-b border-border-default bg-surface px-4 md:static md:px-8"
      style={{ minHeight: '48px' }}
    >
      <div className="flex items-center gap-3">
        <h1 className="text-[length:var(--text-heading)] font-semibold text-text-primary">
          Agend Ops
        </h1>
        {queueCount > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
            {queueCount} queued
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {relativeTime && (
          <span className="text-[length:var(--text-sm)] text-accent">
            Last updated: {relativeTime}
          </span>
        )}
        <a
          href="/help"
          className="rounded border border-border-default bg-transparent px-2 py-1 text-[length:var(--text-sm)] text-text-secondary transition-opacity hover:opacity-80"
          style={{ minHeight: '32px', display: 'inline-flex', alignItems: 'center' }}
        >
          Guide
        </a>
        <button
          onClick={() => signOut({ callbackUrl: '/login' })}
          className="rounded border border-border-default bg-transparent px-2 py-1 text-[length:var(--text-sm)] text-text-secondary transition-opacity hover:opacity-80 cursor-pointer"
          style={{ minHeight: '32px' }}
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
