import React from 'react';
import { cn } from '../../lib/cn';

interface StatusBadgeProps {
  status: string | null | undefined;
  className?: string;
}

const STATUS_MAP: Record<string, { label: string; className: string; dotClassName: string }> = {
  running: {
    label: 'Running',
    className: 'border-accent-blue/25 bg-accent-blue/10 text-accent-blue-light',
    dotClassName: 'bg-accent-blue shadow-[0_0_0_4px_rgba(99,102,241,0.14)]',
  },
  completed: {
    label: 'Completed',
    className: 'border-accent-green/25 bg-accent-green/10 text-accent-green',
    dotClassName: 'bg-accent-green shadow-[0_0_0_4px_rgba(34,197,94,0.12)]',
  },
  approved: {
    label: 'Approved',
    className: 'border-accent-green/25 bg-accent-green/10 text-accent-green',
    dotClassName: 'bg-accent-green shadow-[0_0_0_4px_rgba(34,197,94,0.12)]',
  },
  failed: {
    label: 'Failed',
    className: 'border-accent-rose/25 bg-accent-rose/10 text-accent-rose',
    dotClassName: 'bg-accent-rose shadow-[0_0_0_4px_rgba(244,63,94,0.12)]',
  },
  paused: {
    label: 'Needs review',
    className: 'border-accent-amber/25 bg-accent-amber/10 text-accent-amber',
    dotClassName: 'bg-accent-amber shadow-[0_0_0_4px_rgba(245,158,11,0.12)]',
  },
  pending: {
    label: 'Pending',
    className: 'border-white/10 bg-white/5 text-gray-300',
    dotClassName: 'bg-gray-500 shadow-[0_0_0_4px_rgba(107,114,128,0.12)]',
  },
};

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className }) => {
  const normalizedStatus = (status || 'pending').toLowerCase();
  const style = STATUS_MAP[normalizedStatus] ?? STATUS_MAP.pending;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]',
        style.className,
        className,
      )}
    >
      <span className={cn('h-2 w-2 rounded-full', style.dotClassName)} />
      {style.label}
    </span>
  );
};

export default StatusBadge;
