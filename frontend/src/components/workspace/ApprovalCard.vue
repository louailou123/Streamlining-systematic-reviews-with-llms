<template>
  <StepCard :title="item.title" :step-label="item.stepLabel" :meta-label="metaLabel">
    <template #status>
      <StatusBadge status="paused" />
    </template>

    <div class="approval-card">
      <div class="surface-inline-note is-warning">
        <strong class="approval-card__label">Review needed</strong>
        <span class="muted-copy">{{ description || 'This step is waiting for your review.' }}</span>
      </div>

      <ul v-if="summaryLines.length" class="result-summary-list">
        <li v-for="line in summaryLines" :key="line">{{ line }}</li>
      </ul>
      <p v-else class="m-0 muted-copy line-height-3">
        The latest output for this step is syncing. You can still approve it or request an improvement.
      </p>

      <Button
        :label="showFeedback ? 'Hide feedback' : 'Improve with feedback'"
        icon="pi pi-comment"
        severity="secondary"
        text
        size="small"
        @click="showFeedback = !showFeedback"
      />

      <FeedbackBox
        v-if="showFeedback"
        :model-value="feedback"
        @update:model-value="$emit('update:feedback', $event)"
      />

      <div v-if="actionError" class="surface-inline-note is-danger">
        <span class="muted-copy">{{ actionError }}</span>
      </div>
    </div>

    <template #footer>
      <Button
        label="Continue"
        icon="pi pi-check"
        size="small"
        :loading="actionLoading === 'continue'"
        :disabled="Boolean(actionLoading)"
        @click="$emit('continue')"
      />
      <Button
        label="Send feedback"
        icon="pi pi-send"
        severity="secondary"
        size="small"
        :loading="actionLoading === 'improve'"
        :disabled="Boolean(actionLoading) || !feedback.trim()"
        @click="$emit('improve')"
      />
    </template>
  </StepCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from 'primevue/button';

import type { UiTimelineItem } from '@/types/research';
import { summarizeOutputSummary } from '@/lib/workflow';
import StatusBadge from '@/components/app/StatusBadge.vue';
import FeedbackBox from './FeedbackBox.vue';
import StepCard from './StepCard.vue';

const props = defineProps<{
  item: UiTimelineItem;
  description: string | null;
  outputSummary: Record<string, unknown> | null;
  feedback: string;
  actionLoading: string;
  actionError: string;
}>();

defineEmits<{
  continue: [];
  improve: [];
  'update:feedback': [value: string];
}>();

const showFeedback = ref(false);

const summaryLines = computed(() => summarizeOutputSummary(props.outputSummary));
const metaLabel = computed(() => {
  const parts = [];
  if (props.item.attemptNumber > 1) {
    parts.push(`Attempt ${props.item.attemptNumber}`);
  }
  if (props.item.revisionNumber > 0) {
    parts.push(`Revision ${props.item.revisionNumber}`);
  }
  return parts.join(' | ') || null;
});
</script>

<style scoped>
.approval-card {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.approval-card__label {
  font-size: 0.9rem;
  font-weight: 600;
}
</style>
