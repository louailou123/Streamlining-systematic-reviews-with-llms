import React from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from '../../lib/cn';

interface AppLogoProps {
  compact?: boolean;
  className?: string;
  subtitle?: string;
}

const AppLogo: React.FC<AppLogoProps> = ({ compact = false, className, subtitle }) => {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div
        className={cn(
          'flex items-center justify-center rounded-2xl bg-gradient-to-br from-accent-blue via-accent-cyan to-accent-green shadow-lg shadow-accent-blue/20',
          compact ? 'h-10 w-10' : 'h-12 w-12',
        )}
      >
        <Sparkles className={cn('text-white', compact ? 'h-5 w-5' : 'h-6 w-6')} />
      </div>

      <div className="min-w-0">
        <div className={cn('font-semibold tracking-tight text-white', compact ? 'text-lg' : 'text-2xl')}>
          LiRA
        </div>
        {subtitle && <div className="text-xs uppercase tracking-[0.18em] text-gray-500">{subtitle}</div>}
      </div>
    </div>
  );
};

export default AppLogo;
