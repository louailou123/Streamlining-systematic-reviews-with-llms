<template>
  <StepCard :title="item.title" :step-label="item.stepLabel" :meta-label="metaLabel">
    <template #status>
      <StatusBadge :status="item.status" />
      <span v-if="durationLabel" class="text-xs muted-copy mono">{{ durationLabel }}</span>
    </template>

    <div v-if="item.summaryLines.length" class="flex flex-column gap-3">
      <ul class="result-summary-list">
        <li v-for="line in item.summaryLines" :key="line">{{ line }}</li>
      </ul>

      <Button
        v-if="hasDetails"
        :label="expanded ? 'Hide details' : 'Show details'"
        icon="pi pi-angle-down"
        severity="secondary"
        text
        size="small"
        @click="expanded = !expanded"
      />

      <ul v-if="expanded && detailLines.length" class="result-summary-list result-summary-list--expanded">
        <li v-for="line in detailLines" :key="line">{{ line }}</li>
      </ul>
    </div>

    <p v-else class="m-0 muted-copy line-height-3">
      Completed successfully. Detailed output is available when this step produces structured data.
    </p>
  </StepCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from 'primevue/button';

import type { UiTimelineItem } from '@/types/research';
import { formatDuration } from '@/lib/workflow';
import StatusBadge from '@/components/app/StatusBadge.vue';
import StepCard from './StepCard.vue';

const props = defineProps<{
  item: UiTimelineItem;
}>();

const expanded = ref(false);

const durationLabel = computed(() => formatDuration(props.item.durationMs));
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

const hasDetails = computed(() => props.item.detailLines.length > props.item.summaryLines.length);
const detailLines = computed(() => props.item.detailLines);
</script>

<style scoped>
.result-summary-list--expanded {
  padding-top: 0.15rem;
}
</style>
