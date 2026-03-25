'use client';

import { useState, useEffect } from 'react';

interface QueuedBadgeProps {
  targetId: string;
}

export function QueuedBadge({ targetId }: QueuedBadgeProps) {
  const [isQueued, setIsQueued] = useState(false);

  useEffect(() => {
    // Check sessionStorage on mount
    const queued = JSON.parse(sessionStorage.getItem('queuedActions') || '[]');
    setIsQueued(queued.includes(targetId));

    // Listen for new queue events
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail.targetId === targetId) setIsQueued(true);
    };
    window.addEventListener('action-queued', handler);
    return () => window.removeEventListener('action-queued', handler);
  }, [targetId]);

  if (!isQueued) return null;

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
      Queued
    </span>
  );
}
