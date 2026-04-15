<template>
  <AppShell>
    <template #header>
      <div class="dashboard-header">
        <div class="flex flex-column gap-1">
          <span class="eyebrow">Overview</span>
          <div class="text-xl font-semibold">Research workspace</div>
        </div>
        <Button
          label="Refresh"
          icon="pi pi-refresh"
          severity="secondary"
          :loading="projectsStore.loading"
          @click="refreshProjects"
        />
      </div>
    </template>

    <div class="dashboard-page">
      <section class="dashboard-intro">
        <div class="flex flex-column gap-3">
          <h1 class="app-heading">Start a review or return to one that is already in progress.</h1>
          <p class="app-subheading">
            The experience is intentionally simple: create a workflow, then review each pipeline step inside a focused workspace.
          </p>
        </div>

        <div class="dashboard-summary">
          <span class="dashboard-summary__item">Running {{ runningCount }}</span>
          <span class="dashboard-summary__item">Needs review {{ reviewCount }}</span>
          <span class="dashboard-summary__item">Completed {{ completedCount }}</span>
        </div>
      </section>

      <Card class="app-card dashboard-compose-card">
        <template #content>
          <div class="dashboard-compose">
            <div class="flex flex-column gap-2">
              <span class="eyebrow">New Review</span>
              <h2 class="m-0 text-xl font-semibold">Describe the question you want to investigate</h2>
              <p class="app-subheading">
                Start broad if needed. The workflow will turn the question into clear, reviewable steps after creation.
              </p>
            </div>

            <Message v-if="createError" severity="error" class="w-full">
              {{ createError }}
            </Message>

            <Textarea
              id="research-topic"
              v-model="topic"
              rows="6"
              auto-resize
              placeholder="Example: How does artificial intelligence improve food safety and quality control in industrial food processing?"
              class="dashboard-compose__textarea"
            />

            <div class="flex flex-column gap-3">
              <span class="eyebrow">Suggestions</span>
              <div class="dashboard-suggestions">
                <Button
                  v-for="suggestion in suggestedTopics"
                  :key="suggestion"
                  :label="suggestion"
                  severity="secondary"
                  text
                  size="small"
                  @click="topic = suggestion"
                />
              </div>
            </div>

            <div class="dashboard-compose__footer">
              <p class="m-0 muted-copy">
                You will move directly into the live workspace after the project is created.
              </p>

              <Button
                label="Start research"
                icon="pi pi-arrow-right"
                icon-pos="right"
                :loading="creating"
                :disabled="!topic.trim() || creating"
                @click="handleCreate"
              />
            </div>
          </div>
        </template>
      </Card>

      <Card class="app-card">
        <template #content>
          <div class="dashboard-projects">
            <div class="dashboard-projects__header">
              <div class="flex flex-column gap-1">
                <span class="eyebrow">Recent Projects</span>
                <h2 class="m-0 text-xl font-semibold">Resume existing work</h2>
                <p class="app-subheading">
                  Open any workspace to continue approvals, inspect outputs, or retry failed steps.
                </p>
              </div>

              <div class="dashboard-projects__tools">
                <InputText
                  v-model="searchQuery"
                  placeholder="Search projects"
                />
                <Tag :value="`${projectsStore.sortedItems.length} total`" severity="secondary" />
              </div>
            </div>

            <Message v-if="projectsStore.error" severity="error" class="w-full">
              {{ projectsStore.error }}
            </Message>

            <LoadingState
              v-if="projectsStore.loading && !projectsStore.sortedItems.length"
              title="Loading projects"
              description="Pulling your recent research workspaces."
            />

            <EmptyState
              v-else-if="!filteredProjects.length"
              :title="projectsStore.sortedItems.length ? 'No matching projects' : 'No research projects yet'"
              :description="projectsStore.sortedItems.length
                ? 'Try another search term or clear the filter to see more workspaces.'
                : 'Create your first research workflow to start building a review.'"
              icon="pi pi-folder-open"
            >
              <template v-if="projectsStore.sortedItems.length" #action>
                <Button
                  label="Clear search"
                  icon="pi pi-times"
                  severity="secondary"
                  @click="searchQuery = ''"
                />
              </template>
            </EmptyState>

            <div v-else class="dashboard-project-list">
              <button
                v-for="project in filteredProjects"
                :key="project.id"
                type="button"
                class="dashboard-project-row"
                @click="openProject(project.id)"
              >
                <div class="dashboard-project-row__main">
                  <div class="flex flex-wrap align-items-center gap-2">
                    <StatusBadge :status="project.status" />
                    <Tag
                      v-if="project.current_step"
                      :value="project.current_step"
                      severity="secondary"
                    />
                  </div>

                  <div class="flex flex-column gap-2 min-w-0">
                    <div class="dashboard-project-row__title">
                      {{ project.title }}
                    </div>
                    <p class="dashboard-project-row__copy">
                      {{ project.latest_summary || project.topic }}
                    </p>
                  </div>
                </div>

                <div class="dashboard-project-row__aside">
                  <div class="dashboard-project-row__dates">
                    <span>Created {{ formatDate(project.created_at) }}</span>
                    <span v-if="project.completed_at">Finished {{ formatDate(project.completed_at) }}</span>
                  </div>
                  <span class="dashboard-project-row__cta">Open</span>
                </div>
              </button>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';

import AppShell from '@/components/app/AppShell.vue';
import StatusBadge from '@/components/app/StatusBadge.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import { getErrorMessage } from '@/lib/workflow';
import { useProjectsStore } from '@/stores/projects';

const router = useRouter();
const projectsStore = useProjectsStore();

const topic = ref('');
const searchQuery = ref('');
const creating = ref(false);
const createError = ref('');

const suggestedTopics = [
  'Artificial intelligence applications in food safety and quality control',
  'Machine learning for early disease detection in primary care',
  'Renewable energy adoption and sustainable development outcomes',
];

const filteredProjects = computed(() => {
  const normalizedQuery = searchQuery.value.trim().toLowerCase();
  if (!normalizedQuery) {
    return projectsStore.sortedItems;
  }

  return projectsStore.sortedItems.filter((project) => {
    const haystack = `${project.title} ${project.topic} ${project.latest_summary || ''}`.toLowerCase();
    return haystack.includes(normalizedQuery);
  });
});

const runningCount = computed(() => projectsStore.sortedItems.filter((project) => project.status === 'running').length);
const reviewCount = computed(() =>
  projectsStore.sortedItems.filter((project) => ['paused', 'waiting_for_approval'].includes(project.status)).length,
);
const completedCount = computed(() => projectsStore.sortedItems.filter((project) => project.status === 'completed').length);

function formatDate(value: string | null) {
  if (!value) {
    return 'Not started';
  }

  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

async function refreshProjects() {
  try {
    await projectsStore.fetchProjects(true);
  } catch {
    // handled by store state
  }
}

async function handleCreate() {
  if (!topic.value.trim() || creating.value) {
    return;
  }

  createError.value = '';
  creating.value = true;

  try {
    const project = await projectsStore.createProject({ topic: topic.value.trim() });
    await router.push(`/research/${project.id}`);
  } catch (error) {
    createError.value = getErrorMessage(error, 'Failed to create a research workflow.');
    creating.value = false;
  }
}

async function openProject(id: string) {
  await router.push(`/research/${id}`);
}

onMounted(() => {
  projectsStore.fetchProjects().catch(() => {
    // handled by store state
  });
});
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 1.35rem;
}

.dashboard-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.dashboard-intro {
  display: grid;
  gap: 1rem;
}

.dashboard-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.dashboard-summary__item {
  padding: 0.62rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--app-border);
  background: var(--app-surface-soft);
  color: var(--app-text-soft);
  font-size: 0.9rem;
  font-weight: 600;
}

.dashboard-compose-card :deep(.p-card-body) {
  padding: 1.5rem;
}

.dashboard-compose {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.dashboard-compose__textarea {
  min-height: 10.5rem;
}

.dashboard-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.dashboard-compose__footer {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.dashboard-projects {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.dashboard-projects__header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dashboard-projects__tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.dashboard-project-list {
  display: flex;
  flex-direction: column;
}

.dashboard-project-row {
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.05rem 0;
  border: 0;
  border-top: 1px solid var(--app-border);
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.dashboard-project-row:first-child {
  border-top: 0;
  padding-top: 0;
}

.dashboard-project-row:last-child {
  padding-bottom: 0;
}

.dashboard-project-row__main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dashboard-project-row__title {
  font-size: 1rem;
  font-weight: 600;
}

.dashboard-project-row__copy {
  margin: 0;
  color: var(--app-text-soft);
  line-height: 1.65;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.dashboard-project-row__aside {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.7rem;
}

.dashboard-project-row__dates {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.84rem;
  color: var(--app-text-soft);
  text-align: right;
}

.dashboard-project-row__cta {
  color: var(--app-text);
  font-size: 0.9rem;
  font-weight: 600;
}

@media (max-width: 760px) {
  .dashboard-project-row {
    flex-direction: column;
  }

  .dashboard-project-row__aside {
    align-items: flex-start;
  }

  .dashboard-project-row__dates {
    text-align: left;
  }
}

@media (min-width: 960px) {
  .dashboard-intro {
    grid-template-columns: minmax(0, 1fr) 16rem;
    align-items: end;
  }

  .dashboard-compose__footer {
    align-items: center;
    flex-direction: row;
    justify-content: space-between;
  }

  .dashboard-projects__header {
    align-items: end;
    flex-direction: row;
    justify-content: space-between;
  }
}
</style>
