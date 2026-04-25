import type {
  NodeExecution,
  OptimisticNodeAction,
  PendingApproval,
  ResearchDetail,
  UiTimelineItem,
  WorkflowEvent,
  WorkspaceNarrative,
} from '@/types/research';

function humanizeLabel(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export function humanizeNodeName(nodeName?: string | null) {
  if (!nodeName) {
    return 'Pipeline step';
  }

  return humanizeLabel(nodeName);
}

export function shortenText(value: string, maxLength = 180) {
  const normalized = value.replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }

  return `${normalized.slice(0, maxLength).trimEnd()}...`;
}

function summarizeValue(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) {
    return shortenText(value, 120);
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  if (Array.isArray(value)) {
    if (!value.length) {
      return null;
    }

    const primitives = value
      .slice(0, 3)
      .map((item) => {
        if (typeof item === 'string') {
          return shortenText(item, 72);
        }

        if (typeof item === 'number' || typeof item === 'boolean') {
          return String(item);
        }

        if (item && typeof item === 'object') {
          const record = item as Record<string, unknown>;
          const preferred = record.question ?? record.title ?? record.name ?? record.label;
          if (typeof preferred === 'string' && preferred.trim()) {
            return shortenText(preferred, 72);
          }
        }

        return null;
      })
      .filter((entry): entry is string => Boolean(entry));

    if (primitives.length) {
      const remainder = value.length - primitives.length;
      return remainder > 0 ? `${primitives.join(', ')} and ${remainder} more` : primitives.join(', ');
    }

    return `${value.length} items`;
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, nestedValue]) =>
        typeof nestedValue === 'string' || typeof nestedValue === 'number' || typeof nestedValue === 'boolean',
      )
      .slice(0, 2)
      .map(([key, nestedValue]) => `${humanizeLabel(key)}: ${shortenText(String(nestedValue), 72)}`);

    return entries.length ? entries.join(' | ') : `${Object.keys(value as Record<string, unknown>).length} fields`;
  }

  return null;
}

export function describeOutputSummary(data?: Record<string, unknown> | null, limit = 12): string[] {
  if (!data) {
    return [];
  }

  const skipKeys = new Set(['messages', 'logs', 'errors', 'user_feedback', 'current_approval_node', 'current_step']);

  return Object.entries(data)
    .filter(([key, value]) => !skipKeys.has(key) && value !== null && value !== undefined && value !== '')
    .slice(0, limit)
    .map(([key, value]) => {
      const summary = summarizeValue(value);
      return summary ? `${humanizeLabel(key)}: ${summary}` : null;
    })
    .filter((entry): entry is string => Boolean(entry));
}

/**
 * Expand specific keys (keywords, queries, criteria) to show ALL items
 * instead of truncating. Used in approval cards where full visibility is needed.
 */
export function expandOutputSummary(data?: Record<string, unknown> | null): string[] {
  if (!data) {
    return [];
  }

  const expandKeys = new Set([
    'keywords', 'search_queries', 'inclusion_criteria', 'exclusion_criteria',
    'initial_questions', 'final_ranked_questions',
  ]);
  const skipKeys = new Set(['messages', 'logs', 'errors', 'user_feedback', 'current_approval_node', 'current_step']);
  const lines: string[] = [];

  for (const [key, value] of Object.entries(data)) {
    if (skipKeys.has(key) || value === null || value === undefined || value === '') {
      continue;
    }

    if (expandKeys.has(key)) {
      // Show ALL items for these keys
      if (Array.isArray(value)) {
        lines.push(`${humanizeLabel(key)} (${value.length}):`);
        for (const item of value) {
          if (typeof item === 'string') {
            lines.push(`  • ${item}`);
          } else if (item && typeof item === 'object') {
            const record = item as Record<string, unknown>;
            const preferred = record.question ?? record.title ?? record.name ?? record.label;
            if (typeof preferred === 'string') {
              lines.push(`  • ${preferred}`);
            } else {
              lines.push(`  • ${JSON.stringify(item)}`);
            }
          } else {
            lines.push(`  • ${String(item)}`);
          }
        }
      } else if (value && typeof value === 'object' && !Array.isArray(value)) {
        // For dict-like keys (e.g. search_queries: {db_name: query})
        const entries = Object.entries(value as Record<string, unknown>);
        lines.push(`${humanizeLabel(key)} (${entries.length}):`);
        for (const [subKey, subValue] of entries) {
          lines.push(`  • ${humanizeLabel(subKey)}: ${String(subValue)}`);
        }
      } else {
        const summary = summarizeValue(value);
        if (summary) {
          lines.push(`${humanizeLabel(key)}: ${summary}`);
        }
      }
    } else {
      // Show full content for all keys (since cards now have scroll)
      if (Array.isArray(value) && value.length > 0) {
        lines.push(`${humanizeLabel(key)} (${value.length}):`);
        for (const item of value) {
          if (typeof item === 'string') {
            lines.push(`  • ${item}`);
          } else if (item && typeof item === 'object') {
            const record = item as Record<string, unknown>;
            const preferred = record.question ?? record.title ?? record.name ?? record.label ?? record.description;
            if (typeof preferred === 'string') {
              lines.push(`  • ${preferred}`);
            } else {
              lines.push(`  • ${JSON.stringify(item)}`);
            }
          } else if (item !== null && item !== undefined) {
            lines.push(`  • ${String(item)}`);
          }
        }
      } else if (typeof value === 'string' && value.trim()) {
        lines.push(`${humanizeLabel(key)}: ${value}`);
      } else {
        const summary = summarizeValue(value);
        if (summary) {
          lines.push(`${humanizeLabel(key)}: ${summary}`);
        }
      }
    }
  }

  return lines;
}

export function summarizeOutputSummary(data?: Record<string, unknown> | null): string[] {
  if (!data) {
    return [];
  }

  // Since all pipeline cards now have scroll containers,
  // always show the full expanded output for every key.
  return expandOutputSummary(data);
}

export function deriveApprovalOutput(
  pendingApproval: PendingApproval | null,
  nodeExecutions: NodeExecution[],
  events: WorkflowEvent[],
) {
  if (!pendingApproval) {
    return null;
  }

  if (pendingApproval.output_summary && Object.keys(pendingApproval.output_summary).length) {
    return pendingApproval.output_summary;
  }

  const latestEventMatch = [...events]
    .reverse()
    .find(
      (event) =>
        event.event_type === 'NODE_COMPLETED' &&
        event.node_name === pendingApproval.node_name &&
        event.data?.output_summary &&
        Object.keys(event.data.output_summary).length,
    );

  if (latestEventMatch?.data?.output_summary) {
    return latestEventMatch.data.output_summary;
  }

  const latestNodeMatch = [...nodeExecutions]
    .filter(
      (node) =>
        node.node_name === pendingApproval.node_name &&
        node.output_summary &&
        Object.keys(node.output_summary).length,
    )
    .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0];

  return latestNodeMatch?.output_summary ?? null;
}

function formatFriendlyTime(value?: string | null) {
  if (!value) {
    return null;
  }

  return new Date(value).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  });
}

function getLatestNodeEvent(events: WorkflowEvent[], nodeName: string) {
  return [...events]
    .reverse()
    .find((event) => event.node_name === nodeName && event.event_type !== 'LOG_MESSAGE');
}

function buildTimelineStatusCopy(
  node: NodeExecution,
  events: WorkflowEvent[],
  optimisticAction?: OptimisticNodeAction,
) {
  const latestEvent = getLatestNodeEvent(events, node.node_name);
  const detailLines = describeOutputSummary(node.output_summary);
  const startedAt = formatFriendlyTime(node.started_at);

  if (optimisticAction === 'continue') {
    return {
      status: 'running',
      title: 'Continuing this step',
      description: 'Your approval was sent. The workflow is moving forward now.',
      detailLines: detailLines.length ? detailLines : ['You do not need to do anything right now.'],
    };
  }

  if (optimisticAction === 'improve') {
    return {
      status: 'running',
      title: 'Updating with your feedback',
      description: 'Your feedback was sent. This step is being updated now.',
      detailLines: node.feedback_text
        ? [`Your feedback: ${shortenText(node.feedback_text, 140)}`]
        : ['LiRA is revising this step based on your guidance.'],
    };
  }

  switch (node.status) {
    case 'running':
      return {
        status: 'running',
        title: latestEvent?.event_type === 'NODE_REVISION_STARTED'
          ? 'Updating this step'
          : latestEvent?.event_type === 'NODE_RETRY_STARTED'
            ? 'Retrying this step'
            : 'Step in progress',
        description:
          latestEvent?.message ||
          'This step is currently running. New results will appear here automatically.',
        detailLines: detailLines.length
          ? detailLines
          : [startedAt ? `Started at ${startedAt}.` : 'This step is still in progress.'],
      };
    case 'failed':
      return {
        status: 'failed',
        title: 'Step stopped',
        description: node.error_message || 'This step ran into a problem and stopped.',
        detailLines: [
          ...(node.feedback_text ? [`Last feedback: ${shortenText(node.feedback_text, 140)}`] : []),
          ...detailLines,
        ],
      };
    case 'completed':
    case 'approved':
      return {
        status: node.status,
        title: 'Completed',
        description: 'This step finished successfully.',
        detailLines,
      };
    case 'waiting_for_approval':
      return {
        status: 'paused',
        title: 'Waiting for review',
        description: 'This step is ready for your decision before the workflow can continue.',
        detailLines,
      };
    default:
      return {
        status: node.status || 'pending',
        title: 'Waiting to start',
        description: 'This step has not started yet.',
        detailLines,
      };
  }
}

/**
 * Nodes that are utility/internal and should not appear in the pipeline timeline.
 * These include tool execution nodes, internal LLM call nodes, and gate nodes.
 */
export const HIDDEN_NODE_NAMES = new Set([
  'tool_node',
  'tool_node_2',
  'feasibility_llm_call',
  'originality_llm_call',
  'rank_questions_llm_call',
]);

function isHiddenNode(nodeName: string): boolean {
  if (HIDDEN_NODE_NAMES.has(nodeName)) {
    return true;
  }
  // Gate nodes (gate_*) are internal approval infrastructure
  if (nodeName.startsWith('gate_')) {
    return true;
  }
  return false;
}

export function buildTimelineItems(
  nodeExecutions: NodeExecution[],
  pendingApproval: PendingApproval | null,
  events: WorkflowEvent[],
  optimisticActions: Partial<Record<string, OptimisticNodeAction>> = {},
): UiTimelineItem[] {
  const byNode = new Map<string, NodeExecution[]>();

  for (const node of nodeExecutions) {
    // Skip hidden utility/tool/gate nodes
    if (isHiddenNode(node.node_name)) {
      continue;
    }

    const group = byNode.get(node.node_name) ?? [];
    group.push(node);
    byNode.set(node.node_name, group);
  }

  return [...byNode.entries()]
    .map(([, executions]) => {
      const latest = [...executions].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0];
      const summaryLines = summarizeOutputSummary(latest.output_summary);
      const optimisticAction = optimisticActions[latest.id];
      const requiresApproval =
        !optimisticAction &&
        (latest.status === 'waiting_for_approval' ||
          Boolean(pendingApproval?.node_execution_id && pendingApproval.node_execution_id === latest.id));
      const statusCopy = buildTimelineStatusCopy(latest, events, optimisticAction);

      return {
        id: latest.node_name,
        nodeExecutionId: latest.id,
        nodeName: latest.node_name,
        stepLabel: latest.step_label,
        title: humanizeNodeName(latest.node_name),
        status: statusCopy.status,
        summaryLines,
        outputSummary: latest.output_summary,
        errorMessage: latest.error_message,
        attemptNumber: latest.attempt_number,
        revisionNumber: latest.revision_number,
        durationMs: latest.duration_ms,
        startedAt: latest.started_at,
        updatedAt: latest.completed_at || latest.approved_at || latest.started_at,
        feedbackText: latest.feedback_text,
        requiresApproval,
        isFailed: latest.status === 'failed',
        isCompleted: ['completed', 'approved'].includes(latest.status),
        statusTitle: statusCopy.title,
        statusDescription: statusCopy.description,
        detailLines: statusCopy.detailLines,
      };
    })
    .sort((a, b) => {
      const aExecution = nodeExecutions.find((node) => node.id === a.nodeExecutionId);
      const bExecution = nodeExecutions.find((node) => node.id === b.nodeExecutionId);
      const byOrder = (aExecution?.node_order ?? 0) - (bExecution?.node_order ?? 0);
      if (byOrder !== 0) {
        return byOrder;
      }

      return new Date(a.startedAt).getTime() - new Date(b.startedAt).getTime();
    });
}

export function buildWorkspaceNarrative(params: {
  research: ResearchDetail | null;
  events: WorkflowEvent[];
  pendingApproval: PendingApproval | null;
  currentNode: string | null;
  isRunning: boolean;
  isPaused: boolean;
  optimisticActions?: Partial<Record<string, OptimisticNodeAction>>;
}): WorkspaceNarrative | null {
  const {
    research,
    events,
    pendingApproval,
    currentNode,
    isRunning,
    isPaused,
    optimisticActions = {},
  } = params;

  const activeOptimisticAction = Object.values(optimisticActions)[0];
  const latestEvent = [...events].reverse()[0];

  if (activeOptimisticAction === 'continue') {
    return {
      tone: 'info',
      title: 'Continuing the workflow',
      description: 'Your approval was sent. The workflow is now moving to the next step.',
      details: ['You do not need to do anything right now. New updates will appear automatically.'],
    };
  }

  if (activeOptimisticAction === 'improve') {
    return {
      tone: 'info',
      title: 'Updating this step',
      description: 'Your feedback was sent. LiRA is revising this step now.',
      details: ['When the updated result is ready, it will appear in the timeline automatically.'],
    };
  }

  if (activeOptimisticAction === 'retry') {
    return {
      tone: 'info',
      title: 'Retrying the step',
      description: 'The failed step is being tried again now.',
      details: ['You can keep this page open while the workflow continues.'],
    };
  }

  if (pendingApproval?.has_pending && pendingApproval.node_name) {
    return {
      tone: 'warning',
      title: 'Review needed',
      description: `${humanizeNodeName(pendingApproval.node_name)} is ready for your decision.`,
      details: [
        'Choose Continue if the result looks good.',
        'Choose Send feedback if you want this step improved.',
      ],
    };
  }

  if (research?.status === 'failed' || latestEvent?.event_type === 'WORKFLOW_FAILED') {
    return {
      tone: 'error',
      title: 'Workflow stopped',
      description:
        research?.latest_error ||
        latestEvent?.message ||
        'The workflow stopped because one of the steps ran into a problem.',
      details: ['Check the failed step below and use Retry when you are ready to try again.'],
    };
  }

  if (isRunning && currentNode) {
    const runningEvent = getLatestNodeEvent(events, currentNode);
    return {
      tone: 'info',
      title: `Working on ${humanizeNodeName(currentNode)}`,
      description:
        runningEvent?.message ||
        'This step is currently running. New updates will appear here automatically.',
      details: ['You can keep this page open while the workflow continues in the background.'],
    };
  }

  if (research?.status === 'completed' || latestEvent?.event_type === 'WORKFLOW_COMPLETED') {
    return {
      tone: 'success',
      title: 'Workflow completed',
      description: 'All of the research steps finished successfully.',
      details: ['You can review the completed step summaries below or open the details drawer for artifacts.'],
    };
  }

  if (isPaused && research?.current_step) {
    return {
      tone: 'warning',
      title: 'Waiting for review',
      description: `${research.current_step} is waiting for your review before the workflow can continue.`,
      details: ['Use the approval card below to continue or send feedback.'],
    };
  }

  return null;
}

export function formatEventFeed(events: WorkflowEvent[]) {
  return [...events]
    .slice(-30)
    .reverse()
    .map((event, index) => {
      const summaryLines =
        event.event_type === 'NODE_COMPLETED'
          ? summarizeOutputSummary(event.data?.output_summary)
          : event.event_type === 'NODE_WAITING_FOR_APPROVAL'
            ? summarizeOutputSummary(event.data?.output_summary)
            : [];

      return {
        id: `${event.timestamp ?? 'event'}-${event.event_type}-${index}`,
        title:
          event.event_type === 'NODE_STARTED'
            ? `Started ${humanizeNodeName(event.node_name)}`
            : event.event_type === 'NODE_COMPLETED'
              ? `Completed ${humanizeNodeName(event.node_name)}`
              : event.event_type === 'NODE_FAILED'
                ? `Problem in ${humanizeNodeName(event.node_name)}`
                : event.event_type === 'NODE_WAITING_FOR_APPROVAL'
                  ? `Review required for ${humanizeNodeName(event.node_name)}`
                  : event.event_type === 'NODE_RETRY_STARTED'
                    ? `Retrying ${humanizeNodeName(event.node_name)}`
                    : event.event_type === 'NODE_REVISION_STARTED'
                      ? `Revising ${humanizeNodeName(event.node_name)}`
                      : event.event_type === 'WORKFLOW_COMPLETED'
                        ? 'Pipeline completed'
                        : event.event_type === 'WORKFLOW_FAILED'
                          ? 'Pipeline stopped'
                          : shortenText(event.message || humanizeLabel(event.event_type), 120),
        tone:
          event.event_type === 'NODE_FAILED' || event.event_type === 'WORKFLOW_FAILED'
            ? 'error'
            : event.event_type === 'NODE_WAITING_FOR_APPROVAL' ||
                event.event_type === 'NODE_RETRY_STARTED' ||
                event.event_type === 'NODE_REVISION_STARTED'
              ? 'warning'
              : event.event_type === 'NODE_COMPLETED' ||
                  event.event_type === 'WORKFLOW_COMPLETED' ||
                  event.event_type === 'ARTIFACT_CREATED'
                ? 'success'
                : 'info',
        timestamp: event.timestamp,
        stepLabel: event.step_label,
        nodeName: event.node_name,
        details:
          summaryLines.length > 0
            ? summaryLines
            : [event.message || (event.data?.error ? String(event.data.error) : 'Pipeline event')],
      };
    });
}

export function getErrorMessage(error: unknown, fallback: string) {
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

export function formatDuration(durationMs: number | null) {
  if (!durationMs) {
    return null;
  }

  return `${(durationMs / 1000).toFixed(durationMs >= 10000 ? 0 : 1)}s`;
}
