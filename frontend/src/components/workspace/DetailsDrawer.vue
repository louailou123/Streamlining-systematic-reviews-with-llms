<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: '24rem', maxWidth: '100vw' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <template #header>
      <div class="flex flex-column gap-1">
        <span class="eyebrow">Details</span>
        <div class="text-lg font-semibold">Project context</div>
      </div>
    </template>

    <div class="flex flex-column gap-3">
      <Panel header="Research" toggleable>
        <div class="workspace-detail-list">
          <div class="workspace-detail-item">
            <div class="eyebrow">Timeframe</div>
            <div class="mt-2 line-height-3">{{ research?.timeframe || 'Not specified' }}</div>
          </div>
          <div class="workspace-detail-item">
            <div class="eyebrow">Databases</div>
            <div class="mt-2 line-height-3">{{ databasesSummary }}</div>
          </div>
          <div class="workspace-detail-item">
            <div class="eyebrow">Pipeline version</div>
            <div class="mt-2 line-height-3">{{ research?.pipeline_version || 'Default' }}</div>
          </div>
        </div>
      </Panel>

      <Panel header="Artifacts" toggleable>
        <div class="flex flex-column gap-3">
          <div class="flex gap-2">
            <Button
              label="Refresh artifacts"
              icon="pi pi-refresh"
              severity="secondary"
              @click="$emit('refresh-artifacts')"
            />
            <Button
              label="Open execution log"
              icon="pi pi-external-link"
              severity="secondary"
              @click="$emit('open-execution-log')"
            />
          </div>

          <EmptyState
            v-if="!artifacts.length && !artifactsLoading"
            title="No artifacts yet"
            description="Generated files will appear here once the pipeline produces them."
            icon="pi pi-folder"
          />
          <Skeleton v-else-if="artifactsLoading" height="5rem" borderRadius="1rem" />
          <div v-else class="flex flex-column gap-2">
            <div
              v-for="artifact in artifacts"
              :key="artifact.id"
              class="workspace-detail-item flex align-items-center justify-content-between gap-3"
            >
              <div class="min-w-0">
                <div class="text-sm font-semibold text-overflow-ellipsis overflow-hidden white-space-nowrap">
                  {{ artifact.filename }}
                </div>
                <div class="text-xs muted-copy mt-2">
                  {{ artifact.file_type }} | {{ formatBytes(artifact.file_size) }}
                </div>
              </div>
              <Button
                icon="pi pi-download"
                severity="secondary"
                aria-label="Download artifact"
                @click="$emit('download-artifact', artifact.id, artifact.filename)"
              />
            </div>
          </div>
        </div>
      </Panel>

      <Panel header="Activity" toggleable>
        <EmptyState
          v-if="!filteredEventFeed.length"
          title="No activity yet"
          description="Workflow events will appear here as the pipeline progresses."
          icon="pi pi-bolt"
        />
        <div v-else class="flex flex-column gap-2">
          <div
            v-for="entry in filteredEventFeed"
            :key="entry.id"
            class="workspace-detail-item"
          >
            <div class="flex align-items-center justify-content-between gap-3">
              <div class="text-sm font-semibold">{{ entry.title }}</div>
              <div class="text-xs muted-copy mono">{{ formatTime(entry.timestamp) }}</div>
            </div>
            <div v-if="entry.stepLabel" class="eyebrow mt-2">{{ entry.stepLabel }}</div>
            <ul class="result-summary-list mt-3" v-if="entry.details.length">
              <li v-for="detail in entry.details" :key="detail">{{ detail }}</li>
            </ul>
          </div>
        </div>
      </Panel>

      <Panel header="Messages" toggleable>
        <EmptyState
          v-if="!messages.length"
          title="No messages yet"
          description="Conversation messages will appear here when the workflow exchanges user or assistant context."
          icon="pi pi-comments"
        />
        <div v-else class="flex flex-column gap-2">
          <div
            v-for="message in messages"
            :key="message.id"
            class="workspace-detail-item"
          >
            <div class="flex align-items-center justify-content-between gap-3">
              <span class="eyebrow">{{ message.role }}</span>
              <span class="text-xs muted-copy mono">{{ formatTime(message.created_at) }}</span>
            </div>
            <p class="m-0 mt-2 line-height-3 muted-copy">{{ message.content }}</p>
          </div>
        </div>
      </Panel>
    </div>
  </Drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Button from 'primevue/button';
import Drawer from 'primevue/drawer';
import Panel from 'primevue/panel';
import Skeleton from 'primevue/skeleton';

import type { Artifact, ResearchDetail, ResearchMessage } from '@/types/research';
import { HIDDEN_NODE_NAMES } from '@/lib/workflow';
import EmptyState from '@/components/common/EmptyState.vue';

const props = defineProps<{
  visible: boolean;
  research: ResearchDetail | null;
  databasesSummary: string;
  artifacts: Artifact[];
  artifactsLoading: boolean;
  eventFeed: Array<{
    id: string;
    title: string;
    details: string[];
    stepLabel?: string;
    timestamp?: string;
    nodeName?: string;
  }>;
  visibleNodeNames: Set<string>;
  messages: ResearchMessage[];
}>();

defineEmits<{
  'update:visible': [value: boolean];
  'refresh-artifacts': [];
  'download-artifact': [artifactId: string, filename: string];
  'open-execution-log': [];
}>();

const filteredEventFeed = computed(() =>
  props.eventFeed.filter((entry) => {
    // Always show events without a node name (workflow-level events)
    if (!entry.nodeName) return true;
    // Hide events from internal/hidden nodes
    if (HIDDEN_NODE_NAMES.has(entry.nodeName)) return false;
    if (entry.nodeName.startsWith('gate_')) return false;
    return true;
  }),
);

function formatTime(value?: string) {
  if (!value) {
    return '';
  }

  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatBytes(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
</script>
