<template>
  <Tag :value="label" rounded :class="indicatorClass">
    <template #default>
      <span class="realtime-chip">
        <i class="pi pi-circle-fill realtime-dot" />
        {{ label }}
      </span>
    </template>
  </Tag>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Tag from 'primevue/tag';
import type { ConnectionStatus } from '@/types/research';

const props = defineProps<{
  status: ConnectionStatus;
}>();

const label = computed(() => {
  switch (props.status) {
    case 'connected':
      return 'Live';
    case 'authenticating':
      return 'Authenticating';
    case 'connecting':
      return 'Connecting';
    default:
      return 'Offline';
  }
});

const indicatorClass = computed(() => ({
  'realtime-indicator': true,
  'is-connected': props.status === 'connected',
  'is-waiting': props.status === 'connecting' || props.status === 'authenticating',
  'is-offline': props.status === 'disconnected',
}));
</script>

<style scoped>
.realtime-indicator {
  border: 1px solid transparent;
}

.realtime-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.realtime-dot {
  font-size: 0.5rem;
}

.is-connected {
  background: var(--app-accent-soft);
  color: var(--app-accent);
  border-color: rgba(18, 128, 92, 0.18);
}

.is-waiting {
  background: rgba(217, 119, 6, 0.12);
  color: #b45309;
  border-color: rgba(217, 119, 6, 0.16);
}

.is-offline {
  background: rgba(148, 163, 184, 0.12);
  color: var(--app-text-soft);
  border-color: var(--app-border);
}

:global(html.app-dark) .is-waiting {
  color: #fdba74;
}
</style>
