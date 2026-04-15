<template>
  <Card class="app-card-soft">
    <template #content>
      <div class="flex flex-column align-items-center text-center gap-4 py-5">
        <ProgressSpinner
          strokeWidth="4"
          style="width: 2.5rem; height: 2.5rem"
          aria-label="Loading"
        />
        <div class="flex flex-column gap-2">
          <h3 class="m-0 text-xl font-semibold">{{ title }}</h3>
          <p class="m-0 muted-copy line-height-3">{{ description }}</p>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card';
import ProgressSpinner from 'primevue/progressspinner';

defineProps<{
  title: string;
  description: string;
}>();
</script>
