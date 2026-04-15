<template>
  <AppShell :active-project-id="id">
    <template #header>
      <WorkspaceHeader
        :title="headerTitle"
        :description="headerDescription"
        :status="research?.status"
        :connection-status="connectionStatus"
        :refreshing="refreshing"
        @refresh="loadInitialData"
        @toggle-details="detailsVisible = true"
      />
    </template>

    <LoadingState
      v-if="loading"
      title="Loading workspace"
      description="Pulling the latest messages, approvals, node executions, and live workflow state."
    />

    <Card v-else-if="loadError" class="app-card">
      <template #content>
        <div class="workspace-error-state">
          <div class="flex flex-column gap-2">
            <span class="eyebrow">Workspace Unavailable</span>
            <h2 class="m-0 text-xl font-semibold">We could not load this research workspace</h2>
            <p class="app-subheading">{{ loadError }}</p>
          </div>

          <div class="flex flex-wrap gap-2">
            <Button
              label="Try again"
              icon="pi pi-refresh"
              @click="loadInitialData"
            />
            <Button
              label="Back to dashboard"
              icon="pi pi-arrow-left"
              severity="secondary"
              @click="router.push('/')"
            />
          </div>
        </div>
      </template>
    </Card>

    <div v-else class="workspace-page">
      <Card v-if="research" class="app-card-soft workspace-context">
        <template #content>
          <div class="workspace-context__layout">
            <div class="workspace-context__main">
              <span class="eyebrow">Research Topic</span>
              <p class="workspace-context__topic">{{ research.topic }}</p>
            </div>

            <div class="workspace-context__meta">
              <Tag
                v-if="research.current_step"
                :value="research.current_step"
                severity="secondary"
              />
              <Tag
                v-if="research.timeframe"
                :value="research.timeframe"
                severity="secondary"
              />
            </div>
          </div>

          <Message
            v-if="research.latest_error && !timelineItems.some((item) => item.isFailed)"
            severity="error"
            class="w-full mt-3"
          >
            {{ research.latest_error }}
          </Message>
        </template>
      </Card>

      <div class="workspace-flow">
        <div
          v-if="workspaceNarrative"
          class="surface-inline-note workspace-status"
          :class="workspaceStatusClass"
        >
          <strong class="workspace-status__title">{{ workspaceNarrative.title }}</strong>
          <p class="m-0 muted-copy line-height-3">{{ workspaceNarrative.description }}</p>
          <ul v-if="workspaceNarrative.details.length" class="result-summary-list">
            <li v-for="line in workspaceNarrative.details" :key="line">{{ line }}</li>
          </ul>
        </div>

        <PipelineTimeline
          :items="timelineItems"
          :approval-description="pendingApproval?.description || null"
          :approval-output="approvalOutput"
          :feedback="feedback"
          :action-loading="actionLoading"
          :action-error="actionError"
          :action-error-target="actionErrorTarget"
          :runtime-message="runtimeMessage"
          @continue="handleContinue"
          @improve="handleImprove"
          @retry="handleRetry"
          @update:feedback="feedback = $event"
        />
      </div>
    </div>

    <DetailsDrawer
      :visible="detailsVisible"
      :research="research"
      :databases-summary="databasesSummary"
      :artifacts="artifacts"
      :artifacts-loading="artifactsLoading"
      :event-feed="eventFeed"
      :messages="displayMessages"
      @update:visible="detailsVisible = $event"
      @refresh-artifacts="loadArtifacts"
      @download-artifact="downloadArtifact"
      @open-execution-log="openExecutionLog"
    />
  </AppShell>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import Button from 'primevue/button';
import Card from 'primevue/card';
import Message from 'primevue/message';
import Tag from 'primevue/tag';

import AppShell from '@/components/app/AppShell.vue';
import WorkspaceHeader from '@/components/app/WorkspaceHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import { useWorkspace } from '@/composables/useWorkspace';
import DetailsDrawer from '@/components/workspace/DetailsDrawer.vue';
import PipelineTimeline from '@/components/workspace/PipelineTimeline.vue';

const props = defineProps<{
  id: string;
}>();

const router = useRouter();
const {
  research,
  messages,
  artifacts,
  artifactsLoading,
  loading,
  refreshing,
  loadError,
  feedback,
  actionLoading,
  actionError,
  actionErrorTarget,
  detailsVisible,
  pendingApproval,
  connectionStatus,
  timelineItems,
  approvalOutput,
  eventFeed,
  databasesSummary,
  runtimeMessage,
  workspaceNarrative,
  loadInitialData,
  loadArtifacts,
  handleContinue,
  handleImprove,
  handleRetry,
  downloadArtifact,
  openExecutionLog,
} = useWorkspace(props.id);

const headerTitle = computed(() => research.value?.title || 'Research workspace');
const headerDescription = computed(() =>
  research.value?.latest_summary ||
  research.value?.topic ||
  'Review progress step by step and keep long details in the side drawer.',
);
const displayMessages = computed(() => messages.value.filter((message) => message.message_type !== 'approval'));
const workspaceStatusClass = computed(() => {
  if (!workspaceNarrative.value) {
    return '';
  }

  if (workspaceNarrative.value.tone === 'error') {
    return 'is-danger';
  }

  if (workspaceNarrative.value.tone === 'warning') {
    return 'is-warning';
  }

  if (workspaceNarrative.value.tone === 'success') {
    return 'is-success';
  }

  return '';
});
</script>

<style scoped>
.workspace-page {
  display: grid;
  gap: 1rem;
}

.workspace-flow {
  width: min(100%, 54rem);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.workspace-context :deep(.p-card-body) {
  padding: 1.15rem 1.25rem;
}

.workspace-context__layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.workspace-context__main {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.workspace-context__topic {
  margin: 0;
  font-size: 1rem;
  line-height: 1.75;
  color: var(--app-text);
}

.workspace-context__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.workspace-error-state {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.workspace-status__title {
  font-size: 0.96rem;
  font-weight: 600;
}

@media (min-width: 960px) {
  .workspace-context__layout {
    align-items: start;
    flex-direction: row;
    justify-content: space-between;
  }

  .workspace-context__meta {
    justify-content: flex-end;
  }
}
</style>
