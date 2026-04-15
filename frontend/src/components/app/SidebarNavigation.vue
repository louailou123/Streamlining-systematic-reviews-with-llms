<template>
  <div class="sidebar-shell">
    <div class="sidebar-top">
      <RouterLink to="/" class="sidebar-brand">
        <div class="brand-mark">Li</div>
        <div class="flex flex-column gap-1">
          <span class="text-sm font-semibold">LiRA</span>
          <span class="text-xs muted-copy">Systematic review workspace</span>
        </div>
      </RouterLink>

      <Button
        label="New research"
        icon="pi pi-plus"
        class="sidebar-primary-button"
        @click="navigateToDashboard"
      />

      <div class="sidebar-section">
        <div class="sidebar-section__header">
          <label class="eyebrow">History</label>
          <span class="sidebar-section__meta">{{ projectsStore.sortedItems.length }}</span>
        </div>
        <InputText v-model="query" placeholder="Search projects" />
      </div>

      <div class="sidebar-projects">
        <Skeleton v-if="projectsStore.loading && !projectsStore.sortedItems.length" height="3.5rem" borderRadius="1rem" />
        <Skeleton v-if="projectsStore.loading && !projectsStore.sortedItems.length" height="3.5rem" borderRadius="1rem" />
        <Message
          v-else-if="projectsStore.error"
          severity="secondary"
          class="w-full"
        >
          {{ projectsStore.error }}
        </Message>
        <div v-else class="sidebar-projects__list">
          <RouterLink
            v-for="project in filteredProjects"
            :key="project.id"
            :to="`/research/${project.id}`"
            class="sidebar-project-link"
            :class="{ 'is-active': activeProjectId === project.id }"
          >
            <div class="sidebar-project__body">
              <div class="sidebar-project__row">
                <span class="sidebar-project__title">
                  {{ project.title }}
                </span>
                <StatusBadge :status="project.status" />
              </div>
              <p class="sidebar-project__copy">
                {{ project.latest_summary || project.topic }}
              </p>
            </div>
          </RouterLink>

          <EmptyState
            v-if="!filteredProjects.length && !projectsStore.loading"
            title="No matching projects"
            description="Try another search or create a new workflow."
            icon="pi pi-search"
          />
        </div>
      </div>
    </div>

    <div class="sidebar-bottom">
      <div class="sidebar-user app-card-soft">
        <div class="sidebar-user__content">
          <Avatar
            :label="userInitial"
            shape="circle"
            size="large"
          />
          <div class="sidebar-user__copy">
            <div class="sidebar-user__name">
              {{ authStore.user?.full_name || authStore.user?.email || 'Workspace user' }}
            </div>
            <div class="sidebar-user__email">
              {{ authStore.user?.email }}
            </div>
          </div>
        </div>
      </div>

      <div class="sidebar-actions">
        <Button
          :label="themeLabel"
          :icon="themeIcon"
          severity="secondary"
          class="sidebar-theme-button"
          @click="toggleTheme"
        />
        <Button
          icon="pi pi-sign-out"
          severity="secondary"
          aria-label="Logout"
          @click="handleLogout"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import Avatar from 'primevue/avatar';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Skeleton from 'primevue/skeleton';

import { useAuthStore } from '@/stores/auth';
import { useProjectsStore } from '@/stores/projects';
import { useTheme } from '@/composables/useTheme';
import EmptyState from '@/components/common/EmptyState.vue';
import StatusBadge from './StatusBadge.vue';

const props = defineProps<{
  activeProjectId?: string | null;
}>();

const router = useRouter();
const authStore = useAuthStore();
const projectsStore = useProjectsStore();
const { resolvedTheme, toggleTheme } = useTheme();
const query = ref('');

onMounted(() => {
  if (authStore.isAuthenticated) {
    projectsStore.fetchProjects().catch(() => {
      // sidebar shows its own error state
    });
  }
});

const filteredProjects = computed(() => {
  const normalizedQuery = query.value.trim().toLowerCase();
  if (!normalizedQuery) {
    return projectsStore.sortedItems;
  }

  return projectsStore.sortedItems.filter((project) => {
    const haystack = `${project.title} ${project.topic} ${project.latest_summary || ''}`.toLowerCase();
    return haystack.includes(normalizedQuery);
  });
});

const userInitial = computed(() =>
  (authStore.user?.full_name || authStore.user?.email || 'U').charAt(0).toUpperCase(),
);

const themeLabel = computed(() =>
  resolvedTheme.value === 'dark' ? 'Switch to light' : 'Switch to dark',
);

const themeIcon = computed(() =>
  resolvedTheme.value === 'dark' ? 'pi pi-sun' : 'pi pi-moon',
);

async function handleLogout() {
  await authStore.logout();
  await router.push('/login');
}

async function navigateToDashboard() {
  await router.push('/');
}
</script>

<style scoped>
.sidebar-shell {
  width: 100%;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.15rem 1rem 1rem;
  overflow: hidden;
}

.sidebar-top {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

.sidebar-brand {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.35rem 0.2rem 0.1rem;
  overflow: hidden;
}

.brand-mark {
  width: 2.35rem;
  height: 2.35rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.9rem;
  background: rgba(18, 128, 92, 0.1);
  color: var(--app-accent);
  font-weight: 800;
  letter-spacing: -0.04em;
}

.sidebar-section {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.sidebar-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.sidebar-section__meta {
  font-size: 0.8rem;
  color: var(--app-subtle);
}

.sidebar-projects {
  width: 100%;
  min-width: 0;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.sidebar-projects__list {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: calc(100vh - 17rem);
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 0.15rem;
}

.sidebar-project__row {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.sidebar-project__body {
  width: 100%;
  min-width: 0;
}

.sidebar-project__title {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 0.92rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-project__copy {
  margin: 0.45rem 0 0;
  color: var(--app-text-soft);
  font-size: 0.84rem;
  line-height: 1.55;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.sidebar-bottom {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sidebar-user {
  width: 100%;
  min-width: 0;
  padding: 0.85rem 0.95rem;
  overflow: hidden;
}

.sidebar-user__content {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sidebar-user__copy {
  min-width: 0;
  flex: 1 1 auto;
}

.sidebar-user__name {
  font-size: 0.9rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-user__email {
  margin-top: 0.22rem;
  font-size: 0.78rem;
  color: var(--app-text-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-actions {
  width: 100%;
  min-width: 0;
  display: flex;
  gap: 0.55rem;
}

.sidebar-primary-button,
.sidebar-theme-button {
  width: 100%;
}

.sidebar-actions :deep(.sidebar-theme-button) {
  flex: 1 1 auto;
  min-width: 0;
}

.sidebar-project__row :deep(.surface-status) {
  flex-shrink: 0;
}

:deep(.sidebar-primary-button.p-button),
:deep(.sidebar-theme-button.p-button) {
  width: 100%;
}

:global(html.app-dark) .brand-mark {
  color: #d4fff1;
}
</style>
