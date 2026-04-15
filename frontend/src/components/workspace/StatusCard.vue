<template>
  <StepCard :title="item.title" :step-label="item.stepLabel" :meta-label="metaLabel">
    <template #status>
      <StatusBadge :status="item.status" />
      <span v-if="durationLabel" class="text-xs muted-copy mono">{{ durationLabel }}</span>
    </template>

    <div class="status-card">
      <div class="surface-inline-note" :class="toneClass">
        <strong class="status-card__label">{{ item.statusTitle }}</strong>
        <span class="muted-copy">{{ item.statusDescription }}</span>
      </div>

      <ul v-if="detailLines.length" class="result-summary-list">
        <li v-for="line in detailLines" :key="line">{{ line }}</li>
      </ul>
    </div>
  </StepCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import type { UiTimelineItem } from '@/types/research';
import { formatDuration } from '@/lib/workflow';
import StatusBadge from '@/components/app/StatusBadge.vue';
import StepCard from './StepCard.vue';

const props = defineProps<{
  item: UiTimelineItem;
}>();

const durationLabel = computed(() => formatDuration(props.item.durationMs));
const detailLines = computed(() => props.item.detailLines.filter((line) => line.trim()));
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

const toneClass = computed(() => {
  if (props.item.status === 'failed') {
    return 'is-danger';
  }

  if (props.item.status === 'paused') {
    return 'is-warning';
  }

  if (props.item.status === 'completed' || props.item.status === 'approved') {
    return 'is-success';
  }

  return '';
});
</script>

<style scoped>
.status-card {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.status-card__label {
  font-size: 0.9rem;
  font-weight: 600;
}
</style>
