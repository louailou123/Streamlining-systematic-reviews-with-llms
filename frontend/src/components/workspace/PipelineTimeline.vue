<template>
  <div class="pipeline-feed">
    <div v-if="runtimeMessage" class="surface-inline-note pipeline-feed__note">
      <span class="muted-copy">{{ runtimeMessage }}</span>
    </div>

    <EmptyState
      v-if="!items.length"
      title="No pipeline steps yet"
      description="Once the workflow starts producing step results, they will appear here in a clean sequence."
      icon="pi pi-sparkles"
    />

    <Timeline v-else :value="items" align="left" class="w-full pipeline-feed__timeline">
      <template #marker="{ item }">
        <span class="timeline-marker" :class="markerClass(item)" />
      </template>
      <template #content="{ item }">
        <AsreviewUploadCard
          v-if="item.requiresApproval && isAsreviewType(item)"
          :item="item"
          :approval-type="resolveApprovalType(item)"
          :output-summary="approvalOutput"
          :action-loading="actionLoading"
          :action-error="actionErrorTarget === 'approval' ? actionError : ''"
          :asreview-url="asreviewUrl"
          :download-description="downloadDescription"
          :research-id="researchId"
          @continue="$emit('continue')"
          @upload="$emit('upload', $event)"
          @download="$emit('download')"
        />
        <ApprovalCard
          v-else-if="item.requiresApproval"
          :item="item"
          :description="approvalDescription"
          :output-summary="approvalOutput"
          :feedback="feedback"
          :action-loading="actionLoading"
          :action-error="actionErrorTarget === 'approval' ? actionError : ''"
          @continue="$emit('continue')"
          @improve="$emit('improve')"
          @update:feedback="$emit('update:feedback', $event)"
        />
        <ErrorCard
          v-else-if="item.isFailed"
          :item="item"
          :is-retrying="actionLoading === `retry:${item.nodeExecutionId}`"
          :disable-actions="Boolean(actionLoading)"
          :action-error="actionErrorTarget === item.nodeExecutionId ? actionError : ''"
          @retry="$emit('retry', item.nodeExecutionId)"
        />
        <ResultCard v-else-if="item.isCompleted" :item="item" />
        <StatusCard v-else :item="item" />
      </template>
    </Timeline>
  </div>
</template>

<script setup lang="ts">
import Timeline from 'primevue/timeline';

import type { UiTimelineItem } from '@/types/research';
import EmptyState from '@/components/common/EmptyState.vue';
import ApprovalCard from './ApprovalCard.vue';
import AsreviewUploadCard from './AsreviewUploadCard.vue';
import ErrorCard from './ErrorCard.vue';
import ResultCard from './ResultCard.vue';
import StatusCard from './StatusCard.vue';

const props = defineProps<{
  items: UiTimelineItem[];
  approvalDescription: string | null;
  approvalOutput: Record<string, unknown> | null;
  feedback: string;
  actionLoading: string;
  actionError: string;
  actionErrorTarget: string;
  runtimeMessage: string | null;
  approvalType: string | null;
  asreviewUrl: string | null;
  downloadDescription: string | null;
  researchId: string;
}>();

defineEmits<{
  continue: [];
  improve: [];
  retry: [nodeExecutionId: string];
  upload: [file: File];
  download: [];
  'update:feedback': [value: string];
}>();

const ASREVIEW_TYPES = new Set(['download_and_continue', 'asreview_upload']);

function isAsreviewType(item: UiTimelineItem) {
  // Check if the pending approval type is an asreview variant
  if (props.approvalType && ASREVIEW_TYPES.has(props.approvalType)) {
    return true;
  }
  // Fallback: check by node name
  return item.nodeName === 'llm_classify' || item.nodeName === 'asreview_screen';
}

function resolveApprovalType(item: UiTimelineItem) {
  if (props.approvalType) {
    return props.approvalType;
  }
  // Fallback by node name
  if (item.nodeName === 'llm_classify') {
    return 'download_and_continue';
  }
  if (item.nodeName === 'asreview_screen') {
    return 'asreview_upload';
  }
  return 'node_approval';
}

function markerClass(item: UiTimelineItem) {
  if (item.isFailed) {
    return 'is-error';
  }

  if (item.requiresApproval) {
    return 'is-warning';
  }

  if (item.status === 'running') {
    return 'is-running';
  }

  if (item.status === 'completed' || item.status === 'approved') {
    return 'is-success';
  }

  return 'is-default';
}
</script>

<style scoped>
.pipeline-feed {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pipeline-feed__note {
  max-width: 54rem;
}
</style>
