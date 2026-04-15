import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/cn';

type MetricTone = 'default' | 'blue' | 'green' | 'amber' | 'rose';

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  description?: string;
  tone?: MetricTone;
  className?: string;
}

const TONE_STYLES: Record<MetricTone, { icon: string; glow: string }> = {
  default: { icon: 'text-gray-200', glow: 'from-white/8 to-white/0' },
  blue: { icon: 'text-accent-blue-light', glow: 'from-accent-blue/18 to-transparent' },
  green: { icon: 'text-accent-green', glow: 'from-accent-green/18 to-transparent' },
  amber: { icon: 'text-accent-amber', glow: 'from-accent-amber/18 to-transparent' },
  rose: { icon: 'text-accent-rose', glow: 'from-accent-rose/18 to-transparent' },
};

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon: Icon,
  description,
  tone = 'default',
  className,
}) => {
  const toneStyle = TONE_STYLES[tone];

  return (
    <div className={cn('stat-card relative overflow-hidden', className)}>
      <div className={cn('absolute inset-x-0 top-0 h-px bg-gradient-to-r opacity-80', toneStyle.glow)} />
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">{label}</div>
          <div className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</div>
          {description && <div className="mt-2 text-sm leading-6 text-gray-400">{description}</div>}
        </div>

        <div className="rounded-2xl border border-white/10 bg-dark-surface-2 p-3">
          <Icon className={cn('h-5 w-5', toneStyle.icon)} />
        </div>
      </div>
    </div>
  );
};

export default MetricCard;
