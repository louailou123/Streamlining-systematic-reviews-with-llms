<template>
  <div class="auth-shell">
    <div class="auth-shell__content">
      <div class="auth-shell__brand">
        <div class="auth-shell__mark">Li</div>
        <div class="flex flex-column gap-1">
          <span class="text-sm font-semibold">LiRA</span>
          <span class="text-xs muted-copy">Calm research workspace</span>
        </div>
      </div>

      <Card class="auth-shell__card">
        <template #content>
          <div class="flex flex-column gap-4">
            <div class="flex flex-column gap-2">
              <span class="eyebrow">{{ eyebrow }}</span>
              <h1 class="app-heading">{{ title }}</h1>
              <p class="app-subheading">{{ description }}</p>
            </div>

            <slot />
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import Card from 'primevue/card';

defineProps<{
  eyebrow: string;
  title: string;
  description: string;
}>();
</script>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.auth-shell__content {
  width: min(100%, 32rem);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.auth-shell__brand {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0 0.2rem;
}

.auth-shell__mark {
  width: 2.5rem;
  height: 2.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  background: rgba(18, 128, 92, 0.12);
  color: var(--app-accent);
  font-weight: 800;
  letter-spacing: -0.04em;
}

.auth-shell__card {
  border-radius: 1.6rem;
  border: 1px solid var(--app-border);
  background: var(--app-surface-strong);
  box-shadow: var(--app-shadow-lg);
}
</style>
