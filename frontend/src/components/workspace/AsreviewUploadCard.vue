<template>
  <StepCard :title="item.title" :step-label="item.stepLabel" :meta-label="metaLabel">
    <template #status>
      <StatusBadge status="paused" />
    </template>

    <div class="asreview-card">
      <!-- Download section (for llm_classify gate — download_and_continue type) -->
      <div v-if="approvalType === 'download_and_continue'" class="surface-inline-note is-success">
        <strong class="asreview-card__label">
          <i class="pi pi-check-circle" /> LLM Screening Complete
        </strong>
        <span class="muted-copy">
          {{ downloadDescription || 'Download the ASReview import file with the LLM screening results.' }}
        </span>
      </div>

      <ul v-if="summaryLines.length" class="result-summary-list">
        <li v-for="line in summaryLines" :key="line">{{ line }}</li>
      </ul>

      <div v-if="approvalType === 'download_and_continue'" class="asreview-card__actions-row">
        <Button
          label="Download asreview_import.csv"
          icon="pi pi-download"
          severity="secondary"
          size="small"
          :loading="downloading"
          @click="handleDownload"
        />
      </div>

      <!-- ASReview upload section (for asreview_screen gate — asreview_upload type) -->
      <div v-if="approvalType === 'asreview_upload'" class="surface-inline-note is-warning">
        <strong class="asreview-card__label">
          <i class="pi pi-external-link" /> ASReview Manual Screening
        </strong>
        <span class="muted-copy">
          Screen the papers in ASReview LAB, then upload the exported result file here.
        </span>
      </div>

      <div v-if="approvalType === 'asreview_upload'" class="asreview-card__actions-col">
        <div class="asreview-card__actions-row">
          <Button
            label="Open ASReview LAB"
            icon="pi pi-external-link"
            size="small"
            @click="openAsreview"
          />
          <Button
            label="Download asreview_import.csv"
            icon="pi pi-download"
            severity="secondary"
            size="small"
            :loading="downloading"
            @click="handleDownload"
          />
        </div>

        <div class="asreview-card__upload-zone" :class="{ 'is-drag-over': isDragOver }">
          <input
            ref="fileInputRef"
            type="file"
            accept=".csv,.xlsx,.ris"
            class="asreview-card__file-input"
            @change="handleFileSelect"
          />

          <div
            v-if="!selectedFile"
            class="asreview-card__dropzone"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
            @click="fileInputRef?.click()"
          >
            <i class="pi pi-upload asreview-card__upload-icon" />
            <span class="asreview-card__upload-label">
              Drop ASReview export file here or <strong>browse</strong>
            </span>
            <span class="muted-copy text-xs">Supported: CSV, XLSX, RIS</span>
          </div>

          <div v-else class="asreview-card__selected-file">
            <div class="asreview-card__file-info">
              <i class="pi pi-file" />
              <span>{{ selectedFile.name }}</span>
              <span class="muted-copy text-xs">{{ formatFileSize(selectedFile.size) }}</span>
            </div>
            <Button
              icon="pi pi-times"
              severity="secondary"
              text
              size="small"
              rounded
              @click="clearFile"
            />
          </div>
        </div>
      </div>

      <div v-if="actionError" class="surface-inline-note is-danger">
        <span class="muted-copy">{{ actionError }}</span>
      </div>
    </div>

    <template #footer>
      <Button
        v-if="approvalType === 'download_and_continue'"
        label="Continue to ASReview"
        icon="pi pi-arrow-right"
        size="small"
        :loading="actionLoading === 'continue'"
        :disabled="Boolean(actionLoading)"
        @click="$emit('continue')"
      />
      <Button
        v-if="approvalType === 'asreview_upload'"
        label="Upload & Continue"
        icon="pi pi-check"
        size="small"
        :loading="actionLoading === 'upload'"
        :disabled="!selectedFile || Boolean(actionLoading)"
        @click="$emit('upload', selectedFile!)"
      />
    </template>
  </StepCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from 'primevue/button';

import type { UiTimelineItem } from '@/types/research';
import { summarizeOutputSummary } from '@/lib/workflow';
import StatusBadge from '@/components/app/StatusBadge.vue';
import StepCard from './StepCard.vue';

const props = defineProps<{
  item: UiTimelineItem;
  approvalType: string;
  outputSummary: Record<string, unknown> | null;
  actionLoading: string;
  actionError: string;
  asreviewUrl: string | null;
  downloadDescription: string | null;
  researchId: string;
}>();

defineEmits<{
  continue: [];
  upload: [file: File];
  download: [];
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const isDragOver = ref(false);
const downloading = ref(false);

const summaryLines = computed(() => summarizeOutputSummary(props.outputSummary));
const metaLabel = computed(() => {
  const parts = [];
  if (props.item.attemptNumber > 1) {
    parts.push(`Attempt ${props.item.attemptNumber}`);
  }
  if (props.item.revisionNumber > 0) {
    parts.push(`Revision ${props.item.revisionNumber}`);
  }
  return parts.join(' | ') || null;
});

function openAsreview() {
  const url = props.asreviewUrl || 'http://localhost:5001';
  window.open(url, '_blank', 'noopener,noreferrer');
}

async function handleDownload() {
  downloading.value = true;
  try {
    const { researchApi } = await import('@/api/research');
    const blob = await researchApi.downloadWorkflowArtifact(props.researchId, 'asreview_import.csv');
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'asreview_import.csv';
    link.click();
    URL.revokeObjectURL(url);
  } catch {
    // Fallback: just emit download event
  } finally {
    downloading.value = false;
  }
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files?.length) {
    selectedFile.value = target.files[0];
  }
}

function handleDrop(event: DragEvent) {
  isDragOver.value = false;
  if (event.dataTransfer?.files?.length) {
    selectedFile.value = event.dataTransfer.files[0];
  }
}

function clearFile() {
  selectedFile.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<style scoped>
.asreview-card {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.asreview-card__label {
  font-size: 0.9rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.asreview-card__actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.asreview-card__actions-col {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.asreview-card__upload-zone {
  position: relative;
  border-radius: 1rem;
  transition: border-color 0.2s ease;
}

.asreview-card__file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
}

.asreview-card__dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.8rem 1.2rem;
  border: 2px dashed var(--app-border-strong);
  border-radius: 1rem;
  background: var(--app-surface-soft);
  cursor: pointer;
  text-align: center;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease;
}

.asreview-card__dropzone:hover,
.is-drag-over .asreview-card__dropzone {
  border-color: var(--app-accent);
  background: var(--app-accent-soft);
}

.asreview-card__upload-icon {
  font-size: 1.5rem;
  color: var(--app-accent);
}

.asreview-card__upload-label {
  font-size: 0.88rem;
  color: var(--app-text-soft);
}

.asreview-card__selected-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  padding: 0.8rem 1rem;
  border: 1px solid rgba(18, 128, 92, 0.24);
  border-radius: 1rem;
  background: rgba(18, 128, 92, 0.06);
}

.asreview-card__file-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  font-size: 0.88rem;
  font-weight: 500;
}

.asreview-card__file-info i {
  color: var(--app-accent);
}
</style>
