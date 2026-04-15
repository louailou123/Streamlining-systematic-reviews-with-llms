<template>
  <div class="workspace-header">
    <div class="workspace-header__copy">
      <span class="eyebrow">Workspace</span>
      <h1 class="app-heading">{{ title }}</h1>
      <p class="app-subheading">{{ description }}</p>
    </div>

    <div class="workspace-header__actions">
      <StatusBadge :status="status" />
      <RealtimeIndicator :status="connectionStatus" />
      <Button
        label="Refresh"
        icon="pi pi-refresh"
        severity="secondary"
        :loading="refreshing"
        @click="$emit('refresh')"
      />
      <Button
        label="Details"
        icon="pi pi-sliders-h"
        severity="secondary"
        @click="$emit('toggle-details')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button';

import type { ConnectionStatus } from '@/types/research';
import RealtimeIndicator from './RealtimeIndicator.vue';
import StatusBadge from './StatusBadge.vue';

defineProps<{
  title: string;
  description: string;
  status: string | null | undefined;
  connectionStatus: ConnectionStatus;
  refreshing: boolean;
}>();

defineEmits<{
  refresh: [];
  'toggle-details': [];
}>();
</script>

<style scoped>
.workspace-header {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.workspace-header__copy {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.workspace-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
}

@media (min-width: 960px) {
  .workspace-header {
    align-items: flex-start;
    flex-direction: row;
    justify-content: space-between;
  }

  .workspace-header__actions {
    justify-content: flex-end;
  }
}
</style>
