'use client';

import { useState, useCallback } from 'react';
import clsx from 'clsx';

type ActionType = 'mark-paid' | 'complete-todo' | 'complete-task' | 'trigger-triage';
type ButtonState = 'idle' | 'loading' | 'queued' | 'error';
type Variant = 'primary' | 'danger' | 'ghost';

interface ActionButtonProps {
  action: ActionType;
  targetId: string;
  label: string;
  icon?: string;
  variant?: Variant;
}

export function ActionButton({
  action,
  targetId,
  label,
  icon,
  variant = 'primary',
}: ActionButtonProps) {
  const [state, setState] = useState<ButtonState>('idle');

  const handleClick = useCallback(async () => {
    if (state !== 'idle') return;
    setState('loading');

    try {
      const res = await fetch('/api/actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, target_id: targetId }),
      });

      if (!res.ok) throw new Error('Action failed');

      setState('queued');
      // Persist queued IDs in sessionStorage so badge survives re-renders
      const queued = JSON.parse(sessionStorage.getItem('queuedActions') || '[]');
      if (!queued.includes(targetId)) queued.push(targetId);
      sessionStorage.setItem('queuedActions', JSON.stringify(queued));
      // Dispatch event so cards can react
      window.dispatchEvent(new CustomEvent('action-queued', { detail: { targetId, action } }));
    } catch {
      setState('error');
      setTimeout(() => setState('idle'), 3000);
    }
  }, [action, targetId, state]);

  const baseClasses =
    'inline-flex items-center justify-center gap-1 rounded px-3 py-1.5 text-[length:var(--text-sm)] font-semibold transition-opacity cursor-pointer';
  const minTouch = { minHeight: '44px', minWidth: '44px' };

  const variantClasses: Record<Variant, string> = {
    primary: 'bg-accent text-white hover:opacity-90',
    danger: 'bg-destructive text-white hover:opacity-90',
    ghost:
      'border border-border-default bg-transparent text-text-primary hover:bg-surface-secondary',
  };

  if (state === 'loading') {
    return (
      <button
        disabled
        className={clsx(baseClasses, 'opacity-60 cursor-not-allowed bg-surface-secondary text-text-secondary')}
        style={minTouch}
      >
        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
        <span>{label}</span>
      </button>
    );
  }

  if (state === 'queued') {
    return (
      <button
        disabled
        className={clsx(baseClasses, 'bg-status-completed text-white cursor-default')}
        style={minTouch}
      >
        <span>{'\u2713'}</span>
        <span>Queued</span>
      </button>
    );
  }

  if (state === 'error') {
    return (
      <button
        disabled
        className={clsx(baseClasses, 'bg-destructive text-white cursor-default')}
        style={minTouch}
      >
        <span>Failed</span>
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      className={clsx(baseClasses, variantClasses[variant])}
      style={minTouch}
    >
      {icon && <span>{icon}</span>}
      <span>{label}</span>
    </button>
  );
}
