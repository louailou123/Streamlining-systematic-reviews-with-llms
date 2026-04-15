<template>
  <Card class="app-card-soft">
    <template #content>
      <div class="flex flex-column align-items-start gap-3">
        <div class="empty-state-icon">
          <i :class="icon" />
        </div>
        <div class="flex flex-column gap-2">
          <h3 class="m-0 text-xl font-semibold">{{ title }}</h3>
          <p class="m-0 muted-copy line-height-3">{{ description }}</p>
        </div>
        <div v-if="$slots.action">
          <slot name="action" />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card';

withDefaults(
  defineProps<{
    title: string;
    description: string;
    icon?: string;
  }>(),
  {
    icon: 'pi pi-inbox',
  },
);
</script>

<style scoped>
.empty-state-icon {
  display: inline-flex;
  width: 2.75rem;
  height: 2.75rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.9rem;
  background: var(--app-accent-soft);
  color: var(--app-accent);
}
</style>
