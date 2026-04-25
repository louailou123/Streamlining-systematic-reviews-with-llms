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
  databases: string[] | null;
  started_at: string | null;
  latest_error: string | null;
  pipeline_version: string;
}

export interface ResearchMessage {
  id: string;
  role: string;
  content: string;
  message_type: string;
  metadata_extra: Record<string, unknown> | null;
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
  metadata_extra: Record<string, unknown> | null;
  created_at: string;
}

export interface Approval {
  id: string;
  run_id: string;
  research_id: string;
  node_name: string;
  approval_type: string;
  status: string;
  request_data: Record<string, unknown> | null;
  response_data: Record<string, unknown> | null;
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
  node_order: number;
  attempt_number: number;
  revision_number: number;
  started_at: string;
  completed_at: string | null;
  approved_at: string | null;
  duration_ms: number | null;
  output_summary: Record<string, unknown> | null;
  logs: unknown;
  error_message: string | null;
  feedback_text: string | null;
}

export interface PendingApproval {
  has_pending: boolean;
  approval_id: string | null;
  node_execution_id: string | null;
  node_name: string | null;
  step_label: string | null;
  description: string | null;
  approval_type: string | null;
  output_summary?: Record<string, unknown> | null;
  _source?: 'rest' | 'ws';
  // Extra fields for special approval types
  download_file?: string | null;
  download_description?: string | null;
  asreview_url?: string | null;
  upload_description?: string | null;
}

export interface WorkflowEvent {
  event_type: string;
  research_id: string;
  run_id?: string;
  node_name?: string;
  step_label?: string;
  message?: string;
  data?: Record<string, any>;
  timestamp?: string;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'authenticating' | 'connected';

export type OptimisticNodeAction = 'continue' | 'improve' | 'retry';

export interface UiTimelineItem {
  id: string;
  nodeExecutionId: string;
  nodeName: string;
  stepLabel: string | null;
  title: string;
  status: string;
  summaryLines: string[];
  outputSummary: Record<string, unknown> | null;
  errorMessage: string | null;
  attemptNumber: number;
  revisionNumber: number;
  durationMs: number | null;
  startedAt: string;
  updatedAt: string;
  feedbackText: string | null;
  requiresApproval: boolean;
  isFailed: boolean;
  isCompleted: boolean;
  statusTitle: string;
  statusDescription: string;
  detailLines: string[];
}

export interface WorkspaceNarrative {
  tone: 'info' | 'warning' | 'error' | 'success';
  title: string;
  description: string;
  details: string[];
}
