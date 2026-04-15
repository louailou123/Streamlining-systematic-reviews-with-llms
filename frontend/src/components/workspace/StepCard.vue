<template>
  <Card class="timeline-card step-card">
    <template #content>
      <div class="step-card__body">
        <div class="step-card__header">
          <div class="step-card__heading">
            <div class="step-card__meta">
              <span v-if="stepLabel" class="eyebrow">{{ stepLabel }}</span>
              <span v-if="metaLabel" class="text-xs muted-copy mono">{{ metaLabel }}</span>
            </div>
            <h3 class="step-card__title">{{ title }}</h3>
          </div>

          <div class="step-card__status">
            <slot name="status" />
          </div>
        </div>

        <div v-if="$slots.default" class="step-card__content">
          <slot />
        </div>

        <div v-if="$slots.footer" class="step-card__footer">
          <slot name="footer" />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card';

defineProps<{
  title: string;
  stepLabel: string | null;
  metaLabel?: string | null;
}>();
</script>

<style scoped>
.step-card :deep(.p-card-body) {
  padding: 1rem 1.1rem;
}

.step-card__body {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.step-card__header {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.step-card__heading {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.step-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem 0.7rem;
}

.step-card__title {
  margin: 0;
  font-size: 1rem;
  line-height: 1.4;
  font-weight: 600;
}

.step-card__status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}

.step-card__content {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.step-card__footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--app-border);
}

@media (min-width: 960px) {
  .step-card__header {
    align-items: flex-start;
    flex-direction: row;
    justify-content: space-between;
  }

  .step-card__status {
    justify-content: flex-end;
  }
}
</style>
