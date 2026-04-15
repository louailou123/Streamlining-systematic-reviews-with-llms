<template>
  <StepCard :title="item.title" :step-label="item.stepLabel" :meta-label="metaLabel">
    <template #status>
      <StatusBadge :status="item.status" />
    </template>

    <div class="error-card">
      <div class="surface-inline-note is-danger">
        <strong class="error-card__label">Step failed</strong>
        <span class="muted-copy">{{ item.errorMessage || 'This step failed and needs your attention.' }}</span>
      </div>

      <ul v-if="item.summaryLines.length" class="result-summary-list">
        <li v-for="line in item.summaryLines" :key="line">{{ line }}</li>
      </ul>

      <p v-if="item.feedbackText" class="m-0 text-sm muted-copy line-height-3">
        Last feedback: {{ item.feedbackText }}
      </p>

      <div v-if="actionError" class="surface-inline-note">
        <span class="muted-copy">{{ actionError }}</span>
      </div>
    </div>

    <template #footer>
      <Button
        label="Retry step"
        icon="pi pi-refresh"
        severity="danger"
        size="small"
        :loading="isRetrying"
        :disabled="disableActions"
        @click="$emit('retry')"
      />
    </template>
  </StepCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Button from 'primevue/button';

import type { UiTimelineItem } from '@/types/research';
import StatusBadge from '@/components/app/StatusBadge.vue';
import StepCard from './StepCard.vue';

const props = defineProps<{
  item: UiTimelineItem;
  isRetrying: boolean;
  disableActions: boolean;
  actionError: string;
}>();

defineEmits<{
  retry: [];
}>();

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
.error-card {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.error-card__label {
  font-size: 0.9rem;
  font-weight: 600;
}
</style>
