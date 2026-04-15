<template>
  <Tag :value="label" rounded :class="badgeClass" />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Tag from 'primevue/tag';

const props = defineProps<{
  status: string | null | undefined;
}>();

const normalizedStatus = computed(() => (props.status || 'pending').toLowerCase());

const label = computed(() => {
  switch (normalizedStatus.value) {
    case 'running':
      return 'Running';
    case 'completed':
      return 'Completed';
    case 'approved':
      return 'Approved';
    case 'failed':
      return 'Failed';
    case 'paused':
    case 'waiting_for_approval':
      return 'Needs review';
    default:
      return 'Pending';
  }
});

const badgeClass = computed(() => ({
  'surface-status': true,
  'surface-status--running': normalizedStatus.value === 'running',
  'surface-status--completed': normalizedStatus.value === 'completed' || normalizedStatus.value === 'approved',
  'surface-status--failed': normalizedStatus.value === 'failed',
  'surface-status--paused':
    normalizedStatus.value === 'paused' || normalizedStatus.value === 'waiting_for_approval',
  'surface-status--pending':
    !['running', 'completed', 'approved', 'failed', 'paused', 'waiting_for_approval'].includes(normalizedStatus.value),
}));
</script>

<style scoped>
.surface-status {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  border: 1px solid transparent;
}

.surface-status--running {
  background: var(--app-accent-soft);
  color: var(--app-accent);
  border-color: rgba(18, 128, 92, 0.18);
}

.surface-status--completed {
  background: rgba(22, 163, 74, 0.12);
  color: #15803d;
  border-color: rgba(22, 163, 74, 0.16);
}

.surface-status--failed {
  background: rgba(220, 38, 38, 0.12);
  color: #dc2626;
  border-color: rgba(220, 38, 38, 0.16);
}

.surface-status--paused {
  background: rgba(217, 119, 6, 0.14);
  color: #b45309;
  border-color: rgba(217, 119, 6, 0.2);
}

.surface-status--pending {
  background: rgba(148, 163, 184, 0.12);
  color: var(--app-text-soft);
  border-color: var(--app-border);
}

:global(html.app-dark) .surface-status--completed {
  color: #86efac;
}

:global(html.app-dark) .surface-status--failed {
  color: #fca5a5;
}

:global(html.app-dark) .surface-status--paused {
  color: #fdba74;
}
</style>
