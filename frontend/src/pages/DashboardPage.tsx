import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Clock3,
  FolderKanban,
  LoaderCircle,
  PauseCircle,
  RefreshCw,
  Search,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import { researchApi, type ResearchSummary } from '../api/research';
import { useAuthStore } from '../stores/authStore';
import AppShell from '../components/layout/AppShell';
import MetricCard from '../components/ui/MetricCard';
import SectionHeader from '../components/ui/SectionHeader';
import StatePanel from '../components/ui/StatePanel';
import StatusBadge from '../components/ui/StatusBadge';

function formatDate(value: string | null): string {
  if (!value) return 'Not started';
  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

const suggestedTopics = [
  'Artificial intelligence applications in food safety and quality control',
  'Machine learning for early disease detection in primary care',
  'Renewable energy adoption and sustainable development outcomes',
];

const DashboardPage: React.FC = () => {
  const [histories, setHistories] = useState<ResearchSummary[]>([]);
  const [topic, setTopic] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [createError, setCreateError] = useState('');
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const loadHistories = async () => {
    try {
      setLoadError('');
      setLoading(true);
      const data = await researchApi.list();
      setHistories(data.items);
    } catch (err: any) {
      setLoadError(err?.response?.data?.detail || 'We could not load your research projects right now.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistories();
  }, []);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!topic.trim() || creating) return;

    setCreateError('');
    setCreating(true);

    try {
      const research = await researchApi.create({ topic: topic.trim() });
      navigate(`/research/${research.id}`);
    } catch (err: any) {
      setCreateError(err?.response?.data?.detail || 'Failed to create research. Please try again.');
      setCreating(false);
    }
  };

  const filteredHistories = histories.filter((history) => {
    const haystack = `${history.title} ${history.topic} ${history.latest_summary || ''}`.toLowerCase();
    return haystack.includes(searchQuery.trim().toLowerCase());
  });

  const runningCount = histories.filter((history) => history.status === 'running').length;
  const pausedCount = histories.filter((history) => history.status === 'paused').length;
  const completedCount = histories.filter((history) => history.status === 'completed').length;

  return (
    <AppShell
      currentView="dashboard"
      title="Research operations cockpit"
      description="Launch AI-assisted systematic reviews, monitor live pipeline progress, and return to any project with full context."
      eyebrow="Dashboard"
      user={user}
      onLogout={logout}
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <div className="hidden rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-gray-400 sm:block">
            {histories.length} total projects
          </div>
          <button type="button" onClick={loadHistories} className="btn-subtle">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <section className="panel-strong overflow-hidden p-6 sm:p-8">
          <div className="section-eyebrow">Premium workflow, clear checkpoints</div>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            Turn complex review work into a visible, step-by-step research pipeline.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-gray-400 sm:text-base">
            LiRA helps you frame the question, build the search, screen evidence, extract insights, and draft the review
            while preserving approvals, retries, and live activity.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <MetricCard
              label="Active workflows"
              value={String(runningCount)}
              description="Projects currently moving through the pipeline."
              icon={Sparkles}
              tone="blue"
            />
            <MetricCard
              label="Needs review"
              value={String(pausedCount)}
              description="Steps waiting for your approval or revision."
              icon={PauseCircle}
              tone="amber"
            />
            <MetricCard
              label="Completed"
              value={String(completedCount)}
              description="Projects that have already finished."
              icon={FolderKanban}
              tone="green"
            />
          </div>

          <div className="mt-8 rounded-3xl border border-white/8 bg-white/[0.03] p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <WandSparkles className="h-4 w-4 text-accent-cyan" />
              Suggested starting points
            </div>
            <p className="mt-2 text-sm leading-6 text-gray-400">
              Use a sample topic to seed the create form, then refine the wording before you start the pipeline.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {suggestedTopics.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setTopic(suggestion)}
                  className="rounded-full border border-white/10 bg-dark-surface-2/85 px-4 py-2 text-left text-sm text-gray-300 transition-all duration-200 hover:border-accent-cyan/35 hover:text-white"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="panel p-6 sm:p-7">
          <SectionHeader
            eyebrow="New review"
            title="Start a research workflow"
            description="Describe the question you want LiRA to investigate. You can start broad and refine it during approvals."
          />

          {createError && (
            <div className="mt-5 rounded-2xl border border-accent-rose/20 bg-accent-rose/10 px-4 py-3 text-sm text-accent-rose">
              {createError}
            </div>
          )}

          <form onSubmit={handleCreate} className="mt-6 space-y-5">
            <div>
              <label htmlFor="research-topic-input" className="field-label">
                Research topic
              </label>
              <textarea
                id="research-topic-input"
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                placeholder="Example: How does artificial intelligence improve food safety and quality control in industrial food processing?"
                className="textarea-dark"
                rows={6}
                disabled={creating}
              />
            </div>

            <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm text-gray-400">
              LiRA will create the project immediately, then move you into the live workspace where each major step can be reviewed.
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-gray-500">Use Enter inside the dashboard form after editing, or click the action button below.</div>
              <button id="start-research-btn" type="submit" disabled={!topic.trim() || creating} className="btn-primary">
                {creating ? (
                  <>
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    Creating workspace
                  </>
                ) : (
                  <>
                    Start research
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </section>
      </div>

      <section className="panel p-6 sm:p-7">
        <SectionHeader
          eyebrow="Research history"
          title="Resume recent work"
          description="Open any workspace to inspect completed outputs, approvals, failures, and live activity."
          actions={
            <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
              <label className="relative min-w-[240px]">
                <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  className="input-dark pl-11"
                  placeholder="Search projects"
                />
              </label>
            </div>
          }
        />

        <div className="mt-6">
          {loading ? (
            <div className="grid gap-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="panel-muted p-5">
                  <div className="skeleton h-5 w-48" />
                  <div className="mt-4 flex gap-3">
                    <div className="skeleton h-4 w-24" />
                    <div className="skeleton h-4 w-28" />
                  </div>
                  <div className="mt-4 skeleton h-4 w-full" />
                </div>
              ))}
            </div>
          ) : loadError ? (
            <StatePanel
              tone="error"
              title="Could not load research history"
              description={loadError}
              action={
                <button type="button" onClick={loadHistories} className="btn-secondary">
                  <RefreshCw className="h-4 w-4" />
                  Try again
                </button>
              }
            />
          ) : filteredHistories.length === 0 ? (
            <StatePanel
              title={histories.length === 0 ? 'No research projects yet' : 'No projects match this search'}
              description={
                histories.length === 0
                  ? 'Create your first workflow to start capturing research questions, review gates, and generated outputs.'
                  : 'Try a different search term or clear the project filter to see the full history.'
              }
              action={
                histories.length === 0 ? undefined : (
                  <button type="button" onClick={() => setSearchQuery('')} className="btn-secondary">
                    Clear search
                  </button>
                )
              }
            />
          ) : (
            <div className="grid gap-4">
              {filteredHistories.map((history) => (
                <button
                  key={history.id}
                  type="button"
                  onClick={() => navigate(`/research/${history.id}`)}
                  className="panel-interactive w-full p-5 text-left"
                >
                  <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-3">
                        <StatusBadge status={history.status} />
                        {history.current_step && (
                          <span className="rounded-full border border-white/8 bg-white/[0.04] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">
                            {history.current_step}
                          </span>
                        )}
                      </div>

                      <h3 className="mt-4 text-lg font-semibold text-white">{history.title}</h3>
                      <p className="mt-2 line-clamp-2 text-sm leading-6 text-gray-400">{history.topic}</p>

                      <div className="mt-5 flex flex-wrap items-center gap-4 text-sm text-gray-500">
                        <span className="inline-flex items-center gap-2">
                          <Clock3 className="h-4 w-4" />
                          Created {formatDate(history.created_at)}
                        </span>
                        {history.completed_at && (
                          <span className="inline-flex items-center gap-2">
                            <BookOpen className="h-4 w-4" />
                            Finished {formatDate(history.completed_at)}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex max-w-sm flex-col items-start gap-3 lg:items-end">
                      <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm leading-6 text-gray-400 lg:text-right">
                        {history.latest_summary || 'Open this workspace to inspect its latest outputs and activity.'}
                      </div>
                      <span className="inline-flex items-center gap-2 text-sm font-semibold text-white">
                        Open workspace
                        <ArrowRight className="h-4 w-4" />
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </section>
    </AppShell>
  );
};

export default DashboardPage;
