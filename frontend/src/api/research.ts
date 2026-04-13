import client from './client';

export interface ResearchSummary {
  id: string;
  title: string;
  topic: string;
  status: string;
  current_step: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  latest_summary: string | null;
}

export interface ResearchDetail extends ResearchSummary {
  timeframe: string;
  databases: any;
  started_at: string | null;
  latest_error: string | null;
  pipeline_version: string;
}

export interface ResearchMessage {
  id: string;
  role: string;
  content: string;
  message_type: string;
  metadata_extra: Record<string, any> | null;
  created_at: string;
}

export interface CreateResearchRequest {
  topic: string;
  timeframe?: string;
  databases?: string[];
}

export interface Artifact {
  id: string;
  filename: string;
  file_type: string;
  mime_type: string;
  file_size: number;
  description: string | null;
  metadata_extra: Record<string, any> | null;
  created_at: string;
}

export interface Approval {
  id: string;
  run_id: string;
  research_id: string;
  node_name: string;
  approval_type: string;
  status: string;
  request_data: Record<string, any> | null;
  response_data: Record<string, any> | null;
  requested_at: string;
  responded_at: string | null;
  uploaded_file_id?: string | null;
}

export interface NodeExecution {
  id: string;
  run_id: string;
  node_name: string;
  step_label: string | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  output_summary: Record<string, any> | null;
  logs: any;
  error_message: string | null;
}

export const researchApi = {
  async list(skip = 0, limit = 20): Promise<{ items: ResearchSummary[]; total: number }> {
    const res = await client.get('/research', { params: { skip, limit } });
    return res.data;
  },

  async create(data: CreateResearchRequest): Promise<ResearchDetail> {
    const res = await client.post('/research', data);
    return res.data;
  },

  async get(id: string): Promise<ResearchDetail> {
    const res = await client.get(`/research/${id}`);
    return res.data;
  },

  async delete(id: string): Promise<void> {
    await client.delete(`/research/${id}`);
  },

  async getMessages(id: string, skip = 0, limit = 200): Promise<ResearchMessage[]> {
    const res = await client.get(`/research/${id}/messages`, { params: { skip, limit } });
    return res.data;
  },

  async getArtifacts(id: string): Promise<{ items: Artifact[]; total: number }> {
    const res = await client.get(`/artifacts/${id}`);
    return res.data;
  },

  async getApprovals(id: string): Promise<Approval[]> {
    const res = await client.get(`/approvals/${id}`);
    return res.data;
  },

  async uploadApprovalFile(approvalId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post(`/approvals/${approvalId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async respondToApproval(approvalId: string): Promise<Approval> {
    const res = await client.post(`/approvals/${approvalId}/respond`);
    return res.data;
  },

  async startWorkflow(researchId: string): Promise<any> {
    const res = await client.post(`/workflow/${researchId}/start`);
    return res.data;
  },

  async cancelWorkflow(researchId: string): Promise<any> {
    const res = await client.post(`/workflow/${researchId}/cancel`);
    return res.data;
  },

  async getNodeExecutions(researchId: string): Promise<NodeExecution[]> {
    const res = await client.get(`/workflow/${researchId}/nodes`);
    return res.data;
  },

  getArtifactDownloadUrl(artifactId: string): string {
    return `/api/v1/artifacts/${artifactId}/download`;
  },

  async getArtifactPreview(artifactId: string): Promise<any> {
    const res = await client.get(`/artifacts/${artifactId}/preview`);
    return res.data;
  },
};
