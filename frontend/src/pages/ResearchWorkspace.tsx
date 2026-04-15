import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  ListTree,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useParams } from 'react-router-dom';
import {
  researchApi,
  type NodeExecution,
  type PendingApproval,
  type ResearchDetail,
  type ResearchMessage as MessageType,
} from '../api/research';
import { useAuthStore } from '../stores/authStore';
import AppShell from '../components/layout/AppShell';
import MetricCard from '../components/ui/MetricCard';
import SectionHeader from '../components/ui/SectionHeader';
import StatePanel from '../components/ui/StatePanel';
import StatusBadge from '../components/ui/StatusBadge';
import { useWorkflowStore, type WorkflowEvent } from '../stores/workflowStore';

function getErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  const message = (error as { message?: unknown })?.message;
  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  return fallback;
}

type ActivityTone = 'info' | 'success' | 'warning' | 'error';

interface ActivityEntry {
  id: string;
  title: string;
  details: string[];
  tone: ActivityTone;
  stepLabel?: string;
  timestamp?: string;
}

function humanizeLabel(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function humanizeNodeName(nodeName?: string | null): string {
  if (!nodeName) return 'pipeline step';
  return nodeName.replace(/_/g, ' ');
}

function shortenText(value: string, maxLength = 180): string {
  const normalized = value.replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength).trimEnd()}...`;
}

function summarizeValue(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) {
    return shortenText(value);
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return null;

    const primitiveItems = value
      .slice(0, 3)
      .map((item) => {
        if (typeof item === 'string') return shortenText(item, 80);
        if (typeof item === 'number' || typeof item === 'boolean') return String(item);
        if (item && typeof item === 'object') {
          const record = item as Record<string, unknown>;
          const primary = record.question ?? record.title ?? record.name ?? record.label;
          if (typeof primary === 'string' && primary.trim()) {
            return shortenText(primary, 80);
          }
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));

    if (primitiveItems.length > 0) {
      const suffix = value.length > primitiveItems.length ? ` and ${value.length - primitiveItems.length} more` : '';
      return `${primitiveItems.join(', ')}${suffix}`;
    }

    return `${value.length} items`;
  }

  if (value && typeof value === 'object') {
    const objectValue = value as Record<string, unknown>;
    const primitiveEntries = Object.entries(objectValue)
      .filter(([, nestedValue]) =>
        typeof nestedValue === 'string' ||
        typeof nestedValue === 'number' ||
        typeof nestedValue === 'boolean',
      )
      .slice(0, 2)
      .map(([key, nestedValue]) => `${humanizeLabel(key)}: ${shortenText(String(nestedValue), 80)}`);

    if (primitiveEntries.length > 0) {
      return primitiveEntries.join(' | ');
    }

    return `${Object.keys(objectValue).length} fields`;
  }

  return null;
}

function summarizeOutputSummary(data?: Record<string, any> | null): string[] {
  if (!data) return [];

  const skipKeys = new Set(['messages', 'logs', 'errors', 'user_feedback', 'current_approval_node', 'current_step']);

  return Object.entries(data)
    .filter(([key, value]) => !skipKeys.has(key) && value !== null && value !== undefined && value !== '')
    .slice(0, 4)
    .map(([key, value]) => {
      const summary = summarizeValue(value);
      if (!summary) return null;
      return `${humanizeLabel(key)}: ${summary}`;
    })
    .filter((entry): entry is string => Boolean(entry));
}

function getEventTone(eventType: string): ActivityTone {
  switch (eventType) {
    case 'NODE_COMPLETED':
    case 'WORKFLOW_COMPLETED':
    case 'ARTIFACT_CREATED':
      return 'success';
    case 'NODE_WAITING_FOR_APPROVAL':
    case 'NODE_RETRY_STARTED':
    case 'NODE_REVISION_STARTED':
      return 'warning';
    case 'NODE_FAILED':
    case 'WORKFLOW_FAILED':
      return 'error';
    default:
      return 'info';
  }
}

function formatActivityEntries(events: WorkflowEvent[], nodeExecutions: NodeExecution[]): ActivityEntry[] {
  return [...events]
    .slice(-30)
    .reverse()
    .map((event, index) => {
      const nodeLabel = humanizeNodeName(event.node_name);
      const relatedNode = event.node_name
        ? [...nodeExecutions]
            .filter((node) => node.node_name === event.node_name)
            .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0]
        : null;

      let title = event.message || event.event_type;
      let details: string[] = [];

      switch (event.event_type) {
        case 'NODE_STARTED':
          title = `Started ${nodeLabel}`;
          details = [event.message || `Running ${nodeLabel}.`];
          break;
        case 'NODE_COMPLETED':
          title = `Completed ${nodeLabel}`;
          details = summarizeOutputSummary(event.data?.output_summary) || summarizeOutputSummary(relatedNode?.output_summary);
          if (details.length === 0) {
            details = [event.message || `${nodeLabel} finished successfully.`];
          }
          break;
        case 'NODE_FAILED':
          title = `Problem in ${nodeLabel}`;
          details = [
            shortenText(
              String(event.data?.error || relatedNode?.error_message || event.message || `${nodeLabel} failed.`),
              220,
            ),
          ];
          break;
        case 'NODE_WAITING_FOR_APPROVAL':
          title = `Review required for ${nodeLabel}`;
          details = summarizeOutputSummary(event.data?.output_summary);
          if (details.length === 0) {
            details = [event.message || `This step is waiting for your review.`];
          }
          break;
        case 'NODE_REVISION_STARTED':
          title = `Revising ${nodeLabel}`;
          details = [event.message || `Running ${nodeLabel} again with your feedback.`];
          break;
        case 'NODE_RETRY_STARTED':
          title = `Retrying ${nodeLabel}`;
          details = [event.message || `Running ${nodeLabel} again after a failure.`];
          break;
        case 'WORKFLOW_COMPLETED':
          title = 'Pipeline completed';
          details = [event.message || 'All steps finished successfully.'];
          break;
        case 'WORKFLOW_FAILED':
          title = 'Pipeline stopped';
          details = [event.message || 'The workflow hit an error and stopped.'];
          break;
        case 'ARTIFACT_CREATED':
          title = 'Created output file';
          details = [
            event.data?.filename
              ? `${event.data.filename}${event.data.description ? ` - ${event.data.description}` : ''}`
              : event.message || 'A new artifact was generated.',
          ];
          break;
        case 'LOG_MESSAGE':
          title = shortenText(event.message || 'Pipeline update', 120);
          details = [];
          break;
        default:
          title = shortenText(event.message || humanizeLabel(event.event_type), 120);
          details = summarizeOutputSummary(event.data);
          break;
      }

      return {
        id: `${event.timestamp ?? 'event'}-${event.event_type}-${index}`,
        title,
        details,
        tone: getEventTone(event.event_type || ''),
        stepLabel: event.step_label,
        timestamp: event.timestamp,
      };
    });
}

const ResearchWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [research, setResearch] = useState<ResearchDetail | null>(null);
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [nodeExecutions, setNodeExecutions] = useState<NodeExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionErrorTarget, setActionErrorTarget] = useState<'approval' | string | ''>('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevEventsLenRef = useRef(0);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const {
    events,
    pendingApproval,
    setPendingApproval,
    connectWebSocket,
    disconnectWebSocket,
    isRunning,
    isPaused,
    connectionStatus,
  } = useWorkflowStore();

  const loadInitialData = useCallback(async () => {
    if (!id) return;

    setLoading(true);
    setLoadError('');

    try {
      const [nextResearch, nextMessages, nextNodes, pending] = await Promise.all([
        researchApi.get(id),
        researchApi.getMessages(id),
        researchApi.getNodeExecutions(id),
        researchApi.getPendingApproval(id).catch(() => null),
      ]);

      setResearch(nextResearch);
      setMessages(nextMessages);
      setNodeExecutions(nextNodes);
      setPendingApproval(pending?.has_pending ? { ...pending, _source: 'rest' } : null);
    } catch (err) {
      console.error('Failed to load workspace:', err);
      setLoadError(getErrorMessage(err, 'Failed to load this research workspace.'));
    } finally {
      setLoading(false);
    }
  }, [id, setPendingApproval]);

  useEffect(() => {
    if (!id) return;

    prevEventsLenRef.current = 0;
    setFeedback('');
    setActionLoading('');
    setActionError('');
    setActionErrorTarget('');

    loadInitialData();
    connectWebSocket(id);

    return () => disconnectWebSocket();
  }, [id, loadInitialData, connectWebSocket, disconnectWebSocket]);

  useEffect(() => {
    if (!id || events.length <= prevEventsLenRef.current) {
      prevEventsLenRef.current = events.length;
      return;
    }

    const newEvents = events.slice(prevEventsLenRef.current);
    prevEventsLenRef.current = events.length;

    const refreshTriggers = new Set([
      'NODE_COMPLETED',
      'NODE_WAITING_FOR_APPROVAL',
      'NODE_FAILED',
      'WORKFLOW_COMPLETED',
      'WORKFLOW_FAILED',
      'ARTIFACT_CREATED',
      'NODE_REVISION_STARTED',
      'NODE_RETRY_STARTED',
    ]);

    const shouldRefresh = newEvents.some((event) => refreshTriggers.has(event.event_type || ''));

    if (!shouldRefresh || actionLoading !== '') {
      return;
    }

    Promise.all([
      researchApi.getNodeExecutions(id),
      researchApi.get(id),
      researchApi.getMessages(id),
      researchApi.getPendingApproval(id).catch(() => null),
    ])
      .then(([nextNodes, nextResearch, nextMessages, pending]) => {
        setNodeExecutions(nextNodes);
        setResearch(nextResearch);
        setMessages(nextMessages);
        setPendingApproval(pending?.has_pending ? { ...pending, _source: 'rest' } : null);
      })
      .catch(() => {
        // A later event or manual refresh will heal this.
      });
  }, [actionLoading, events.length, id, setPendingApproval]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, events, pendingApproval, nodeExecutions]);

  useEffect(() => {
    if (!pendingApproval) {
      setFeedback('');
      setActionError('');
      setActionErrorTarget('');
    }
  }, [pendingApproval?.approval_id]);

  const getActionableApproval = useCallback(async (): Promise<PendingApproval | null> => {
    if (!id) return null;
    if (pendingApproval?.node_execution_id) return pendingApproval;

    try {
      const pending = await researchApi.getPendingApproval(id);
      if (pending.has_pending) {
        const hydrated: PendingApproval = { ...pending, _source: 'rest' };
        setPendingApproval(hydrated);
        return hydrated;
      }
    } catch (err) {
      console.error('Failed to hydrate pending approval:', err);
    }

    return pendingApproval;
  }, [id, pendingApproval, setPendingApproval]);

  const runApprovalAction = useCallback(async (
    action: 'continue' | 'improve',
    request: (nodeExecutionId: string) => Promise<unknown>,
    feedbackSnapshot = feedback,
  ) => {
    if (actionLoading || !id) return;

    const approvalSnapshot = await getActionableApproval();
    if (!approvalSnapshot?.node_execution_id) {
      setActionErrorTarget('approval');
      setActionError('This approval is still syncing. Try again in a moment.');
      return;
    }

    setActionErrorTarget('');
    setActionError('');
    setActionLoading(action);
    setPendingApproval(null);

    if (action === 'improve') {
      setFeedback('');
    }

    try {
      await request(approvalSnapshot.node_execution_id);
    } catch (err) {
      console.error(`${action} failed:`, err);
      setPendingApproval(approvalSnapshot);
      setActionErrorTarget('approval');
      setActionError(getErrorMessage(err, `Unable to ${action} this step right now.`));

      if (action === 'improve') {
        setFeedback(feedbackSnapshot);
      }
    } finally {
      setActionLoading('');
    }
  }, [actionLoading, feedback, getActionableApproval, id, setPendingApproval]);

  const handleContinue = useCallback(async () => {
    if (!id) return;
    await runApprovalAction('continue', (nodeExecutionId) => researchApi.continueNode(id, nodeExecutionId));
  }, [id, runApprovalAction]);

  const handleImprove = useCallback(async () => {
    if (!id) return;

    const trimmedFeedback = feedback.trim();
    if (!trimmedFeedback) {
      setActionErrorTarget('approval');
      setActionError('Add feedback before requesting a revision.');
      return;
    }

    await runApprovalAction(
      'improve',
      (nodeExecutionId) => researchApi.improveNode(id, nodeExecutionId, trimmedFeedback),
      trimmedFeedback,
    );
  }, [feedback, id, runApprovalAction]);

  const handleRetryFailedStep = useCallback(async (nodeExecutionId: string) => {
    if (!id || actionLoading) return;

    setActionErrorTarget('');
    setActionError('');
    setActionLoading(`retry-failed:${nodeExecutionId}`);

    try {
      await researchApi.retryNode(id, nodeExecutionId);

      const [nextResearch, nextMessages, nextNodes, pending] = await Promise.all([
        researchApi.get(id),
        researchApi.getMessages(id),
        researchApi.getNodeExecutions(id),
        researchApi.getPendingApproval(id).catch(() => null),
      ]);

      setResearch(nextResearch);
      setMessages(nextMessages);
      setNodeExecutions(nextNodes);
      setPendingApproval(pending?.has_pending ? { ...pending, _source: 'rest' } : null);
    } catch (err) {
      console.error('failed-step retry failed:', err);
      setActionErrorTarget(nodeExecutionId);
      setActionError(getErrorMessage(err, 'Unable to retry this failed step right now.'));
    } finally {
      setActionLoading('');
    }
  }, [actionLoading, id, setPendingApproval]);

  const approvalOutput = pendingApproval
    ? (() => {
        const liveOutput = pendingApproval.output_summary;
        if (liveOutput && Object.keys(liveOutput).length > 0) {
          return liveOutput;
        }

        const latestCompletedEvent = [...events]
          .reverse()
          .find((event) =>
            event.event_type === 'NODE_COMPLETED' &&
            event.node_name === pendingApproval.node_name &&
            event.data?.output_summary &&
            Object.keys(event.data.output_summary).length > 0,
          );

        if (latestCompletedEvent?.data?.output_summary) {
          return latestCompletedEvent.data.output_summary;
        }

        const latestCompletedNode = [...nodeExecutions]
          .filter((node) =>
            node.node_name === pendingApproval.node_name &&
            node.output_summary &&
            Object.keys(node.output_summary).length > 0,
          )
          .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0];

        return latestCompletedNode?.output_summary ?? null;
      })()
    : null;

  const completedNodes = nodeExecutions.filter((node) =>
    (node.status === 'completed' || node.status === 'approved') &&
    node.output_summary &&
    Object.keys(node.output_summary).length > 0,
  );
  const failedNodes = [...nodeExecutions]
    .filter((node) => node.status === 'failed')
    .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
  const latestFailedNodeId = failedNodes[0]?.id ?? null;

  const liveFeedLabel = connectionStatus !== 'connected'
    ? 'Reconnecting live updates...'
    : isRunning
      ? 'Pipeline running...'
      : isPaused
        ? 'Waiting for your review'
        : 'Pipeline activity';
  const activityEntries = formatActivityEntries(events, nodeExecutions);
  const timelineMessages = messages.filter((message) => message.message_type !== 'approval');
  const databasesSummary = research
    ? Array.isArray(research.databases)
      ? research.databases.join(', ')
      : research.databases && typeof research.databases === 'object'
        ? Object.keys(research.databases).join(', ')
        : 'Not defined'
    : 'Not defined';
  const shellTitle = research?.title || 'Research workspace';
  const shellDescription =
    research?.topic ||
    'Inspect live activity, review approvals, and monitor every stage of the research workflow.';

  return (
    <AppShell
      currentView="workspace"
      title={shellTitle}
      description={shellDescription}
      eyebrow="Live workspace"
      user={user}
      onLogout={logout}
      backLink={{ to: '/', label: 'Back to dashboard' }}
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={research?.status || 'pending'} />
          <button type="button" onClick={loadInitialData} className="btn-subtle">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      }
    >
      {loading ? (
        <div className="panel-strong flex min-h-[320px] flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-dark-surface-2">
            <LoaderCircle className="h-7 w-7 animate-spin text-accent-blue-light" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Loading workspace</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-gray-400">
              Pulling the latest messages, approvals, node executions, and live workflow state.
            </p>
          </div>
        </div>
      ) : loadError ? (
        <StatePanel
          tone="error"
          title="Workspace unavailable"
          description={loadError}
          action={
            <button type="button" onClick={loadInitialData} className="btn-secondary">
              <RefreshCw className="h-4 w-4" />
              Reload workspace
            </button>
          }
        />
      ) : !research ? (
        <StatePanel
          title="Research not found"
          description="This workspace could not be found. Return to the dashboard and open a different project."
        />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Current stage"
              value={research.current_step || 'Queued'}
              description="Latest stage reported by the backend workflow."
              icon={ListTree}
              tone="blue"
            />
            <MetricCard
              label="Completed outputs"
              value={String(completedNodes.length)}
              description="Finished step outputs available to inspect."
              icon={CheckCircle2}
              tone="green"
            />
            <MetricCard
              label="Pending review"
              value={pendingApproval ? '1 step' : 'Clear'}
              description={pendingApproval ? 'A step is waiting for your approval.' : 'No approval checkpoints are currently open.'}
              icon={ShieldCheck}
              tone={pendingApproval ? 'amber' : 'default'}
            />
            <MetricCard
              label="Live connection"
              value={connectionStatus === 'connected' ? 'Connected' : 'Recovering'}
              description="Realtime websocket status for incoming pipeline events."
              icon={connectionStatus === 'connected' ? Wifi : WifiOff}
              tone={connectionStatus === 'connected' ? 'green' : 'amber'}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.95fr)]">
            <div className="space-y-6">
              {pendingApproval?.node_name && (
                <div style={styles.approvalCard} id="approval-card">
                  <div style={styles.approvalHeader}>
                    <div style={styles.approvalHeading}>
                      <span style={styles.pauseIcon}>PAUSE</span>
                      <div>
                        <h3 style={styles.approvalTitle}>
                          Review: {pendingApproval.description || pendingApproval.node_name.replace(/_/g, ' ')}
                        </h3>
                        {pendingApproval.step_label && (
                          <span style={styles.stepBadge}>{pendingApproval.step_label}</span>
                        )}
                      </div>
                    </div>

                    <div style={styles.connectionBadge}>
                      <span
                        style={{
                          ...styles.connectionDot,
                          background:
                            connectionStatus === 'connected'
                              ? '#10b981'
                              : connectionStatus === 'connecting' || connectionStatus === 'authenticating'
                                ? '#f59e0b'
                                : '#6b7280',
                        }}
                      />
                      <span style={styles.connectionText}>
                        {connectionStatus === 'connected' ? 'Live updates connected' : 'Live updates reconnecting'}
                      </span>
                    </div>
                  </div>

                  <div style={styles.outputBox}>
                    <div style={{ marginBottom: 8 }}>
                      <span style={styles.outputLabel}>Result from this step</span>
                    </div>
                    {approvalOutput ? (
                      <SimpleOutput data={approvalOutput} />
                    ) : (
                      <p style={{ color: '#6b7280', fontSize: 13, margin: 0 }}>
                        Output is still loading. The latest node result will appear here automatically.
                      </p>
                    )}
                  </div>

                  <div style={styles.feedbackBlock}>
                    <label htmlFor="feedback-input" style={styles.feedbackLabel}>
                      Feedback for revision requests
                    </label>
                    <textarea
                      id="feedback-input"
                      value={feedback}
                      onChange={(event) => setFeedback(event.target.value)}
                      placeholder="Example: tighten the inclusion criteria and make the summary more specific to precision medicine."
                      style={styles.feedbackInput}
                      rows={4}
                    />
                    <p style={styles.feedbackHint}>
                      Approve to continue as-is, or improve to rerun this step with your notes.
                    </p>
                    {actionErrorTarget === 'approval' && actionError && <p style={styles.actionError}>{actionError}</p>}
                  </div>

                  <div style={styles.buttonRow}>
                    <button
                      id="btn-approve"
                      onClick={handleContinue}
                      disabled={!!actionLoading}
                      style={{ ...styles.btnContinue, opacity: actionLoading ? 0.5 : 1 }}
                    >
                      {actionLoading === 'continue' ? 'Processing...' : 'Approve and continue'}
                    </button>

                    <button
                      id="btn-improve"
                      onClick={handleImprove}
                      disabled={!!actionLoading || !feedback.trim()}
                      style={{ ...styles.btnImprove, opacity: (actionLoading || !feedback.trim()) ? 0.45 : 1 }}
                    >
                      {actionLoading === 'improve' ? 'Re-running...' : 'Improve with feedback'}
                    </button>
                  </div>
                </div>
              )}

              {failedNodes.length > 0 && (
                <section className="panel p-6 sm:p-7">
                  <SectionHeader
                    eyebrow="Interventions"
                    title="Failed steps"
                    description="Retry actions appear only when the workflow stops on a problem."
                  />
                  <div className="mt-6 space-y-4">
                    {failedNodes.map((node) => (
                      <FailedNodeCard
                        key={node.id}
                        node={node}
                        isLatestFailed={node.id === latestFailedNodeId}
                        isRetrying={actionLoading === `retry-failed:${node.id}`}
                        onRetry={() => handleRetryFailedStep(node.id)}
                        actionError={actionErrorTarget === node.id ? actionError : ''}
                        disableActions={!!actionLoading}
                      />
                    ))}
                  </div>
                </section>
              )}

              <section className="panel p-6 sm:p-7">
                <SectionHeader
                  eyebrow="Generated results"
                  title="Completed step outputs"
                  description="Expand any completed node to inspect the latest structured output from that stage."
                />
                <div className="mt-6 space-y-4">
                  {completedNodes.length === 0 ? (
                    <StatePanel
                      title="No completed outputs yet"
                      description="Finished node outputs will appear here as the workflow moves forward."
                    />
                  ) : (
                    completedNodes.map((node) => <CompletedNodeCard key={node.id} node={node} />)
                  )}
                </div>
              </section>

              <section className="panel p-6 sm:p-7">
                <SectionHeader
                  eyebrow="Conversation"
                  title="Timeline messages"
                  description="User prompts and pipeline messages stay visible here so the research run remains understandable."
                />
                <div className="mt-6 space-y-4">
                  {timelineMessages.length === 0 ? (
                    <StatePanel
                      title="No timeline messages yet"
                      description="Messages will appear here once the workflow starts producing chat and timeline updates."
                    />
                  ) : (
                    timelineMessages.map((message) => <SimpleMessage key={message.id} message={message} />)
                  )}
                </div>
              </section>
            </div>

            <aside className="space-y-6 xl:sticky xl:top-28 xl:self-start">
              <section className="panel p-6">
                <SectionHeader
                  eyebrow="Progress"
                  title="Pipeline stages"
                  description="A quick stage-by-stage view of where this review is currently sitting."
                />
                <div className="mt-6">
                  <StepBar currentStep={research.current_step} status={research.status} />
                </div>
              </section>

              <section className="panel p-6">
                <SectionHeader
                  eyebrow="Project details"
                  title="Research context"
                  description="Core metadata for this workspace and the current run."
                />
                <div className="mt-6 space-y-3">
                  <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Timeframe</div>
                    <div className="mt-2 text-sm leading-6 text-gray-300">{research.timeframe || 'Not specified'}</div>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Databases</div>
                    <div className="mt-2 text-sm leading-6 text-gray-300">{databasesSummary || 'Not defined'}</div>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Last updated</div>
                    <div className="mt-2 text-sm leading-6 text-gray-300">
                      {new Date(research.updated_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Pipeline version</div>
                    <div className="mt-2 text-sm leading-6 text-gray-300">{research.pipeline_version || 'Default'}</div>
                  </div>
                  {research.latest_error && (
                    <div className="rounded-2xl border border-accent-rose/20 bg-accent-rose/10 px-4 py-3">
                      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent-rose">Latest error</div>
                      <div className="mt-2 text-sm leading-6 text-accent-rose">{research.latest_error}</div>
                    </div>
                  )}
                </div>
              </section>

              <section className="panel p-6">
                <SectionHeader
                  eyebrow="Live activity"
                  title="Readable pipeline log"
                  description="Plain-language workflow events, adapted from the backend logs for people instead of raw payloads."
                />
                <div className="mt-6 space-y-3">
                  {connectionStatus !== 'connected' && (
                    <div className="rounded-2xl border border-accent-amber/20 bg-accent-amber/10 p-4">
                      <div className="flex items-start gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-accent-amber/20 bg-dark-surface-2">
                          <Activity className="h-5 w-5 text-accent-amber" />
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-white">{liveFeedLabel}</div>
                          <div className="mt-1 text-sm leading-6 text-gray-400">
                            {connectionStatus === 'connecting' || connectionStatus === 'authenticating'
                              ? 'Connecting to the pipeline stream so new events appear automatically.'
                              : 'Live updates are temporarily disconnected. The workspace will reconnect and refresh on the next event.'}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  {activityEntries.length === 0 ? (
                    <StatePanel
                      title="No activity yet"
                      description="As soon as the workflow emits events, they will appear here in a readable audit trail."
                    />
                  ) : (
                    activityEntries.map((entry) => <ActivityLogCard key={entry.id} entry={entry} />)
                  )}
                </div>
              </section>
            </aside>
          </div>

          <div ref={bottomRef} />
        </div>
      )}
    </AppShell>
  );
};

const StatusPill: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    running: { bg: '#1e3a5f', text: '#60a5fa', label: 'Running' },
    completed: { bg: '#14532d', text: '#4ade80', label: 'Done' },
    failed: { bg: '#4c1d1d', text: '#f87171', label: 'Failed' },
    paused: { bg: '#422006', text: '#fbbf24', label: 'Waiting for review' },
    pending: { bg: '#1f2937', text: '#9ca3af', label: 'Pending' },
  };
  const current = map[status] || map.pending;

  return (
    <span
      style={{
        background: current.bg,
        color: current.text,
        padding: '2px 10px',
        borderRadius: 20,
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {current.label}
    </span>
  );
};

const StepBar: React.FC<{ currentStep: string | null; status: string }> = ({ currentStep, status }) => {
  const steps = ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5'];
  const currentIndex = currentStep ? steps.findIndex((step) => currentStep.includes(step.replace('Step ', ''))) : -1;

  return (
    <div style={styles.stepBarContainer}>
      {steps.map((step, index) => (
        <React.Fragment key={step}>
          <div style={styles.stepBarNode}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background:
                  status === 'completed'
                    ? '#4ade80'
                    : index < currentIndex
                      ? '#4ade80'
                      : index === currentIndex
                        ? status === 'paused'
                          ? '#fbbf24'
                          : '#3b82f6'
                        : '#374151',
                boxShadow:
                  index === currentIndex
                    ? `0 0 6px ${status === 'paused' ? '#fbbf24' : '#3b82f6'}`
                    : 'none',
              }}
            />
            <span style={{ fontSize: 11, color: index <= currentIndex ? '#d1d5db' : '#4b5563', fontFamily: 'monospace' }}>
              {step}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div style={{ ...styles.stepBarTrack, background: index < currentIndex ? '#4ade8050' : '#374151' }} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

const CompletedNodeCard: React.FC<{ node: NodeExecution }> = ({ node }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={styles.completedCard}>
      <div
        onClick={() => setExpanded((value) => !value)}
        style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
      >
        <span style={{ color: '#4ade80', fontSize: 14 }}>OK</span>
        {node.step_label && <span style={styles.stepBadge}>{node.step_label}</span>}
        <span style={{ color: '#d1d5db', fontSize: 13, flex: 1 }}>{node.node_name.replace(/_/g, ' ')}</span>
        {node.duration_ms != null && (
          <span style={{ color: '#6b7280', fontSize: 10, fontFamily: 'monospace' }}>
            {(node.duration_ms / 1000).toFixed(1)}s
          </span>
        )}
        <span style={{ color: '#6b7280', fontSize: 12 }}>{expanded ? 'v' : '>'}</span>
      </div>

      {expanded && node.output_summary && Object.keys(node.output_summary).length > 0 && (
        <div style={{ marginTop: 12, padding: 12, background: '#0d1117', borderRadius: 8, border: '1px solid #21262d' }}>
          <SimpleOutput data={node.output_summary} />
        </div>
      )}
    </div>
  );
};

const FailedNodeCard: React.FC<{
  node: NodeExecution;
  isLatestFailed: boolean;
  isRetrying: boolean;
  onRetry: () => void;
  actionError: string;
  disableActions: boolean;
}> = ({ node, isLatestFailed, isRetrying, onRetry, actionError, disableActions }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div style={styles.failedCard}>
      <div
        onClick={() => setExpanded((value) => !value)}
        style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', flexWrap: 'wrap' }}
      >
        <span style={{ color: '#f87171', fontSize: 14, fontWeight: 700 }}>FAILED</span>
        {node.step_label && <span style={styles.stepBadge}>{node.step_label}</span>}
        <span style={{ color: '#f3f4f6', fontSize: 13, flex: 1 }}>{node.node_name.replace(/_/g, ' ')}</span>
        {isLatestFailed && <span style={styles.failedStepPill}>Stopped here</span>}
        <span style={{ color: '#6b7280', fontSize: 12 }}>{expanded ? 'v' : '>'}</span>
      </div>

      {expanded && (
        <div style={styles.failedCardBody}>
          <p style={styles.failedCardText}>
            {node.error_message?.trim() || 'This step stopped because the pipeline hit an error.'}
          </p>

          {node.feedback_text && (
            <div style={styles.failedMetaBlock}>
              <div style={styles.outputLabel}>Last feedback</div>
              <p style={styles.failedMetaText}>{node.feedback_text}</p>
            </div>
          )}

          {node.output_summary && Object.keys(node.output_summary).length > 0 && (
            <div style={styles.failedMetaBlock}>
              <div style={styles.outputLabel}>Last output before failure</div>
              <SimpleOutput data={node.output_summary} />
            </div>
          )}

          {actionError && <p style={styles.actionError}>{actionError}</p>}

          <div style={styles.buttonRow}>
            <button
              onClick={onRetry}
              disabled={disableActions}
              style={{ ...styles.btnRetry, opacity: disableActions ? 0.5 : 1 }}
            >
              {isRetrying ? 'Retrying...' : 'Retry step'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const ActivityLogCard: React.FC<{ entry: ActivityEntry }> = ({ entry }) => {
  const toneStyle =
    entry.tone === 'success'
      ? styles.activitySuccess
      : entry.tone === 'warning'
        ? styles.activityWarning
        : entry.tone === 'error'
          ? styles.activityError
          : styles.activityInfo;

  const icon =
    entry.tone === 'success'
      ? 'DONE'
      : entry.tone === 'warning'
        ? 'WAIT'
        : entry.tone === 'error'
          ? 'ERROR'
          : 'INFO';

  return (
    <div style={{ ...styles.activityCard, ...toneStyle }}>
      <div style={styles.activityTitleRow}>
        <span style={styles.activityIcon}>{icon}</span>
        <div style={{ flex: 1 }}>
          <div style={styles.activityMetaRow}>
            {entry.stepLabel && <span style={styles.stepBadge}>{entry.stepLabel}</span>}
            {entry.timestamp && (
              <span style={styles.activityTime}>
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
          <p style={styles.activityTitle}>{entry.title}</p>
        </div>
      </div>

      {entry.details.map((detail, index) => (
        <p key={index} style={styles.activityDetail}>
          {detail}
        </p>
      ))}
    </div>
  );
};

const SimpleMessage: React.FC<{ message: MessageType }> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        background: isUser ? '#1e3a5f' : '#111827',
        border: `1px solid ${isUser ? '#2563eb30' : '#1f2937'}`,
        borderRadius: 10,
        padding: '10px 14px',
        marginLeft: isUser ? 'auto' : 0,
        maxWidth: isUser ? '70%' : '95%',
      }}
    >
      <p style={{ color: '#e5e7eb', fontSize: 13, lineHeight: 1.5, margin: 0 }}>{message.content}</p>
      <span style={{ color: '#4b5563', fontSize: 10, marginTop: 4, display: 'block' }}>
        {new Date(message.created_at).toLocaleTimeString()}
      </span>
    </div>
  );
};

const SimpleOutput: React.FC<{ data: Record<string, any> }> = ({ data }) => {
  const skipKeys = new Set(['messages', 'logs', 'errors', 'user_feedback', 'current_approval_node', 'current_step']);
  const entries = Object.entries(data).filter(([key]) => !skipKeys.has(key));

  if (entries.length === 0) {
    return <p style={{ color: '#9ca3af', fontSize: 13, margin: 0 }}>No output data.</p>;
  }

  return (
    <div>
      {entries.map(([key, value]) => {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());

        if (typeof value === 'string' && value.trim()) {
          return (
            <div key={key} style={{ marginBottom: 10 }}>
              <div style={styles.outputLabel}>{label}</div>
              <div style={{ color: '#e6edf3', fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                {value}
              </div>
            </div>
          );
        }

        if (Array.isArray(value) && value.length > 0) {
          return (
            <div key={key} style={{ marginBottom: 10 }}>
              <div style={styles.outputLabel}>{label} ({value.length} items)</div>
              <ul style={{ margin: 0, paddingLeft: 18, listStyle: 'disc' }}>
                {value.slice(0, 15).map((item, index) => (
                  <li key={index} style={{ color: '#e6edf3', fontSize: 13, lineHeight: 1.6, marginBottom: 2 }}>
                    {typeof item === 'object' ? JSON.stringify(item) : String(item)}
                  </li>
                ))}
                {value.length > 15 && (
                  <li style={{ color: '#6b7280', fontSize: 13 }}>...and {value.length - 15} more</li>
                )}
              </ul>
            </div>
          );
        }

        if (typeof value === 'object' && value !== null) {
          return (
            <div key={key} style={{ marginBottom: 10 }}>
              <div style={styles.outputLabel}>{label}</div>
              <pre
                style={{
                  color: '#8b949e',
                  fontSize: 11,
                  fontFamily: 'monospace',
                  background: '#161b22',
                  padding: 8,
                  borderRadius: 6,
                  overflow: 'auto',
                  maxHeight: 150,
                  margin: 0,
                }}
              >
                {JSON.stringify(value, null, 2)}
              </pre>
            </div>
          );
        }

        if (value !== null && value !== undefined && value !== '') {
          return (
            <div key={key} style={{ display: 'flex', gap: 8, alignItems: 'baseline', marginBottom: 6 }}>
              <span style={styles.outputLabel}>{label}:</span>
              <span style={{ color: '#e6edf3', fontSize: 13 }}>{String(value)}</span>
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#0f1117' },
  center: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' },
  spinner: { width: 32, height: 32, border: '3px solid #374151', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
  header: { padding: '16px 24px', borderBottom: '1px solid #1f2937' },
  title: { color: '#f3f4f6', fontSize: 18, fontWeight: 600, margin: 0 },
  headerMeta: { display: 'flex', alignItems: 'center', gap: 10, marginTop: 4, flexWrap: 'wrap' },
  stepLabel: { color: '#6b7280', fontSize: 11, fontFamily: 'monospace' },
  stepBarContainer: { display: 'flex', alignItems: 'center', gap: 8, width: '100%' },
  stepBarNode: { display: 'flex', alignItems: 'center', gap: 6, minWidth: 'fit-content' },
  stepBarTrack: { flex: 1, height: 1, minWidth: 18 },
  stepBadge: { background: '#1e3a5f', color: '#60a5fa', padding: '1px 8px', borderRadius: 4, fontSize: 10, fontFamily: 'monospace', fontWeight: 600 },
  content: { flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: 12 },
  completedCard: { background: '#111827', border: '1px solid #1f2937', borderRadius: 10, padding: '12px 16px' },
  failedCard: {
    background: 'linear-gradient(135deg, #2a1313 0%, #1b1418 100%)',
    border: '1px solid #7f1d1d',
    borderRadius: 12,
    padding: '14px 16px',
    boxShadow: '0 0 24px #7f1d1d22',
  },
  failedCardBody: {
    marginTop: 12,
    paddingTop: 12,
    borderTop: '1px solid #7f1d1d66',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  failedCardText: {
    color: '#fecaca',
    fontSize: 13,
    lineHeight: 1.6,
    margin: 0,
    whiteSpace: 'pre-wrap',
  },
  failedMetaBlock: {
    background: '#0d1117',
    border: '1px solid #2b2f36',
    borderRadius: 10,
    padding: 12,
  },
  failedMetaText: {
    color: '#e5e7eb',
    fontSize: 13,
    lineHeight: 1.6,
    margin: 0,
    whiteSpace: 'pre-wrap',
  },
  failedStepPill: {
    background: '#7f1d1d66',
    color: '#fca5a5',
    padding: '2px 8px',
    borderRadius: 999,
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  approvalCard: {
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '2px solid #f59e0b40',
    borderRadius: 16,
    padding: 24,
    boxShadow: '0 0 40px #f59e0b08',
  },
  approvalHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  approvalHeading: { display: 'flex', alignItems: 'center', gap: 12 },
  pauseIcon: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 52,
    height: 32,
    borderRadius: 999,
    background: '#f59e0b20',
    color: '#fbbf24',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 0.8,
  },
  approvalTitle: { color: '#f3f4f6', fontSize: 16, fontWeight: 600, margin: 0 },
  connectionBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 10px',
    borderRadius: 999,
    background: '#0f172a80',
    border: '1px solid #334155',
  },
  connectionDot: { width: 8, height: 8, borderRadius: '50%' },
  connectionText: { color: '#cbd5e1', fontSize: 11, fontWeight: 500 },
  outputBox: {
    background: '#0d1117',
    border: '1px solid #21262d',
    borderRadius: 10,
    padding: 16,
    marginBottom: 16,
    maxHeight: 400,
    overflowY: 'auto',
  },
  outputLabel: {
    color: '#8b949e',
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  feedbackBlock: { marginBottom: 16 },
  feedbackLabel: { display: 'block', color: '#9ca3af', fontSize: 12, marginBottom: 6, fontWeight: 500 },
  feedbackInput: {
    width: '100%',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 10,
    padding: '10px 14px',
    color: '#e6edf3',
    fontSize: 13,
    resize: 'vertical',
    outline: 'none',
    fontFamily: 'inherit',
    lineHeight: 1.5,
  },
  feedbackHint: { color: '#6b7280', fontSize: 12, lineHeight: 1.5, margin: '8px 0 0' },
  actionError: {
    color: '#fca5a5',
    fontSize: 12,
    lineHeight: 1.5,
    margin: '8px 0 0',
    padding: '8px 10px',
    borderRadius: 8,
    background: '#7f1d1d33',
    border: '1px solid #dc262640',
  },
  buttonRow: { display: 'flex', gap: 10, flexWrap: 'wrap' },
  btnContinue: {
    padding: '10px 22px',
    borderRadius: 10,
    border: 'none',
    cursor: 'pointer',
    background: 'linear-gradient(135deg, #059669, #10b981)',
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 600,
  },
  btnImprove: {
    padding: '10px 22px',
    borderRadius: 10,
    cursor: 'pointer',
    background: '#7c3aed15',
    color: '#a78bfa',
    border: '1px solid #7c3aed40',
    fontSize: 14,
    fontWeight: 600,
  },
  btnRetry: {
    padding: '10px 22px',
    borderRadius: 10,
    cursor: 'pointer',
    background: '#dc262615',
    color: '#f87171',
    border: '1px solid #dc262640',
    fontSize: 14,
    fontWeight: 600,
  },
  liveFeed: { background: '#111827', border: '1px solid #1f2937', borderRadius: 10, overflow: 'hidden' },
  liveFeedHeader: { display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderBottom: '1px solid #1f2937' },
  liveFeedBody: { display: 'flex', flexDirection: 'column', gap: 10, padding: 12 },
  activityCard: {
    borderRadius: 12,
    padding: '12px 14px',
    border: '1px solid #243041',
    background: '#0f172a',
  },
  activityInfo: { borderColor: '#22314d', background: '#111827' },
  activitySuccess: { borderColor: '#14532d', background: '#0d1f17' },
  activityWarning: { borderColor: '#7c5a10', background: '#20180b' },
  activityError: { borderColor: '#7f1d1d', background: '#241214' },
  activityTitleRow: { display: 'flex', alignItems: 'flex-start', gap: 10 },
  activityIcon: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 42,
    height: 24,
    borderRadius: 999,
    background: '#0b1220',
    color: '#93c5fd',
    border: '1px solid #334155',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: 0.5,
  },
  activityMetaRow: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' },
  activityTitle: { margin: 0, color: '#e5e7eb', fontSize: 14, fontWeight: 600, lineHeight: 1.4 },
  activityDetail: { margin: '8px 0 0', color: '#cbd5e1', fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' },
  activityTime: { color: '#64748b', fontSize: 11, fontFamily: 'monospace' },
};

export default ResearchWorkspace;
