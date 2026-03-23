'use client';

import { formatDistanceToNow } from 'date-fns';
import type { FeedEntry } from '@/lib/types';

interface ActivityCardProps {
  record: FeedEntry;
}

const TYPE_ICONS: Record<string, string> = {
  triage: '\u{1F4E5}',   // inbox
  task: '\u2713',          // check
  draft: '\u270F',         // pencil
  system: '\u2699',        // gear
  briefing: '\u2600',      // sun
  todo: '\u2611',          // checkbox
  command: '\u276F',       // right angle bracket
};

export function ActivityCard({ record }: ActivityCardProps) {
  const icon = TYPE_ICONS[record.type] || '\u2022';
  const relativeTime = formatDistanceToNow(new Date(record.ts), {
    addSuffix: true,
  });

  return (
    <div className="rounded-lg border border-border-default bg-surface px-3 py-2">
      {/* Line 1: Type icon + summary */}
      <div className="flex items-start gap-2">
        <span className="shrink-0">{icon}</span>
        <p className="text-[length:var(--text-body)] text-text-primary">
          {record.summary}
        </p>
      </div>

      {/* Line 2: Timestamp + duration */}
      <div className="mt-0.5 flex items-center gap-2 pl-6">
        <span className="text-[length:var(--text-sm)] text-text-secondary">
          {relativeTime}
        </span>
        {record.duration_ms != null && (
          <span className="text-[length:var(--text-sm)] text-text-secondary">
            ({(record.duration_ms / 1000).toFixed(1)}s)
          </span>
        )}
      </div>
    </div>
  );
}
