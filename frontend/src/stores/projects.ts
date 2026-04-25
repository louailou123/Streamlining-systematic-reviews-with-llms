import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import { researchApi } from '@/api/research';
import type { CreateResearchRequest, ResearchSummary } from '@/types/research';

export const useProjectsStore = defineStore('projects', () => {
  const items = ref<ResearchSummary[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const loaded = ref(false);
  const error = ref('');

  const sortedItems = computed(() =>
    [...items.value].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
  );

  async function fetchProjects(force = false) {
    if (loaded.value && !force) {
      return;
    }

    loading.value = true;
    error.value = '';

    try {
      const response = await researchApi.list();
      items.value = response.items;
      total.value = response.total;
      loaded.value = true;
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Unable to load research projects right now.';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function createProject(payload: CreateResearchRequest) {
    const project = await researchApi.create(payload);
    await fetchProjects(true);
    return project;
  }

  function upsertProject(project: ResearchSummary) {
    const index = items.value.findIndex((item) => item.id === project.id);
    if (index >= 0) {
      items.value.splice(index, 1, project);
    } else {
      items.value.unshift(project);
      total.value += 1;
    }
  }

  async function deleteProject(id: string) {
    await researchApi.delete(id);
    const index = items.value.findIndex((item) => item.id === id);
    if (index >= 0) {
      items.value.splice(index, 1);
      total.value = Math.max(0, total.value - 1);
    }
  }

  return {
    items,
    total,
    loading,
    loaded,
    error,
    sortedItems,
    fetchProjects,
    createProject,
    upsertProject,
    deleteProject,
  };
});
