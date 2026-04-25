import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';

import { researchApi } from '@/api/research';
import { useProjectsStore } from '@/stores/projects';
import { useWorkflowStore } from '@/stores/workflow';
import type { PendingApproval, ResearchDetail, ResearchMessage, NodeExecution, Artifact } from '@/types/research';
import {
  buildWorkspaceNarrative,
  buildTimelineItems,
  deriveApprovalOutput,
  formatEventFeed,
  getErrorMessage,
} from '@/lib/workflow';

export function useWorkspace(researchId: string) {
  const workflowStore = useWorkflowStore();
  const projectsStore = useProjectsStore();
  const { events, pendingApproval, currentNode, isRunning, isPaused, connectionStatus } = storeToRefs(workflowStore);

  const research = ref<ResearchDetail | null>(null);
  const messages = ref<ResearchMessage[]>([]);
  const nodeExecutions = ref<NodeExecution[]>([]);
  const artifacts = ref<Artifact[]>([]);
  const artifactsLoading = ref(false);
  const loading = ref(true);
  const refreshing = ref(false);
  const loadError = ref('');
  const feedback = ref('');
  const actionLoading = ref('');
  const actionError = ref('');
  const actionErrorTarget = ref('');
  const detailsVisible = ref(false);
  const prevEventsLength = ref(0);
  const optimisticActions = ref<Record<string, 'continue' | 'improve' | 'retry'>>({});

  function setOptimisticAction(nodeExecutionId: string, action: 'continue' | 'improve' | 'retry') {
    optimisticActions.value = {
      ...optimisticActions.value,
      [nodeExecutionId]: action,
    };
  }

  function clearOptimisticAction(nodeExecutionId: string) {
    const nextActions = { ...optimisticActions.value };
    delete nextActions[nodeExecutionId];
    optimisticActions.value = nextActions;
  }

  function reconcileOptimisticActions(nextNodes: NodeExecution[]) {
    const nextActions = { ...optimisticActions.value };

    for (const nodeExecutionId of Object.keys(nextActions)) {
      const nextNode = nextNodes.find((node) => node.id === nodeExecutionId);
      if (!nextNode || nextNode.status !== 'waiting_for_approval') {
        delete nextActions[nodeExecutionId];
      }
    }

    optimisticActions.value = nextActions;
  }

  function upsertProjectSummary(detail: ResearchDetail) {
    projectsStore.upsertProject({
      id: detail.id,
      title: detail.title,
      topic: detail.topic,
      status: detail.status,
      current_step: detail.current_step,
      created_at: detail.created_at,
      updated_at: detail.updated_at,
      completed_at: detail.completed_at,
      latest_summary: detail.latest_summary,
    });
  }

  async function loadInitialData() {
    refreshing.value = true;
    loadError.value = '';

    try {
      const [nextResearch, nextMessages, nextNodes, nextPending] = await Promise.all([
        researchApi.get(researchId),
        researchApi.getMessages(researchId),
        researchApi.getNodeExecutions(researchId),
        researchApi.getPendingApproval(researchId).catch(() => null),
      ]);

      research.value = nextResearch;
      messages.value = nextMessages;
      nodeExecutions.value = nextNodes;
      workflowStore.setPendingApproval(nextPending?.has_pending ? { ...nextPending, _source: 'rest' } : null);
      reconcileOptimisticActions(nextNodes);
      upsertProjectSummary(nextResearch);
    } catch (error) {
      loadError.value = getErrorMessage(error, 'Failed to load this research workspace.');
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  async function loadArtifacts() {
    artifactsLoading.value = true;
    try {
      const response = await researchApi.getArtifacts(researchId);
      artifacts.value = response.items;
    } finally {
      artifactsLoading.value = false;
    }
  }

  async function getActionableApproval(): Promise<PendingApproval | null> {
    if (pendingApproval.value?.node_execution_id) {
      return pendingApproval.value;
    }

    try {
      const hydrated = await researchApi.getPendingApproval(researchId);
      if (hydrated.has_pending) {
        const resolved = { ...hydrated, _source: 'rest' as const };
        workflowStore.setPendingApproval(resolved);
        return resolved;
      }
    } catch {
      // fallback to current store state
    }

    return pendingApproval.value;
  }

  async function runApprovalAction(action: 'continue' | 'improve', request: (nodeExecutionId: string) => Promise<unknown>) {
    if (actionLoading.value) {
      return;
    }

    const approvalSnapshot = await getActionableApproval();
    if (!approvalSnapshot?.node_execution_id) {
      actionErrorTarget.value = 'approval';
      actionError.value = 'This approval is still syncing. Try again in a moment.';
      return;
    }

    actionError.value = '';
    actionErrorTarget.value = '';
    actionLoading.value = action;
    workflowStore.setPendingApproval(null);
    setOptimisticAction(approvalSnapshot.node_execution_id, action);

    try {
      await request(approvalSnapshot.node_execution_id);
      if (action === 'improve') {
        feedback.value = '';
      }
    } catch (error) {
      clearOptimisticAction(approvalSnapshot.node_execution_id);
      workflowStore.setPendingApproval(approvalSnapshot);
      actionErrorTarget.value = 'approval';
      actionError.value = getErrorMessage(error, `Unable to ${action} this step right now.`);
    } finally {
      actionLoading.value = '';
    }
  }

  async function handleContinue() {
    await runApprovalAction('continue', (nodeExecutionId) => researchApi.continueNode(researchId, nodeExecutionId));
  }

  async function handleImprove() {
    if (!feedback.value.trim()) {
      actionErrorTarget.value = 'approval';
      actionError.value = 'Add feedback before requesting an improvement.';
      return;
    }

    const feedbackSnapshot = feedback.value.trim();
    await runApprovalAction('improve', (nodeExecutionId) =>
      researchApi.improveNode(researchId, nodeExecutionId, feedbackSnapshot),
    );
  }

  async function handleRetry(nodeExecutionId: string) {
    if (actionLoading.value) {
      return;
    }

    actionError.value = '';
    actionErrorTarget.value = '';
    actionLoading.value = `retry:${nodeExecutionId}`;
    setOptimisticAction(nodeExecutionId, 'retry');

    try {
      await researchApi.retryNode(researchId, nodeExecutionId);
      await loadInitialData();
    } catch (error) {
      clearOptimisticAction(nodeExecutionId);
      actionErrorTarget.value = nodeExecutionId;
      actionError.value = getErrorMessage(error, 'Unable to retry this failed step right now.');
    } finally {
      actionLoading.value = '';
    }
  }

  async function handleRetryPipeline() {
    if (actionLoading.value) {
      return;
    }

    actionError.value = '';
    actionErrorTarget.value = '';
    actionLoading.value = 'retry:pipeline';

    try {
      await researchApi.retryPipeline(researchId);
      await loadInitialData();
    } catch (error) {
      actionError.value = getErrorMessage(error, 'Unable to retry the pipeline right now.');
    } finally {
      actionLoading.value = '';
    }
  }

  async function downloadArtifact(artifactId: string, filename: string) {
    const blob = await researchApi.downloadArtifact(artifactId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handleUploadAsreview(file: File) {
    if (actionLoading.value) {
      return;
    }

    const approvalSnapshot = await getActionableApproval();
    if (!approvalSnapshot?.node_execution_id) {
      actionErrorTarget.value = 'approval';
      actionError.value = 'This approval is still syncing. Try again in a moment.';
      return;
    }

    actionError.value = '';
    actionErrorTarget.value = '';
    actionLoading.value = 'upload';
    workflowStore.setPendingApproval(null);
    setOptimisticAction(approvalSnapshot.node_execution_id, 'continue');

    try {
      await researchApi.uploadAsreviewFile(researchId, approvalSnapshot.node_execution_id, file);
    } catch (error) {
      clearOptimisticAction(approvalSnapshot.node_execution_id);
      workflowStore.setPendingApproval(approvalSnapshot);
      actionErrorTarget.value = 'approval';
      actionError.value = getErrorMessage(error, 'Unable to upload the file right now.');
    } finally {
      actionLoading.value = '';
    }
  }

  async function openExecutionLog() {
    const url = await researchApi.openExecutionLog(researchId);
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  const timelineItems = computed(() =>
    buildTimelineItems(nodeExecutions.value, pendingApproval.value, events.value, optimisticActions.value),
  );
  const approvalOutput = computed(() => deriveApprovalOutput(pendingApproval.value, nodeExecutions.value, events.value));
  const eventFeed = computed(() => formatEventFeed(events.value));

  const databasesSummary = computed(() => {
    if (!research.value?.databases?.length) {
      return 'Not specified';
    }

    return research.value.databases.join(', ');
  });

  const runtimeMessage = computed(() => null);

  const approvalType = computed(() => pendingApproval.value?.approval_type || null);
  const asreviewUrl = computed(() => pendingApproval.value?.asreview_url || null);
  const downloadDescription = computed(() => pendingApproval.value?.download_description || null);

  const workspaceNarrative = computed(() =>
    buildWorkspaceNarrative({
      research: research.value,
      events: events.value,
      pendingApproval: pendingApproval.value,
      currentNode: currentNode.value,
      isRunning: isRunning.value,
      isPaused: isPaused.value,
      optimisticActions: optimisticActions.value,
    }),
  );

  watch(
    () => events.value.length,
    async (nextLength) => {
      if (nextLength <= prevEventsLength.value) {
        prevEventsLength.value = nextLength;
        return;
      }

      const newEvents = events.value.slice(prevEventsLength.value);
      prevEventsLength.value = nextLength;

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

      if (!newEvents.some((event) => refreshTriggers.has(event.event_type)) || actionLoading.value) {
        return;
      }

      await loadInitialData();
    },
  );

  watch(detailsVisible, (visible) => {
    if (visible && !artifacts.value.length && !artifactsLoading.value) {
      loadArtifacts().catch(() => {
        // drawer handles missing artifacts gracefully
      });
    }
  });

  onMounted(async () => {
    prevEventsLength.value = 0;
    await loadInitialData();
    workflowStore.connectWebSocket(researchId);
  });

  onUnmounted(() => {
    workflowStore.disconnectWebSocket();
  });

  return {
    research,
    messages,
    artifacts,
    artifactsLoading,
    loading,
    refreshing,
    loadError,
    feedback,
    actionLoading,
    actionError,
    actionErrorTarget,
    detailsVisible,
    pendingApproval,
    connectionStatus,
    timelineItems,
    approvalOutput,
    eventFeed,
    databasesSummary,
    runtimeMessage,
    workspaceNarrative,
    loadInitialData,
    loadArtifacts,
    handleContinue,
    handleImprove,
    handleRetry,
    handleRetryPipeline,
    handleUploadAsreview,
    downloadArtifact,
    openExecutionLog,
    approvalType,
    asreviewUrl,
    downloadDescription,
  };
}
