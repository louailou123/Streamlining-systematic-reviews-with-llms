import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { researchApi, type ResearchDetail, type ResearchMessage as MessageType, type Approval } from '../api/research';
import { useWorkflowStore } from '../stores/workflowStore';
import {
  Sparkles, Send, Loader2, CheckCircle2, XCircle, PauseCircle, Clock,
  ChevronDown, ChevronRight, FileText, Image, Download, Upload
} from 'lucide-react';

// ── Status Badge ──────────────────────────────────────────

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cls = {
    running: 'badge-running', completed: 'badge-completed', failed: 'badge-failed',
    paused: 'badge-paused', pending: 'badge-pending',
  }[status] || 'badge-pending';
  return <span className={cls}>{status}</span>;
};

// ── Step Progress Bar ──────────────────────────────────────

const STEPS = ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5'];

const StepProgress: React.FC<{ currentStep: string | null; status: string }> = ({ currentStep, status }) => {
  const currentIdx = currentStep
    ? STEPS.findIndex((s) => currentStep.toLowerCase().includes(s.toLowerCase().replace('step ', '')))
    : -1;

  return (
    <div className="flex items-center gap-2 px-4 py-3 border-b border-dark-border bg-dark-surface/50">
      {STEPS.map((step, i) => {
        let dotClass = 'step-dot-pending';
        if (status === 'completed') dotClass = 'step-dot-done';
        else if (status === 'failed' && i === currentIdx) dotClass = 'step-dot-failed';
        else if (i < currentIdx || (i === currentIdx && status !== 'running')) dotClass = 'step-dot-done';
        else if (i === currentIdx) dotClass = 'step-dot-active';

        return (
          <React.Fragment key={step}>
            <div className="flex items-center gap-1.5">
              <div className={dotClass} />
              <span className={`text-xs font-mono ${i <= currentIdx ? 'text-gray-300' : 'text-gray-600'}`}>
                {step}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-px ${i < currentIdx ? 'bg-accent-green/50' : 'bg-dark-border'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

// ── Message Card ───────────────────────────────────────────

const MessageCard: React.FC<{ message: MessageType }> = ({ message }) => {
  const [expanded, setExpanded] = useState(false);

  if (message.role === 'user') {
    return (
      <div className="message-user animate-slide-up">
        <p className="text-sm text-gray-200">{message.content}</p>
        <p className="text-xs text-gray-500 mt-2">
          {new Date(message.created_at).toLocaleTimeString()}
        </p>
      </div>
    );
  }

  // System messages
  const iconMap: Record<string, React.ReactNode> = {
    node_event: <Sparkles className="w-4 h-4 text-accent-blue" />,
    workflow_completed: <CheckCircle2 className="w-4 h-4 text-accent-green" />,
    error: <XCircle className="w-4 h-4 text-accent-rose" />,
    approval: <PauseCircle className="w-4 h-4 text-accent-amber" />,
    text: <Clock className="w-4 h-4 text-gray-400" />,
    artifact: <FileText className="w-4 h-4 text-accent-cyan" />,
  };

  const borderMap: Record<string, string> = {
    workflow_completed: 'border-accent-green/20 bg-accent-green/5',
    error: 'border-accent-rose/20 bg-accent-rose/5',
    approval: 'border-accent-amber/20 bg-accent-amber/5',
  };

  const extraBorder = borderMap[message.message_type] || '';

  return (
    <div className={`message-system animate-slide-up ${extraBorder}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          {iconMap[message.message_type] || iconMap.text}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-200">{message.content}</p>

          {message.metadata_extra && Object.keys(message.metadata_extra).length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 mt-2 transition-colors"
            >
              {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              Details
            </button>
          )}

          {expanded && message.metadata_extra && (
            <pre className="mt-2 p-3 bg-dark-bg/50 rounded-lg text-xs text-gray-400 overflow-auto max-h-48 font-mono">
              {JSON.stringify(message.metadata_extra, null, 2)}
            </pre>
          )}

          <p className="text-xs text-gray-600 mt-2">
            {new Date(message.created_at).toLocaleTimeString()}
          </p>
        </div>
      </div>
    </div>
  );
};

// ── Live Event Card ────────────────────────────────────────

const LiveEventCard: React.FC<{ event: any }> = ({ event }) => {
  const typeColors: Record<string, string> = {
    NODE_STARTED: 'text-accent-blue',
    NODE_COMPLETED: 'text-accent-green',
    NODE_FAILED: 'text-accent-rose',
    ARTIFACT_CREATED: 'text-accent-cyan',
    LOG_MESSAGE: 'text-gray-400',
    APPROVAL_REQUIRED: 'text-accent-amber',
    WORKFLOW_COMPLETED: 'text-accent-green',
    WORKFLOW_FAILED: 'text-accent-rose',
  };

  return (
    <div className="flex items-start gap-2 px-4 py-2 animate-fade-in">
      <div className={`w-1.5 h-1.5 rounded-full mt-1.5 ${
        event.event_type === 'NODE_STARTED' ? 'bg-accent-blue animate-pulse' :
        event.event_type === 'NODE_COMPLETED' ? 'bg-accent-green' :
        event.event_type === 'NODE_FAILED' ? 'bg-accent-rose' :
        'bg-gray-500'
      }`} />
      <div className="flex-1">
        <span className={`text-xs font-mono ${typeColors[event.event_type] || 'text-gray-400'}`}>
          {event.step_label && `[${event.step_label}] `}
          {event.message || event.event_type}
        </span>
      </div>
      <span className="text-xs text-gray-600 font-mono">
        {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}
      </span>
    </div>
  );
};

// ── Approval Action Card ───────────────────────────────────

const ApprovalCard: React.FC<{ approval: Approval; onResume: () => void }> = ({ approval, onResume }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(!!approval.uploaded_file_id);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      await researchApi.uploadApprovalFile(approval.id, file);
      setUploaded(true);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleResume = async () => {
    try {
      await researchApi.respondToApproval(approval.id);
      onResume();
    } catch (err) {
      console.error('Resume failed:', err);
    }
  };

  if (approval.status !== 'pending') return null;

  return (
    <div className="glass-card border-accent-amber/30 bg-accent-amber/5 p-5 animate-slide-up">
      <div className="flex items-center gap-3 mb-3">
        <PauseCircle className="w-5 h-5 text-accent-amber" />
        <h3 className="font-semibold text-gray-100">Manual Review Required</h3>
      </div>

      <p className="text-sm text-gray-300 mb-4">
        Download the ASReview import CSV, screen papers in ASReview LAB, then upload the export CSV to resume the pipeline.
      </p>

      <div className="space-y-3">
        {/* Download button */}
        <button className="btn-ghost flex items-center gap-2 text-sm border border-dark-border">
          <Download className="w-4 h-4" />
          Download ASReview Import CSV
        </button>

        {/* Upload zone */}
        <div className="border-2 border-dashed border-dark-border hover:border-accent-amber/50 rounded-lg p-4 transition-colors">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg
                       file:border-0 file:text-sm file:font-medium file:bg-dark-surface-3 file:text-gray-300
                       hover:file:bg-dark-border file:cursor-pointer"
          />
        </div>

        {file && !uploaded && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="btn-ghost flex items-center gap-2 text-sm border border-accent-amber/30 text-accent-amber"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            Upload {file.name}
          </button>
        )}

        {uploaded && (
          <button
            onClick={handleResume}
            className="btn-primary flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Resume Pipeline
          </button>
        )}
      </div>
    </div>
  );
};

// ── Main Workspace ─────────────────────────────────────────

const ResearchWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [research, setResearch] = useState<ResearchDetail | null>(null);
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { events, connectSSE, disconnectSSE, isRunning } = useWorkflowStore();

  // Fetch data
  useEffect(() => {
    if (!id) return;
    const load = async () => {
      try {
        const [r, msgs, apprs] = await Promise.all([
          researchApi.get(id),
          researchApi.getMessages(id),
          researchApi.getApprovals(id),
        ]);
        setResearch(r);
        setMessages(msgs);
        setApprovals(apprs);
      } catch (err) {
        console.error('Failed to load research:', err);
      } finally {
        setLoading(false);
      }
    };
    load();

    // Connect SSE for live updates
    connectSSE(id);
    return () => disconnectSSE();
  }, [id, connectSSE, disconnectSSE]);

  // Auto-scroll on new messages/events
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, events]);

  // Polling for messages (refresh every 5s while running)
  useEffect(() => {
    if (!id || !isRunning) return;
    const interval = setInterval(async () => {
      try {
        const msgs = await researchApi.getMessages(id);
        setMessages(msgs);
      } catch {}
    }, 5000);
    return () => clearInterval(interval);
  }, [id, isRunning]);

  const handleResume = async () => {
    if (!id) return;
    const [r, msgs, apprs] = await Promise.all([
      researchApi.get(id),
      researchApi.getMessages(id),
      researchApi.getApprovals(id),
    ]);
    setResearch(r);
    setMessages(msgs);
    setApprovals(apprs);
    connectSSE(id);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent-blue animate-spin" />
      </div>
    );
  }

  if (!research) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        Research not found
      </div>
    );
  }

  const pendingApproval = approvals.find((a) => a.status === 'pending');

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-border bg-dark-surface/50 backdrop-blur-sm">
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-semibold text-gray-100 truncate">{research.title}</h2>
          <div className="flex items-center gap-3 mt-1">
            <StatusBadge status={research.status} />
            {research.current_step && (
              <span className="text-xs text-gray-500 font-mono">{research.current_step}</span>
            )}
          </div>
        </div>
      </div>

      {/* Step progress */}
      <StepProgress currentStep={research.current_step} status={research.status} />

      {/* Messages timeline */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {/* Persisted messages */}
        {messages.map((msg) => (
          <MessageCard key={msg.id} message={msg} />
        ))}

        {/* Pending approval card */}
        {pendingApproval && (
          <ApprovalCard approval={pendingApproval} onResume={handleResume} />
        )}

        {/* Live SSE events */}
        {events.length > 0 && (
          <div className="glass-card overflow-hidden">
            <div className="px-4 py-2 bg-dark-surface-2/50 border-b border-dark-border flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-blue animate-pulse" />
              <span className="text-xs font-medium text-gray-400">Live Pipeline Feed</span>
            </div>
            <div className="max-h-64 overflow-y-auto divide-y divide-dark-border/50">
              {events.slice(-20).map((event, i) => (
                <LiveEventCard key={i} event={event} />
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ResearchWorkspace;
