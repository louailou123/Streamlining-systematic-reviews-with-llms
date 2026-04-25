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

          <div
            v-if="research.latest_error && research.status === 'failed'"
            class="pipeline-error-banner"
          >
            <Message severity="error" class="w-full">
              {{ research.latest_error }}
            </Message>
            <Button
              label="Retry Pipeline"
              icon="pi pi-refresh"
              severity="danger"
              size="small"
              :loading="actionLoading === 'retry:pipeline'"
              @click="handleRetryPipeline"
            />
          </div>
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
          :approval-type="approvalType"
          :asreview-url="asreviewUrl"
          :download-description="downloadDescription"
          :research-id="id"
          @continue="handleContinue"
          @improve="handleImprove"
          @retry="handleRetry"
          @upload="handleUploadAsreview"
          @update:feedback="feedback = $event"
        />

        <!-- Download PDF button at end of completed pipeline -->
        <div v-if="research?.status === 'completed'" class="workspace-download-section">
          <div class="surface-inline-note is-success">
            <strong class="workspace-status__title">
              <i class="pi pi-check-circle" /> Literature Review Ready
            </strong>
            <span class="muted-copy">Your final literature review is ready. Download it as a PDF file.</span>
          </div>
          <Button
            label="Download Literature Review (PDF)"
            icon="pi pi-file-pdf"
            size="small"
            :loading="downloadingPdf"
            @click="handleDownloadPdf"
          />
        </div>
      </div>
    </div>

    <DetailsDrawer
      :visible="detailsVisible"
      :research="research"
      :databases-summary="databasesSummary"
      :artifacts="artifacts"
      :artifacts-loading="artifactsLoading"
      :event-feed="eventFeed"
      :visible-node-names="visibleNodeNames"
      :messages="displayMessages"
      @update:visible="detailsVisible = $event"
      @refresh-artifacts="loadArtifacts"
      @download-artifact="downloadArtifact"
      @open-execution-log="openExecutionLog"
    />
  </AppShell>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
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
import { researchApi } from '@/api/research';

const props = defineProps<{
  id: string;
}>();

const router = useRouter();
const downloadingPdf = ref(false);
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
  approvalType,
  asreviewUrl,
  downloadDescription,
  loadInitialData,
  loadArtifacts,
  handleContinue,
  handleImprove,
  handleRetry,
  handleRetryPipeline,
  handleUploadAsreview,
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

const visibleNodeNames = computed(() => new Set(timelineItems.value.map((item) => item.nodeName)));

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

async function handleDownloadPdf() {
  downloadingPdf.value = true;
  try {
    const blob = await researchApi.downloadWorkflowArtifact(props.id, 'literature_review_final.md');
    const markdownText = await blob.text();

    // Convert markdown to simple styled HTML
    const htmlContent = markdownToHtml(markdownText);

    // Open a new window and trigger print (save as PDF)
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      // Fallback: download as .md if popup blocked
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'literature_review_final.md';
      link.click();
      URL.revokeObjectURL(url);
      return;
    }

    printWindow.document.write(htmlContent);
    printWindow.document.close();

    // Wait for content to render, then trigger print
    printWindow.onload = () => {
      setTimeout(() => {
        printWindow.print();
      }, 400);
    };
  } catch {
    // Silently handle
  } finally {
    downloadingPdf.value = false;
  }
}

function markdownToHtml(md: string): string {
  // Simple markdown to HTML conversion
  let html = md
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Headers
    .replace(/^##### (.+)$/gm, '<h5>$1</h5>')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold and italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Unordered lists
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    // Numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Paragraphs (double newlines)
    .replace(/\n\n/g, '</p><p>')
    // Single newlines within paragraphs
    .replace(/\n/g, '<br/>');

  // Wrap consecutive <li> items in <ul>
  html = html.replace(/(<li>.*?<\/li>)(?:<br\/>)?/g, '$1');
  html = html.replace(/((?:<li>.*?<\/li>)+)/g, '<ul>$1</ul>');

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Literature Review</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body {
      font-family: 'Inter', system-ui, sans-serif;
      line-height: 1.8;
      color: #1a1a1a;
      max-width: 48rem;
      margin: 2rem auto;
      padding: 0 2rem;
      font-size: 11pt;
    }
    h1 { font-size: 1.8em; margin: 1.5em 0 0.5em; font-weight: 700; color: #111; }
    h2 { font-size: 1.4em; margin: 1.3em 0 0.4em; font-weight: 600; color: #222; border-bottom: 1px solid #e5e5e5; padding-bottom: 0.3em; }
    h3 { font-size: 1.15em; margin: 1.1em 0 0.3em; font-weight: 600; color: #333; }
    h4, h5 { font-size: 1em; margin: 1em 0 0.2em; font-weight: 600; color: #444; }
    p { margin: 0.6em 0; }
    ul { padding-left: 1.5em; margin: 0.5em 0; }
    li { margin: 0.3em 0; }
    strong { font-weight: 600; }
    @media print {
      body { margin: 0; padding: 1rem; font-size: 10pt; }
      @page { margin: 2cm; }
    }
  </style>
</head>
<body>
  <p>${html}</p>
</body>
</html>`;
}
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

.workspace-download-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.pipeline-error-banner {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.75rem;
  align-items: flex-start;
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
