import React from 'react';
import AppLogo from '../ui/AppLogo';

interface AuthLayoutProps {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ eyebrow, title, description, children }) => {
  const highlights = [
    'Structure research questions into a repeatable review workflow.',
    'Track approvals, retries, and live pipeline progress in one place.',
    'Move from question framing to draft synthesis with clear checkpoints.',
  ];

  return (
    <div className="relative min-h-screen overflow-hidden bg-dark-bg">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-[8%] top-[12%] h-72 w-72 rounded-full bg-accent-blue/16 blur-3xl" />
        <div className="absolute bottom-[12%] right-[10%] h-80 w-80 rounded-full bg-accent-cyan/12 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.06),transparent_42%)]" />
      </div>

      <div className="relative grid min-h-screen lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,0.95fr)]">
        <div className="hidden border-r border-white/5 lg:flex">
          <div className="page-container flex flex-1 items-center py-14">
            <div className="max-w-xl space-y-8">
              <AppLogo subtitle="LLM research workspace" />

              <div>
                <div className="section-eyebrow">High-trust research operations</div>
                <h1 className="section-title mt-4">
                  Build systematic reviews with a workflow that feels clear, reviewable, and production-ready.
                </h1>
                <p className="section-copy mt-5">
                  LiRA helps research teams coordinate search, screening, analysis, and drafting with explicit
                  checkpoints instead of opaque one-shot generation.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="panel p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Workflow</div>
                  <div className="mt-3 text-2xl font-semibold text-white">5 stages</div>
                </div>
                <div className="panel p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Review gates</div>
                  <div className="mt-3 text-2xl font-semibold text-white">Per step</div>
                </div>
                <div className="panel p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Tracking</div>
                  <div className="mt-3 text-2xl font-semibold text-white">Live status</div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Why teams use LiRA</div>
                <ul className="mt-4 space-y-3">
                  {highlights.map((highlight) => (
                    <li key={highlight} className="flex items-start gap-3 text-sm leading-6 text-gray-300">
                      <span className="mt-2 h-2 w-2 rounded-full bg-accent-cyan" />
                      <span>{highlight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center px-4 py-10 sm:px-6 lg:px-10">
          <div className="w-full max-w-lg">
            <div className="mb-8 lg:hidden">
              <AppLogo subtitle="LLM research workspace" />
            </div>

            <div className="panel-strong p-6 sm:p-8">
              <div className="section-eyebrow">{eyebrow}</div>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">{title}</h1>
              <p className="mt-3 text-sm leading-6 text-gray-400">{description}</p>

              <div className="mt-8">{children}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
