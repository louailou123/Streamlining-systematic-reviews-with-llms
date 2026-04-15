<template>
  <div class="app-page surface-grid">
    <aside class="surface-sidebar app-shell-surface hidden lg:flex">
      <SidebarNavigation :active-project-id="activeProjectId" />
    </aside>

    <div class="surface-main">
      <header class="surface-header">
        <div class="surface-header-inner">
          <Button
            icon="pi pi-bars"
            severity="secondary"
            class="lg:hidden"
            aria-label="Open navigation"
            @click="mobileSidebarVisible = true"
          />
          <slot name="header" />
        </div>
      </header>

      <main class="surface-content">
        <div class="surface-content-inner">
          <slot />
        </div>
      </main>
    </div>

    <Drawer
      v-model:visible="mobileSidebarVisible"
      position="left"
      modal
      class="lg:hidden"
      :style="{ width: '20rem' }"
    >
      <SidebarNavigation :active-project-id="activeProjectId" />
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Button from 'primevue/button';
import Drawer from 'primevue/drawer';

import SidebarNavigation from './SidebarNavigation.vue';

withDefaults(
  defineProps<{
    activeProjectId?: string | null;
  }>(),
  {
    activeProjectId: null,
  },
);

const mobileSidebarVisible = ref(false);
</script>

<style scoped>
.surface-grid {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 17.5rem minmax(0, 1fr);
}

.surface-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  min-width: 0;
  overflow: hidden;
  border-right: 1px solid var(--app-border);
  border-radius: 0;
  background: var(--app-surface-soft);
  box-shadow: none;
}

.surface-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.surface-header {
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(18px);
  background: color-mix(in srgb, var(--app-bg) 84%, transparent);
  border-bottom: 1px solid var(--app-border);
}

.surface-header-inner {
  width: min(100%, 72rem);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.1rem 1.5rem;
}

.surface-content {
  padding: 1.6rem 0 2.2rem;
}

.surface-content-inner {
  width: min(100%, 72rem);
  margin: 0 auto;
  padding: 0 1.5rem;
}

@media (max-width: 1023px) {
  .surface-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .surface-content {
    padding: 1rem 0 1.5rem;
  }

  .surface-header-inner,
  .surface-content-inner {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

:global(html.app-dark) .surface-header {
  background: color-mix(in srgb, var(--app-bg) 84%, transparent);
}
</style>
