import React from 'react';
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from 'lucide-react';
import { cn } from '../../lib/cn';

type StateTone = 'default' | 'error' | 'success' | 'warning';

interface StatePanelProps {
  title: string;
  description: string;
  tone?: StateTone;
  action?: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}

const TONE_STYLES: Record<StateTone, string> = {
  default: 'border-white/10 bg-white/[0.03]',
  error: 'border-accent-rose/25 bg-accent-rose/8',
  success: 'border-accent-green/20 bg-accent-green/8',
  warning: 'border-accent-amber/20 bg-accent-amber/8',
};

const TONE_ICONS: Record<StateTone, React.ReactNode> = {
  default: <Info className="h-5 w-5 text-accent-blue-light" />,
  error: <AlertCircle className="h-5 w-5 text-accent-rose" />,
  success: <CheckCircle2 className="h-5 w-5 text-accent-green" />,
  warning: <TriangleAlert className="h-5 w-5 text-accent-amber" />,
};

const StatePanel: React.FC<StatePanelProps> = ({
  title,
  description,
  tone = 'default',
  action,
  className,
  icon,
}) => {
  return (
    <div className={cn('state-panel', TONE_STYLES[tone], className)}>
      <div className="flex items-start gap-4">
        <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-dark-surface-2">
          {icon ?? TONE_ICONS[tone]}
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-white">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-gray-400">{description}</p>
          {action && <div className="mt-4">{action}</div>}
        </div>
      </div>
    </div>
  );
};

export default StatePanel;
