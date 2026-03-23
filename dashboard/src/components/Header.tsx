'use client';

import { formatDistanceToNow } from 'date-fns';
import { signOut } from 'next-auth/react';

interface HeaderProps {
  lastUpdated: string | null;
}

export function Header({ lastUpdated }: HeaderProps) {
  const relativeTime = lastUpdated
    ? formatDistanceToNow(new Date(lastUpdated), { addSuffix: true })
    : null;

  return (
    <header
      className="sticky top-0 z-10 flex items-center justify-between border-b border-border-default bg-surface px-4 md:static md:px-8"
      style={{ minHeight: '48px' }}
    >
      <h1 className="text-[length:var(--text-heading)] font-semibold text-text-primary">
        Agend Ops
      </h1>
      <div className="flex items-center gap-3">
        {relativeTime && (
          <span className="text-[length:var(--text-sm)] text-accent">
            Last updated: {relativeTime}
          </span>
        )}
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
