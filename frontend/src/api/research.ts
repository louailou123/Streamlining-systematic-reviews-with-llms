import client from './client';
import type {
  Approval,
  Artifact,
  CreateResearchRequest,
  NodeExecution,
  PendingApproval,
  ResearchDetail,
  ResearchMessage,
  ResearchSummary,
} from '@/types/research';

export const researchApi = {
  async list(skip = 0, limit = 20): Promise<{ items: ResearchSummary[]; total: number }> {
    const response = await client.get('/research', { params: { skip, limit } });
    return response.data;
  },

  async create(data: CreateResearchRequest): Promise<ResearchDetail> {
    const response = await client.post<ResearchDetail>('/research', data);
    return response.data;
  },

  async get(id: string): Promise<ResearchDetail> {
    const response = await client.get<ResearchDetail>(`/research/${id}`);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await client.delete(`/research/${id}`);
  },

  async getMessages(id: string, skip = 0, limit = 200): Promise<ResearchMessage[]> {
    const response = await client.get<ResearchMessage[]>(`/research/${id}/messages`, {
      params: { skip, limit },
    });
    return response.data;
  },

  async getArtifacts(id: string): Promise<{ items: Artifact[]; total: number }> {
    const response = await client.get(`/artifacts/${id}`);
    return response.data;
  },

  async getApprovals(id: string): Promise<Approval[]> {
    const response = await client.get<Approval[]>(`/approvals/${id}`);
    return response.data;
  },

  async startWorkflow(researchId: string) {
    const response = await client.post(`/workflow/${researchId}/start`);
    return response.data;
  },

  async cancelWorkflow(researchId: string) {
    const response = await client.post(`/workflow/${researchId}/cancel`);
    return response.data;
  },

  async getNodeExecutions(researchId: string): Promise<NodeExecution[]> {
    const response = await client.get<NodeExecution[]>(`/workflow/${researchId}/nodes`);
    return response.data;
  },

  async getPendingApproval(researchId: string): Promise<PendingApproval> {
    const response = await client.get<PendingApproval>(`/workflow/${researchId}/pending-approval`);
    return response.data;
  },

  async continueNode(researchId: string, nodeExecutionId: string) {
    const response = await client.post(`/workflow/${researchId}/nodes/${nodeExecutionId}/action`, {
      action: 'continue',
    });
    return response.data;
  },

  async improveNode(researchId: string, nodeExecutionId: string, feedback: string) {
    const response = await client.post(`/workflow/${researchId}/nodes/${nodeExecutionId}/action`, {
      action: 'improve_result',
      feedback,
    });
    return response.data;
  },

  async retryNode(researchId: string, nodeExecutionId: string) {
    const response = await client.post(`/workflow/${researchId}/nodes/${nodeExecutionId}/action`, {
      action: 'retry',
    });
    return response.data;
  },

  async retryPipeline(researchId: string) {
    const response = await client.post(`/workflow/${researchId}/retry`);
    return response.data;
  },

  async downloadArtifact(artifactId: string): Promise<Blob> {
    const response = await client.get(`/artifacts/${artifactId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  async openExecutionLog(researchId: string): Promise<string> {
    const response = await client.get(`/research/${researchId}/execution_log`, {
      responseType: 'blob',
    });
    return URL.createObjectURL(response.data);
  },

  async uploadAsreviewFile(researchId: string, nodeExecutionId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post(
      `/workflow/${researchId}/nodes/${nodeExecutionId}/upload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },

  async downloadWorkflowArtifact(researchId: string, filename: string): Promise<Blob> {
    const response = await client.get(`/artifacts/${researchId}/by-name/${filename}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};
