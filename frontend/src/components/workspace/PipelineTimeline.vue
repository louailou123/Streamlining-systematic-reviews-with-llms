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
        <ApprovalCard
          v-if="item.requiresApproval"
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
import ErrorCard from './ErrorCard.vue';
import ResultCard from './ResultCard.vue';
import StatusCard from './StatusCard.vue';

defineProps<{
  items: UiTimelineItem[];
  approvalDescription: string | null;
  approvalOutput: Record<string, unknown> | null;
  feedback: string;
  actionLoading: string;
  actionError: string;
  actionErrorTarget: string;
  runtimeMessage: string | null;
}>();

defineEmits<{
  continue: [];
  improve: [];
  retry: [nodeExecutionId: string];
  'update:feedback': [value: string];
}>();

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
