import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, LayoutGrid, LogOut, Workflow } from 'lucide-react';
import type { User } from '../../api/auth';
import AppLogo from '../ui/AppLogo';
import { cn } from '../../lib/cn';

interface AppShellProps {
  currentView: 'dashboard' | 'workspace';
  title: string;
  description?: string;
  eyebrow?: string;
  user: User | null;
  onLogout: () => void;
  actions?: React.ReactNode;
  backLink?: {
    to: string;
    label: string;
  };
  children: React.ReactNode;
}

const AppShell: React.FC<AppShellProps> = ({
  currentView,
  title,
  description,
  eyebrow,
  user,
  onLogout,
  actions,
  backLink,
  children,
}) => {
  const navItems = [
    { key: 'dashboard', label: 'Dashboard', to: '/', icon: LayoutGrid },
    { key: 'workspace', label: 'Workspace', to: currentView === 'workspace' ? '#' : '/', icon: Workflow },
  ] as const;

  return (
    <div className="relative min-h-screen overflow-hidden bg-dark-bg">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-[6%] top-[8%] h-72 w-72 rounded-full bg-accent-blue/12 blur-3xl" />
        <div className="absolute right-[8%] top-[18%] h-64 w-64 rounded-full bg-accent-cyan/10 blur-3xl" />
        <div className="absolute bottom-0 left-1/2 h-80 w-80 -translate-x-1/2 rounded-full bg-accent-green/6 blur-3xl" />
      </div>

      <header className="topbar-blur sticky top-0 z-40">
        <div className="page-container flex flex-wrap items-center justify-between gap-4 py-4">
          <div className="flex items-center gap-5">
            <Link to="/" className="transition-transform duration-200 hover:scale-[1.01]">
              <AppLogo compact subtitle="Research workflow" />
            </Link>

            <nav className="hidden items-center gap-2 md:flex">
              {navItems.map(({ key, label, to, icon: Icon }) => {
                const isActive = currentView === key;

                return (
                  <Link
                    key={key}
                    to={to}
                    className={cn('nav-pill', isActive && 'nav-pill-active')}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {user && (
              <div className="hidden items-center gap-3 rounded-full border border-white/10 bg-white/[0.03] px-3 py-2 sm:flex">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-accent-blue to-accent-cyan text-sm font-semibold text-white">
                  {(user.full_name || user.email || 'U').charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{user.full_name || user.email}</div>
                  <div className="truncate text-xs text-gray-500">{user.email}</div>
                </div>
              </div>
            )}

            <button type="button" onClick={onLogout} className="btn-subtle">
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </header>

      <main className="relative">
        <div className="page-container py-8 sm:py-10">
          {backLink && (
            <Link
              to={backLink.to}
              className="mb-4 inline-flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              {backLink.label}
            </Link>
          )}

          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="min-w-0">
                {eyebrow && <div className="section-eyebrow">{eyebrow}</div>}
                <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">{title}</h1>
                {description && <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-400 sm:text-base">{description}</p>}
              </div>

              {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
            </div>

            {children}
          </div>
        </div>
      </main>
    </div>
  );
};

export default AppShell;
