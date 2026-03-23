import type { ReactNode } from 'react';

interface ColumnProps {
  title: string;
  count: number;
  children: ReactNode;
  emptyMessage?: string;
}

export function Column({ title, count, children, emptyMessage }: ColumnProps) {
  return (
    <section className="hidden rounded-lg bg-surface-secondary p-4 md:block" style={{ minHeight: '200px' }}>
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-[length:var(--text-heading)] font-semibold text-text-primary">
          {title}
        </h2>
        <span className="rounded bg-accent px-1.5 py-0.5 text-[length:var(--text-sm)] font-semibold leading-none text-white">
          {count}
        </span>
      </div>

      {/* Cards */}
      <div
        className="flex flex-col gap-2 overflow-y-auto"
        style={{ maxHeight: 'calc(100vh - 200px)' }}
      >
        {count === 0 && emptyMessage ? (
          <p className="py-8 text-center text-[length:var(--text-body)] text-text-secondary">
            {emptyMessage}
          </p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}
